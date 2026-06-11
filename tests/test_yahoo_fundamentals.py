"""Tests des helpers purs de l'adaptateur Yahoo (sanitization, lecture des états).

Sans réseau : _positive et _pick_row sont purs ; _fill_gaps est exercé avec un
faux Ticker (fast_info / income_stmt / balance_sheet contrôlés).
"""
from __future__ import annotations

import pandas as pd

from comparables.models import CompanyRecord
from comparables.sources import yahoo


# --- _positive : filtre des multiples pré-calculés ---

def test_positive_filtre_negatifs_et_non_finis():
    assert yahoo._positive(12.5) == 12.5
    assert yahoo._positive(-4.2) is None          # EBITDA negatif -> multiple sans objet
    assert yahoo._positive(0) is None
    assert yahoo._positive(None) is None
    assert yahoo._positive(float("nan")) is None
    assert yahoo._positive(float("inf")) is None
    assert yahoo._positive("Infinity") is None    # Yahoo renvoie parfois des chaines


# --- _pick_row : lecture d'un état financier yfinance ---

def _stmt(rows: dict[str, list]) -> pd.DataFrame:
    cols = pd.to_datetime(["2024-12-31", "2023-12-31"])
    return pd.DataFrame.from_dict(rows, orient="index", columns=cols)


def test_pick_row_premier_libelle_disponible():
    df = _stmt({"Total Revenue": [100.0, 90.0], "EBITDA": [20.0, 18.0]})
    assert yahoo._pick_row(df, ("Total Revenue", "Operating Revenue")) == 100.0
    assert yahoo._pick_row(df, ("Operating Revenue", "Total Revenue")) == 100.0  # fallback
    assert yahoo._pick_row(df, ("Absent",)) is None


def test_pick_row_saute_les_exercices_vides():
    df = _stmt({"EBITDA": [float("nan"), 18.0]})
    assert yahoo._pick_row(df, ("EBITDA",)) == 18.0      # le plus recent non vide


def test_pick_row_df_vide_ou_none():
    assert yahoo._pick_row(None, ("X",)) is None
    assert yahoo._pick_row(pd.DataFrame(), ("X",)) is None


# --- _fill_gaps : comblement depuis fast_info / états financiers ---

class _FakeFastInfo:
    def __init__(self, data):
        self._data = data

    def __getitem__(self, key):
        return self._data[key]


class _FakeTicker:
    def __init__(self, fast=None, stmt=None, bs=None):
        self._fast, self._stmt, self._bs = fast, stmt, bs

    @property
    def fast_info(self):
        if self._fast is None:
            raise RuntimeError("indisponible")
        return _FakeFastInfo(self._fast)

    @property
    def income_stmt(self):
        return self._stmt

    @property
    def balance_sheet(self):
        return self._bs


def test_fill_gaps_complete_les_champs_absents():
    tk = _FakeTicker(
        fast={"marketCap": 500.0, "currency": "EUR"},
        stmt=_stmt({"Total Revenue": [100.0, 90.0], "EBITDA": [20.0, 18.0]}),
        bs=_stmt({"Total Debt": [60.0, 55.0],
                  "Cash And Cash Equivalents": [10.0, 12.0]}),
    )
    rec = CompanyRecord(ticker="X")
    yahoo._fill_gaps(tk, rec)
    assert rec.market_cap == 500.0 and rec.currency == "EUR"
    assert rec.revenue == 100.0 and rec.ebitda == 20.0
    assert rec.total_debt == 60.0 and rec.total_cash == 10.0


def test_fill_gaps_ne_touche_pas_aux_champs_presents():
    tk = _FakeTicker(fast={"marketCap": 999.0, "currency": "USD"},
                     stmt=_stmt({"Total Revenue": [999.0, 888.0]}))
    rec = CompanyRecord(ticker="X", market_cap=500.0, currency="EUR",
                        revenue=100.0, ebitda=20.0, total_debt=60.0, total_cash=10.0)
    yahoo._fill_gaps(tk, rec)
    assert rec.market_cap == 500.0 and rec.currency == "EUR"      # inchangés
    assert rec.revenue == 100.0


def test_fill_gaps_tolere_les_echecs():
    rec = CompanyRecord(ticker="X")
    yahoo._fill_gaps(_FakeTicker(), rec)          # tout indisponible -> aucun crash
    assert rec.market_cap is None and rec.revenue is None and rec.total_debt is None
