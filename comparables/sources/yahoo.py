"""Adaptateur Yahoo Finance (via yfinance). Gratuit, sans cle. Fondamentaux + cours.

Limites connues : champs parfois incomplets sur les small/mid caps ; multiples non
retraites ; acces non officiel (scraping) susceptible de casser. Voir CLAUDE.md.
"""
from __future__ import annotations
import unicodedata
from typing import Optional

import pandas as pd
import yfinance as yf

from comparables import cache
from comparables.models import CompanyRecord
from comparables.sources.base import DataSource

SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search"
_SEARCH_HEADERS = {"User-Agent": "Mozilla/5.0"}
# Places privilegiees (cotation principale) par ordre de preference ; les autres
# (cross-listings, OTC, GDR : MUN, DUS, STU, PNK, IOB, CXE/DXE...) sont depriorisees.
_EXCHANGE_PRIORITY = ("PAR", "AMS", "BRU", "EBR", "LIS", "MIL", "MTA", "MCE", "MAD",
                      "NMS", "NGM", "NCM", "NYQ", "ASE", "PCX", "LSE", "GER",
                      "SWX", "EBS", "VIE", "STO", "CPH", "HEL", "OSL")


def _normalize_query(query: str) -> str:
    """Yahoo gère mal accents et apostrophes (« L'Oréal » -> introuvable) : on les retire."""
    q = unicodedata.normalize("NFKD", query)
    q = "".join(c for c in q if not unicodedata.combining(c))   # retire les accents
    return q.replace("'", "").replace("’", "").strip()      # retire les apostrophes


def _parse_search(payload: dict) -> list[dict]:
    """Extrait les actions (EQUITY) d'une reponse de recherche Yahoo."""
    out = []
    for q in (payload or {}).get("quotes", []):
        if q.get("quoteType") == "EQUITY" and q.get("symbol"):
            out.append({"symbol": q["symbol"],
                        "name": q.get("longname") or q.get("shortname") or "",
                        "exchange": q.get("exchange", "")})
    return out


def _rank(candidates: list[dict]) -> list[dict]:
    """Trie les candidats : place principale d'abord (cf. _EXCHANGE_PRIORITY), ordre Yahoo ensuite."""
    def score(item):
        i, c = item
        ex = c.get("exchange", "")
        return (_EXCHANGE_PRIORITY.index(ex) if ex in _EXCHANGE_PRIORITY else 999, i)
    return [c for _, c in sorted(enumerate(candidates), key=score)]


def search_symbol(query: str) -> list[dict]:
    """Recherche un nom de societe -> liste de candidats {symbol, name, exchange}, classes."""
    if not query or not query.strip():
        return []
    session = cache.get_session()
    resp = session.get(SEARCH_URL, headers=_SEARCH_HEADERS, timeout=20,
                       params={"q": _normalize_query(query), "quotesCount": 8, "newsCount": 0})
    resp.raise_for_status()
    return _rank(_parse_search(resp.json()))


def best_symbol(query: str) -> Optional[dict]:
    """Meilleur ticker pour un nom de societe (place principale privilegiee), ou None."""
    cands = search_symbol(query)
    return cands[0] if cands else None


def _val(info: dict, *keys):
    for k in keys:
        v = info.get(k)
        if v is not None and v == v:   # v == v ecarte les NaN
            return v
    return None


def _ebit(tk: "yf.Ticker") -> Optional[float]:
    for attr in ("income_stmt", "financials"):
        try:
            df = getattr(tk, attr)
            if df is None or df.empty:
                continue
            for row in ("EBIT", "Operating Income", "OperatingIncome"):
                if row in df.index:
                    s = df.loc[row].dropna()
                    if not s.empty:
                        return float(s.iloc[0])
        except Exception:
            continue
    return None


class YahooSource(DataSource):
    name = "yahoo"
    provides_fundamentals = True
    provides_prices = True

    def fetch_fundamentals(self, ticker: str) -> Optional[CompanyRecord]:
        tk = yf.Ticker(ticker)
        try:
            info = tk.info or {}
        except Exception:
            info = {}
        return CompanyRecord(
            ticker=ticker,
            name=_val(info, "longName", "shortName"),
            country=_val(info, "country"),
            sector=_val(info, "sector"),
            currency=_val(info, "currency"),
            market_cap=_val(info, "marketCap"),
            enterprise_value=_val(info, "enterpriseValue"),
            total_debt=_val(info, "totalDebt"),
            total_cash=_val(info, "totalCash"),
            revenue=_val(info, "totalRevenue"),
            ebitda=_val(info, "ebitda"),
            ebit=_ebit(tk),
            beta_source=_val(info, "beta", "beta3Year"),
            ev_sales=_val(info, "enterpriseToRevenue"),
            ev_ebitda=_val(info, "enterpriseToEbitda"),
            pe_trailing=_val(info, "trailingPE"),
            pe_forward=_val(info, "forwardPE"),
            pb=_val(info, "priceToBook"),
            source="yahoo",
        )

    def fetch_prices(self, ticker: str, period: str, interval: str) -> Optional[pd.Series]:
        cached = cache.load_cached_prices(ticker, period, interval)
        if cached is not None:
            return cached
        df = yf.download(ticker, period=period, interval=interval,
                         auto_adjust=True, progress=False)
        if df is None or len(df) == 0:
            return None
        close = df["Close"]
        if hasattr(close, "columns"):          # MultiIndex (cas multi-ticker)
            close = close.iloc[:, 0]
        series = close.dropna()
        cache.store_cached_prices(ticker, period, interval, series)
        return series
