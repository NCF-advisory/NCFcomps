"""Tests de la base locale SQLite des cessions FR (store_fr), sur base temporaire."""
from __future__ import annotations

from comparables.fr import store_fr
from comparables.fr.models import Cession


def _db(tmp_path):
    return str(tmp_path / "cessions_test.sqlite")


def _seed(db):
    # 2 cessions : A enrichie (CA+EBE), B sans finances.
    store_fr.upsert_cessions([
        Cession(ann_id="A1", siren="111111111", nom="MENUIS A", departement="33",
                date="2023-06-01", prix=120000.0, descriptif="cession fonds menuiserie"),
        Cession(ann_id="B1", siren="222222222", nom="RESTO B", departement="75",
                date="2023-01-01", prix=90000.0, descriptif="cession fonds restaurant"),
    ], db_path=db)
    store_fr.upsert_company("111111111", {"nom": "Menuiserie A", "naf": "43.32A",
                                          "nb_etablissements": 1}, db_path=db)
    store_fr.upsert_financials("111111111", [
        {"date_cloture_exercice": "2022-12-31", "chiffre_d_affaires": 200000.0,
         "ebe": 30000.0, "ebit": 25000.0}], db_path=db)


def test_upsert_dedup_by_ann_id(tmp_path):
    db = _db(tmp_path)
    store_fr.upsert_cessions([Cession(ann_id="X", siren="1", prix=10.0, date="2024-01-01")], db_path=db)
    store_fr.upsert_cessions([Cession(ann_id="X", siren="1", prix=99.0, date="2024-01-01")], db_path=db)
    assert store_fr.get_stats(db_path=db)["n_cessions"] == 1     # même ann_id -> 1 ligne


def test_load_computes_ratios_and_requires_financials(tmp_path):
    db = _db(tmp_path)
    _seed(db)
    # require_financials par défaut -> seule A (qui a un CA/EBE) ressort.
    got = store_fr.load_cessions(db_path=db)
    assert [c.siren for c in got] == ["111111111"]
    a = got[0]
    assert a.ca == 200000.0 and a.ebe == 30000.0 and a.ca_annee == 2022
    assert abs(a.pct_ca - 0.60) < 1e-9 and abs(a.mult_ebe - 4.0) < 1e-9
    assert a.naf == "43.32A" and a.nb_etablissements == 1
    assert a.nom == "Menuiserie A"                               # nom de companies prioritaire
    # sans exigence financière -> B ressort aussi
    assert len(store_fr.load_cessions(require_financials=False, db_path=db)) == 2


def test_load_filters(tmp_path):
    db = _db(tmp_path)
    _seed(db)
    assert [c.siren for c in store_fr.load_cessions(naf_filters=["43"], db_path=db)] == ["111111111"]
    assert store_fr.load_cessions(naf_filters=["56"], db_path=db) == []
    assert [c.siren for c in store_fr.load_cessions(departement="33", require_financials=False,
                                                    db_path=db)] == ["111111111"]
    # filtre activité (LIKE descriptif/nom)
    got = store_fr.load_cessions(terms=["restaurant"], require_financials=False, db_path=db)
    assert [c.siren for c in got] == ["222222222"]


def test_sirens_without_company(tmp_path):
    db = _db(tmp_path)
    _seed(db)
    # A est enrichie, B ne l'est pas -> seul B à enrichir.
    assert store_fr.sirens_without_company(db_path=db) == ["222222222"]


def test_get_stats(tmp_path):
    db = _db(tmp_path)
    _seed(db)
    s = store_fr.get_stats(db_path=db)
    assert s["n_cessions"] == 2 and s["n_companies"] == 1 and s["n_financials"] == 1
    assert s["date_min"] == "2023-01-01" and s["date_max"] == "2023-06-01"
