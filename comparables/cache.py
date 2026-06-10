"""Couche de cache : sessions HTTP cachees (sources `requests`) et cache disque des cours.

- get_session() : session `requests` avec cache SQLite, pour EDGAR/FX/FMP (respect des quotas).
  yfinance gere son propre transport (curl_cffi) et ne passe pas par cette session.
- load_cached_prices / store_cached_prices : cache disque des series de cours yfinance, pour
  ne pas re-telecharger l'historique a chaque execution (cle = ticker + periode + intervalle).
- load_cached_fundamentals / store_cached_fundamentals : cache disque (JSON) des fondamentaux
  Yahoo, l'appel le plus lourd et le plus throttle (TTL plus long que les cours).
"""
from __future__ import annotations
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import requests_cache

from comparables.config import settings
from comparables.models import CompanyRecord


def get_session(expire_after: int = 24 * 3600) -> requests_cache.CachedSession:
    """Session HTTP avec cache SQLite (defaut : 24 h)."""
    backend = requests_cache.SQLiteCache(settings.cache_path)
    return requests_cache.CachedSession(backend=backend, expire_after=expire_after)


# --- Cache disque des series de cours (yfinance n'utilise pas `requests`) ---

def _price_ttl_seconds() -> int:
    return int(getattr(settings, "price_cache_ttl_hours", 24)) * 3600


def _price_cache_dir() -> Path:
    """Dossier `prices/` a cote du cache SQLite ; cree au besoin."""
    d = Path(settings.cache_path).parent / "prices"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _price_key(ticker: str, period: str, interval: str) -> str:
    raw = f"{ticker}__{period}__{interval}"
    return "".join(ch if ch.isalnum() else "_" for ch in raw)


def load_cached_prices(ticker: str, period: str, interval: str) -> Optional[pd.Series]:
    """Serie de cours en cache si presente et non expiree, sinon None."""
    ttl = _price_ttl_seconds()
    if ttl <= 0:                       # cache desactive
        return None
    path = _price_cache_dir() / f"{_price_key(ticker, period, interval)}.pkl"
    if not path.exists() or (time.time() - path.stat().st_mtime) > ttl:
        return None
    try:
        s = pd.read_pickle(path)       # cache local de confiance (donnees produites par nous)
    except Exception:
        return None                    # cache illisible (version pandas...) -> on re-telecharge
    return s if isinstance(s, pd.Series) and not s.empty else None


def store_cached_prices(ticker: str, period: str, interval: str,
                        series: Optional[pd.Series]) -> None:
    """Enregistre une serie de cours sur disque ; ignore les series vides/None."""
    if _price_ttl_seconds() <= 0:
        return
    if not isinstance(series, pd.Series) or series.empty:
        return
    path = _price_cache_dir() / f"{_price_key(ticker, period, interval)}.pkl"
    try:
        series.to_pickle(path)
    except Exception:
        pass                           # un echec d'ecriture du cache ne doit jamais casser le calcul


# --- Cache disque des fondamentaux (CompanyRecord serialise en JSON) ---

def _fundamentals_ttl_seconds() -> int:
    return int(getattr(settings, "fundamentals_cache_ttl_hours", 72)) * 3600


def _fundamentals_cache_dir() -> Path:
    d = Path(settings.cache_path).parent / "fundamentals"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_cached_fundamentals(ticker: str) -> Optional[CompanyRecord]:
    """CompanyRecord en cache si present et non expire, sinon None."""
    ttl = _fundamentals_ttl_seconds()
    if ttl <= 0:
        return None
    path = _fundamentals_cache_dir() / f"{_price_key(ticker, 'fund', 'json')}.json"
    if not path.exists() or (time.time() - path.stat().st_mtime) > ttl:
        return None
    try:
        return CompanyRecord.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception:
        return None                    # cache illisible -> on re-telecharge


def store_cached_fundamentals(ticker: str, record: Optional[CompanyRecord]) -> None:
    """Enregistre un CompanyRecord sur disque ; ignore None."""
    if _fundamentals_ttl_seconds() <= 0 or record is None:
        return
    path = _fundamentals_cache_dir() / f"{_price_key(ticker, 'fund', 'json')}.json"
    try:
        path.write_text(record.model_dump_json(), encoding="utf-8")
    except Exception:
        pass                           # un echec d'ecriture du cache ne doit jamais casser le calcul
