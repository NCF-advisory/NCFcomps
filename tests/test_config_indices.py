"""Tests du routage indice-par-place et des seuils de points du bêta (config)."""
from __future__ import annotations

from comparables import config
from comparables.config import index_for, index_is_assumed, min_obs_for, settings


def test_index_for_places_principales():
    assert index_for("AIR.PA") == "^FCHI"
    assert index_for("AAPL") == "^GSPC"           # sans suffixe -> USA
    assert index_for("NOVO-B.CO") == "^OMXC25"    # Copenhague (nouveau)
    assert index_for("NOKIA.HE") == "^OMXH25"     # Helsinki (nouveau)
    assert index_for("EQNR.OL") == "^OSEAX"       # Oslo (nouveau)
    assert index_for("EDP.LS") == "PSI20.LS"      # Lisbonne (nouveau)
    assert index_for("RY.TO") == "^GSPTSE"        # Toronto (nouveau)
    assert index_for("BHP.AX") == "^AXJO"         # Sydney (nouveau)
    assert index_for("7203.T") == "^N225"         # Tokyo (nouveau)
    assert index_for("AIR.F") == "^GDAXI"         # Francfort parquet -> DAX


def test_index_for_insensible_a_la_casse():
    assert index_for("air.pa") == "^FCHI"


def test_index_is_assumed_signale_les_suffixes_inconnus():
    assert index_is_assumed("XXX.ZZ") is True     # place inconnue -> defaut signale
    assert index_is_assumed("AIR.PA") is False
    assert index_is_assumed("AAPL") is False      # sans suffixe = USA, voulu


def test_index_is_assumed_benchmark_unique(monkeypatch):
    monkeypatch.setattr(settings, "benchmark_unique", "^STOXX")
    assert index_for("XXX.ZZ") == "^STOXX"
    assert index_is_assumed("XXX.ZZ") is False    # benchmark explicite -> pas un defaut
    monkeypatch.setattr(settings, "benchmark_unique", None)


def test_min_obs_par_frequence(monkeypatch):
    monkeypatch.setattr(settings, "min_beta_obs", 24)
    monkeypatch.setattr(settings, "min_beta_obs_weekly", 52)
    assert min_obs_for("1mo") == 24
    assert min_obs_for("1wk") == 52


def test_mapping_sans_doublon_de_suffixe():
    # garde-fou : chaque suffixe est unique et associe a un symbole non vide
    assert all(config.INDEX_BY_SUFFIX.values())
    assert len(config.INDEX_BY_SUFFIX) == len(set(config.INDEX_BY_SUFFIX))
