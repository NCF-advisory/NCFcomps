"""Tests des référentiels locaux (Sirene + ratios BCE) : chargement et lookups, sans réseau."""
from __future__ import annotations

from comparables.fr import referentiels


def _db(tmp_path) -> str:
    return str(tmp_path / "ref.sqlite")


def test_load_et_lookup_sirene(tmp_path):
    db = _db(tmp_path)
    n = referentiels.load_sirene_rows([
        {"siren": "111111111", "denominationUniteLegale": "ALPHA SAS",
         "activitePrincipaleUniteLegale": "62.02A"},
        # Personne physique : nom + prénom, pas de dénomination.
        {"siren": "222222222", "denominationUniteLegale": "",
         "nomUniteLegale": "DURAND", "prenom1UniteLegale": "MARIE",
         "activitePrincipaleUniteLegale": "10.71C"},
        {"siren": "", "denominationUniteLegale": "SANS SIREN"},     # ignorée
    ], db_path=db)
    assert n == 2
    assert referentiels.available("unites_legales", db_path=db)
    assert referentiels.lookup_company("111111111", db_path=db) == {
        "nom": "ALPHA SAS", "naf": "62.02A", "ca": None, "ca_annee": None}
    assert referentiels.lookup_company("222222222", db_path=db)["nom"] == "MARIE DURAND"
    assert referentiels.lookup_company("999999999", db_path=db) is None


def test_load_et_lookup_ratios(tmp_path):
    db = _db(tmp_path)
    n = referentiels.load_ratios_rows([
        {"siren": "111111111", "date_cloture_exercice": "2021-12-31",
         "chiffre_d_affaires": "180000", "ebe": "28000", "ebit": "22000"},
        {"siren": "111111111", "date_cloture_exercice": "2022-12-31",
         "chiffre_d_affaires": "200000.5", "ebe": "", "ebit": "abc"},  # vides/invalides
        {"siren": "", "date_cloture_exercice": "2022-12-31"},          # ignorée
    ], db_path=db)
    assert n == 2
    assert referentiels.available("ratios", db_path=db)
    fins = referentiels.lookup_financials("111111111", db_path=db)
    assert [f["date_cloture_exercice"] for f in fins] == ["2022-12-31", "2021-12-31"]
    assert fins[0]["chiffre_d_affaires"] == 200000.5
    assert fins[0]["ebe"] is None and fins[0]["ebit"] is None        # champs invalides -> None
    assert fins[1]["ebe"] == 28000.0
    assert referentiels.lookup_financials("999999999", db_path=db) == []


def test_disponibilite_sans_base(tmp_path):
    db = str(tmp_path / "absente.sqlite")
    assert not referentiels.available("unites_legales", db_path=db)
    assert not referentiels.available("ratios", db_path=db)
    assert referentiels.status(db_path=db) == {}


def test_lookups_base_indisponible_ne_levent_pas(tmp_path):
    """Base absente (ou verrouillée par un refresh) : None, jamais d'exception —
    le pipeline retombe alors sur les API unitaires."""
    db = str(tmp_path / "absente.sqlite")
    assert referentiels.lookup_company("111111111", db_path=db) is None
    assert referentiels.lookup_financials("111111111", db_path=db) is None


def test_rechargement_remplace_la_table(tmp_path):
    db = _db(tmp_path)
    referentiels.load_sirene_rows(
        [{"siren": "111111111", "denominationUniteLegale": "ANCIENNE"}], db_path=db)
    referentiels.load_sirene_rows(
        [{"siren": "333333333", "denominationUniteLegale": "NOUVELLE"}], db_path=db)
    assert referentiels.lookup_company("111111111", db_path=db) is None
    assert referentiels.lookup_company("333333333", db_path=db)["nom"] == "NOUVELLE"
    assert referentiels.status(db_path=db)["unites_legales"]["n_rows"] == 1
