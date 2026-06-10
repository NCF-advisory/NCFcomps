"""Cascade d'extraction d'un PDF de comptes annuels : gratuit d'abord, LLM en dernier.

    1. PDF texte  (pdfplumber, gratuit)    — liasses générées par logiciel comptable
    2. OCR        (Tesseract, gratuit)     — liasses scannées
    3. LLM        (API Claude, payant)     — documents que 1-2 n'ont pas su lire

(L'étape XBRL est portée par le dataset « bilans saisis » côté client INPI, pas par
un parseur local.) Chaque extracteur renvoie un LiasseResult ou None ; le premier
résultat avec un CA gagne. Un échec d'extracteur ne casse jamais la cascade.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Callable, Optional

from comparables.fr.comptes import llm, ocr, pdftext
from comparables.fr.comptes.liasse import LiasseResult

logger = logging.getLogger(__name__)

Extractor = tuple[str, Callable[[bytes], Optional[LiasseResult]]]


@dataclass
class ExtractionResult:
    ca: Optional[float]
    ebe: Optional[float]
    ebit: Optional[float]
    method: str                            # "pdf_texte" | "ocr" | "llm"
    regime: Optional[str]
    missing_codes: list[str]


def default_extractors() -> list[Extractor]:
    """Chaîne par défaut, selon ce qui est installé/configuré (LLM toujours en dernier)."""
    chain: list[Extractor] = [("pdf_texte", pdftext.extract_from_pdf)]
    if ocr.available():
        chain.append(("ocr", ocr.extract_from_pdf))
    if llm.configured():
        chain.append(("llm", llm.extract_from_pdf))
    return chain


def extract_comptes(pdf_bytes: bytes,
                    extractors: Optional[list[Extractor]] = None) -> Optional[ExtractionResult]:
    """Tente les extracteurs dans l'ordre ; renvoie le premier résultat avec un CA."""
    for name, fn in (default_extractors() if extractors is None else extractors):
        try:
            result = fn(pdf_bytes)
        except Exception as exc:           # un extracteur défaillant ne casse pas la cascade
            logger.warning("Extracteur %s en échec : %s", name, exc)
            continue
        if result is not None and result.ca is not None:
            return ExtractionResult(ca=result.ca, ebe=result.ebe, ebit=result.ebit,
                                    method=name, regime=result.regime,
                                    missing_codes=result.missing_codes)
    return None
