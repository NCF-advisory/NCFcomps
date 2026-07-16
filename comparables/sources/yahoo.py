"""Adaptateur Yahoo Finance (via yfinance). Gratuit, sans cle. Fondamentaux + cours.

Limites connues : champs parfois incomplets sur les small/mid caps ; multiples non
retraites ; acces non officiel (scraping) susceptible de casser. Voir CLAUDE.md.
"""
from __future__ import annotations
import logging
import re
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
                      "NMS", "NGM", "NCM", "NYQ", "ASE", "PCX", "TOR", "LSE", "GER",
                      "SWX", "EBS", "VIE", "STO", "CPH", "HEL", "OSL")
# Places SECONDAIRES (regionales allemandes, parquet Francfort) : sous la cotation
# principale (GER = Xetra). OTC / pink sheets / cross-listings : tout en bas (une
# cotation OTC n'a ni la liquidite ni la devise locale qu'on veut pour un beta).
_SECONDARY_EXCHANGES = frozenset({"FRA", "MUN", "STU", "DUS", "HAM", "HAN", "BER"})
_OTC_EXCHANGES = frozenset({"PNK", "PINX", "OTC", "OBB", "OOTC", "IOB", "DXE", "CXE", "NEO"})

# Formes juridiques retirees AVANT la recherche (elles degradent la pertinence Yahoo
# et font remonter les ADR/OTC) : « Voestalpine AG » -> « Voestalpine ».
_LEGAL_FORMS = frozenset({
    "ag", "se", "sa", "spa", "sas", "nv", "ab", "asa", "as", "oyj", "oy", "plc", "llc",
    "inc", "incorporated", "corp", "corporation", "co", "company", "ltd", "limited",
    "holding", "holdings", "group", "groupe", "gmbh", "kgaa", "sca", "aktiengesellschaft",
})


# Translitteration allemande : Yahoo indexe les umlauts en oe/ae/ue (« Klöckner » ->
# « Kloeckner »), pas en o/a/u. A appliquer AVANT le retrait generique des accents
# (sinon « ö » -> « o » et la recherche « Klockner » ne ramene rien).
_GERMAN_TRANSLIT = str.maketrans({
    "ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss",
})


def _normalize_query(query: str) -> str:
    """Yahoo gère mal accents et apostrophes (« L'Oréal » -> introuvable) : on les retire.
    Les umlauts allemands sont translittérés en oe/ae/ue/ss (graphie indexée par Yahoo)."""
    q = query.translate(_GERMAN_TRANSLIT)                    # ö->oe (allemand) AVANT le strip
    q = unicodedata.normalize("NFKD", q)
    q = "".join(c for c in q if not unicodedata.combining(c))   # retire les accents restants
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


def _strip_legal_forms(name: str) -> str:
    """Retire les formes juridiques (« Voestalpine AG » -> « Voestalpine ») et le « & ».

    Elles degradent la pertinence de la recherche Yahoo et font remonter les cotations
    ADR/OTC. On garde le nom original si tout serait retire (ex. nom = « Holding »)."""
    kept = [t for t in name.replace("&", " ").split()
            if re.sub(r"[^a-z0-9]", "", t.lower()) not in _LEGAL_FORMS]   # « S.A. » -> « sa »
    return " ".join(kept) if kept else name


def _exchange_tier(exchange: str) -> int:
    """Niveau de place : 0 principale, 1 secondaire (regionale DE), 2 inconnue, 3 OTC."""
    if exchange in _EXCHANGE_PRIORITY:
        return 0
    if exchange in _SECONDARY_EXCHANGES:
        return 1
    if exchange in _OTC_EXCHANGES:
        return 3
    return 2


def _isin_like(symbol: str) -> bool:
    """Symbole de type ISIN (« AT0000A3A9Z9.VI ») : ligne technique, depriorisee
    face au ticker propre de la meme societe (« VOE.VI »)."""
    root = symbol.split(".")[0]
    return bool(re.fullmatch(r"[A-Z]{2}[0-9A-Z]{9,}", root))


def _tokens(text: str) -> list[str]:
    """Tokens alphanumeriques significatifs (sans accents, formes juridiques, casse)."""
    return re.findall(r"[a-z0-9]+", _normalize_query(_strip_legal_forms(text)).lower())


def _name_match(query: str, name: str) -> tuple[bool, float]:
    """(passe la porte ?, score [0..1]) entre la requete et le nom du candidat.

    Couverture des deux cotes : le candidat couvre-t-il la requete (query_cov) ET sans
    tokens parasites en plus (cand_cov) ? cand_cov elimine les trackers/certificats
    (« RBI OETrackX3 voestalpine » : 1 token utile noye dans 3 parasites) et la porte
    elimine les autres societes (« AG » -> First Majestic Silver)."""
    q, c = set(_tokens(query)), set(_tokens(name))
    if not q or not c:
        return (False, 0.0)
    overlap = q & c
    query_cov = len(overlap) / len(q)        # le candidat contient-il ce que je cherche ?
    cand_cov = len(overlap) / len(c)          # ... sans bruit (tracker, autre entite) ?
    passes = query_cov >= 0.6 and cand_cov >= 0.5
    return (passes, query_cov * cand_cov)


