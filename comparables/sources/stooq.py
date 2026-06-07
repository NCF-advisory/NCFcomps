"""Adaptateur Stooq - ABANDONNE (stub conserve pour memoire).

Constat 2026-06-03 : l'historique CSV gratuit de Stooq a ete ferme. L'endpoint
https://stooq.com/q/d/l/?s=<symbole>&i=d (et .pl, et avec plage de dates) renvoie
desormais « Get your apikey: » au lieu des donnees -> il faut une cle API (payante).
Seule la cotation instantanee https://stooq.com/q/l/?s=<symbole>&e=csv reste gratuite,
mais elle ne donne qu'un seul cours du jour : insuffisant pour une regression de beta.

Il n'existe donc plus de source de cours de secours STRICTEMENT GRATUITE. yfinance reste
l'unique source de cours (voir CLAUDE.md, Step 4 abandonne). Ne pas reimplementer sans
cle API valide ; le cas echeant, la brancher via .env comme FMP/AlphaVantage.
"""
from __future__ import annotations
from typing import Optional

import pandas as pd

from comparables.sources.base import DataSource


class StooqSource(DataSource):
    name = "stooq"
    provides_fundamentals = False
    provides_prices = True

    def fetch_prices(self, ticker: str, period: str, interval: str) -> Optional[pd.Series]:
        raise NotImplementedError("StooqSource.fetch_prices : a implementer (voir docstring).")
