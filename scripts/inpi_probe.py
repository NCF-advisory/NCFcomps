"""Sonde de validation de l'API RNE / INPI (lot 3).

But : confronter les schémas *supposés* de `comparables.fr.comptes.inpi_client`
(login, attachments, download) à l'API réelle, une fois les credentials dans .env.

Sécurité : n'imprime JAMAIS les identifiants ni le token, seulement des booléens,
des codes HTTP et la *structure* des réponses (clés, types, nombres). Les comptes
annuels déposés sont des données publiques (art. L232-23 C. com.).

Usage :
    .venv/bin/python scripts/inpi_probe.py [SIREN]
    # SIREN par défaut : Danone (552032534), gros déposant non confidentiel a priori.
"""
from __future__ import annotations

import sys
from typing import Any

import requests

from comparables.config import settings
from comparables.fr.comptes import inpi_client


def _shape(value: Any, depth: int = 0) -> str:
    """Décrit la *forme* d'une valeur JSON sans révéler les contenus volumineux."""
    if isinstance(value, dict):
        return "{" + ", ".join(sorted(value.keys())) + "}"
    if isinstance(value, list):
        head = _shape(value[0], depth + 1) if value else "vide"
        return f"[{len(value)} × {head}]"
    if isinstance(value, str):
        return f"str(len={len(value)})"
    return type(value).__name__


def main() -> int:
    siren = sys.argv[1] if len(sys.argv) > 1 else "552032534"  # Danone par défaut

    print(f"BASE_URL              : {inpi_client.BASE_URL}")
    print(f"credentials présents  : {inpi_client.configured()}")
    if not inpi_client.configured():
        print("→ Remplis INPI_USERNAME / INPI_PASSWORD dans .env, puis relance.")
        return 1

    client = inpi_client.InpiClient()

    # --- 1) Login -----------------------------------------------------------
    print("\n[1] POST /sso/login")
    try:
        resp = client._session.post(
            f"{inpi_client.BASE_URL}/sso/login",
            timeout=40,
            json={"username": settings.inpi_username, "password": settings.inpi_password},
        )
        print(f"    HTTP {resp.status_code}")
        try:
            body = resp.json()
            print(f"    clés réponse        : {sorted(body.keys()) if isinstance(body, dict) else type(body).__name__}")
            print(f"    champ 'token' présent: {'token' in body if isinstance(body, dict) else False}")
        except ValueError:
            print(f"    corps non-JSON (len={len(resp.text)}) : {resp.text[:200]!r}")
        resp.raise_for_status()
        token = resp.json().get("token")
        if not token:
            print("    ✗ pas de jeton → vérifier le nom du champ ci-dessus")
            return 2
        client._token = token
    except requests.RequestException as exc:
        print(f"    ✗ échec login : {exc}")
        return 2

    # --- 2) Attachments -----------------------------------------------------
    print(f"\n[2] GET /companies/{siren}/attachments")
    try:
        data = client.attachments(siren)
        print(f"    structure racine     : {_shape(data)}")
        if isinstance(data, dict):
            for key in ("bilans", "bilansSaisis", "actes", "comptesAnnuels"):
                if key in data:
                    print(f"    '{key}'               : {_shape(data[key])}")
            bilans = data.get("bilans") or data.get("comptesAnnuels") or []
            if bilans:
                print(f"    1er bilan (clés)     : {_shape(bilans[0])}")
                # champs qui nous intéressent pour la convention exercice<cession
                b = bilans[0]
                for f in ("id", "dateCloture", "dateDepot", "typeBilan", "confidentiality", "confidentialite"):
                    if isinstance(b, dict) and f in b:
                        print(f"        {f:18}: {b[f]!r}")
    except requests.RequestException as exc:
        print(f"    ✗ échec attachments : {exc}")
        return 3

    # --- 3) Download du 1er bilan ------------------------------------------
    print("\n[3] GET /bilans/{id}/download")
    try:
        bilans = client.bilans(siren)
        if not bilans:
            print("    (aucun bilan à télécharger pour ce SIREN)")
            return 0
        bid = str(bilans[0].get("id"))
        pdf = client.download_bilan(bid)
        magic = pdf[:5]
        print(f"    id                   : {bid}")
        print(f"    taille               : {len(pdf)} octets")
        print(f"    en-tête PDF (%PDF-)  : {magic == b'%PDF-'}  ({magic!r})")
    except requests.RequestException as exc:
        print(f"    ✗ échec download : {exc}")
        return 4

    print("\n✓ Sonde terminée — comparer les schémas ci-dessus à inpi_client.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
