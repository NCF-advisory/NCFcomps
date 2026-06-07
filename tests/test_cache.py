"""Tests de la couche de cache : session HTTP cachee + cache disque des cours.

Aucun reseau : on redirige `settings.cache_path` vers un dossier temporaire et on
remplace `yf.download` par un faux pour compter les appels.
"""
from __future__ import annotations

import os
import time

import pandas as pd
import requests_cache

from comparables import cache
from comparables.config import settings


def _series() -> pd.Series:
    idx = pd.date_range("2020-01-01", periods=5, freq="MS")
    return pd.Series([1.0, 2.0, 3.0, 4.0, 5.0], index=idx, name="Close")


def _use_tmp_cache(tmp_path, monkeypatch, ttl_hours: int = 24) -> None:
    monkeypatch.setattr(settings, "cache_path", str(tmp_path / "cache.sqlite"))
    monkeypatch.setattr(settings, "price_cache_ttl_hours", ttl_hours)


def test_get_session_returns_cached_session():
    s = cache.get_session(expire_after=3600)
    assert isinstance(s, requests_cache.CachedSession)
    assert s.cache is not None


def test_price_cache_round_trip(tmp_path, monkeypatch):
    _use_tmp_cache(tmp_path, monkeypatch)
    assert cache.load_cached_prices("AAPL", "5y", "1mo") is None   # vide au depart
    s = _series()
    cache.store_cached_prices("AAPL", "5y", "1mo", s)
    out = cache.load_cached_prices("AAPL", "5y", "1mo")
    assert out is not None
    pd.testing.assert_series_equal(out, s)


def test_price_cache_keys_are_independent(tmp_path, monkeypatch):
    _use_tmp_cache(tmp_path, monkeypatch)
    cache.store_cached_prices("AAPL", "5y", "1mo", _series())
    # Une cle differente (periode ou intervalle) ne doit pas etre servie par erreur.
    assert cache.load_cached_prices("AAPL", "2y", "1mo") is None
    assert cache.load_cached_prices("AAPL", "5y", "1wk") is None
    assert cache.load_cached_prices("MSFT", "5y", "1mo") is None


def test_price_cache_expiry(tmp_path, monkeypatch):
    _use_tmp_cache(tmp_path, monkeypatch)
    cache.store_cached_prices("MSFT", "5y", "1mo", _series())
    path = cache._price_cache_dir() / f"{cache._price_key('MSFT', '5y', '1mo')}.pkl"
    old = time.time() - 25 * 3600                  # au-dela du TTL de 24 h
    os.utime(path, (old, old))
    assert cache.load_cached_prices("MSFT", "5y", "1mo") is None


def test_price_cache_disabled(tmp_path, monkeypatch):
    _use_tmp_cache(tmp_path, monkeypatch, ttl_hours=0)   # cache desactive
    cache.store_cached_prices("X", "5y", "1mo", _series())
    assert cache.load_cached_prices("X", "5y", "1mo") is None


def test_store_ignores_empty_or_none(tmp_path, monkeypatch):
    _use_tmp_cache(tmp_path, monkeypatch)
    cache.store_cached_prices("EMPTY", "5y", "1mo", pd.Series(dtype=float))
    cache.store_cached_prices("NONE", "5y", "1mo", None)
    assert cache.load_cached_prices("EMPTY", "5y", "1mo") is None
    assert cache.load_cached_prices("NONE", "5y", "1mo") is None


def test_yahoo_fetch_prices_hits_network_once(tmp_path, monkeypatch):
    """Acceptance Step 2 : le 2e appel pour la meme cle est servi par le cache."""
    from comparables.sources import yahoo

    _use_tmp_cache(tmp_path, monkeypatch)
    calls = {"n": 0}

    def fake_download(ticker, period=None, interval=None, auto_adjust=True, progress=False):
        calls["n"] += 1
        idx = pd.date_range("2020-01-01", periods=6, freq="MS")
        return pd.DataFrame({"Close": [10.0, 11.0, 12.0, 13.0, 14.0, 15.0]}, index=idx)

    monkeypatch.setattr(yahoo.yf, "download", fake_download)

    src = yahoo.YahooSource()
    first = src.fetch_prices("AAPL", "5y", "1mo")
    second = src.fetch_prices("AAPL", "5y", "1mo")

    assert calls["n"] == 1                          # un seul telechargement
    assert first is not None and second is not None
    pd.testing.assert_series_equal(first, second)
