"""Calcul du beta par regression OLS des rendements + R2.

beta  = pente de la regression r_titre = alpha + beta * r_indice
R2    = part de variance du titre expliquee par l'indice (entre 0 et 1)

NOTE : ce module est PUR (pas d'I/O, pas de reseau) et couvert par des tests.
Ne pas y introduire de dependance aux adaptateurs de sources.
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
import statsmodels.api as sm


@dataclass
class BetaResult:
    beta: Optional[float]
    r2: Optional[float]
    n_obs: int
    alpha: Optional[float] = None


def returns_from_prices(prices: pd.Series) -> pd.Series:
    """Rendements simples a partir d'une serie de cours."""
    return prices.dropna().pct_change().dropna()


def compute_beta(stock_returns: pd.Series, index_returns: pd.Series,
                 min_obs: int = 24) -> BetaResult:
    """Regresse les rendements du titre sur ceux de l'indice (memes dates)."""
    df = pd.concat([stock_returns, index_returns], axis=1, join="inner")
    df.columns = ["stock", "index"]
    # Ecarte les valeurs non finies (ex: rendement inf si un cours passe par 0).
    df = df.replace([np.inf, -np.inf], np.nan).dropna()
    n = len(df)
    if n < min_obs:
        return BetaResult(None, None, n)
    x = df["index"].to_numpy()
    y = df["stock"].to_numpy()
    # Indice constant -> pas de pente estimable. On s'aligne sur add_constant,
    # qui supprime la colonne constante (np.std peut renvoyer ~1e-18, pas 0.0).
    design = sm.add_constant(x)
    if design.shape[1] < 2:
        return BetaResult(None, None, n)
    model = sm.OLS(y, design).fit()
    alpha = float(model.params[0])
    beta = float(model.params[1])
    r2 = float(model.rsquared)
    # Filet de securite : ne jamais propager un beta/R2 non fini en aval.
    if not (math.isfinite(beta) and math.isfinite(r2)):
        return BetaResult(None, None, n)
    return BetaResult(beta=beta, r2=r2, n_obs=n, alpha=alpha)
