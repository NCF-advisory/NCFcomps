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
