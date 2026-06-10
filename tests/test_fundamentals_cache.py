"""Tests du retry Yahoo et du cache disque des fondamentaux. Aucun reseau."""
from __future__ import annotations

import os
import time

from comparables import cache
from comparables.config import settings
from comparables.models import CompanyRecord
from comparables.sources import yahoo


def _use_tmp_cache(tmp_path, monkeypatch, ttl_hours: int = 72) -> None:
    monkeypatch.setattr(settings, "cache_path", str(tmp_path / "cache.sqlite"))
    monkeypatch.setattr(settings, "fundamentals_cache_ttl_hours", ttl_hours)
    monkeypatch.setattr(settings, "yahoo_backoff_seconds", 0.0)   # pas d'attente en test


# --- _with_retry ---

def test_retry_reessaie_puis_reussit(monkeypatch):
    monkeypatch.setattr(settings, "yahoo_max_attempts", 3)
    monkeypatch.setattr(settings, "yahoo_backoff_seconds", 0.0)
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("transitoire")
        return "ok"

    assert yahoo._with_retry(flaky, "test") == "ok"
    assert calls["n"] == 3


def test_retry_renvoie_none_apres_epuisement(monkeypatch):
    monkeypatch.setattr(settings, "yahoo_max_attempts", 2)
    monkeypatch.setattr(settings, "yahoo_backoff_seconds", 0.0)
    calls = {"n": 0}

    def always_fails():
        calls["n"] += 1
        raise ConnectionError("panne")

    assert yahoo._with_retry(always_fails, "test") is None
    assert calls["n"] == 2


# --- Cache disque des fondamentaux ---

def test_fundamentals_cache_round_trip(tmp_path, monkeypatch):
    _use_tmp_cache(tmp_path, monkeypatch)
    assert cache.load_cached_fundamentals("AAPL") is None
    rec = CompanyRecord(ticker="AAPL", name="Apple", market_cap=3e12)
    cache.store_cached_fundamentals("AAPL", rec)
    out = cache.load_cached_fundamentals("AAPL")
    assert out == rec
    assert cache.load_cached_fundamentals("MSFT") is None   # cles independantes


def test_fundamentals_cache_expiry(tmp_path, monkeypatch):
    _use_tmp_cache(tmp_path, monkeypatch)
    cache.store_cached_fundamentals("MSFT", CompanyRecord(ticker="MSFT", name="Microsoft"))
    path = cache._fundamentals_cache_dir() / f"{cache._price_key('MSFT', 'fund', 'json')}.json"
    old = time.time() - 73 * 3600                  # au-dela du TTL de 72 h
    os.utime(path, (old, old))
    assert cache.load_cached_fundamentals("MSFT") is None


def test_fundamentals_cache_disabled(tmp_path, monkeypatch):
    _use_tmp_cache(tmp_path, monkeypatch, ttl_hours=0)
    cache.store_cached_fundamentals("X", CompanyRecord(ticker="X", name="X"))
    assert cache.load_cached_fundamentals("X") is None


# --- fetch_fundamentals : cache + non-pollution par les echecs ---

class _FakeTicker:
    """Faux yf.Ticker comptant les acces a .info."""
    calls = {"n": 0}

    def __init__(self, ticker):
        self.ticker = ticker

    @property
    def info(self):
        _FakeTicker.calls["n"] += 1
        return {"longName": "Apple Inc.", "marketCap": 3e12}


def test_fetch_fundamentals_sert_le_cache(tmp_path, monkeypatch):
    _use_tmp_cache(tmp_path, monkeypatch)
    _FakeTicker.calls["n"] = 0
    monkeypatch.setattr(yahoo.yf, "Ticker", _FakeTicker)

    src = yahoo.YahooSource()
    first = src.fetch_fundamentals("AAPL")
    second = src.fetch_fundamentals("AAPL")

    assert _FakeTicker.calls["n"] == 1              # un seul appel reseau
    assert first is not None and second is not None
    assert second.name == "Apple Inc."


class _BrokenTicker:
    def __init__(self, ticker):
        self.ticker = ticker

    @property
    def info(self):
        raise ConnectionError("panne")


def test_fetch_fundamentals_echec_non_mis_en_cache(tmp_path, monkeypatch):
    """Un record vide (echec transitoire) ne doit pas etre fige dans le cache."""
    _use_tmp_cache(tmp_path, monkeypatch)
    monkeypatch.setattr(settings, "yahoo_max_attempts", 1)
    monkeypatch.setattr(yahoo.yf, "Ticker", _BrokenTicker)

    src = yahoo.YahooSource()
    rec = src.fetch_fundamentals("FAIL")
    assert rec is not None and rec.name is None     # record partiel (regle 5)
    assert cache.load_cached_fundamentals("FAIL") is None
