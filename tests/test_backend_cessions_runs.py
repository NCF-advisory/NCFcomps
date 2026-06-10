"""Tests des endpoints cessions FR et historique des runs. Aucun réseau."""
from __future__ import annotations

import time

from fastapi.testclient import TestClient

from backend.main import create_app
from comparables.config import settings
from comparables.fr import pipeline as fr_pipeline
from comparables.fr.models import Cession


def _client(monkeypatch) -> TestClient:
    monkeypatch.setattr(settings, "auth_enabled", False)
    return TestClient(create_app())


def _wait_done(client: TestClient, url: str, timeout: float = 10.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        payload = client.get(url).json()
        if payload["status"] in ("done", "error"):
            return payload
        time.sleep(0.05)
    raise AssertionError(f"Job toujours en cours après {timeout}s")


# --- Cessions FR ---

def test_job_cessions_complet(monkeypatch):
    cessions = [
        Cession(siren="111222333", nom="BOULANGERIE A", prix=150000.0, ca=200000.0,
                ebe=40000.0, pct_ca=0.75, mult_ebe=3.75, naf="10.71C", date="2025-01-15"),
        Cession(siren="444555666", nom="BOULANGERIE B", prix=90000.0, ca=120000.0,
                ebe=25000.0, pct_ca=0.75, mult_ebe=3.6, naf="10.71C", date="2024-11-02"),
    ]
    monkeypatch.setattr(fr_pipeline, "build_cessions",
                        lambda **kwargs: cessions)
    client = _client(monkeypatch)

    r = client.post("/api/cessions/jobs",
                    json={"contains": "boulangerie", "departement": "75", "limit": 50})
    assert r.status_code == 202
    job = r.json()
    assert job["kind"] == "cessions"
    assert job["params"]["contains"] == "boulangerie"

    done = _wait_done(client, f"/api/cessions/jobs/{job['id']}")
    assert done["status"] == "done"
    assert len(done["cessions"]) == 2
    assert done["summary"]["overall"]["n_total"] == 2
    assert abs(done["summary"]["overall"]["median_pct_ca"] - 0.75) < 1e-9
    assert done["summary"]["by_activite"][0]["naf"] == "10.71C"


def test_job_cessions_kind_isole(monkeypatch):
    """Un job comparables n'est pas visible via l'endpoint cessions (et inversement)."""
    monkeypatch.setattr(fr_pipeline, "build_cessions", lambda **kwargs: [])
    client = _client(monkeypatch)
    job = client.post("/api/cessions/jobs", json={"limit": 5}).json()
    _wait_done(client, f"/api/cessions/jobs/{job['id']}")
    assert client.get(f"/api/comparables/jobs/{job['id']}").status_code == 404


def test_cessions_limit_borne(monkeypatch):
    client = _client(monkeypatch)
    assert client.post("/api/cessions/jobs", json={"limit": 9999}).status_code == 422


# --- Runs (historique) ---

def _records_json() -> list[dict]:
    return [{"ticker": "WMS", "market_cap": 1e9, "ev_ebitda": 8.5},
            {"ticker": "MWA", "market_cap": 2e9, "ev_ebitda": 10.0}]


def test_runs_cycle_complet(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "history_db_path", str(tmp_path / "history.sqlite"))
    client = _client(monkeypatch)

    # Sauvegarde
    r = client.post("/api/runs", json={"records": _records_json(),
                                       "label": "Test", "params": {"tax_rate": 0.25}})
    assert r.status_code == 201
    run_id = r.json()["id"]

    # Liste (utilisateur 'dev' car auth désactivée)
    runs = client.get("/api/runs").json()["runs"]
    assert len(runs) == 1
    assert runs[0]["label"] == "Test" and runs[0]["username"] == "dev"
    assert runs[0]["n_records"] == 2

    # Rechargement
    loaded = client.get(f"/api/runs/{run_id}").json()
    assert [rec["ticker"] for rec in loaded["records"]] == ["WMS", "MWA"]

    # Ré-export Excel
    x = client.get(f"/api/runs/{run_id}/export")
    assert x.status_code == 200 and x.content[:2] == b"PK"

    # Suppression
    assert client.delete(f"/api/runs/{run_id}").status_code == 204
    assert client.get(f"/api/runs/{run_id}").status_code == 404


def test_run_inconnu_404(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "history_db_path", str(tmp_path / "history.sqlite"))
    client = _client(monkeypatch)
    assert client.get("/api/runs/999").status_code == 404
    assert client.get("/api/runs/999/export").status_code == 404


def test_run_vide_rejete(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "history_db_path", str(tmp_path / "history.sqlite"))
    client = _client(monkeypatch)
    assert client.post("/api/runs", json={"records": []}).status_code == 422


def test_endpoints_proteges_sans_auth(monkeypatch):
    """Auth activée + pas de cookie -> 401 sur les endpoints métier."""
    monkeypatch.setattr(settings, "auth_enabled", True)
    monkeypatch.setattr(settings, "auth_cookie_key", "cle-de-test")
    client = TestClient(create_app())
    assert client.get("/api/runs").status_code == 401
    assert client.post("/api/comparables/jobs", json={"tickers": ["WMS"]}).status_code == 401
    assert client.post("/api/cessions/jobs", json={}).status_code == 401
