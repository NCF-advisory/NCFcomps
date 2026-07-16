"""Recuperation des cours / infos Yahoo pour le harnais de benchmark.

Cache disque (pickle) par cle ticker+fenetre : les relances du harnais ne
retelechargent pas. Fetch serialise avec throttle + backoff simple sur 429/erreur.
Ne depend d'aucun module produit reseau (import direct de yfinance).
"""
from __future__ import annotations

import pickle
import time
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd
import yfinance as yf

CACHE_DIR = Path(__file__).resolve().parent / ".cache"
CACHE_DIR.mkdir(exist_ok=True)

_THROTTLE_S = 0.6          # pause mini entre deux appels reseau
_MAX_ATTEMPTS = 4
_BACKOFF_S = 3.0
_last_call = {"t": 0.0}


def _throttle() -> None:
    dt = time.time() - _last_call["t"]
    if dt < _THROTTLE_S:
        time.sleep(_THROTTLE_S - dt)
    _last_call["t"] = time.time()


def _cache_path(key: str) -> Path:
    safe = key.replace("/", "_").replace(":", "_").replace(" ", "_")
    return CACHE_DIR / f"{safe}.pkl"


def _load_cache(key: str):
    p = _cache_path(key)
    if p.exists():
        try:
            with open(p, "rb") as f:
                return pickle.load(f)
        except Exception:
            return None
    return None


def _store_cache(key: str, value) -> None:
    try:
        with open(_cache_path(key), "wb") as f:
            pickle.dump(value, f)
    except Exception:
        pass


def _extract_close(df: pd.DataFrame, ticker: str) -> Optional[pd.Series]:
    if df is None or len(df) == 0:
        return None
    cols = df.columns
    if isinstance(cols, pd.MultiIndex):
        # yfinance recent : colonnes ('Close', TICKER)
        if "Close" in cols.get_level_values(0):
            sub = df["Close"]
            s = sub[ticker] if ticker in sub.columns else sub.iloc[:, 0]
        else:
            return None
    else:
        if "Close" not in cols:
            return None
        s = df["Close"]
    s = pd.to_numeric(s, errors="coerce").dropna()
    if s.index.tz is not None:
        s.index = s.index.tz_localize(None)
    return s if len(s) else None


def fetch_prices(ticker: str, start: date, end: date) -> Optional[pd.Series]:
    """Cours de cloture ajustes (quotidiens) [start, end], via cache disque.

    Renvoie None (consigne) si Yahoo ne renvoie rien apres retries."""
    key = f"px_{ticker}_{start.isoformat()}_{end.isoformat()}"
    cached = _load_cache(key)
    if cached is not None:
        return cached if (isinstance(cached, pd.Series) and len(cached)) else None
    series: Optional[pd.Series] = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        _throttle()
        try:
            df = yf.download(ticker, start=start.isoformat(),
                             end=(end).isoformat(), interval="1d",
                             auto_adjust=True, progress=False, threads=False)
            series = _extract_close(df, ticker)
            if series is not None:
                break
        except Exception:
            series = None
        if attempt < _MAX_ATTEMPTS:
            time.sleep(_BACKOFF_S * attempt)
    # On memorise meme un None (serie vide) pour ne pas re-tenter en boucle.
    _store_cache(key, series if series is not None else pd.Series(dtype=float))
    return series


def fetch_info(ticker: str) -> dict:
    """info Yahoo (beta publie, industrie, devise), tolerant a l'echec. Cache disque."""
    key = f"info_{ticker}"
    cached = _load_cache(key)
    if cached is not None:
        return cached
    out: dict = {"beta": None, "industry": None, "currency": None}
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        _throttle()
        try:
            info = yf.Ticker(ticker).info
            if info:
                out["beta"] = info.get("beta")
                out["industry"] = info.get("industry")
                out["currency"] = info.get("currency")
                break
        except Exception:
            pass
        if attempt < _MAX_ATTEMPTS:
            time.sleep(_BACKOFF_S * attempt)
    _store_cache(key, out)
    return out
