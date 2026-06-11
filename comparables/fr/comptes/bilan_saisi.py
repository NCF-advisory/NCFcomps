"""Extraction des comptes structurés « bilans saisis » de l'API RNE / INPI.

Les dépôts `bilansSaisis` contiennent la liasse fiscale déjà numérisée (code CERFA
-> montants par colonne) : on aplatit les lignes en {code: montant exercice N} puis
on réutilise `liasse.compute()` (même convention EBE Banque de France). Aucun PDF,
OCR ni LLM — déterministe et gratuit. Module PUR (aucune I/O).

Forme observée sur l'API réelle (2026-06) :

    bilanSaisi = {
      "bilan": {
        "identite": {...},
        "detail": {"pages": [ {"numero": 1, "liasses": [ <ligne>, ... ]}, ... ]}
      },
      "version": "1.0"
    }
    <ligne> = {"code": "FL"|"210", "m1": "000...", "m2": ..., "m3": ..., "m4": ...}

Montants : entiers en euros, zéro-paddés sur 15 caractères, signe « - » éventuel
(ex. "000001030000000" -> 1 030 000 000 ; "-000000119000000" -> -119 000 000).

Colonne « exercice N » selon le régime (déterminé par les codes, cf. liasse.detect_regime) :
    - simplifié 2033-B (codes numériques)   -> m1   (m2 = N-1)
    - réel normal 2052  (codes alphabétiques) -> m3 (m1/m2 = France/Export, m4 = N-1)

Le choix strict de colonne est auto-filtrant : au régime normal, les lignes de bilan
(passif 2051 : colonnes m1/m2 seules) n'ont pas de m3 et sont naturellement écartées ;
seules les lignes du compte de résultat (m3 = total N) sont retenues.
"""
from __future__ import annotations

import logging
from typing import Iterator, Optional

from comparables.fr.comptes import liasse

logger = logging.getLogger(__name__)

# Colonne portant l'exercice N selon le régime détecté.
_COLUMN_BY_REGIME = {"simplifie": "m1", "normal": "m3"}


def parse_saisi_amount(raw: Optional[str]) -> Optional[float]:
    """Montant d'un « bilan saisi » : entier euros zéro-paddé, signe « - » éventuel.

    Chaîne vide ou non numérique -> None (cellule non renseignée)."""
    if raw is None:
        return None
    s = raw.strip()
    if not s:
        return None
    negative = s.startswith("-")
    digits = s.lstrip("-").lstrip("0") or "0"
    if not digits.isdigit():
        return None
    value = float(digits)
    return -value if negative else value


def _iter_liasses(bilan_saisi: dict) -> Iterator[dict]:
    """Itère sur toutes les lignes {code, m1...} du dépôt structuré, toutes pages confondues."""
    bilan = (bilan_saisi or {}).get("bilan") or {}
    pages = (bilan.get("detail") or {}).get("pages") or []
    for page in pages:
        if not isinstance(page, dict):
            continue
        for line in page.get("liasses") or []:
            if isinstance(line, dict) and line.get("code"):
                yield line


def _codes_present(bilan_saisi: dict) -> set[str]:
    return {line["code"] for line in _iter_liasses(bilan_saisi)}


def extract(bilan_saisi: Optional[dict]) -> Optional[liasse.LiasseResult]:
    """CA / EBE / EBIT depuis un dépôt structuré INPI.

    Renvoie None si le contenu est vide ou le régime indétectable (le pipeline
    bascule alors sur la cascade PDF). L'EBE suit la convention Banque de France
    portée par `liasse.compute` (publié seulement si CA + une charge structurante)."""
    if not bilan_saisi:
        return None
    regime = liasse.detect_regime({code: 0.0 for code in _codes_present(bilan_saisi)})
    if regime is None:
        return None
    column = _COLUMN_BY_REGIME[regime]
    codes: dict[str, float] = {}
    for line in _iter_liasses(bilan_saisi):
        amount = parse_saisi_amount(line.get(column))
        if amount is not None:
            codes[line["code"]] = amount
    return liasse.compute(codes)
