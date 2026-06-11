"""Adaptateur Yahoo Finance (via yfinance). Gratuit, sans cle. Fondamentaux + cours.

Limites connues : champs parfois incomplets sur les small/mid caps ; multiples non
retraites ; acces non officiel (scraping) susceptible de casser. Voir CLAUDE.md.
"""
from __future__ import annotations
import logging
import time
import unicodedata
from typing import Callable, Optional, TypeVar

import pandas as pd
import yfinance as yf

from comparables import cache
from comparables.config import settings
from comparables.models import CompanyRecord
from comparables.sources.base import DataSource

logger = logging.getLogger(__name__)
T = TypeVar("T")

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


def _with_retry(fn: Callable[[], T], what: str) -> Optional[T]:
    """Execute un appel Yahoo avec retry borne + backoff exponentiel.

    Seules les exceptions (erreur reseau, 429...) declenchent un nouvel essai : un
    resultat vide est traite comme un echec definitif par l'appelant (ticker inconnu).
    Renvoie None apres epuisement des tentatives (contrat DataSource : None, pas d'exception).
    """
    attempts = max(1, int(settings.yahoo_max_attempts))
    delay = max(0.0, float(settings.yahoo_backoff_seconds))
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:
            if i == attempts - 1:
                logger.warning("Echec Yahoo (%s) apres %d tentatives : %s", what, attempts, exc)
                return None
            time.sleep(delay * (2 ** i))
    return None


def _val(info: dict, *keys):
    for k in keys:
        v = info.get(k)
        if v is not None and v == v:   # v == v ecarte les NaN
            return v
    return None


def _positive(v) -> Optional[float]:
    """Multiple pre-calcule Yahoo : ne garder que les valeurs finies > 0.

    Un multiple negatif (EBITDA ou resultat negatif) n'a pas de sens pour des
    comparables et polluerait les statistiques d'echantillon."""
    if v is None or not isinstance(v, (int, float)):
        return None
    if v != v or v in (float("inf"), float("-inf")) or v <= 0:
        return None
    return float(v)


def _pick_row(df, names: tuple[str, ...]) -> Optional[float]:
    """Premiere valeur non nulle (exercice le plus recent) parmi des lignes candidates
    d'un etat financier yfinance (index = libelles de lignes, colonnes = exercices)."""
    if df is None or getattr(df, "empty", True):
        return None
    for row in names:
        if row in df.index:
            s = df.loc[row].dropna()
            if not s.empty:
                return float(s.iloc[0])
    return None


def _ebit(tk: "yf.Ticker") -> Optional[float]:
    for attr in ("income_stmt", "financials"):
        try:
            v = _pick_row(getattr(tk, attr), ("EBIT", "Operating Income", "OperatingIncome"))
        except Exception:
            continue
        if v is not None:
            return v
    return None


def _fill_gaps(tk: "yf.Ticker", rec: CompanyRecord) -> None:
    """Comble les champs absents de `info` depuis fast_info et les etats financiers.

    Les small/mid caps ont souvent un `info` lacunaire alors que les etats yfinance
    portent la donnee : ce repli evite des lignes « partielle/vide » inutiles.
    Chaque acces est tolere en echec (None conserve), aucun reseau supplementaire
    n'est force si tout est deja renseigne."""
    if rec.market_cap is None or rec.currency is None:
        try:
            fi = tk.fast_info
            if rec.market_cap is None:
                rec.market_cap = _positive(fi["marketCap"])
            if rec.currency is None:
                rec.currency = fi["currency"] or None
        except Exception:
            pass
    if rec.revenue is None or rec.ebitda is None:
        try:
            stmt = tk.income_stmt
            if rec.revenue is None:
                rec.revenue = _pick_row(stmt, ("Total Revenue", "Operating Revenue"))
            if rec.ebitda is None:
                rec.ebitda = _pick_row(stmt, ("EBITDA", "Normalized EBITDA"))
        except Exception:
            pass
    if rec.total_debt is None or rec.total_cash is None:
        try:
            bs = tk.balance_sheet
            if rec.total_debt is None:
                rec.total_debt = _pick_row(bs, ("Total Debt",))
            if rec.total_cash is None:
                rec.total_cash = _pick_row(
                    bs, ("Cash Cash Equivalents And Short Term Investments",
                         "Cash And Cash Equivalents"))
        except Exception:
            pass


class YahooSource(DataSource):
    name = "yahoo"
    provides_fundamentals = True
    provides_prices = True

    def fetch_fundamentals(self, ticker: str) -> Optional[CompanyRecord]:
        cached = cache.load_cached_fundamentals(ticker)
        if cached is not None:
            return cached
        tk = yf.Ticker(ticker)
        info = _with_retry(lambda: tk.info or {}, f"fondamentaux {ticker}") or {}
        rec = CompanyRecord(
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
            # Multiples pre-calcules Yahoo : repli si nos composants manquent (le
            # pipeline prefere les multiples derives de la VE affichee). Filtres > 0.
            ev_sales=_positive(_val(info, "enterpriseToRevenue")),
            ev_ebitda=_positive(_val(info, "enterpriseToEbitda")),
            pe_trailing=_positive(_val(info, "trailingPE")),
            pe_forward=_positive(_val(info, "forwardPE")),
            pb=_positive(_val(info, "priceToBook")),
            source="yahoo",
        )
        _fill_gaps(tk, rec)
        # Ne cache que les recuperations utiles : figer 72 h un record vide issu d'un
        # echec transitoire empecherait toute nouvelle tentative.
        if rec.name is not None or rec.market_cap is not None:
            cache.store_cached_fundamentals(ticker, rec)
        return rec

    def fetch_prices(self, ticker: str, period: str, interval: str) -> Optional[pd.Series]:
        cached = cache.load_cached_prices(ticker, period, interval)
        if cached is not None:
            return cached
        df = _with_retry(
            lambda: yf.download(ticker, period=period, interval=interval,
                                auto_adjust=True, progress=False),
            f"cours {ticker}",
        )
        if df is None or len(df) == 0:
            return None
        close = df["Close"]
        if hasattr(close, "columns"):          # MultiIndex (cas multi-ticker)
            close = close.iloc[:, 0]
        series = close.dropna()
        cache.store_cached_prices(ticker, period, interval, series)
        return series
