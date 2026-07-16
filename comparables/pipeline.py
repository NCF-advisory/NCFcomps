"""Orchestration : pour chaque ticker -> fondamentaux + cours -> calculs -> CompanyRecord."""
from __future__ import annotations
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Optional

import pandas as pd

from comparables.config import settings, index_for, index_is_assumed, min_obs_for
from comparables.models import CompanyRecord
from comparables.sources.registry import fundamentals_source_for, price_source_for
from comparables.finance.beta import (
    adjusted_beta, aligned_returns, compute_beta, drop_incomplete_last_period,
)
from comparables.finance.unlever import unlever_beta
from comparables.finance import multiples as m

logger = logging.getLogger(__name__)


def build_record(ticker: str, tax_rate: float, period: str, frequency: str,
                 index_prices: Optional[pd.Series] = None,
                 floor_net_debt: Optional[bool] = None) -> CompanyRecord:
    floor = settings.unlever_floor_net_debt if floor_net_debt is None else floor_net_debt
    rec = fundamentals_source_for(ticker).fetch_fundamentals(ticker) or CompanyRecord(ticker=ticker)

    # Coherence interne (tie-out) : la VE et les multiples affiches sont recalcules
    # depuis les composants affiches (capi, dette nette, agregats) des qu'ils existent.
    # Les valeurs pre-calculees de la source (dates/definitions opaques) ne servent
    # que de repli quand un composant manque.
    if rec.net_debt is None:
        rec.net_debt = m.net_debt(rec.total_debt, rec.total_cash)
    own_ev = m.enterprise_value(rec.market_cap, rec.net_debt)
    if own_ev is not None:
        rec.enterprise_value = own_ev
    # VE <= 0 (tresorerie nette > capi) -> multiples de VE non significatifs, repli source.
    ev = rec.enterprise_value if rec.enterprise_value and rec.enterprise_value > 0 else None
    rec.ev_sales = m.safe_ratio(ev, rec.revenue) or rec.ev_sales
    rec.ev_ebitda = m.safe_ratio(ev, rec.ebitda) or rec.ev_ebitda
    rec.ev_ebit = m.safe_ratio(ev, rec.ebit) or rec.ev_ebit

    # Beta par regression + R2 ; seuil de points adapte a la frequence (24 points
    # mensuels sont defendables, 24 points hebdo = ~6 mois ne le sont pas).
    idx = index_for(ticker)
    rec.index_used = f"{idx} (defaut)" if index_is_assumed(ticker) else idx
    ps = price_source_for(ticker)
    try:
        stock = ps.fetch_prices(ticker, period, frequency)
        index = index_prices if index_prices is not None else ps.fetch_prices(idx, period, frequency)
        if stock is not None and index is not None:
            # Ecarte la periode calendaire EN COURS (incomplete) puis aligne les PRIX
            # avant d'en deriver des rendements comparables periode a periode.
            stock = drop_incomplete_last_period(stock, frequency)
            index = drop_incomplete_last_period(index, frequency)
            stock_ret, index_ret = aligned_returns(stock, index)
            br = compute_beta(stock_ret, index_ret, min_obs_for(frequency))
            rec.beta_regression, rec.r2, rec.n_obs = br.beta, br.r2, br.n_obs
            rec.beta_std_err = br.std_err
            rec.zero_return_share = br.zero_return_share
            rec.beta_start, rec.beta_end = br.start, br.end
    except Exception as exc:
        logger.warning("Echec du calcul du beta pour %s : %s", ticker, exc)

    # Gearing + desendettement (sur le beta de regression). Le gearing AFFICHE reste le
    # vrai gearing (negatif si tresorerie nette) ; seul le desendettement peut plancher
    # la dette nette a 0 (option `floor`), pour ne pas ressortir un beta_u > beta_l.
    if rec.market_cap and rec.net_debt is not None:
        rec.gearing = rec.net_debt / rec.market_cap
        rec.beta_unlevered = unlever_beta(rec.beta_regression, rec.net_debt,
                                          rec.market_cap, tax_rate,
                                          floor_net_debt_at_zero=floor)
    # Beta desendette ajuste vers le beta de marche (0,67 x desendette + 0,33).
    rec.beta_unlevered_adjusted = adjusted_beta(rec.beta_unlevered)
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
                      floor_net_debt: Optional[bool] = None,
                      progress: Optional[Callable[[int, int], None]] = None) -> list[CompanyRecord]:
    """Construit le lot. `progress(fait, total)` est appele apres chaque societe traitee
    (toutes branches confondues), pour affichage d'avancement (UI / API). `floor_net_debt`
    (defaut : settings) planche la dette nette a 0 dans le desendettement (Hamada)."""
    tax_rate = settings.tax_rate if tax_rate is None else tax_rate
    period = settings.beta_period if period is None else period
    frequency = settings.beta_frequency if frequency is None else frequency

    indices = _prefetch_indices(tickers, period, frequency)
    done = {"n": 0}
    done_lock = threading.Lock()

    def task(t: str) -> CompanyRecord:
        try:
            rec = build_record(t, tax_rate, period, frequency,
                               index_prices=indices.get(index_for(t)),
                               floor_net_debt=floor_net_debt)
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
