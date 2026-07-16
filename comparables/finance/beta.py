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
from datetime import date, datetime
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
    std_err: Optional[float] = None            # ecart-type OLS de la pente (bse[1])
    zero_return_share: Optional[float] = None  # part de rendements titre nuls (illiquidite)
    start: Optional[str] = None                # 1re date de rendement retenue (ISO)
    end: Optional[str] = None                  # derniere date de rendement retenue (ISO)


def returns_from_prices(prices: pd.Series) -> pd.Series:
    """Rendements simples a partir d'une serie de cours."""
    return prices.dropna().pct_change().dropna()


def _iso_date(value: object) -> Optional[str]:
    """Date ISO (AAAA-MM-JJ) d'un element d'index temporel, ou None s'il n'est pas date.

    Les regressions reelles ont un index de dates (DatetimeIndex) ; les tests
    unitaires passent parfois un index entier -> on renvoie None sans inventer 1970."""
    if isinstance(value, (pd.Timestamp, datetime, date, np.datetime64)):
        ts = pd.Timestamp(value)
        return None if pd.isna(ts) else ts.date().isoformat()
    return None


def drop_incomplete_last_period(prices: pd.Series, interval: str,
                                today: Optional[date] = None) -> pd.Series:
    """Ecarte la derniere observation si elle tombe dans la periode calendaire EN COURS.

    yf.download(period=...) inclut la periode courante INCOMPLETE (mois/semaine/jour
    entame) : son rendement ne couvre qu'une fraction de periode mais pese comme une
    periode entiere dans l'OLS, et comme le cache des cours expire en 24 h, le beta
    bouge chaque jour. On l'ecarte A LA CONSOMMATION (le cache disque reste brut).

    Periode courante = meme mois civil pour "1mo", meme semaine ISO pour "1wk", meme
    jour pour "1d". Intervalle inconnu -> serie renvoyee inchangee. `today` injectable
    pour les tests. Ne mute jamais la serie d'origine (renvoie une vue tronquee).
    Les index yfinance pouvant etre tz-aware, la comparaison se fait sur les composantes
    calendaires (annee/mois, annee/semaine ISO, date), tz retiree au prealable."""
    if prices is None or len(prices) == 0 or interval not in ("1mo", "1wk", "1d"):
        return prices
    ref = date.today() if today is None else today
    ts = pd.Timestamp(prices.index[-1])
    if ts.tzinfo is not None:
        ts = ts.tz_localize(None)
    if interval == "1mo":
        current = (ts.year, ts.month) == (ref.year, ref.month)
    elif interval == "1wk":
        iso_ts, iso_ref = ts.isocalendar(), ref.isocalendar()
        current = (iso_ts[0], iso_ts[1]) == (iso_ref[0], iso_ref[1])
    else:  # "1d"
        current = ts.date() == ref
    return prices.iloc[:-1] if current else prices


def aligned_returns(stock_prices: pd.Series,
                    index_prices: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Rendements titre & indice calcules sur les MEMES dates (prix alignes d'abord).

    Jointure inner des PRIX sur les dates communes, PUIS pct_change de chaque cote :
    chaque rendement couvre alors le meme intervalle des deux cotes. Sans cet alignement
    prealable, un trou de cotation du titre (suspension, mois sans echange, frequent sur
    small caps) ferait enjamber son pct_change sur deux periodes, regresse contre une
    seule periode d'indice -> biais. Le rendement enjambant est ainsi elimine des deux
    cotes (la date manquante ne survit pas a la jointure)."""
    df = pd.concat([stock_prices.dropna(), index_prices.dropna()],
                   axis=1, join="inner")
    df.columns = ["stock", "index"]
    stock_ret = df["stock"].pct_change().dropna()
    index_ret = df["index"].pct_change().dropna()
    return stock_ret, index_ret


def compute_beta(stock_returns: pd.Series, index_returns: pd.Series,
                 min_obs: int = 24) -> BetaResult:
    """Regresse les rendements du titre sur ceux de l'indice (memes dates).

    Renvoie aussi l'ecart-type OLS de la pente (std_err), la part de rendements du
    titre strictement nuls (zero_return_share, indicateur d'illiquidite) et la fenetre
    effectivement regressee (start/end, dates ISO des premiere/derniere observations)."""
    df = pd.concat([stock_returns, index_returns], axis=1, join="inner")
    df.columns = ["stock", "index"]
    # Ecarte les valeurs non finies (ex: rendement inf si un cours passe par 0).
    df = df.replace([np.inf, -np.inf], np.nan).dropna()
    n = len(df)
    if n == 0:
        return BetaResult(None, None, 0)
    # Diagnostics disponibles des qu'il reste des observations (meme sous le seuil) :
    # illiquidite (rendements titre nuls) et fenetre reelle de regression.
    zero_share = float((df["stock"] == 0.0).mean())
    start, end = _iso_date(df.index[0]), _iso_date(df.index[-1])
    if n < min_obs:
        return BetaResult(None, None, n, zero_return_share=zero_share, start=start, end=end)
    x = df["index"].to_numpy()
    y = df["stock"].to_numpy()
    # Indice constant -> pas de pente estimable. On s'aligne sur add_constant,
    # qui supprime la colonne constante (np.std peut renvoyer ~1e-18, pas 0.0).
    design = sm.add_constant(x)
    if design.shape[1] < 2:
        return BetaResult(None, None, n, zero_return_share=zero_share, start=start, end=end)
    model = sm.OLS(y, design).fit()
    alpha = float(model.params[0])
    beta = float(model.params[1])
    r2 = float(model.rsquared)
    std_err = float(model.bse[1])
    # Filet de securite : ne jamais propager un beta/R2 non fini en aval.
    if not (math.isfinite(beta) and math.isfinite(r2)):
        return BetaResult(None, None, n, zero_return_share=zero_share, start=start, end=end)
    return BetaResult(beta=beta, r2=r2, n_obs=n, alpha=alpha,
                      std_err=std_err if math.isfinite(std_err) else None,
                      zero_return_share=zero_share, start=start, end=end)


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


# Ajustement du beta vers le beta de marche (1,0), poids demandes par l'analyste
# (proches de Blume 2/3-1/3). APPLIQUE AU BETA DESENDETTE (cf. adjusted_beta).
ADJ_BETA_WEIGHT = 0.67
ADJ_MARKET_WEIGHT = 0.33


def adjusted_beta(beta: Optional[float]) -> Optional[float]:
    """Beta ajuste vers le beta de marche : 0,67 x beta + 0,33 x 1,0.

    Applique au beta DESENDETTE : convergence prospective de l'actif economique
    vers le risque de marche. Renvoie None si le beta est absent ou non fini."""
    if beta is None or not math.isfinite(beta):
        return None
    return ADJ_BETA_WEIGHT * beta + ADJ_MARKET_WEIGHT * 1.0


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
    mean_unlevered = statistics.mean(unlevered) if unlevered else None
    return {
        "min_r2": min_r2,
        "n_retained": len(levered),
        "n_excluded_low_r2": excluded,
        "mean_levered": mean_levered,
        "median_levered": statistics.median(levered) if levered else None,
        "mean_adjusted": blume_adjusted(mean_levered),
        "mean_unlevered": mean_unlevered,
        # Ajustement de l'analyste : 0,67 x beta DESENDETTE + 0,33 (convergence vers 1).
        "mean_unlevered_adjusted": adjusted_beta(mean_unlevered),
    }
