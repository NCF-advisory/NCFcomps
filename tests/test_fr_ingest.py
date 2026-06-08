"""Tests de l'enrichissement résumable (ingest.enrich) face aux échecs / rate-limiting."""
from __future__ import annotations

from comparables.fr import ingest, entreprises, finances_inpi, store_fr
from comparables.fr.models import Cession


def _seed_one(db):
    store_fr.upsert_cessions(
        [Cession(ann_id="A1", siren="111111111", prix=120000.0, date="2023-06-01")], db_path=db)


def test_enrich_does_not_mark_on_failure_then_retries(tmp_path, monkeypatch):
    db = str(tmp_path / "c.sqlite")
    _seed_one(db)
    monkeypatch.setattr(finances_inpi, "fetch_financials", lambda s: [])

    # 1) L'identité échoue (ex 429) -> société NON marquée, reste à enrichir.
    def boom(siren):
        raise RuntimeError("429 Too Many Requests")
    monkeypatch.setattr(entreprises, "fetch_company", boom)
    assert ingest.enrich(db_path=db, delay=0) == 0
    assert store_fr.sirens_without_company(db_path=db) == ["111111111"]   # toujours en file

    # 2) Au run suivant, l'identité aboutit -> marquée, sort de la file.
    monkeypatch.setattr(entreprises, "fetch_company",
                        lambda s: {"nom": "Boulange A", "naf": "10.71C", "nb_etablissements": 1})
    assert ingest.enrich(db_path=db, delay=0) == 1
    assert store_fr.sirens_without_company(db_path=db) == []
    got = store_fr.load_cessions(require_financials=False, db_path=db)
    assert got[0].naf == "10.71C" and got[0].nb_etablissements == 1


def test_enrich_marks_company_when_not_found(tmp_path, monkeypatch):
    # fetch_company renvoie None (SIREN sans identité) : marqué quand même -> pas de boucle infinie.
    db = str(tmp_path / "c.sqlite")
    _seed_one(db)
    monkeypatch.setattr(finances_inpi, "fetch_financials", lambda s: [])
    monkeypatch.setattr(entreprises, "fetch_company", lambda s: None)
    assert ingest.enrich(db_path=db, delay=0) == 1
    assert store_fr.sirens_without_company(db_path=db) == []
