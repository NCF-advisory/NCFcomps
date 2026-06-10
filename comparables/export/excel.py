"""Export Excel formate du tableau de comparables (openpyxl). Renvoie des bytes (telechargement)."""
from __future__ import annotations
import io
from typing import Optional

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from comparables.models import CompanyRecord
from comparables.config import settings
from comparables.finance.multiples import summary_stats

# (champ, libelle, type, largeur)
DISPLAY = [
    ("name", "Societe", "texte", 24),
    ("ticker", "Ticker", "texte", 10),
    ("country", "Pays", "texte", 13),
    ("sector", "Secteur", "texte", 18),
    ("currency", "Devise", "texte", 7),
    ("market_cap", "Capitalisation", "M", 15),
    ("net_debt", "Dette nette", "M", 13),
    ("enterprise_value", "VE", "M", 15),
    ("beta_source", "Beta (source)", "beta", 12),
    ("index_used", "Indice ref.", "texte", 11),
    ("beta_regression", "Beta (regression)", "beta", 15),
    ("r2", "R2", "r2", 8),
    ("gearing", "Gearing net", "pct", 12),
    ("beta_unlevered", "Beta desendette", "beta", 15),
    ("ev_sales", "VE/CA", "mult", 9),
    ("ev_ebitda", "VE/EBITDA", "mult", 10),
    ("ev_ebit", "VE/EBIT", "mult", 9),
    ("pe_trailing", "PER (publie)", "mult", 11),
    ("pe_forward", "PER (estime)", "mult", 11),
    ("pb", "P/B", "mult", 8),
]
STATS_FIELDS = ["beta_source", "beta_regression", "r2", "gearing", "beta_unlevered",
                "ev_sales", "ev_ebitda", "ev_ebit", "pe_trailing", "pe_forward", "pb"]

_FMT = {"M": "# ##0", "beta": "0.00", "r2": "0.00", "pct": "0.0%", "mult": '0.0"x"'}


_STAT_LABELS = {"median": "Mediane", "mean": "Moyenne", "min": "Minimum", "max": "Maximum"}


def _stats(records: list[CompanyRecord]) -> dict[str, dict[str, float]]:
    # Delegue a summary_stats (filtre None ET inf/nan) : memes stats que l'ecran.
    out: dict[str, dict[str, float]] = {}
    for f in STATS_FIELDS:
        s = summary_stats(getattr(r, f) for r in records)
        if s:
            out[f] = {_STAT_LABELS[k]: v for k, v in s.items()}
    return out


def build_workbook(records: list[CompanyRecord], warning: Optional[str] = None) -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = "Comparables"

    blue, grey = "1F3864", "D9E1F2"
    head = Font(bold=True, color="FFFFFF", size=10)
    bold = Font(bold=True, size=10)
    ital = Font(italic=True, size=10)
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    border = Border(bottom=Side(style="thin", color="BFBFBF"))

    ws.cell(row=1, column=1, value="Echantillon de comparables boursiers").font = Font(bold=True, size=13)
    ws.cell(row=2, column=1, value="Source : Yahoo Finance - montants en millions de la devise indiquee").font = ital
    header_row = 4

    for j, (_f, label, _t, width) in enumerate(DISPLAY, start=1):
        c = ws.cell(row=header_row, column=j, value=label)
        c.font = head
        c.fill = PatternFill("solid", fgColor=blue)
        c.alignment = center
        ws.column_dimensions[get_column_letter(j)].width = width
    ws.row_dimensions[header_row].height = 34

    r = header_row
    for rec in records:
        r += 1
        for j, (field, _label, typ, _w) in enumerate(DISPLAY, start=1):
            v = getattr(rec, field)
            if typ == "M" and v is not None:
                v = v / 1_000_000.0
            cell = ws.cell(row=r, column=j, value=("n.d." if v is None else v))
            cell.border = border
            if v is None:
                cell.alignment = Alignment(horizontal="center")
                cell.font = Font(color="A6A6A6", size=10)
            elif typ in _FMT:
                cell.number_format = _FMT[typ]
            if typ == "texte":
                cell.alignment = Alignment(horizontal="left")

    stats = _stats(records)
    r += 1
    for label in ("Mediane", "Moyenne", "Minimum", "Maximum"):
        r += 1
        cl = ws.cell(row=r, column=1, value=label)
        cl.font = bold
        cl.fill = PatternFill("solid", fgColor=grey)
        for j, (field, _label, typ, _w) in enumerate(DISPLAY, start=1):
            if j == 1:
                continue
            cell = ws.cell(row=r, column=j)
            cell.fill = PatternFill("solid", fgColor=grey)
            if field in stats and label in stats[field]:
                cell.value = stats[field][label]
                cell.font = bold
                if typ in _FMT:
                    cell.number_format = _FMT[typ]

    r += 2
    freq = {"1mo": "mensuels", "1wk": "hebdomadaires"}.get(settings.beta_frequency, settings.beta_frequency)
    notes = [
        f"Hypothese d'impot (desendettement) : {settings.tax_rate:.0%}.",
        f"Beta (regression) et R2 : rendements {freq} du titre regresses sur son indice "
        f"de reference, sur {settings.beta_period}. R2 entre 0 et 1 = part de variance expliquee.",
        "Beta (desendette) = beta de regression / (1 + (1 - IS) x Dette nette / Capi) (Hamada).",
        "Multiples tels que publies : non retraites (exceptionnels, minoritaires, IFRS 16...).",
        "Devises potentiellement differentes : comparer les montants avec prudence.",
    ]
    if warning:
        notes.insert(0, warning)
    for n in notes:
        cell = ws.cell(row=r, column=1, value="- " + n)
        cell.font = Font(italic=True, size=9, color="595959")
        r += 1

    ws.freeze_panes = ws.cell(row=header_row + 1, column=2)
    return wb


def build_excel_bytes(records: list[CompanyRecord], warning: Optional[str] = None) -> bytes:
    buf = io.BytesIO()
    build_workbook(records, warning).save(buf)
    return buf.getvalue()
