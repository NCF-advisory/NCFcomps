"""2e source financière FR : API INPI RNE (Registre National des Entreprises).

Compte **GRATUIT** sur https://data.inpi.fr (identifiants via `.env` : INPI_RNE_USERNAME /
INPI_RNE_PASSWORD). Sert de complément quand le jeu Ratios INPI/BCE n'a ni CA ni EBE pour un
SIREN (cf. finances_inpi). Le RNE expose les **comptes annuels déposés** — potentiellement plus
larges/récents — mais les comptes **confidentiels** restent masqués partout (limite structurelle).

État : le client d'authentification et de récupération est implémenté (endpoints stables et
documentés) ; l'EXTRACTION du CA/EBE depuis la structure des bilans déposés est volontairement
laissée en no-op (`_extract_financials` -> []) tant qu'elle n'a pas été validée sur une **vraie
réponse** (nécessite un compte). Brancher dans le pipeline en même temps que sa finalisation,
pour ne pas injecter de chiffres non vérifiés. `is_configured()` garde tout dormant sans clé.
"""
from __future__ import annotations
import logging
from typing import Optional

from comparables import cache
from comparables.config import settings

logger = logging.getLogger(__name__)

LOGIN_URL = "https://registre-national-entreprises.inpi.fr/api/sso/login"
COMPANY_URL = "https://registre-national-entreprises.inpi.fr/api/companies/{siren}"
_HEADERS = {"User-Agent": "ncf-comparables/0.1 (interne)"}

_token: Optional[str] = None


def is_configured() -> bool:
    """Des identifiants INPI RNE sont-ils fournis (.env) ? Sinon la source reste inactive."""
    return bool(settings.inpi_rne_username and settings.inpi_rne_password)


def _get_token(force: bool = False) -> Optional[str]:
    """Jeton bearer RNE (mémoïsé). None si non configuré ou échec d'auth."""
    global _token
    if not is_configured():
        return None
    if _token and not force:
        return _token
    session = cache.get_session()
    resp = session.post(LOGIN_URL, headers=_HEADERS, timeout=30, json={
        "username": settings.inpi_rne_username, "password": settings.inpi_rne_password})
    resp.raise_for_status()
    _token = resp.json().get("token")
    return _token


def _extract_financials(company: dict) -> list[dict]:
    """Convertit la réponse RNE en exercices {date_cloture_exercice, chiffre_d_affaires, ebe,
    ebit, ...} — MÊME forme que finances_inpi, pour rester interchangeable.

    NON FINALISÉ : à compléter sur une vraie réponse RNE (les comptes déposés peuvent être des
    bilans « saisis » structurés ou des liasses). Renvoie [] pour ne JAMAIS injecter de chiffres
    non vérifiés dans les médianes.
    """
    logger.debug("RNE _extract_financials non finalisé (réponse à valider)")
    return []


def fetch_financials_rne(siren: str) -> list[dict]:
    """Exercices financiers d'un SIREN via le RNE, ou [] (non configuré / non finalisé / échec)."""
    if not siren or not is_configured():
        return []
    try:
        token = _get_token()
        if not token:
            return []
        session = cache.get_session()
        resp = session.get(COMPANY_URL.format(siren=siren), timeout=30,
                           headers={**_HEADERS, "Authorization": f"Bearer {token}"})
        resp.raise_for_status()
        return _extract_financials(resp.json())
    except Exception as exc:                         # une source de secours ne casse jamais le lot
        logger.warning("Echec RNE SIREN %s : %s", siren, exc)
        return []
