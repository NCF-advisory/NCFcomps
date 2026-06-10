"""Extraction « OCR » (cascade étape 3) : liasses scannées, via Tesseract (gratuit).

Dépendances optionnelles (groupe `ocr` de pyproject + binaires système tesseract/poppler) :
le module s'absente proprement si elles manquent — la cascade passe à l'étape suivante.
"""
from __future__ import annotations
import logging
from typing import Optional

from comparables.fr.comptes import liasse, pdftext
from comparables.fr.comptes.liasse import LiasseResult

logger = logging.getLogger(__name__)


def available() -> bool:
    """Les dépendances OCR (pytesseract + pdf2image) sont-elles importables ?"""
    try:
        import pdf2image  # noqa: F401
        import pytesseract  # noqa: F401
    except ImportError:
        return False
    return True


def extract_text(pdf_bytes: bytes, dpi: int = 200, max_pages: int = 12) -> Optional[str]:
    """Texte OCR des premières pages du PDF (le compte de résultat est en tête de liasse)."""
    if not available():
        return None
    import pdf2image
    import pytesseract
    try:
        images = pdf2image.convert_from_bytes(pdf_bytes, dpi=dpi,
                                              first_page=1, last_page=max_pages)
        pages = [pytesseract.image_to_string(img, lang="fra") for img in images]
    except Exception as exc:                     # binaire absent, PDF corrompu...
        logger.warning("OCR impossible : %s", exc)
        return None
    text = "\n".join(pages).strip()
    return text or None


def extract_from_pdf(pdf_bytes: bytes) -> Optional[LiasseResult]:
    text = extract_text(pdf_bytes)
    if not text:
        return None
    result = liasse.compute(pdftext.parse_codes(text))
    return result if result.ca is not None else None
