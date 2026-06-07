"""Tests du parsing de l'API Recherche d'entreprises (sans réseau)."""
from __future__ import annotations

from comparables.fr import entreprises as e


def test_latest_ca_picks_most_recent_positive():
    fin = {"2021": {"ca": 100000, "resultat_net": 1}, "2023": {"ca": 250000}, "2022": {"ca": 0}}
    ca, year = e.latest_ca(fin)
    assert ca == 250000.0 and year == 2023


def test_latest_ca_ignores_zero_and_null():
    assert e.latest_ca({"2024": {"ca": 0}}) == (None, None)       # holding -> 0
    assert e.latest_ca(None) == (None, None)                      # comptes confidentiels
    assert e.latest_ca({}) == (None, None)


def test_parse_company():
    result = {"nom_complet": "LE SLIP FRANCAIS", "activite_principale": "47.91B",
              "finances": {"2023": {"ca": 18754140, "resultat_net": -1692858}}}
    info = e.parse_company(result)
    assert info["nom"] == "LE SLIP FRANCAIS"
    assert info["naf"] == "47.91B"
    assert info["ca"] == 18754140.0 and info["ca_annee"] == 2023
