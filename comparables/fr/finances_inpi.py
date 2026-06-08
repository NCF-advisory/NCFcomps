"""Données financières par SIREN depuis le jeu « Ratios Financiers (BCE/INPI) ».

Source publique GRATUITE sans clé (opendatasoft data.economie.gouv.fr) : ~6,5 M de comptes
sociaux NON confidentiels, ~10 exercices, avec CA, EBE, EBIT, résultat. Bien plus riche que
l'API recherche-entreprises (qui n'expose que CA+résultat du dernier exercice).

Couvre les comptes PUBLICS uniquement : les sociétés à comptes confidentiels (art. L232-25)
en sont absentes — limite structurelle commune à toutes les sources gratuites.
"""
from __future__ import annotations
from typing import Optional

from comparables import cache

RATIOS_URL = ("https://data.economie.gouv.fr/api/explore/v2.1"
              "/catalog/datasets/ratios_inpi_bce/records")
_HEADERS = {"User-Agent": "ncf-comparables/0.1 (interne)"}
_FIELDS = ("date_cloture_exercice", "chiffre_d_affaires", "ebe", "ebit",
           "resultat_net", "confidentiality", "type_bilan")


def fetch_financials(siren: str) -> list[dict]:
    """Tous les exercices disponibles d'un SIREN, du plus récent au plus ancien."""
    if not siren:
        return []
    session = cache.get_session()
    resp = session.get(RATIOS_URL, headers=_HEADERS, timeout=40, params={
        "where": f'siren="{siren}"',
        "select": ",".join(_FIELDS),
        "order_by": "date_cloture_exercice desc",
        "limit": 30,
    })
    resp.raise_for_status()
    return resp.json().get("results", [])


def _pick(cand: list[dict], cession_date: Optional[str]) -> Optional[dict]:
    """Parmi `cand`, l'exercice le plus récent clos AVANT la cession ; sinon le plus récent."""
    if not cand:
        return None
    if cession_date:
        before = [f for f in cand if f["date_cloture_exercice"] <= cession_date]
        if before:
            return max(before, key=lambda f: f["date_cloture_exercice"])
    return max(cand, key=lambda f: f["date_cloture_exercice"])


def pick_for_date(financials: list[dict], cession_date: Optional[str],
                  require: str = "chiffre_d_affaires") -> Optional[dict]:
    """Choisit l'exercice pertinent : le plus récent CLOS AVANT la cession et portant la
    donnée requise (CA par défaut) ; sinon le plus récent disponible. PURE (testée)."""
    cand = [f for f in financials
            if f.get(require) and f.get(require) > 0 and f.get("date_cloture_exercice")]
    return _pick(cand, cession_date)


def _positive(f: dict, field: str) -> bool:
    v = f.get(field)
    return isinstance(v, (int, float)) and v > 0


def pick_financials(financials: list[dict], cession_date: Optional[str]) -> Optional[dict]:
    """Comme pick_for_date mais accepte un exercice portant le CA **OU** l'EBE (> 0).

    Permet de calculer un multiple × EBE même quand le CA manque (couverture élargie).
    PURE (testée)."""
    cand = [f for f in financials
            if f.get("date_cloture_exercice") and (_positive(f, "chiffre_d_affaires")
                                                   or _positive(f, "ebe"))]
    return _pick(cand, cession_date)
