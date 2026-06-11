"""Export Excel formate du tableau de comparables (openpyxl). Renvoie des bytes (telechargement)."""
from __future__ import annotations
import io
from typing import Optional

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from comparables.models import CompanyRecord
from comparables.config import settings
from comparables.finance.beta import reliable_beta, sample_summary
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
# Champs derives de la regression : exclus des stats quand R2 < settings.beta_min_r2.
BETA_QUALITY_FIELDS = ("beta_regression", "beta_unlevered")

_FMT = {"M": "# ##0", "beta": "0.00", "r2": "0.00", "pct": "0.0%", "mult": '0.0"x"'}
_LOW_R2_COLOR = "B45309"   # ambre : beta affiche mais exclu des statistiques


_STAT_LABELS = {"median": "Mediane", "mean": "Moyenne", "min": "Minimum", "max": "Maximum"}


def _low_r2(rec: CompanyRecord) -> bool:
    """Regression trop faible pour exploiter la pente (meme regle que l'ecran)."""
    return (rec.beta_regression is not None
            and reliable_beta(rec.beta_regression, rec.r2, settings.beta_min_r2) is None)


def _stats(records: list[CompanyRecord]) -> dict[str, dict[str, float]]:
    # Delegue a summary_stats (filtre None ET inf/nan) : memes stats que l'ecran.
    # Les champs beta excluent en plus les R2 < beta_min_r2 (pente non exploitable).
    out: dict[str, dict[str, float]] = {}
    for f in STATS_FIELDS:
        if f in BETA_QUALITY_FIELDS:
            values = (reliable_beta(getattr(r, f), r.r2, settings.beta_min_r2)
                      for r in records)
        else:
            values = (getattr(r, f) for r in records)
        s = summary_stats(values)
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
        low = _low_r2(rec)
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
                # R2 trop faible : beta visible mais hors stats -> en ambre (meme regle que l'ecran)
                if low and field in (*BETA_QUALITY_FIELDS, "r2"):
                    cell.font = Font(color=_LOW_R2_COLOR, size=10)
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

    # Synthese beta : betas moyens RETENUS (R2 >= seuil), endette / ajuste / desendette
    summary = sample_summary(
        ((rec.beta_regression, rec.r2, rec.beta_unlevered) for rec in records),
        settings.beta_min_r2,
    )
    if summary and summary["mean_levered"] is not None:
        r += 2
        head_cell = ws.cell(row=r, column=1,
                            value=f"Synthese beta : {summary['n_retained']} retenu(s), "
                                  f"{summary['n_excluded_low_r2']} ecarte(s) (R2 < {settings.beta_min_r2:.2f})")
        head_cell.font = bold
        lines = [
            ("Beta endette moyen retenu", summary["mean_levered"]),
            ("Beta ajuste (Blume : 2/3 x beta + 1/3)", summary["mean_adjusted"]),
            ("Beta desendette moyen retenu", summary["mean_unlevered"]),
        ]
        for label, value in lines:
            r += 1
            ws.cell(row=r, column=1, value=label).font = bold
            cell = ws.cell(row=r, column=2, value=value if value is not None else "n.d.")
            cell.font = bold
            if value is not None:
                cell.number_format = _FMT["beta"]

    r += 2
    freq = {"1mo": "mensuels", "1wk": "hebdomadaires"}.get(settings.beta_frequency, settings.beta_frequency)
    notes = [
        f"Hypothese d'impot (desendettement) : {settings.tax_rate:.0%}.",
        f"Beta (regression) et R2 : rendements {freq} du titre regresses sur son indice "
        f"de reference, sur {settings.beta_period}. R2 entre 0 et 1 = part de variance expliquee.",
        "Beta (desendette) = beta de regression / (1 + (1 - IS) x Dette nette / Capi) (Hamada).",
        f"Betas en ambre : R2 < {settings.beta_min_r2:.2f}, affiches mais exclus des "
        "statistiques et de la synthese (pente non exploitable).",
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
