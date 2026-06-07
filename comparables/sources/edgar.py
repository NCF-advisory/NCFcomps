"""Adaptateur SEC EDGAR (data.sec.gov) - fondamentaux des societes COTEES AMERICAINES.

Gratuit, officiel, sans cle. A IMPLEMENTER (stub).

Plan d'implementation :
  1. Resoudre le CIK depuis le ticker via
     https://www.sec.gov/files/company_tickers.json   (ou data.sec.gov/.../company_tickers.json)
  2. Recuperer les faits XBRL :
     https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json   (CIK sur 10 chiffres)
  3. Extraire les concepts US-GAAP utiles (annee la plus recente, formulaire 10-K) :
     Revenues / RevenueFromContractWithCustomerExcludingAssessedTax,
     OperatingIncomeLoss (EBIT), NetIncomeLoss, Assets, StockholdersEquity,
     dette (LongTermDebt(+Current)) et tresorerie (CashAndCashEquivalentsAtCarryingValue).
  4. Mapper vers CompanyRecord (market_cap NON fourni par EDGAR : a recuperer via une
     source de cours/capitalisation).

Contraintes : limite ~10 req/s, en-tete User-Agent OBLIGATOIRE (ex: "Cabinet X contact@x.fr"),
sinon reponse 403. Mettre en cache (voir comparables.cache).
"""
from __future__ import annotations
from typing import Optional

from comparables.models import CompanyRecord
from comparables.sources.base import DataSource

SEC_USER_AGENT = "comparables-tool contact@example.com"  # TODO: personnaliser


class EdgarSource(DataSource):
    name = "edgar"
    provides_fundamentals = True
    provides_prices = False

    def supports(self, ticker: str) -> bool:
        # EDGAR ne couvre que les societes deposant aupres de la SEC (US) -> ticker sans suffixe
        return "." not in ticker

    def fetch_fundamentals(self, ticker: str) -> Optional[CompanyRecord]:
        raise NotImplementedError("EdgarSource.fetch_fundamentals : a implementer (voir docstring).")
