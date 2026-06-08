"""Tests du helper pur de construction de requête BODACC (_build_where)."""
from __future__ import annotations

from comparables.fr import bodacc


def test_build_where_base_filters_present():
    w = bodacc._build_where(None, None, None)
    assert "familleavis = 'vente'" in w
    assert "search(acte, 'fonds')" in w
    assert "search(acte, 'prix')" in w and "search(acte, 'moyennant')" in w
    # pas de filtre activité quand aucun terme
    assert "commercant" not in w


def test_build_where_multi_terms_are_ored_across_acte_and_commercant():
    w = bodacc._build_where(None, ["menuiserie", "charpente"], None)
    assert "search(acte, 'menuiserie')" in w
    assert "search(commercant, 'menuiserie')" in w
    assert "search(acte, 'charpente')" in w
    assert "search(commercant, 'charpente')" in w
    # les termes sont reliés par OU (pas un ET qui exigerait les deux mots)
    activity = w.split(" and ")[-1]
    assert " or " in activity and " and " not in activity


def test_build_where_departement_and_since():
    w = bodacc._build_where("75", ["bar"], "2021-06-08")
    assert "numerodepartement = '75'" in w
    assert "dateparution >= date'2021-06-08'" in w


def test_build_where_escapes_quotes_in_terms():
    # une apostrophe dans un terme ne doit pas casser la requête ODSQL.
    w = bodacc._build_where(None, ["l'atelier"], None)
    assert "l'atelier" not in w           # l'apostrophe est neutralisée
    assert "search(acte, 'l atelier')" in w
