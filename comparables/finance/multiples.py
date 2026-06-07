"""Calcul des agregats derives (dette nette, VE, multiples) et statistiques d'echantillon.

Module PUR, couvert par des tests.
"""
from __future__ import annotations
import math
import statistics
from typing import Optional, Iterable


def net_debt(total_debt: Optional[float], total_cash: Optional[float]) -> Optional[float]:
    if total_debt is None or total_cash is None:
        return None
    return total_debt - total_cash


def enterprise_value(market_cap: Optional[float], nd: Optional[float]) -> Optional[float]:
    if market_cap is None or nd is None:
        return None
    return market_cap + nd


def safe_ratio(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    """Ratio robuste : None si numerateur absent/non fini ou denominateur nul/absent/negatif/non fini."""
    if numerator is None or denominator is None:
        return None
    if not math.isfinite(numerator) or not math.isfinite(denominator):
        return None
    if denominator <= 0:
        return None
    return numerator / denominator


def summary_stats(values: Iterable[Optional[float]]) -> Optional[dict[str, float]]:
    """Mediane / moyenne / min / max en ignorant les valeurs absentes ou non finies (inf/nan)."""
    vals = [v for v in values if v is not None and math.isfinite(v)]
    if not vals:
        return None
    return {
        "median": statistics.median(vals),
        "mean": statistics.mean(vals),
        "min": min(vals),
        "max": max(vals),
    }
