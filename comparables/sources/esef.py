"""Adaptateur ESEF (filings.xbrl.org) - fondamentaux des societes COTEES EUROPEENNES.

Gratuit mais AVANCE : les rapports annuels sont en Inline XBRL et la recuperation
automatisee est inegale selon les pays. A IMPLEMENTER plus tard (stub).

Pistes :
  - Index des depots : https://filings.xbrl.org/  (API / listing par entite, LEI)
  - Parser le XBRL avec arelle (https://arelle.org) ou un parseur iXBRL.
  - Mapper les concepts IFRS (Revenue, ProfitLossFromOperatingActivities,
    Equity, dette financiere, tresorerie) vers CompanyRecord.
Reserve : a defaut, Yahoo couvre (imparfaitement) les valeurs europeennes.
"""
from __future__ import annotations
from typing import Optional

from comparables.models import CompanyRecord
from comparables.sources.base import DataSource


class EsefSource(DataSource):
    name = "esef"
    provides_fundamentals = True
    provides_prices = False

    def supports(self, ticker: str) -> bool:
        return "." in ticker  # places europeennes (a affiner par suffixe)

    def fetch_fundamentals(self, ticker: str) -> Optional[CompanyRecord]:
        raise NotImplementedError("EsefSource.fetch_fundamentals : a implementer (voir docstring).")
