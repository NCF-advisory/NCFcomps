"""Extraction « LLM » (cascade étape 4, dernier recours) : API Claude sur le PDF brut.

Réservé aux documents que les étapes gratuites n'ont pas su lire (scans dégradés,
mises en page atypiques). Inactif sans clé API (ANTHROPIC_API_KEY ou .env) : la
cascade s'arrête alors à l'OCR. Modèle par défaut : Haiku (décision coût du
2026-06-10 : ~0,4-0,8 ct €/document) — surchargable via CLAUDE_MODEL.
"""
from __future__ import annotations
import base64
import json
import logging
import os
from typing import Optional

from comparables.config import settings
from comparables.fr.comptes.liasse import LiasseResult

logger = logging.getLogger(__name__)

_SCHEMA = {
    "type": "object",
    "properties": {
        "ca": {"type": ["number", "null"],
               "description": "Chiffre d'affaires net total de l'exercice N, en euros"},
        "ebe": {"type": ["number", "null"],
                "description": "Excédent brut d'exploitation de l'exercice N, en euros"},
        "ebit": {"type": ["number", "null"],
                 "description": "Résultat d'exploitation de l'exercice N, en euros"},
    },
    "required": ["ca", "ebe", "ebit"],
    "additionalProperties": False,
}

_PROMPT = (
    "Voici les comptes annuels déposés d'une entreprise française (liasse fiscale, "
    "formulaire 2052 ou 2033-B). Extrais, pour l'exercice le plus récent (colonne N) :\n"
    "- ca : le chiffre d'affaires net total (ligne FL du 2052, ou somme des lignes "
    "210/214/218 du 2033-B) ;\n"
    "- ebe : l'excédent brut d'exploitation = CA + production stockée + production "
    "immobilisée + subventions d'exploitation - achats et variations de stocks - autres "
    "achats et charges externes - impôts et taxes - salaires - charges sociales ;\n"
    "- ebit : le résultat d'exploitation (ligne GG du 2052 ou 270 du 2033-B).\n"
    "Montants en euros (pas en milliers, sauf si la liasse précise « en K€ » : convertis). "
    "Si une valeur est illisible ou absente, renvoie null."
)


def configured() -> bool:
    """Une clé API Claude est-elle disponible (env ou .env) ?"""
    return bool(os.environ.get("ANTHROPIC_API_KEY") or settings.anthropic_api_key)


def extract_from_pdf(pdf_bytes: bytes) -> Optional[LiasseResult]:
    """Cascade étape 4 : envoie le PDF à Claude (sortie structurée JSON), ou None sans clé."""
    if not configured():
        return None
    try:
        import anthropic
    except ImportError:
        logger.warning("SDK anthropic non installé : étape LLM sautée.")
        return None

    api_key = os.environ.get("ANTHROPIC_API_KEY") or settings.anthropic_api_key
    client = anthropic.Anthropic(api_key=api_key)
    try:
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": base64.standard_b64encode(pdf_bytes).decode("ascii"),
                        },
                    },
                    {"type": "text", "text": _PROMPT},
                ],
            }],
            output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
        )
    except Exception as exc:                     # quota, clé invalide, PDF trop lourd...
        logger.warning("Echec extraction Claude : %s", exc)
        return None

    text = next((b.text for b in response.content if b.type == "text"), None)
    if not text:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Réponse Claude non-JSON inattendue.")
        return None
    result = LiasseResult(ca=data.get("ca"), ebe=data.get("ebe"), ebit=data.get("ebit"))
    return result if result.ca is not None else None
