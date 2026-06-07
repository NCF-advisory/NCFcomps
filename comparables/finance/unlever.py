"""Desendettement / reendettement du beta (formule de Hamada, sans beta de la dette).

beta_u = beta_l / (1 + (1 - IS) * D/E)
beta_l = beta_u * (1 + (1 - IS) * D/E)

ou D = dette nette et E = capitalisation (valeur de marche des fonds propres).

Module PUR, couvert par des tests.
"""
from __future__ import annotations
import math
from typing import Optional


def unlever_beta(beta_levered: Optional[float], net_debt: Optional[float],
                 equity: Optional[float], tax_rate: float,
                 floor_net_debt_at_zero: bool = False) -> Optional[float]:
    if beta_levered is None or net_debt is None or not equity:
        return None
    if not (math.isfinite(beta_levered) and math.isfinite(net_debt) and math.isfinite(equity)):
        return None
    nd = max(net_debt, 0.0) if floor_net_debt_at_zero else net_debt
    denom = 1.0 + (1.0 - tax_rate) * (nd / equity)
    if denom == 0.0:
        return None
    result = beta_levered / denom
    return result if math.isfinite(result) else None


def relever_beta(beta_unlevered: Optional[float], target_net_debt: float,
                 target_equity: float, tax_rate: float) -> Optional[float]:
    if beta_unlevered is None or not target_equity:
        return None
    if not (math.isfinite(beta_unlevered) and math.isfinite(target_net_debt)
            and math.isfinite(target_equity)):
        return None
    result = beta_unlevered * (1.0 + (1.0 - tax_rate) * (target_net_debt / target_equity))
    return result if math.isfinite(result) else None
