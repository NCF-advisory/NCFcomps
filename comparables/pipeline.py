"""Orchestration : pour chaque ticker -> fondamentaux + cours -> calculs -> CompanyRecord."""
from __future__ import annotations
import logging
from typing import Optional

import pandas as pd

from comparables.config import settings, index_for
from comparables.models import CompanyRecord
from comparables.sources.registry import fundamentals_source_for, price_source_for
from comparables.finance.beta import compute_beta, returns_from_prices
from comparables.finance.unlever import unlever_beta
from comparables.finance import multiples as m

logger = logging.getLogger(__name__)


def build_record(ticker: str, tax_rate: float, period: str, frequency: str) -> CompanyRecord:
    rec = fundamentals_source_for(ticker).fetch_fundamentals(ticker) or CompanyRecord(ticker=ticker)

    # Derives manquants
    if rec.net_debt is None:
        rec.net_debt = m.net_debt(rec.total_debt, rec.total_cash)
    if rec.enterprise_value is None:
        rec.enterprise_value = m.enterprise_value(rec.market_cap, rec.net_debt)
    if rec.ev_sales is None:
        rec.ev_sales = m.safe_ratio(rec.enterprise_value, rec.revenue)
    if rec.ev_ebitda is None:
        rec.ev_ebitda = m.safe_ratio(rec.enterprise_value, rec.ebitda)
    if rec.ev_ebit is None:
        rec.ev_ebit = m.safe_ratio(rec.enterprise_value, rec.ebit)

    # Beta par regression + R2
    idx = index_for(ticker)
    rec.index_used = idx
    ps = price_source_for(ticker)
    try:
        stock = ps.fetch_prices(ticker, period, frequency)
        index = ps.fetch_prices(idx, period, frequency)
        if stock is not None and index is not None:
            br = compute_beta(returns_from_prices(stock), returns_from_prices(index),
                              settings.min_beta_obs)
            rec.beta_regression, rec.r2, rec.n_obs = br.beta, br.r2, br.n_obs
    except Exception as exc:
        logger.warning("Echec du calcul du beta pour %s : %s", ticker, exc)

    # Gearing + desendettement (sur le beta de regression)
    if rec.market_cap and rec.net_debt is not None:
        rec.gearing = rec.net_debt / rec.market_cap
        rec.beta_unlevered = unlever_beta(rec.beta_regression, rec.net_debt,
                                          rec.market_cap, tax_rate)
    return rec


def build_comparables(tickers: list[str], tax_rate: Optional[float] = None,
                      period: Optional[str] = None,
                      frequency: Optional[str] = None) -> list[CompanyRecord]:
    tax_rate = settings.tax_rate if tax_rate is None else tax_rate
    period = settings.beta_period if period is None else period
    frequency = settings.beta_frequency if frequency is None else frequency
    records: list[CompanyRecord] = []
    for t in tickers:
        try:
            records.append(build_record(t, tax_rate, period, frequency))
        except Exception as exc:
            # Filet de securite (regle 5) : l'echec d'un ticker ne casse pas le lot.
            logger.warning("Echec du traitement de %s : %s", t, exc)
            records.append(CompanyRecord(ticker=t))
    return records


def to_dataframe(records: list[CompanyRecord]) -> pd.DataFrame:
    return pd.DataFrame([r.model_dump() for r in records])
