"""Enrichissement via l'API Recherche d'entreprises (data.gouv) : SIREN -> nom, NAF, CA.

API publique gratuite, SANS clé : https://recherche-entreprises.api.gouv.fr
Le CA provient des comptes déposés à l'INPI (partiel : holdings -> 0, comptes
confidentiels -> absent).

Garde-fou de débit : l'API limite à 7 req/s par IP -> cadence minimale entre appels
réseau (les réponses servies par le cache ne comptent pas) + retry avec back-off sur 429.
"""
from __future__ import annotations
import time
from typing import Optional

from comparables import cache

SEARCH_URL = "https://recherche-entreprises.api.gouv.fr/search"
_HEADERS = {"User-Agent": "ncf-comparables/0.1 (interne)"}

_MIN_INTERVAL_SECONDS = 0.2     # < 7 req/s (limite publique par IP)
_RETRY_DELAYS = (1.0, 3.0)      # back-off après un 429
_last_call = 0.0


def latest_ca(finances: Optional[dict]) -> tuple[Optional[float], Optional[int]]:
    """CA le plus récent strictement positif (et son année) à partir du bloc `finances`."""
    if not isinstance(finances, dict):
        return (None, None)
    best_year: Optional[int] = None
    best_ca: Optional[float] = None
    for year, vals in finances.items():
        if not isinstance(vals, dict):
            continue
        ca = vals.get("ca")
        try:
            yr = int(year)
        except (TypeError, ValueError):
            continue
        if isinstance(ca, (int, float)) and ca > 0 and (best_year is None or yr > best_year):
            best_year, best_ca = yr, float(ca)
    return (best_ca, best_year)


def parse_company(result: dict) -> dict:
    """Extrait nom / NAF / CA d'un résultat de l'API Recherche d'entreprises."""
    ca, ca_year = latest_ca(result.get("finances"))
    return {
        "nom": result.get("nom_complet"),
        "naf": result.get("activite_principale"),
        "ca": ca,
        "ca_annee": ca_year,
    }


def _throttled_get(session, params: dict):
    """GET cadencé (7 req/s max) avec retry sur 429 ; lève sur échec persistant."""
    global _last_call
    resp = None
    for delay in (0.0,) + _RETRY_DELAYS:
        if delay:
            time.sleep(delay)
        wait = _MIN_INTERVAL_SECONDS - (time.monotonic() - _last_call)
        if wait > 0:
            time.sleep(wait)
        resp = session.get(SEARCH_URL, params=params, headers=_HEADERS, timeout=30)
        if not getattr(resp, "from_cache", False):
            _last_call = time.monotonic()
        if resp.status_code != 429:
            break
    resp.raise_for_status()
    return resp


def fetch_company(siren: str) -> Optional[dict]:
    """Recherche une entreprise par SIREN ; renvoie {nom, naf, ca, ca_annee} ou None."""
    if not siren:
        return None
    session = cache.get_session()
    resp = _throttled_get(session, {"q": siren, "page": 1, "per_page": 1})
    results = resp.json().get("results") or []
    if not results:
        return None
    return parse_company(results[0])
