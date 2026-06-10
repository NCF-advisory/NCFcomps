"""Orchestration cessions FR : BODACC (prix + SIREN) -> finances INPI (CA/EBE, exercice
calé sur la cession) + identité (NAF) -> prix/CA et prix/EBE."""
from __future__ import annotations
import logging
from datetime import date
from typing import Optional

import pandas as pd

from comparables.fr import bodacc, entreprises, finances_inpi
from comparables.fr.comptes import cascade, inpi_client
from comparables.fr.models import Cession
from comparables.fr.parsing import compute_pct_ca, compute_mult_ebe, summarize_by_activity

logger = logging.getLogger(__name__)

__all__ = ["build_cessions", "summarize_by_activity", "to_dataframe", "default_since"]


def default_since(years: int = 10) -> str:
    """Date 'YYYY-MM-DD' il y a `years` ans (fenêtre d'analyse par défaut)."""
    today = date.today()
    return today.replace(year=today.year - years).isoformat()


def build_cessions(departement: Optional[str] = None, contains: Optional[str] = None,
                   since: Optional[str] = None, limit: int = 50, enrich: bool = True,
                   require_ca: bool = True, max_scan: Optional[int] = None) -> list[Cession]:
    """Récupère des cessions (prix) et calcule prix/CA et prix/EBE quand disponibles.

    Couvre TOUTES les entreprises françaises (aucun filtre de taille) ; en pratique le
    BODACC ne publie que des cessions de fonds de commerce (commerces/TPE/PME).

    require_ca=True : ne renvoie QUE les sociétés dont le CA est disponible (comptes publics),
    en sur-balayant le BODACC (jusqu'à max_scan cessions) pour en réunir `limit`. L'identité
    (NAF) n'est récupérée que pour les cessions retenues. L'échec d'une société n'arrête pas le lot.
    """
    if max_scan is None:
        max_scan = min(600, max(limit * 12, limit)) if require_ca else limit
    pool = bodacc.fetch_cessions(departement=departement, contains=contains,
                                 since=since or default_since(), limit=max_scan)
    if not enrich:
        return pool[:limit]

    out: list[Cession] = []
    fin_cache: dict[str, list] = {}
    id_cache: dict[str, Optional[dict]] = {}
    for c in pool:
        # 1) Finances (CA/EBE) de l'exercice calé sur la date de cession
        if c.siren:
            try:
                if c.siren not in fin_cache:
                    fin_cache[c.siren] = finances_inpi.fetch_financials(c.siren)
                fin = finances_inpi.pick_for_date(fin_cache[c.siren], c.date)
            except Exception as exc:
                logger.warning("Echec finances SIREN %s : %s", c.siren, exc)
                fin = None
            if fin:
                c.ca = fin.get("chiffre_d_affaires")
                c.ebe = fin.get("ebe")
                c.ebit = fin.get("ebit")
                cloture = fin.get("date_cloture_exercice") or ""
                c.ca_annee = int(cloture[:4]) if cloture[:4].isdigit() else None
                c.pct_ca = compute_pct_ca(c.prix, c.ca)
                c.mult_ebe = compute_mult_ebe(c.prix, c.ebe)
        # 1bis) Comptes déposés INPI (cascade PDF/OCR/LLM) quand le dataset ratios n'a
        #        rien donné — inactif sans credentials INPI (lot 3 du cahier des charges).
        if c.siren and c.ca is None and inpi_client.configured():
            try:
                fetched = inpi_client.fetch_comptes_pdf(c.siren, before_date=c.date)
                extraction = cascade.extract_comptes(fetched[1]) if fetched else None
            except Exception as exc:
                logger.warning("Echec comptes déposés SIREN %s : %s", c.siren, exc)
                fetched, extraction = None, None
            if fetched and extraction:
                c.ca, c.ebe, c.ebit = extraction.ca, extraction.ebe, extraction.ebit
                cloture = fetched[0].get("dateCloture") or ""
                c.ca_annee = int(cloture[:4]) if cloture[:4].isdigit() else None
                c.pct_ca = compute_pct_ca(c.prix, c.ca)
                c.mult_ebe = compute_mult_ebe(c.prix, c.ebe)
        # 2) Exclusion des sociétés sans CA disponible
        if require_ca and c.ca is None:
            continue
        # 3) Identité (NAF, nom) — uniquement pour les cessions retenues
        if c.siren:
            try:
                if c.siren not in id_cache:
                    id_cache[c.siren] = entreprises.fetch_company(c.siren)
                info = id_cache[c.siren]
            except Exception as exc:
                logger.warning("Echec identité SIREN %s : %s", c.siren, exc)
                info = None
            if info:
                c.nom = info.get("nom") or c.nom
                c.naf = info.get("naf")
                c.activite = info.get("naf")
        out.append(c)
        if len(out) >= limit:
            break
    return out


def to_dataframe(cessions: list[Cession]) -> pd.DataFrame:
    return pd.DataFrame([c.model_dump() for c in cessions])
