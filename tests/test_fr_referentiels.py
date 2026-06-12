"""Tests des référentiels locaux (Sirene + ratios BCE + ventes BODACC), sans réseau."""
from __future__ import annotations

import json

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


def _vente_csv_row(siren: str, prix: str, date: str, nom: str = "BOULANGERIE X",
                   typeavis: str = "annonce", descriptif: str | None = None) -> dict:
    """Ligne telle que sortie par l'export CSV (champ acte = JSON sérialisé)."""
    desc = descriptif or (f"Vente de fonds moyennant le prix de {prix} euros. "
                          f"Cédant immatriculé {siren}.")
    return {
        "registre": f"{siren},{siren[:3]} {siren[3:6]} {siren[6:]}",
        "commercant": nom, "ville": "PARIS", "numerodepartement": "75",
        "dateparution": date, "typeavis": typeavis,
        "acte": json.dumps({"descriptif": desc, "vente": {"categorieVente": "Vente"}}),
        "url_complete": f"https://bodacc.example/{siren}",
    }


def test_load_ventes_extraction_et_dedup(tmp_path):
    db = _db(tmp_path)
    n = referentiels.load_ventes_rows([
        _vente_csv_row("111222333", "150 000,00", "2024-03-01"),
        _vente_csv_row("111222333", "150 000,00", "2024-03-08"),   # republication -> dédupliquée
        _vente_csv_row("111222333", "150 000,00", "2021-05-01"),   # autre année -> conservée
        _vente_csv_row("444555666", "80 000,00", "2024-06-01", typeavis="Rectificatif"),
        _vente_csv_row("777888999", "0,00", "2024-06-01",          # prix non extractible
                       descriptif="Vente de fonds, prix non communiqué."),
    ], db_path=db)
    assert n == 2
    assert referentiels.available("ventes", db_path=db)
    ventes = referentiels.lookup_ventes(since="2020-01-01", db_path=db)
    assert [v["date"] for v in ventes] == ["2024-03-01", "2021-05-01"]   # plus récent d'abord
    assert ventes[0]["siren"] == "111222333" and ventes[0]["prix"] == 150000.0


def test_lookup_ventes_jointure_sirene_et_filtres(tmp_path):
    db = _db(tmp_path)
    referentiels.load_sirene_rows([
        {"siren": "111222333", "denominationUniteLegale": "MENUISERIE ALPHA",
         "activitePrincipaleUniteLegale": "43.32A"},
    ], db_path=db)
    referentiels.load_ventes_rows([
        _vente_csv_row("111222333", "150 000,00", "2024-03-01"),
        _vente_csv_row("999000111", "60 000,00", "2024-04-01"),    # absent de Sirene
        _vente_csv_row("111222333", "70 000,00", "2018-01-01"),    # hors fenêtre
    ], db_path=db)
    ventes = referentiels.lookup_ventes(since="2020-01-01", db_path=db)
    assert len(ventes) == 2
    par_siren = {v["siren"]: v for v in ventes}
    assert par_siren["111222333"]["nom_officiel"] == "MENUISERIE ALPHA"
    assert par_siren["111222333"]["naf"] == "43.32A"
    assert par_siren["999000111"]["nom_officiel"] is None          # identité inconnue
    # Filtre département
    assert referentiels.lookup_ventes(since="2020-01-01", departement="33",
                                      db_path=db) == []


def test_lookup_ventes_base_indisponible(tmp_path):
    assert referentiels.lookup_ventes(since="2020-01-01",
                                      db_path=str(tmp_path / "absente.sqlite")) is None


def test_rechargement_remplace_la_table(tmp_path):
    db = _db(tmp_path)
    referentiels.load_sirene_rows(
        [{"siren": "111111111", "denominationUniteLegale": "ANCIENNE"}], db_path=db)
    referentiels.load_sirene_rows(
        [{"siren": "333333333", "denominationUniteLegale": "NOUVELLE"}], db_path=db)
    assert referentiels.lookup_company("111111111", db_path=db) is None
    assert referentiels.lookup_company("333333333", db_path=db)["nom"] == "NOUVELLE"
    assert referentiels.status(db_path=db)["unites_legales"]["n_rows"] == 1
