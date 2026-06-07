"""Conversion de devises via l'API Frankfurter (taux de reference BCE). Gratuit, sans cle.

Sert a normaliser capitalisations / VE dans une devise commune pour les visuels,
les comparables couvrant plusieurs devises (USD, CHF, EUR, GBP...).
"""
from __future__ import annotations
from typing import Optional

import requests

_RATE_CACHE: dict[tuple, float] = {}


def get_rate(from_ccy: str, to_ccy: str, date: str = "latest") -> Optional[float]:
    if from_ccy == to_ccy:
        return 1.0
    key = (from_ccy, to_ccy, date)
    if key in _RATE_CACHE:
        return _RATE_CACHE[key]
    try:
        r = requests.get(f"https://api.frankfurter.app/{date}",
                         params={"from": from_ccy, "to": to_ccy}, timeout=10)
        rate = float(r.json()["rates"][to_ccy])
        _RATE_CACHE[key] = rate
        return rate
    except Exception:
        return None


def convert(amount: Optional[float], from_ccy: Optional[str], to_ccy: str,
            date: str = "latest") -> Optional[float]:
    if amount is None or not from_ccy:
        return None
    rate = get_rate(from_ccy, to_ccy, date)
    return amount * rate if rate is not None else None
