"""Orchestration : pour chaque ticker -> fondamentaux + cours -> calculs -> CompanyRecord."""
from __future__ import annotations
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Optional

import pandas as pd

from comparables.config import settings, index_for
from comparables.models import CompanyRecord
from comparables.sources.registry import fundamentals_source_for, price_source_for
from comparables.finance.beta import compute_beta, returns_from_prices
from comparables.finance.unlever import unlever_beta
from comparables.finance import multiples as m

logger = logging.getLogger(__name__)


def build_record(ticker: str, tax_rate: float, period: str, frequency: str,
                 index_prices: Optional[pd.Series] = None) -> CompanyRecord:
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
        index = index_prices if index_prices is not None else ps.fetch_prices(idx, period, frequency)
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


def _prefetch_indices(tickers: list[str], period: str,
                      frequency: str) -> dict[str, pd.Series]:
    """Telecharge une seule fois chaque indice de reference distinct du lot."""
    out: dict[str, pd.Series] = {}
    for idx in {index_for(t) for t in tickers}:
        try:
            series = price_source_for(idx).fetch_prices(idx, period, frequency)
        except Exception as exc:
            logger.warning("Echec du telechargement de l'indice %s : %s", idx, exc)
            series = None
        if series is not None:
            out[idx] = series
    return out


def build_comparables(tickers: list[str], tax_rate: Optional[float] = None,
                      period: Optional[str] = None,
                      frequency: Optional[str] = None,
                      progress: Optional[Callable[[int, int], None]] = None) -> list[CompanyRecord]:
    """Construit le lot. `progress(fait, total)` est appele apres chaque societe traitee
    (toutes branches confondues), pour affichage d'avancement (UI / API)."""
    tax_rate = settings.tax_rate if tax_rate is None else tax_rate
    period = settings.beta_period if period is None else period
    frequency = settings.beta_frequency if frequency is None else frequency

    indices = _prefetch_indices(tickers, period, frequency)
    done = {"n": 0}
    done_lock = threading.Lock()

    def task(t: str) -> CompanyRecord:
        try:
            rec = build_record(t, tax_rate, period, frequency,
                               index_prices=indices.get(index_for(t)))
        except Exception as exc:
            # Filet de securite (regle 5) : l'echec d'un ticker ne casse pas le lot.
            logger.warning("Echec du traitement de %s : %s", t, exc)
            rec = CompanyRecord(ticker=t)
        if progress is not None:
            with done_lock:
                done["n"] += 1
                n = done["n"]
            try:
                progress(n, len(tickers))
            except Exception:               # un callback defaillant ne casse pas le lot
                pass
        return rec

    workers = max(1, min(int(settings.pipeline_max_workers), len(tickers) or 1))
    if workers == 1:
        return [task(t) for t in tickers]
    with ThreadPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(task, tickers))   # map preserve l'ordre des tickers


def to_dataframe(records: list[CompanyRecord]) -> pd.DataFrame:
    return pd.DataFrame([r.model_dump() for r in records])
