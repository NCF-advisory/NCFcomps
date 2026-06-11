"""Calcul du beta par regression OLS des rendements + R2, et qualite d'echantillon.

beta  = pente de la regression r_titre = alpha + beta * r_indice
R2    = part de variance du titre expliquee par l'indice (entre 0 et 1)

Regle de qualite (decision 2026-06-11) : un beta dont le R2 est inferieur au seuil
(settings.beta_min_r2, 0,10 par defaut) reste AFFICHE mais est EXCLU des statistiques
d'echantillon (mediane, moyenne...) et de la synthese — l'indice n'explique presque
rien du titre, la pente n'est pas exploitable pour un cout du capital.

NOTE : ce module est PUR (pas d'I/O, pas de reseau) et couvert par des tests.
Ne pas y introduire de dependance aux adaptateurs de sources.
"""
from __future__ import annotations
import math
import statistics
from dataclasses import dataclass
from typing import Iterable, Optional

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


def reliable_beta(beta: Optional[float], r2: Optional[float],
                  min_r2: float) -> Optional[float]:
    """Beta filtre par qualite de regression : la valeur si R2 >= min_r2, sinon None.

    Un R2 absent vaut exclusion (pas de regression = pas de qualite mesurable) ;
    s'applique aussi au beta desendette, derive de la meme regression."""
    if beta is None or not math.isfinite(beta):
        return None
    if r2 is None or not math.isfinite(r2) or r2 < min_r2:
        return None
    return beta


def blume_adjusted(beta: Optional[float]) -> Optional[float]:
    """Beta ajuste (Blume) : 2/3 x beta estime + 1/3 (convergence vers le beta de marche).

    Convention de place (Bloomberg « adjusted beta ») pour un cout du capital prospectif."""
    if beta is None or not math.isfinite(beta):
        return None
    return (2.0 / 3.0) * beta + 1.0 / 3.0


def sample_summary(triples: Iterable[tuple[Optional[float], Optional[float], Optional[float]]],
                   min_r2: float) -> Optional[dict]:
    """Synthese des betas RETENUS d'un echantillon : moyens endette, ajuste, desendette.

    `triples` = (beta_regression, r2, beta_unlevered) par societe. Retenu = R2 >= min_r2.
    Renvoie {n_retained, n_excluded_low_r2, mean/median_levered, mean_adjusted,
    mean_unlevered, min_r2}, ou None si aucune societe ne porte de beta."""
    levered: list[float] = []
    unlevered: list[float] = []
    excluded = 0
    for beta, r2, beta_u in triples:
        kept = reliable_beta(beta, r2, min_r2)
        if kept is not None:
            levered.append(kept)
            u = reliable_beta(beta_u, r2, min_r2)
            if u is not None:
                unlevered.append(u)
        elif beta is not None and math.isfinite(beta):
            excluded += 1
    if not levered and excluded == 0:
        return None
    mean_levered = statistics.mean(levered) if levered else None
    return {
        "min_r2": min_r2,
        "n_retained": len(levered),
        "n_excluded_low_r2": excluded,
        "mean_levered": mean_levered,
        "median_levered": statistics.median(levered) if levered else None,
        "mean_adjusted": blume_adjusted(mean_levered),
        "mean_unlevered": statistics.mean(unlevered) if unlevered else None,
    }
