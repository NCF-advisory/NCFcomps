"""Tests offline de l'export Excel (comparables/export/excel.py)."""
from __future__ import annotations
import io
import math

from openpyxl import load_workbook

from comparables.export.excel import build_excel_bytes, _stats
from comparables.models import CompanyRecord


def _wb(records, warning=None):
    return load_workbook(io.BytesIO(build_excel_bytes(records, warning)))


def test_stats_filtrent_inf_et_nan():
    records = [
        CompanyRecord(ticker="A", ev_ebitda=8.0),
        CompanyRecord(ticker="B", ev_ebitda=12.0),
        CompanyRecord(ticker="C", ev_ebitda=math.inf),
        CompanyRecord(ticker="D", ev_ebitda=math.nan),
        CompanyRecord(ticker="E", ev_ebitda=None),
    ]
    s = _stats(records)["ev_ebitda"]
    assert s == {"Mediane": 10.0, "Moyenne": 10.0, "Minimum": 8.0, "Maximum": 12.0}


def test_stats_champ_sans_valeur_finie_absent():
    records = [CompanyRecord(ticker="A", pb=math.inf), CompanyRecord(ticker="B")]
    assert "pb" not in _stats(records)


def test_workbook_montants_en_millions_et_nd():
    records = [CompanyRecord(ticker="WMS", name="ADS", market_cap=2_500_000_000.0)]
    ws = _wb(records)["Comparables"]
    # Ligne de donnees = header_row(4) + 1 ; market_cap est la colonne 6 (cf. DISPLAY).
    assert ws.cell(row=5, column=6).value == 2_500.0
    # Champ absent -> "n.d." (net_debt, colonne 7).
    assert ws.cell(row=5, column=7).value == "n.d."


def test_workbook_ligne_mediane_filtre_inf():
    records = [
        CompanyRecord(ticker="A", beta_regression=1.0),
        CompanyRecord(ticker="B", beta_regression=2.0),
        CompanyRecord(ticker="C", beta_regression=math.inf),
    ]
    ws = _wb(records)["Comparables"]
    # Stats : ligne vide puis Mediane/Moyenne/Min/Max apres les 3 lignes de donnees.
    labels = {ws.cell(row=r, column=1).value: r for r in range(8, 13)}
    r_med = labels["Mediane"]
    # beta_regression est la colonne 11 (cf. DISPLAY).
    assert ws.cell(row=r_med, column=11).value == 1.5
    assert ws.cell(row=labels["Maximum"], column=11).value == 2.0