def _score_candidates(query: str, candidates: list[dict]) -> list[dict]:
    """Classe les candidats par : bonne societe (nom) -> place principale -> ticker propre.

    Cle de tri (croissante) : (porte de ressemblance, niveau de place, penalite ISIN,
    -ressemblance, ordre Yahoo). La porte passe AVANT la place : une cotation principale
    d'une AUTRE societe (ou un tracker) ne doit jamais battre la bonne societe."""
    scored = []
    for i, c in enumerate(candidates):
        passes, score = _name_match(query, c.get("name", ""))
        key = (
            0 if passes else 1,
            _exchange_tier(c.get("exchange", "")),
            1 if _isin_like(c.get("symbol", "")) else 0,
            -round(score, 3),
            i,
        )
        scored.append((key, c))
    return [c for _, c in sorted(scored, key=lambda x: x[0])]


def search_symbol(query: str) -> list[dict]:
    """Recherche un nom de societe -> candidats {symbol, name, exchange} classes (meilleur d'abord).

    La requete envoyee a Yahoo est nettoyee des formes juridiques ; le classement, lui,
    note la ressemblance au nom ORIGINAL (place principale + ticker propre privilegies)."""
    if not query or not query.strip():
        return []
    session = cache.get_session()
    resp = session.get(SEARCH_URL, headers=_SEARCH_HEADERS, timeout=20,
                       params={"q": _normalize_query(_strip_legal_forms(query)),
                               "quotesCount": 10, "newsCount": 0})
    resp.raise_for_status()
    return _score_candidates(query, _parse_search(resp.json()))


def best_symbol(query: str) -> Optional[dict]:
    """Meilleur ticker pour un nom de societe (place principale privilegiee), ou None."""
    cands = search_symbol(query)
    return cands[0] if cands else None


# Places allemandes (Xetra + parquets regionaux) : la cotation principale est Xetra (.DE).
_GERMAN_VENUES = _SECONDARY_EXCHANGES | {"GER"}
_MAX_PRIMARY_PROBES = 3


def _needs_primary_probe(candidate: dict) -> bool:
    """Le meilleur candidat est-il douteux : place non principale (tier >= 1) ou symbole ISIN ?

    C'est le seul cas ou l'on sonde (les cotations principales propres ne coutent aucun appel)."""
    return (_exchange_tier(candidate.get("exchange", "")) >= 1
            or _isin_like(candidate.get("symbol", "")))


def _primary_guesses(candidates: list[dict]) -> list[dict]:
    """Tickers de place principale a sonder, reconstruits depuis les racines des candidats.

    Yahoo masque souvent la cotation Xetra (.DE) / Vienne (.VI) dans la recherche par nom :
    on la reconstruit (racine partagee + suffixe du marche d'origine deduit des places des
    candidats), a charge ensuite de la VALIDER (_symbol_trades) avant de l'adopter."""
    exchanges = {c.get("exchange", "") for c in candidates}
    if "VIE" in exchanges:
        suffix, primary = ".VI", "VIE"
    elif exchanges & _GERMAN_VENUES:
        suffix, primary = ".DE", "GER"
    else:
        return []
    out: list[dict] = []
    seen: set[str] = set()
    for c in candidates:
        root = c.get("symbol", "").split(".")[0]
        if root.isalpha() and 2 <= len(root) <= 4 and root not in seen:
            seen.add(root)
            out.append({"symbol": root + suffix, "name": c.get("name", ""), "exchange": primary})
    return out[:_MAX_PRIMARY_PROBES]


def _symbol_trades(symbol: str) -> bool:
    """Le symbole existe-t-il et cote-t-il (appel leger 5 jours) ? Filet : jamais d'exception."""
    try:
        h = yf.Ticker(symbol).history(period="5d", interval="1d")
        return h is not None and len(h) > 0
    except Exception:
        return False


def resolve_candidates(query: str, limit: int = 6) -> dict:
    """Resolution d'un nom : {query, match (meilleur), alternatives (suivants)}.

    Quand le meilleur candidat est douteux (place secondaire/OTC ou ISIN), on tente de
    reconstruire et de VALIDER la cotation principale (.DE/.VI, absente de la recherche
    Yahoo par nom) ; validee, elle passe en tete. Les cas propres ne coutent aucun appel."""
    cands = search_symbol(query)
    if cands and _needs_primary_probe(cands[0]):
        existing = {c["symbol"] for c in cands}
        for guess in _primary_guesses(cands):
            if guess["symbol"] not in existing and _symbol_trades(guess["symbol"]):
                cands = [guess, *cands]      # place principale validee -> en tete
                break
    return {
        "query": query,
        "match": cands[0] if cands else None,
        "alternatives": cands[1:limit],
    }


def _is_fetchable_symbol(ticker: Optional[str]) -> bool:
    """Vrai si `ticker` ressemble a un symbole Yahoo (pas d'espace interne).

    Un libelle multi-mots saisi comme ticker (« VOESTALPINE AG ») serait decoupe
    par yfinance en plusieurs symboles et ramenerait les cours d'une AUTRE societe
    (« AG » = First Majestic Silver) : on refuse net plutot que de renvoyer une
    donnee silencieusement fausse. Pour rechercher par nom, passer par best_symbol()."""
    if not ticker:
        return False
    t = ticker.strip()
    return bool(t) and not any(c.isspace() for c in t)


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
        if not _is_fetchable_symbol(ticker):     # libelle multi-mots saisi comme ticker
            return None
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
            industry=_val(info, "industry", "industryDisp"),   # ex. « Steel » -> Damodaran
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
        if not _is_fetchable_symbol(ticker):     # « VOESTALPINE AG » -> yfinance ramene « AG »
            return None
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
