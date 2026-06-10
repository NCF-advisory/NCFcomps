"""Client API INPI / Registre national des entreprises (comptes annuels déposés).

Authentification par compte INPI (gratuit, data.inpi.fr) : INPI_USERNAME / INPI_PASSWORD
dans .env. Sans credentials, `configured()` est False et l'enrichissement par les
comptes déposés est simplement sauté (le dataset ratios INPI/BCE reste la source 1).

Endpoints (documentation INPI « API RNE ») :
    POST /api/sso/login                      {username, password} -> {token}
    GET  /api/companies/{siren}/attachments  -> {bilans: [...], actes: [...], ...}
    GET  /api/bilans/{id}/download           -> PDF (bytes)

NB : schémas à confirmer au premier appel réel (credentials requis) — voir tests mockés.
"""
from __future__ import annotations
import logging
from typing import Optional

import requests

from comparables.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://registre-national-entreprises.inpi.fr/api"
_TIMEOUT = 40


def configured() -> bool:
    return bool(settings.inpi_username and settings.inpi_password)


class InpiClient:
    """Session authentifiée RNE : login paresseux + une seule re-tentative sur 401."""

    def __init__(self, session: Optional[requests.Session] = None):
        self._session = session or requests.Session()
        self._token: Optional[str] = None

    def _login(self) -> None:
        resp = self._session.post(f"{BASE_URL}/sso/login", timeout=_TIMEOUT,
                                  json={"username": settings.inpi_username,
                                        "password": settings.inpi_password})
        resp.raise_for_status()
        self._token = resp.json().get("token")
        if not self._token:
            raise RuntimeError("Login INPI : pas de jeton dans la réponse.")

    def _get(self, path: str, **kwargs):
        if self._token is None:
            self._login()
        headers = {"Authorization": f"Bearer {self._token}"}
        resp = self._session.get(f"{BASE_URL}{path}", headers=headers,
                                 timeout=_TIMEOUT, **kwargs)
        if resp.status_code == 401:        # jeton expiré -> re-login, une seule fois
            self._login()
            headers = {"Authorization": f"Bearer {self._token}"}
            resp = self._session.get(f"{BASE_URL}{path}", headers=headers,
                                     timeout=_TIMEOUT, **kwargs)
        resp.raise_for_status()
        return resp

    def attachments(self, siren: str) -> dict:
        """Pièces déposées d'une société (bilans, actes...), schéma brut INPI."""
        return self._get(f"/companies/{siren}/attachments").json()

    def bilans(self, siren: str) -> list[dict]:
        """Bilans déposés, du plus récent au plus ancien : [{id, dateCloture, ...}]."""
        data = self.attachments(siren)
        bilans = data.get("bilans") or []
        return sorted(bilans, key=lambda b: b.get("dateCloture") or "", reverse=True)

    def download_bilan(self, bilan_id: str) -> bytes:
        """PDF d'un bilan déposé."""
        return self._get(f"/bilans/{bilan_id}/download").content


def fetch_comptes_pdf(siren: str, before_date: Optional[str] = None,
                      client: Optional[InpiClient] = None) -> Optional[tuple[dict, bytes]]:
    """(métadonnées, PDF) du dernier bilan clôturé avant `before_date` (sinon le plus récent).

    Point d'entrée de l'enrichissement par les comptes déposés (cf. cascade.extract_comptes) :
    même convention que finances_inpi.pick_for_date — l'exercice doit précéder la cession.
    Renvoie None sans credentials, sans dépôt, ou sur échec réseau (jamais d'exception).
    """
    if not configured():
        return None
    client = client or InpiClient()
    try:
        candidats = client.bilans(siren)
        if before_date:
            avant = [b for b in candidats if (b.get("dateCloture") or "") <= before_date]
            candidats = avant or candidats         # fallback : le plus récent
        if not candidats:
            return None
        meta = candidats[0]
        return meta, client.download_bilan(str(meta.get("id")))
    except Exception as exc:
        logger.warning("Echec INPI pour le SIREN %s : %s", siren, exc)
        return None
