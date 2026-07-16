"""Tests du referentiel Damodaran embarque (snapshot CSV, sans reseau)."""
from __future__ import annotations

from comparables import damodaran


def test_snapshot_charge_et_contient_les_secteurs_cles():
    inds = damodaran.industries("Global")
    assert len(inds) > 50
    noms = {r["industry"] for r in inds}
    assert {"Steel", "Metals & Mining", "Machinery"} <= noms
    assert damodaran.as_of("Global")          # date de mise a jour presente


def test_lookup_renvoie_le_beta_desendette():
    steel = damodaran.lookup("Steel")
    assert steel is not None
    assert steel["n_firms"] and steel["n_firms"] > 0
    assert 0.0 < steel["unlevered_beta"] < 3.0
    assert steel["unlevered_beta_cash"] is not None
    # insensible a la casse / aux espaces
    assert damodaran.lookup("  steel ") == steel
    assert damodaran.lookup("Inexistant zzz") is None


def test_suggest_industry_vote_majoritaire_et_alias():
    # vote majoritaire
    assert damodaran.suggest_industry(["Steel", "Steel", "Aluminum"]) == "Steel"
    # alias Yahoo -> Damodaran (Aluminum n'existe pas chez Damodaran -> Metals & Mining)
    assert damodaran.suggest_industry(["Aluminum"]) == "Metals & Mining"
    # rien d'exploitable
    assert damodaran.suggest_industry([]) is None
    assert damodaran.suggest_industry([None, ""]) is None
    assert damodaran.suggest_industry(["secteur totalement inconnu zzz"]) is None


def test_best_industry_exact_alias_et_flou():
    assert damodaran._best_industry("Steel", "Global") == "Steel"            # exact
    assert damodaran._best_industry("Specialty Industrial Machinery",
                                    "Global") == "Machinery"                  # alias
    # ressemblance : un libelle proche retombe sur l'industrie Damodaran
    assert damodaran._best_industry("Steels", "Global") == "Steel"


def test_toutes_les_cibles_alias_existent():
    # garde-fou : chaque valeur de la table d'alias doit pointer un secteur Damodaran reel.
    for target in set(damodaran._ALIAS.values()):
        assert damodaran.lookup(target) is not None, f"cible alias inconnue: {target}"


def test_mapping_des_industries_yahoo_reelles():
    # les industries Yahoo vues dans les tests reels -> bon secteur Damodaran.
    cases = {
        "Luxury Goods": "Apparel",
        "Airlines": "Air Transport",
        "REIT - Retail": "R.E.I.T.",
        "REIT - Office": "R.E.I.T.",
        "Beverages - Brewers": "Beverage (Alcoholic)",
        "Beverages - Wineries & Distilleries": "Beverage (Alcoholic)",
        "Drug Manufacturers - General": "Drugs (Pharmaceutical)",
        "Oil & Gas Integrated": "Oil/Gas (Integrated)",
        "Gold": "Precious Metals",              # Damodaran separe l'or des metaux de base
        "Aluminum": "Metals & Mining",
        "Semiconductors": "Semiconductor",
        "Banks - Regional": "Banks (Regional)",
    }
    for yahoo_ind, dam in cases.items():
        assert damodaran._best_industry(yahoo_ind, "Global") == dam, yahoo_ind


def test_pas_de_rattachement_hasardeux():
    # le fuzzy conservateur (0,8) refuse plutot que de rattacher a tort
    # (regression : « REIT - Retail » tombait sur « Precious Metals »).
    assert damodaran._best_industry("REIT - Retail", "Global") != "Precious Metals"
    assert damodaran._best_industry("Totally Unrelated Widget Co", "Global") is None
    assert damodaran.suggest_industry(["Luxury Goods", "Luxury Goods", "Apparel Manufacturing"]) == "Apparel"
