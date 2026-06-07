"""Selection des sources par ticker (routage). Point central a faire evoluer.

Strategie cible (gratuite) :
  - Fondamentaux US (ticker sans suffixe) : EDGAR une fois implemente, sinon Yahoo.
  - Fondamentaux EU : Yahoo aujourd'hui ; ESEF en option avancee.
  - Cours (pour le beta) : Yahoo, avec Stooq en secours.
Tant que EDGAR/Stooq/ESEF sont des stubs, on route tout vers Yahoo.
"""
from __future__ import annotations

from comparables.sources.base import DataSource
from comparables.sources.yahoo import YahooSource
# from comparables.sources.edgar import EdgarSource   # TODO: activer une fois implemente
# from comparables.sources.stooq import StooqSource   # TODO
# from comparables.sources.esef import EsefSource      # TODO

_yahoo = YahooSource()


def fundamentals_source_for(ticker: str) -> DataSource:
    # TODO: if "." not in ticker and edgar disponible -> EdgarSource()
    return _yahoo


def price_source_for(ticker: str) -> DataSource:
    # TODO: fallback Stooq si Yahoo echoue
    return _yahoo
