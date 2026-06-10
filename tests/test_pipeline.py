"""Tests d'integration de l'orchestration (pipeline) avec des sources factices.

Aucun reseau : on injecte une DataSource de test via monkeypatch du routage.
Verifie la regle 5 (l'echec d'un ticker ne casse pas le lot) et le calcul des
champs derives (dette nette, VE, multiples, gearing, beta desendette).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from comparables import pipeline
from comparables.models import CompanyRecord
from comparables.sources.base import DataSource


def _price_series(seed: int, n: int = 60) -> pd.Series:
    rng = np.random.default_rng(seed)
    prices = 100.0 * np.cumprod(1.0 + rng.normal(0, 0.05, n))
    idx = pd.date_range("2018-01-01", periods=n, freq="MS")
    return pd.Series(prices, index=idx)


class FakeSource(DataSource):
    """Source de test : renvoie un CompanyRecord et/ou une serie de cours fixes."""

    def __init__(self, record: CompanyRecord | None = None,
                 prices: pd.Series | None = None,
                 raise_fundamentals: bool = False,
                 raise_prices: bool = False):
        self._record = record
        self._prices = prices
        self._raise_fundamentals = raise_fundamentals
        self._raise_prices = raise_prices

    def fetch_fundamentals(self, ticker: str) -> CompanyRecord | None:
        if self._raise_fundamentals:
            raise RuntimeError("boom fundamentals")
        return self._record

    def fetch_prices(self, ticker: str, period: str, interval: str) -> pd.Series | None:
        if self._raise_prices:
            raise RuntimeError("boom prices")
        return self._prices


def _patch_sources(monkeypatch, fund: DataSource, price: DataSource) -> None:
    monkeypatch.setattr(pipeline, "fundamentals_source_for", lambda ticker: fund)
    monkeypatch.setattr(pipeline, "price_source_for", lambda ticker: price)


def test_build_record_derives_and_unlevers(monkeypatch):
    rec_in = CompanyRecord(ticker="TEST", market_cap=100.0, total_debt=40.0,
                           total_cash=10.0, revenue=50.0, ebitda=20.0, ebit=15.0)
    prices = _price_series(0)
    _patch_sources(monkeypatch, FakeSource(record=rec_in),
                   FakeSource(prices=prices))

    rec = pipeline.build_record("TEST", tax_rate=0.25, period="5y", frequency="1mo")

    assert rec.net_debt == 30.0                      # 40 - 10
    assert rec.enterprise_value == 130.0             # 100 + 30
    assert abs(rec.ev_sales - 2.6) < 1e-9            # 130 / 50
    assert abs(rec.ev_ebitda - 6.5) < 1e-9          # 130 / 20
    assert abs(rec.gearing - 0.30) < 1e-9            # 30 / 100
    # cours stock == cours indice -> beta ~ 1.0, R2 ~ 1.0
    assert rec.beta_regression is not None and np.isfinite(rec.beta_regression)
    assert rec.beta_unlevered is not None and np.isfinite(rec.beta_unlevered)


def test_build_record_survives_price_failure(monkeypatch):
    rec_in = CompanyRecord(ticker="TEST", market_cap=100.0, total_debt=40.0,
                           total_cash=10.0, revenue=50.0)
    _patch_sources(monkeypatch, FakeSource(record=rec_in),
                   FakeSource(raise_prices=True))

    rec = pipeline.build_record("TEST", tax_rate=0.25, period="5y", frequency="1mo")

    # L'echec des cours ne doit PAS lever : on renvoie un record partiel.
    assert rec.beta_regression is None
    assert rec.net_debt == 30.0                      # les derives restent calcules
    assert rec.enterprise_value == 130.0


def test_build_comparables_isolates_per_ticker_failure(monkeypatch):
    good = CompanyRecord(ticker="GOOD", market_cap=200.0, total_debt=50.0,
                         total_cash=20.0, revenue=80.0)

    def fund_for(ticker: str) -> DataSource:
        if ticker == "BAD":
            return FakeSource(raise_fundamentals=True)   # plante au fetch
        return FakeSource(record=good)

    monkeypatch.setattr(pipeline, "fundamentals_source_for", fund_for)
    monkeypatch.setattr(pipeline, "price_source_for",
                        lambda ticker: FakeSource(prices=_price_series(1)))

    recs = pipeline.build_comparables(["GOOD", "BAD"], tax_rate=0.25,
                                      period="5y", frequency="1mo")

    assert len(recs) == 2                             # regle 5 : lot complet
    assert recs[0].ticker == "GOOD" and recs[0].net_debt == 30.0
    assert recs[1].ticker == "BAD"                    # record partiel, pas d'exception
    assert recs[1].net_debt is None


def test_to_dataframe_round_trips_fields(monkeypatch):
    rec_in = CompanyRecord(ticker="TEST", market_cap=100.0, total_debt=40.0,
                           total_cash=10.0, revenue=50.0)
    _patch_sources(monkeypatch, FakeSource(record=rec_in),
                   FakeSource(prices=_price_series(2)))

    recs = pipeline.build_comparables(["TEST"], tax_rate=0.25,
                                      period="5y", frequency="1mo")
    df = pipeline.to_dataframe(recs)

    assert len(df) == 1
    for field in CompanyRecord.model_fields:
        assert field in df.columns
    assert df.loc[0, "ticker"] == "TEST"


class CountingPriceSource(DataSource):
    """Source de cours comptant les fetchs par symbole (verifie la mutualisation)."""

    def __init__(self):
        self.calls: dict[str, int] = {}

    def fetch_fundamentals(self, ticker: str) -> CompanyRecord | None:
        return None

    def fetch_prices(self, ticker: str, period: str, interval: str) -> pd.Series | None:
        self.calls[ticker] = self.calls.get(ticker, 0) + 1
        return _price_series(3)


def test_build_comparables_fetches_each_index_once(monkeypatch):
    """L'indice partage (^GSPC pour les tickers US) n'est telecharge qu'une fois."""
    price = CountingPriceSource()
    monkeypatch.setattr(pipeline, "fundamentals_source_for",
                        lambda ticker: FakeSource(record=CompanyRecord(ticker=ticker)))
    monkeypatch.setattr(pipeline, "price_source_for", lambda ticker: price)

    recs = pipeline.build_comparables(["AAA", "BBB", "CCC"], tax_rate=0.25,
                                      period="5y", frequency="1mo")

    assert [r.ticker for r in recs] == ["AAA", "BBB", "CCC"]   # ordre preserve
    assert price.calls["^GSPC"] == 1                           # 1 fetch d'indice, pas 3
    assert all(price.calls[t] == 1 for t in ("AAA", "BBB", "CCC"))


def test_build_comparables_parallel_preserves_order_and_rule5(monkeypatch):
    """Avec plusieurs workers, l'ordre est preserve et un echec reste isole."""
    monkeypatch.setattr(pipeline.settings, "pipeline_max_workers", 4)

    def fund_for(ticker: str) -> DataSource:
        if ticker == "BAD":
            return FakeSource(raise_fundamentals=True)
        return FakeSource(record=CompanyRecord(ticker=ticker, market_cap=100.0,
                                               total_debt=40.0, total_cash=10.0))

    monkeypatch.setattr(pipeline, "fundamentals_source_for", fund_for)
    monkeypatch.setattr(pipeline, "price_source_for",
                        lambda ticker: FakeSource(prices=_price_series(4)))

    tickers = ["T1", "T2", "BAD", "T3", "T4"]
    recs = pipeline.build_comparables(tickers, tax_rate=0.25, period="5y", frequency="1mo")

    assert [r.ticker for r in recs] == tickers
    assert recs[2].net_debt is None                  # BAD : record partiel
    assert all(r.net_debt == 30.0 for i, r in enumerate(recs) if i != 2)
