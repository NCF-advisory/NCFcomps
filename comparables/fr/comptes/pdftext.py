"""Extraction « PDF texte » : liasses générées par les logiciels comptables (couche texte).

Le cœur (`parse_codes`) est pur et testé : il repère sur chaque ligne un code de
liasse (FL, GG, 210...) suivi de montants et retient le PREMIER montant (colonne
de l'exercice N ; la colonne N-1 vient après). `extract_from_pdf` n'est que la
glue pdfplumber -> texte -> parse_codes -> liasse.compute.
"""
from __future__ import annotations
import io
import logging
import re
from typing import Optional

from comparables.fr.comptes import liasse
from comparables.fr.comptes.liasse import LiasseResult

logger = logging.getLogger(__name__)

# Codes alphabétiques du 2052 (FA..GW) et numériques du 2033-B (3 chiffres).
# Le code doit être un token isolé, suivi d'au moins un montant sur la même ligne.
#
# Le montant ne franchit qu'UN SEUL espace entre groupes de 3 chiffres (séparateur
# de milliers FR) : combiné à extract_text(layout=True) — qui rend les écarts de
# colonnes par 2+ espaces — cela évite d'avaler la colonne N-1 avec la colonne N.
_CODE_ALPHA = r"F[A-Z]|G[A-W]"
_CODE_NUM = r"\d{3}"
_SEP = "[   ]"                  # espace simple, insécable, fine
_AMOUNT = rf"\(?-?\d[\d.,]*(?:{_SEP}\d{{3}})*\)?"

_LINE_ALPHA_RE = re.compile(
    rf"\b({_CODE_ALPHA})\b[^\S\n]+({_AMOUNT})(?=\s|$)")
_LINE_NUM_RE = re.compile(
    rf"(?:^|\s)({_CODE_NUM})\b[^\S\n]+({_AMOUNT})(?=\s|$)")


def parse_codes(text: str) -> dict[str, float]:
    """Dict {code: montant exercice N} depuis le texte d'une liasse.

    Les codes numériques (2033-B) ne sont retenus que si le texte mentionne le
    formulaire 2033 : un nombre à 3 chiffres isolé est sinon trop ambigu.
    """
    out: dict[str, float] = {}
    for m in _LINE_ALPHA_RE.finditer(text):
        code, raw = m.group(1), m.group(2)
        amount = liasse.parse_amount(raw)
        if amount is not None and code not in out:    # 1re occurrence = exercice N
            out[code] = amount
    if "2033" in text:
        for m in _LINE_NUM_RE.finditer(text):
            code, raw = m.group(1), m.group(2)
            amount = liasse.parse_amount(raw)
            if amount is not None and code not in out:
                out[code] = amount
    return out


def extract_text(pdf_bytes: bytes) -> Optional[str]:
    """Texte de la couche texte du PDF (None si vide : scan -> OCR en aval)."""
    try:
        import pdfplumber
    except ImportError:                                # dépendance d'extraction absente
        logger.warning("pdfplumber non installé : étape PDF texte sautée.")
        return None
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            # layout=True : l'espacement des colonnes est préservé (2+ espaces),
            # condition du découpage exercice N / N-1 dans parse_codes.
            pages = [page.extract_text(layout=True) or "" for page in pdf.pages]
    except Exception as exc:
        logger.warning("PDF illisible par pdfplumber : %s", exc)
        return None
    text = "\n".join(pages).strip()
    return text or None


def extract_from_pdf(pdf_bytes: bytes) -> Optional[LiasseResult]:
    """Cascade étape 2 : couche texte -> codes -> CA/EBE/EBIT. None si inexploitable."""
    text = extract_text(pdf_bytes)
    if not text:
        return None
    result = liasse.compute(parse_codes(text))
    return result if result.ca is not None else None
