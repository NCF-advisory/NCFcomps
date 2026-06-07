"""Interface commune a toutes les sources de donnees (adapter pattern).

Pour AJOUTER une source : creer un module dans ce dossier, sous-classer DataSource,
declarer les capacites (provides_fundamentals / provides_prices) et implementer les
methodes utiles. Enregistrer ensuite la source dans registry.py.
"""
from __future__ import annotations
from abc import ABC
from typing import Optional

import pandas as pd

from comparables.models import CompanyRecord


class DataSource(ABC):
    name: str = "base"
    provides_fundamentals: bool = False
    provides_prices: bool = False

    def supports(self, ticker: str) -> bool:
        """La source sait-elle traiter ce ticker ? (par defaut : oui)."""
        return True

    def fetch_fundamentals(self, ticker: str) -> Optional[CompanyRecord]:
        """Retourne les fondamentaux (capi, dette, EBITDA, multiples...) ou None."""
        raise NotImplementedError

    def fetch_prices(self, ticker: str, period: str, interval: str) -> Optional[pd.Series]:
        """Retourne une serie de cours de cloture (index = dates) ou None."""
        raise NotImplementedError
