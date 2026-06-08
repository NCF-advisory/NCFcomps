"""Tests de la sélection d'exercice (finances INPI), sans réseau."""
from __future__ import annotations

from comparables.fr import finances_inpi as f

FIN = [
    {"date_cloture_exercice": "2024-12-31", "chiffre_d_affaires": 250000, "ebe": 40000},
    {"date_cloture_exercice": "2023-12-31", "chiffre_d_affaires": 200000, "ebe": 30000},
    {"date_cloture_exercice": "2022-12-31", "chiffre_d_affaires": 180000, "ebe": 0},
]


def test_pick_exercice_clos_avant_la_cession():
    r = f.pick_for_date(FIN, "2024-06-01")           # dernier clos avant -> 2023
    assert r["date_cloture_exercice"] == "2023-12-31"
    assert r["chiffre_d_affaires"] == 200000


def test_pick_plus_recent_si_tous_apres():
    r = f.pick_for_date(FIN, "2020-01-01")           # tous postérieurs -> plus récent dispo
    assert r["date_cloture_exercice"] == "2024-12-31"


def test_pick_ignore_ca_non_positif():
    only_zero = [{"date_cloture_exercice": "2022-12-31", "chiffre_d_affaires": 0}]
    assert f.pick_for_date(only_zero, "2024-01-01") is None


def test_pick_sans_date_prend_plus_recent():
    r = f.pick_for_date(FIN, None)
    assert r["date_cloture_exercice"] == "2024-12-31"


def test_pick_liste_vide():
    assert f.pick_for_date([], "2024-01-01") is None


def test_pick_financials_accepts_ebe_without_ca():
    # Exercice sans CA mais avec EBE > 0 : retenu par pick_financials (pas par pick_for_date).
    fin = [{"date_cloture_exercice": "2023-12-31", "chiffre_d_affaires": 0, "ebe": 25000}]
    assert f.pick_for_date(fin, "2024-06-01") is None            # CA seul -> rien
    r = f.pick_financials(fin, "2024-06-01")
    assert r is not None and r["ebe"] == 25000


def test_pick_financials_prefers_exercice_before_cession():
    r = f.pick_financials(FIN, "2024-06-01")
    assert r["date_cloture_exercice"] == "2023-12-31"            # même logique de date que pick_for_date


def test_pick_financials_rejette_sans_ca_ni_ebe():
    fin = [{"date_cloture_exercice": "2023-12-31", "chiffre_d_affaires": 0, "ebe": 0}]
    assert f.pick_financials(fin, "2024-06-01") is None
