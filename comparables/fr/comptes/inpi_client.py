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
import threading
import time
from typing import Optional

import requests

from comparables.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://registre-national-entreprises.inpi.fr/api"
_TIMEOUT = 40


def configured() -> bool:
    return bool(settings.inpi_username and settings.inpi_password)


def _select_deposit(deposits: list[dict], before_date: Optional[str]) -> Optional[dict]:
    """Dépôt le plus pertinent : non supprimé, public de préférence, exercice <= cession.

    Écarte les dépôts `deleted`. Privilégie les comptes `Public` (les confidentiels —
    art. L232-25, ~45 % — masquent le compte de résultat) ; à défaut, tolère les autres.
    Retient le plus récent clôturé avant `before_date` (sinon le plus récent tout court)."""
    usable = [d for d in deposits if not d.get("deleted")]
    public = [d for d in usable if (d.get("confidentiality") or "").lower() == "public"]
    pool = public or usable
    pool.sort(key=lambda d: d.get("dateCloture") or "", reverse=True)
    if before_date:
        prior = [d for d in pool if (d.get("dateCloture") or "") <= before_date]
        pool = prior or pool
    return pool[0] if pool else None


class InpiClient:
    """Session authentifiée RNE : login paresseux + re-tentative sur 401.

    Garde-fou de débit (le RNE refuse les connexions IP en cas de rafale) : cadence
    minimale entre appels (`inpi_min_interval_seconds`) et un retry avec back-off sur
    refus de connexion ou 429 (`inpi_max_attempts` / `inpi_backoff_seconds`). Un seul
    client partagé pour tout un lot évite la multiplication des logins (le point le
    plus surveillé)."""

    def __init__(self, session: Optional[requests.Session] = None):
        self._session = session or requests.Session()
        self._token: Optional[str] = None
        self._lock = threading.Lock()
        self._last_request = 0.0           # horodatage monotone du dernier appel

    def _throttle(self) -> None:
        """Impose la cadence minimale entre deux appels RNE (sérialisé par le verrou)."""
        gap = settings.inpi_min_interval_seconds
        with self._lock:
            if gap > 0:
                wait = gap - (time.monotonic() - self._last_request)
                if wait > 0:
                    time.sleep(wait)
            self._last_request = time.monotonic()

    def _call(self, fn, *args, **kwargs):
        """Appel session avec cadence + retry (refus de connexion / 429)."""
        attempts = max(1, settings.inpi_max_attempts)
        for attempt in range(1, attempts + 1):
            self._throttle()
            try:
                resp = fn(*args, **kwargs)
            except requests.exceptions.ConnectionError:
                if attempt >= attempts:
                    raise
                time.sleep(settings.inpi_backoff_seconds * attempt)
                continue
            if resp.status_code == 429 and attempt < attempts:
                time.sleep(settings.inpi_backoff_seconds * attempt)
                continue
            return resp

    def _login(self) -> None:
        resp = self._call(self._session.post, f"{BASE_URL}/sso/login", timeout=_TIMEOUT,
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
        resp = self._call(self._session.get, f"{BASE_URL}{path}", headers=headers,
                         timeout=_TIMEOUT, **kwargs)
        if resp.status_code == 401:        # jeton expiré -> re-login, une seule fois
            self._login()
            headers = {"Authorization": f"Bearer {self._token}"}
            resp = self._call(self._session.get, f"{BASE_URL}{path}", headers=headers,
                             timeout=_TIMEOUT, **kwargs)
        resp.raise_for_status()
        return resp

    def attachments(self, siren: str) -> dict:
        """Pièces déposées d'une société (bilans, actes...), schéma brut INPI."""
        return self._get(f"/companies/{siren}/attachments").json()

    def bilans(self, siren: str) -> list[dict]:
        """Bilans PDF déposés (non supprimés), du plus récent au plus ancien."""
        data = self.attachments(siren)
        bilans = [b for b in (data.get("bilans") or []) if not b.get("deleted")]
        return sorted(bilans, key=lambda b: b.get("dateCloture") or "", reverse=True)

    def bilans_saisis(self, siren: str) -> list[dict]:
        """Comptes structurés saisis (non supprimés), du plus récent au plus ancien.

        Chaque entrée porte le champ `bilanSaisi` (liasse numérisée, codes -> montants)
        en plus des métadonnées (dateCloture, confidentiality, typeBilan...)."""
        data = self.attachments(siren)
        saisis = [b for b in (data.get("bilansSaisis") or []) if not b.get("deleted")]
        return sorted(saisis, key=lambda b: b.get("dateCloture") or "", reverse=True)

    def download_bilan(self, bilan_id: str) -> bytes:
        """PDF d'un bilan déposé."""
        return self._get(f"/bilans/{bilan_id}/download").content


def fetch_comptes_saisi(siren: str, before_date: Optional[str] = None,
                        client: Optional[InpiClient] = None) -> Optional[tuple[dict, dict]]:
    """(métadonnées, bilanSaisi) du compte structuré le plus pertinent — voie privilégiée.

    Source déterministe et gratuite (cf. bilan_saisi.extract) : à essayer AVANT la cascade
    PDF/OCR/LLM. Même convention que finances_inpi.pick_for_date — l'exercice doit précéder
    la cession. Renvoie None sans credentials, sans dépôt saisi, ou sur échec réseau.
    """
    if not configured():
        return None
    client = client or InpiClient()
    try:
        meta = _select_deposit(client.bilans_saisis(siren), before_date)
        if not meta or not meta.get("bilanSaisi"):
            return None
        return meta, meta["bilanSaisi"]
    except Exception as exc:
        logger.warning("Echec INPI (bilan saisi) pour le SIREN %s : %s", siren, exc)
        return None


def fetch_comptes_pdf(siren: str, before_date: Optional[str] = None,
                      client: Optional[InpiClient] = None) -> Optional[tuple[dict, bytes]]:
    """(métadonnées, PDF) du dernier bilan clôturé avant `before_date` — filet de secours.

    Utilisé quand le compte structuré est absent (cf. fetch_comptes_saisi) : alimente la
    cascade PDF/OCR/LLM (cascade.extract_comptes). Même convention d'exercice que ci-dessus.
    Renvoie None sans credentials, sans dépôt, ou sur échec réseau (jamais d'exception).
    """
    if not configured():
        return None
    client = client or InpiClient()
    try:
        meta = _select_deposit(client.bilans(siren), before_date)
        if not meta:
            return None
        return meta, client.download_bilan(str(meta.get("id")))
    except Exception as exc:
        logger.warning("Echec INPI pour le SIREN %s : %s", siren, exc)
        return None
