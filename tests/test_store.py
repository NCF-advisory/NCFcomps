"""Tests de la persistance SQLite des analyses (comparables.store)."""
from __future__ import annotations

from comparables import store
from comparables.models import CompanyRecord


def _records() -> list[CompanyRecord]:
    return [
        CompanyRecord(ticker="AAPL", name="Apple", market_cap=3.0e12, ev_ebitda=22.5,
                      beta_regression=1.21, currency="USD"),
        CompanyRecord(ticker="OR.PA", name="L'Oreal", ev_ebitda=18.0, currency="EUR"),
    ]


def test_save_and_load_round_trip(tmp_path):
    db = str(tmp_path / "history.sqlite")
    recs = _records()
    run_id = store.save_run(recs, username="coullion", label="Lux",
                            params={"tax_rate": 0.25, "period": "5y"}, db_path=db)
    assert isinstance(run_id, int)

    loaded = store.load_run(run_id, db_path=db)
    assert [r.ticker for r in loaded] == ["AAPL", "OR.PA"]
    assert loaded[0].name == "Apple" and loaded[0].ev_ebitda == 22.5
    assert loaded[0].market_cap == 3.0e12 and loaded[0].currency == "USD"


def test_list_runs_orders_recent_first(tmp_path):
    db = str(tmp_path / "history.sqlite")
    id1 = store.save_run(_records(), username="a", label="run1", db_path=db)
    id2 = store.save_run(_records(), username="b", label="run2", db_path=db)
    runs = store.list_runs(db_path=db)
    assert [r["id"] for r in runs] == [id2, id1]            # plus recent d'abord
    assert runs[0]["label"] == "run2" and runs[0]["username"] == "b"
    assert runs[0]["n_records"] == 2
    assert runs[1]["params"] == {}                          # params absents -> dict vide


def test_params_round_trip(tmp_path):
    db = str(tmp_path / "history.sqlite")
    rid = store.save_run(_records(), params={"tickers": ["AAPL", "OR.PA"], "tax_rate": 0.3},
                         db_path=db)
    run = next(r for r in store.list_runs(db_path=db) if r["id"] == rid)
    assert run["params"]["tax_rate"] == 0.3
    assert run["params"]["tickers"] == ["AAPL", "OR.PA"]


def test_delete_run(tmp_path):
    db = str(tmp_path / "history.sqlite")
    rid = store.save_run(_records(), db_path=db)
    store.delete_run(rid, db_path=db)
    assert store.list_runs(db_path=db) == []
    assert store.load_run(rid, db_path=db) == []


def test_load_unknown_run_is_empty(tmp_path):
    db = str(tmp_path / "history.sqlite")
    assert store.load_run(999, db_path=db) == []


# --- Base sectorielle ---

def _sector_records() -> list[CompanyRecord]:
    return [
        CompanyRecord(ticker="AAPL", name="Apple", sector="Technology", country="US",
                      beta_unlevered=1.0, ev_ebitda=20.0),
        CompanyRecord(ticker="MSFT", name="Microsoft", sector="Technology", country="US",
                      beta_unlevered=1.2, ev_ebitda=24.0),
        CompanyRecord(ticker="OR.PA", name="L'Oreal", sector="Consumer Defensive",
                      country="FR", beta_unlevered=0.8, ev_ebitda=18.0),
        CompanyRecord(ticker="NOSEC", name="Sans secteur", ev_ebitda=10.0),   # ignoré
    ]


def test_sector_aggregates(tmp_path):
    db = str(tmp_path / "h.sqlite")
    store.save_run(_sector_records(), db_path=db)
    aggs = store.sector_aggregates(db_path=db)

    assert [a["sector"] for a in aggs] == ["Consumer Defensive", "Technology"]  # trié, sans vide
    tech = next(a for a in aggs if a["sector"] == "Technology")
    assert tech["n_companies"] == 2 and tech["n_records"] == 2
    assert tech["metrics"]["beta_unlevered"]["median"] == 1.1     # median(1.0, 1.2)
    assert tech["metrics"]["ev_ebitda"]["median"] == 22.0         # median(20, 24)
    assert tech["metrics"]["beta_unlevered"]["n"] == 2


def test_sector_aggregates_compte_les_occurrences(tmp_path):
    """Même société dans 2 runs = 2 points, mais 1 société distincte."""
    db = str(tmp_path / "h.sqlite")
    store.save_run([CompanyRecord(ticker="AAPL", sector="Technology", beta_unlevered=1.0)], db_path=db)
    store.save_run([CompanyRecord(ticker="AAPL", sector="Technology", beta_unlevered=1.4)], db_path=db)
    tech = next(a for a in store.sector_aggregates(db_path=db) if a["sector"] == "Technology")
    assert tech["n_records"] == 2
    assert tech["n_companies"] == 1
    assert tech["metrics"]["beta_unlevered"]["median"] == 1.2     # median(1.0, 1.4)


def test_sector_metric_absent_si_aucune_valeur(tmp_path):
    db = str(tmp_path / "h.sqlite")
    store.save_run([CompanyRecord(ticker="X", sector="Energy", ev_ebitda=9.0)], db_path=db)
    energy = next(a for a in store.sector_aggregates(db_path=db) if a["sector"] == "Energy")
    assert "ev_ebitda" in energy["metrics"]
    assert "beta_unlevered" not in energy["metrics"]              # aucune valeur -> absente


def test_sector_records_detail(tmp_path):
    db = str(tmp_path / "h.sqlite")
    store.save_run(_sector_records(), label="Lux", db_path=db)
    recs = store.sector_records("technology", db_path=db)         # casse ignorée
    assert {r["ticker"] for r in recs} == {"AAPL", "MSFT"}
    assert all(r["label"] == "Lux" for r in recs)
    assert recs[0]["beta_unlevered"] is not None


def test_sector_aggregates_vide(tmp_path):
    db = str(tmp_path / "h.sqlite")
    assert store.sector_aggregates(db_path=db) == []
    assert store.sector_records("Technology", db_path=db) == []
