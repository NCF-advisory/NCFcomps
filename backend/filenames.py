"""Noms de fichiers servis par l'API."""
from __future__ import annotations

import re
from datetime import date

_BAD_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')
_SPACES = re.compile(r"\s+")


def comparables_excel_filename(libelle: str | None, today: date | None = None) -> str:
    label = (libelle or "Échantillon").strip() or "Échantillon"
    label = _SPACES.sub("_", label)
    label = _BAD_FILENAME_CHARS.sub("", label).strip("._ ")
    if not label:
        label = "Échantillon"
    stamp = (today or date.today()).strftime("%d%m%Y")
    return f"Beta_{label}_{stamp}.xlsx"
