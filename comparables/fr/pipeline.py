"""Orchestration cessions FR : BODACC (prix + SIREN) -> finances INPI (CA/EBE, exercice
calé sur la cession) + identité (NAF) -> prix/CA et prix/EBE."""
from __future__ import annotations
import logging
from datetime import date
from typing import Optional

import pandas as pd

from comparables.fr import bodacc, entreprises, finances_inpi
from comparables.fr.models import Cession
from comparables.fr.parsing import (compute_pct_ca, compute_mult_ebe, summarize_by_activity,
                                    parse_search_terms, expand_synonyms, naf_matches)

logger = logging.getLogger(__name__)

__all__ = ["build_cessions", "summarize_by_activity", "to_dataframe", "default_since",
           "resolve_terms"]


def default_since(years: int = 10) -> str:
    """Date 'YYYY-MM-DD' il y a `years` ans (fenêtre d'analyse par défaut)."""
    today = date.today()
    return today.replace(year=today.year - years).isoformat()


def resolve_terms(contains: Optional[str], expand: bool = True) -> list[str]:
    """Saisie libre -> termes de recherche (OU), élargis aux synonymes métier si `expand`."""
    terms = parse_search_terms(contains)
    return expand_synonyms(terms) if (expand and terms) else terms


def build_cessions(departement: Optional[str] = None, contains: Optional[str] = None,
                   since: Optional[str] = None, limit: int = 50, enrich: bool = True,
                   require_ca: bool = True, max_scan: Optional[int] = None,
                   expand: bool = True, naf_filters: Optional[list[str]] = None,
                   stats: Optional[dict] = None) -> list[Cession]:
    """Récupère des cessions (prix) et calcule prix/CA et prix/EBE quand disponibles.

    Couvre TOUTES les entreprises françaises (aucun filtre de taille) ; en pratique le
    BODACC ne publie que des cessions de fonds de commerce (commerces/TPE/PME).

    La saisie `contains` est découpée en termes combinés en OU et élargie aux synonymes
    métier (`expand`) — cf. parsing.resolve_terms.

    require_ca=True : ne renvoie QUE les sociétés portant une donnée financière exploitable
    (CA *ou* EBE, comptes publics), en sur-balayant le BODACC (jusqu'à max_scan cessions) pour
    en réunir `limit`. L'identité (NAF) n'est récupérée que pour les cessions retenues.
    L'échec d'une société n'arrête pas le lot.

    `stats` : dict optionnel rempli avec le funnel (termes, n annonces avec prix examinées,
    n avec CA / EBE public, n retenues) — pour afficher où se perd l'échantillon.
    """
    terms = resolve_terms(contains, expand=expand)
    if max_scan is None:
        max_scan = min(600, max(limit * 12, limit)) if require_ca else limit
    pool = bodacc.fetch_cessions(departement=departement, terms=terms or None,
                                 since=since or default_since(), limit=max_scan)
    if not enrich:
        out = pool[:limit]
        if stats is not None:
            stats.update({"terms": terms, "n_pool": len(pool), "n_examined": len(out),
                          "n_ca_public": 0, "n_ebe_public": 0, "n_returned": len(out)})
        return out

    out: list[Cession] = []
    fin_cache: dict[str, list] = {}
    id_cache: dict[str, Optional[dict]] = {}
    n_examined = n_ca_public = n_ebe_public = 0
    for c in pool:
        n_examined += 1
        # 1) Finances (CA/EBE) de l'exercice calé sur la date de cession
        if c.siren:
            try:
                if c.siren not in fin_cache:
                    fin_cache[c.siren] = finances_inpi.fetch_financials(c.siren)
                fin = finances_inpi.pick_financials(fin_cache[c.siren], c.date)
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
        has_ca = c.ca is not None
        has_ebe = c.ebe is not None and c.ebe > 0
        if has_ca:
            n_ca_public += 1
        if has_ebe:
            n_ebe_public += 1
        # 2) Exclusion des sociétés sans donnée financière exploitable (ni CA ni EBE)
        if require_ca and not (has_ca or has_ebe):
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
                c.nb_etablissements = info.get("nb_etablissements")
        # 4) Filtre NAF (après identité) : ne compte vers `limit` que le bon secteur
        if naf_filters and not naf_matches(c.naf, naf_filters):
            continue
        out.append(c)
        if len(out) >= limit:
            break
    if stats is not None:
        stats.update({"terms": terms, "n_pool": len(pool), "n_examined": n_examined,
                      "n_ca_public": n_ca_public, "n_ebe_public": n_ebe_public,
                      "n_returned": len(out)})
    return out


def to_dataframe(cessions: list[Cession]) -> pd.DataFrame:
    return pd.DataFrame([c.model_dump() for c in cessions])
