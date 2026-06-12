"""Tests de la logique pure PME FR (extraction prix/SIREN, % de CA, agrégation)."""
from __future__ import annotations

import math

from comparables.fr import parsing as p
from comparables.fr.models import Cession


def test_parse_fr_amount_formats():
    assert p.parse_fr_amount("124.548") == 124548.0          # point = milliers
    assert p.parse_fr_amount("1.250.000") == 1250000.0
    assert p.parse_fr_amount("150 000,00") == 150000.0       # espace milliers + virgule décimale
    assert p.parse_fr_amount("47 000") == 47000.0
    assert p.parse_fr_amount("85000") == 85000.0
    assert p.parse_fr_amount("320 000,50") == 320000.5
    assert p.parse_fr_amount("abc") is None


def test_extract_price_picks_cession_not_capital():
    # Le capital social ne doit PAS être confondu avec le prix de cession.
    desc = ("SARL au capital de 50 000 €, immatriculée 517561023 RCS NANTES, "
            "a cédé un fonds de commerce de boulangerie. Moyennant le prix de 124.548 €.")
    assert p.extract_price(desc) == 124548.0


def test_extract_price_variants():
    assert p.extract_price("moyennant le prix principal de 1.250.000 euros") == 1250000.0
    assert p.extract_price("Prix de cession : 85 000 €") == 85000.0
    assert p.extract_price("moyennant un prix de 47 000 €") == 47000.0
    assert p.extract_price("moyennant le prix stipulé de 320 000,00 €") == 320000.0
    assert p.extract_price("cédé pour 9 500 000 €") == 9500000.0


def test_extract_price_absent():
    assert p.extract_price("Achat d'un établissement par une personne physique (immatriculation).") is None
    assert p.extract_price("") is None
    assert p.extract_price(None) is None


def test_extract_sirens_dedup_and_formats():
    registre = ["994829935", "994 829 935", "980159602", "980 159 602"]
    assert p.extract_sirens(registre) == ["994829935", "980159602"]
    assert p.extract_sirens("RCS 422 452 045") == ["422452045"]
    assert p.extract_sirens(None) == []


def test_compute_pct_ca():
    assert p.compute_pct_ca(85000.0, 100000.0) == 0.85
    assert p.compute_pct_ca(85000.0, 0.0) is None       # CA nul -> pas de ratio
    assert p.compute_pct_ca(None, 100000.0) is None
    assert p.compute_pct_ca(85000.0, None) is None


def test_compute_mult_ebe():
    assert p.compute_mult_ebe(120000.0, 30000.0) == 4.0   # 4,0x l'EBE
    assert p.compute_mult_ebe(120000.0, 0.0) is None      # EBE nul/negatif -> pas de multiple
    assert p.compute_mult_ebe(120000.0, -5000.0) is None
    assert p.compute_mult_ebe(None, 30000.0) is None


def test_is_plausible_mult_ebe():
    assert p.is_plausible_mult_ebe(4.2) is True
    assert p.is_plausible_mult_ebe(0.5) is True and p.is_plausible_mult_ebe(15.0) is True
    assert p.is_plausible_mult_ebe(50.0) is False
    assert p.is_plausible_mult_ebe(None) is False


def test_robust_values_hard_bounds_only_on_small_sample():
    # n < 8 : pas de trim statistique, juste le garde-fou métier.
    kept, out = p.robust_values([3.0, 14.0, 100.0, None, float("nan")], p.MULT_EBE_BOUNDS)
    assert sorted(kept) == [3.0, 14.0]      # 100 (hors borne) et None/nan écartés
    assert out == 0                         # pas d'outlier statistique (échantillon trop petit)


def test_robust_values_trims_statistical_extreme():
    # n >= 8, cluster serré + 1 valeur extrême (mais dans les bornes) -> exclue par la MAD.
    vals = [2.5, 3.0, 3.2, 3.5, 4.0, 4.2, 4.5, 5.0, 14.0]
    kept, out = p.robust_values(vals, p.MULT_EBE_BOUNDS)
    assert 14.0 not in kept and out == 1
    assert len(kept) == 8


def test_robust_values_no_trim_when_mad_zero():
    # valeurs identiques -> MAD = 0 -> aucun trim (évite la division par zéro).
    kept, out = p.robust_values([4.0] * 9, p.MULT_EBE_BOUNDS)
    assert len(kept) == 9 and out == 0


def test_is_plausible_pct():
    assert p.is_plausible_pct(0.76) is True
    assert p.is_plausible_pct(0.05) is True and p.is_plausible_pct(4.0) is True
    assert p.is_plausible_pct(52.5) is False      # 5250% -> appariement douteux
    assert p.is_plausible_pct(0.01) is False      # 1% -> fonds = établissement d'un groupe
    assert p.is_plausible_pct(None) is False


def test_summarize_by_activity():
    cessions = [
        Cession(siren="1", naf="10.71C", activite="Boulangerie", prix=120000, ca=200000,
                pct_ca=0.60, ebe=30000, mult_ebe=4.0),
        Cession(siren="2", naf="10.71C", activite="Boulangerie", prix=90000, ca=150000,
                pct_ca=0.60, ebe=15000, mult_ebe=6.0),
        Cession(siren="3", naf="56.10A", activite="Restauration", prix=300000, ca=400000,
                pct_ca=0.75),
        Cession(siren="4", naf="56.10A", activite="Restauration", prix=50000, ca=None, pct_ca=None),
        Cession(siren="5", naf="46.49Z", activite="Gros", prix=6e6, ca=120000, pct_ca=50.0,
                ebe=1000, mult_ebe=6000.0),   # aberrant (pct ET ebe hors bande)
    ]
    s = p.summarize_by_activity(cessions)
    assert s["overall"]["n_total"] == 5
    assert s["overall"]["n_avec_pct"] == 4          # 4 ont un ratio prix/CA
    assert s["overall"]["n_plausible"] == 3         # mais 1 hors bande exclu
    assert s["overall"]["n_avec_ebe"] == 2          # 2 multiples EBE plausibles (6000x exclu)
    assert s["overall"]["n_pct_outliers"] == 0      # petit échantillon -> pas de trim statistique
    assert s["overall"]["n_ebe_outliers"] == 0
    assert abs(s["overall"]["median_pct_ca"] - 0.60) < 1e-9
    assert abs(s["overall"]["median_mult_ebe"] - 5.0) < 1e-9    # médiane de [4.0, 6.0]
    # tri par n décroissant : boulangerie (2) avant restauration (1 plausible)
    assert s["by_activite"][0]["naf"] == "10.71C" and s["by_activite"][0]["n"] == 2
    assert math.isclose(s["by_activite"][0]["median_pct_ca"], 0.60)
    assert math.isclose(s["by_activite"][0]["median_mult_ebe"], 5.0)
    # l'activité aberrante (46.49Z) n'apparaît pas dans les groupes plausibles
    assert all(g["naf"] != "46.49Z" for g in s["by_activite"])


def test_extract_sirens_ignore_le_siren_factice():
    from comparables.fr.parsing import extract_sirens
    assert extract_sirens("000000000, 442 003 117") == ["442003117"]
