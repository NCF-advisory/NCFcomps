"""Tests des endpoints comparables (jobs, stats de sélection, résolution, export).

Aucun réseau : sources factices injectées dans le pipeline (cf. test_pipeline) et
auth désactivée. Les jobs tournent dans les threads du JobManager -> petite boucle
d'attente bornée.
"""
from __future__ import annotations

import math
import time

from fastapi.testclient import TestClient

from backend.main import create_app
from comparables import pipeline
from comparables.config import settings
from comparables.models import CompanyRecord
from tests.test_pipeline import FakeSource, _price_series


def _client(monkeypatch) -> TestClient:
    monkeypatch.setattr(settings, "auth_enabled", False)
    return TestClient(create_app())


def _patch_pipeline(monkeypatch) -> None:
    rec = CompanyRecord(ticker="X", market_cap=100.0, total_debt=40.0,
                        total_cash=10.0, revenue=50.0, ebitda=20.0)

    def fund_for(ticker: str):
        return FakeSource(record=rec.model_copy(update={"ticker": ticker}))

    monkeypatch.setattr(pipeline, "fundamentals_source_for", fund_for)
    monkeypatch.setattr(pipeline, "price_source_for",
                        lambda ticker: FakeSource(prices=_price_series(7)))


def _wait_done(client: TestClient, url: str, timeout: float = 10.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        payload = client.get(url).json()
        if payload["status"] in ("done", "error"):
            return payload
        time.sleep(0.05)
    raise AssertionError(f"Job toujours en cours après {timeout}s")


def test_job_comparables_complet(monkeypatch):
    _patch_pipeline(monkeypatch)
    client = _client(monkeypatch)

    r = client.post("/api/comparables/jobs",
                    json={"tickers": [" wms ", "gf.sw"], "tax_rate": 0.25})
    assert r.status_code == 202
    job = r.json()
    assert job["kind"] == "comparables"
    assert job["params"]["tickers"] == ["WMS", "GF.SW"]    # strip + upper

    done = _wait_done(client, f"/api/comparables/jobs/{job['id']}")
    assert done["status"] == "done"
    assert done["progress"] == 2 and done["total"] == 2
    assert [rec["ticker"] for rec in done["records"]] == ["WMS", "GF.SW"]
    assert done["records"][0]["net_debt"] == 30.0
    assert done["coverage"]["WMS"] == "ok"
    assert "ev_ebitda" in done["stats"]


def test_job_inconnu_404(monkeypatch):
    client = _client(monkeypatch)
    assert client.get("/api/comparables/jobs/inexistant").status_code == 404


def test_tax_rate_hors_bornes_rejete(monkeypatch):
    client = _client(monkeypatch)
    r = client.post("/api/comparables/jobs", json={"tickers": ["WMS"], "tax_rate": 1.5})
    assert r.status_code == 422                      # garde 0 <= IS < 1


def test_stats_sur_selection_sans_refetch(monkeypatch):
    """Exclure un comparable = renvoyer le sous-ensemble ; stats recalculées, zéro réseau."""
    client = _client(monkeypatch)
    recs = [
        {"ticker": "A", "ev_ebitda": 8.0},
        {"ticker": "B", "ev_ebitda": 12.0},
        {"ticker": "C", "ev_ebitda": None},          # ligne sans donnée : ignorée des stats
    ]
    r = client.post("/api/comparables/stats", json={"records": recs})
    assert r.status_code == 200
    body = r.json()
    assert body["n"] == 3
    assert body["stats"]["ev_ebitda"]["median"] == 10.0

    r2 = client.post("/api/comparables/stats", json={"records": recs[:1]})
    assert r2.json()["stats"]["ev_ebitda"]["median"] == 8.0


def test_record_avec_inf_serialise_en_none(monkeypatch):
    """Un inf venu de Yahoo ne doit pas faire planter la réponse JSON (allow_nan=False)."""
    from backend.routers.comparables import _records_payload
    payload = _records_payload([CompanyRecord(ticker="A", ev_ebitda=math.inf, pb=2.0)])
    assert payload["records"][0]["ev_ebitda"] is None    # inf -> None dans le JSON
    assert payload["records"][0]["pb"] == 2.0
    assert "ev_ebitda" not in payload["stats"]           # et exclu des stats


def test_resolve_names(monkeypatch):
    from backend.routers import comparables as router_mod
    monkeypatch.setattr(router_mod.yahoo, "best_symbol",
                        lambda name: {"symbol": "MC.PA", "name": "LVMH", "exchange": "PAR"})
    client = _client(monkeypatch)
    r = client.post("/api/comparables/resolve", json={"names": ["LVMH"]})
    assert r.status_code == 200
    assert r.json()["results"][0]["match"]["symbol"] == "MC.PA"


def test_export_excel(monkeypatch):
    client = _client(monkeypatch)
    r = client.post("/api/comparables/export",
                    json={"records": [{"ticker": "WMS", "market_cap": 1e9}]})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert r.content[:2] == b"PK"                    # signature zip d'un .xlsx


def test_stats_excluent_les_betas_faible_r2(monkeypatch):
    """R2 < seuil : beta hors mediane/moyenne ET synthese beta_summary coherente."""
    monkeypatch.setattr(settings, "beta_min_r2", 0.10)
    client = _client(monkeypatch)

    records = [
        {"ticker": "A", "beta_regression": 1.2, "r2": 0.40, "beta_unlevered": 0.9},
        {"ticker": "B", "beta_regression": 0.8, "r2": 0.20, "beta_unlevered": 0.7},
        {"ticker": "C", "beta_regression": 9.0, "r2": 0.03, "beta_unlevered": 8.0},  # ecarte
    ]
    r = client.post("/api/comparables/stats", json={"records": records})
    assert r.status_code == 200
    payload = r.json()

    # mediane/moyenne du beta de regression : sans le 9.0 au R2 quasi nul
    assert abs(payload["stats"]["beta_regression"]["median"] - 1.0) < 1e-9
    assert abs(payload["stats"]["beta_regression"]["mean"] - 1.0) < 1e-9
    assert abs(payload["stats"]["beta_unlevered"]["mean"] - 0.8) < 1e-9
    # le R2 lui-meme reste decrit sur tout l'echantillon (qualite globale)
    assert abs(payload["stats"]["r2"]["min"] - 0.03) < 1e-9

    s = payload["beta_summary"]
    assert s["n_retained"] == 2 and s["n_excluded_low_r2"] == 1
    assert abs(s["mean_levered"] - 1.0) < 1e-9
    assert abs(s["mean_adjusted"] - 1.0) < 1e-9              # Blume(1.0) = 1.0
    assert s["min_r2"] == 0.10
