"""Enrichissement via l'API Recherche d'entreprises (data.gouv) : SIREN -> nom, NAF, CA.

API publique gratuite, SANS clé : https://recherche-entreprises.api.gouv.fr
Le CA provient des comptes déposés à l'INPI (partiel : holdings -> 0, comptes
confidentiels -> absent).
"""
from __future__ import annotations
from typing import Optional

from comparables import cache

SEARCH_URL = "https://recherche-entreprises.api.gouv.fr/search"
_HEADERS = {"User-Agent": "ncf-comparables/0.1 (interne)"}


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
    """Extrait nom / NAF / nb d'établissements / CA d'un résultat Recherche d'entreprises."""
    ca, ca_year = latest_ca(result.get("finances"))
    nb = result.get("nombre_etablissements")
    return {
        "nom": result.get("nom_complet"),
        "naf": result.get("activite_principale"),
        "nb_etablissements": int(nb) if isinstance(nb, (int, float)) else None,
        "ca": ca,
        "ca_annee": ca_year,
    }


def fetch_company(siren: str) -> Optional[dict]:
    """Recherche une entreprise par SIREN ; renvoie {nom, naf, ca, ca_annee} ou None."""
    if not siren:
        return None
    session = cache.get_session()
    resp = session.get(SEARCH_URL, params={"q": siren, "page": 1, "per_page": 1},
                       headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    results = resp.json().get("results") or []
    if not results:
        return None
    return parse_company(results[0])
