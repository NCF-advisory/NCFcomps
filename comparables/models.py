"""Modeles de donnees (pydantic). CompanyRecord = une ligne du tableau de comparables."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class CompanyRecord(BaseModel):
    # Identite
    ticker: str
    name: Optional[str] = None
    country: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None          # industrie fine Yahoo (ex. « Steel ») -> Damodaran
    currency: Optional[str] = None
    source: Optional[str] = None            # provenance des fondamentaux

    # Donnees brutes
    market_cap: Optional[float] = None
    total_debt: Optional[float] = None
    total_cash: Optional[float] = None
    revenue: Optional[float] = None
    ebitda: Optional[float] = None
    ebit: Optional[float] = None

    # Derives
    net_debt: Optional[float] = None
    enterprise_value: Optional[float] = None

    # Betas
    beta_source: Optional[float] = None     # beta pre-calcule (ex: Yahoo)
    index_used: Optional[str] = None
    beta_regression: Optional[float] = None
    r2: Optional[float] = None
    n_obs: Optional[int] = None
    beta_std_err: Optional[float] = None              # ecart-type OLS de la pente (fiabilite)
    zero_return_share: Optional[float] = None         # part de rendements titre nuls (illiquidite)
    beta_start: Optional[str] = None                  # 1re date de rendement regressee (ISO)
    beta_end: Optional[str] = None                    # derniere date de rendement regressee (ISO)
    gearing: Optional[float] = None
    beta_unlevered: Optional[float] = None
    beta_unlevered_adjusted: Optional[float] = None   # 0,67 x desendette + 0,33 (vers 1)

    # Multiples
    ev_sales: Optional[float] = None
    ev_ebitda: Optional[float] = None
    ev_ebit: Optional[float] = None
    pe_trailing: Optional[float] = None
    pe_forward: Optional[float] = None
    pb: Optional[float] = None
