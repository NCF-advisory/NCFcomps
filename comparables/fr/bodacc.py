"""Accès BODACC : annonces de cessions de fonds de commerce (familleavis = 'vente').

API publique opendatasoft, sans clé. On extrait le prix (texte libre) et le SIREN du
cédant, et on renvoie des Cession partiellement remplies (CA ajouté ensuite par le pipeline).
"""
from __future__ import annotations
import json
from typing import Optional

from comparables import cache
from comparables.fr.models import Cession
from comparables.fr.parsing import extract_price, extract_sirens

_BODACC_BASE = "https://bodacc-datadila.opendatasoft.com/api/explore"
BODACC_URL = _BODACC_BASE + "/v2.0/catalog/datasets/annonces-commerciales/records"
BODACC_EXPORT_URL = _BODACC_BASE + "/v2.1/catalog/datasets/annonces-commerciales/exports/json"
_HEADERS = {"User-Agent": "ncf-comparables/0.1 (interne)"}


def _acte_dict(fields: dict) -> dict:
    acte = fields.get("acte")
    if isinstance(acte, str):
        try:
            acte = json.loads(acte)
        except json.JSONDecodeError:
            return {}
    return acte if isinstance(acte, dict) else {}


def _cedant_siren(fields: dict, descriptif: str) -> Optional[str]:
    """SIREN du cédant. Le champ `registre` donne les SIREN *validés* (cédant + cessionnaire) ;
    le cédant est nommé en premier dans le descriptif. On prend donc le 1er SIREN du descriptif
    qui figure aussi dans `registre` (évite les n° de dossier/enregistrement parasites)."""
    registre = set(extract_sirens(fields.get("registre")))
    for s in extract_sirens(descriptif):
        if s in registre:
            return s
    return next(iter(registre), None)


def _build_where(departement: Optional[str], terms: Optional[list[str]],
                 since: Optional[str]) -> str:
    """Construit la clause ODSQL `where`. PURE (testée, sans I/O).

    Cessions de fonds de commerce avec un prix : 'fonds' + ('prix' ou 'moyennant').
    'fonds' ecarte fusions / cessions de titres ; le prix reel est extrait par extract_price,
    et les ratios aberrants sont filtres par les bandes de plausibilite en aval.
    (Exiger 'moyennant' seul etait trop restrictif : ~7,7k annonces vs ~58k avec 'prix'.)

    `terms` : termes d'activite combines en OU (chacun cherche dans l'acte ET le nom du
    commercant). Le `search()` d'opendatasoft fait un ET entre les mots d'une meme chaine,
    donc on passe UN terme par `search()` et on les relie par OR (un seul terme multi-mots
    resterait un ET — c'est ce qui faisait '0 resultat' sur 'celf, menuiserie')."""
    where = ["familleavis = 'vente'", "search(acte, 'fonds')",
             "(search(acte, 'prix') or search(acte, 'moyennant'))"]
    if departement:
        where.append(f"numerodepartement = '{departement}'")
    if since:
        where.append(f"dateparution >= date'{since}'")
    if terms:
        # L'activite figure souvent dans le NOM du commercant (ex. "PHARMACIE...") autant
        # que dans le texte de l'acte -> chercher dans les deux champs.
        clauses = []
        for t in terms:
            safe = t.replace("'", " ").strip()
            if safe:
                clauses.append(f"search(acte, '{safe}')")
                clauses.append(f"search(commercant, '{safe}')")
        if clauses:
            where.append("(" + " or ".join(clauses) + ")")
    return " and ".join(where)


def _cession_from_fields(fields: dict) -> Optional[Cession]:
    """Construit une Cession à partir d'un dict de champs BODACC, ou None si pas de prix.

    Tolérant aux deux structures : records v2.0 et export v2.1 (mêmes noms de champs utiles ;
    `ville`/`url_complete` absents de l'export -> None)."""
    descriptif = _acte_dict(fields).get("descriptif", "") or ""
    prix = extract_price(descriptif)
    if prix is None:
        return None
    vente = _acte_dict(fields).get("vente", {})
    return Cession(
        ann_id=fields.get("id"),
        siren=_cedant_siren(fields, descriptif),
        nom=fields.get("commercant"),
        ville=fields.get("ville"),
        departement=fields.get("numerodepartement"),
        date=fields.get("dateparution"),
        categorie=vente.get("categorieVente") if isinstance(vente, dict) else None,
        prix=prix,
        descriptif=descriptif,
        url=fields.get("url_complete"),
    )


def fetch_cessions(departement: Optional[str] = None, contains: Optional[str] = None,
                   since: Optional[str] = None, limit: int = 50,
                   terms: Optional[list[str]] = None) -> list[Cession]:
    """Récupère des cessions portant un prix, du plus récent au plus ancien (API records, v2.0).

    departement : code département (ex '75'). terms : termes d'activité combinés en OU
    (ex ['menuiserie', 'charpente']). contains : compat — terme libre unique si `terms` absent.
    since : date min de parution 'YYYY-MM-DD' (ex 10 ans en arrière).
    Ne renvoie que les annonces dont on a su extraire un prix.
    """
    if terms is None and contains:
        terms = [contains]
    where = _build_where(departement, terms, since)

    session = cache.get_session()
    out: list[Cession] = []
    offset = 0
    page = min(100, max(limit, 10))
    while len(out) < limit and offset < 3000:           # garde-fou (API plafonne à 10000)
        params = {"where": where, "limit": page, "offset": offset,
                  "order_by": "dateparution desc"}
        resp = session.get(BODACC_URL, params=params, headers=_HEADERS, timeout=40)
        resp.raise_for_status()
        records = resp.json().get("records", [])
        if not records:
            break
        for rec in records:
            c = _cession_from_fields(rec.get("record", {}).get("fields", {}))
            if c is not None:
                out.append(c)
                if len(out) >= limit:
                    break
        offset += page
    return out


def fetch_cessions_bulk(departement: Optional[str] = None, terms: Optional[list[str]] = None,
                        since: Optional[str] = None, until: Optional[str] = None,
                        timeout: int = 300) -> list[Cession]:
    """Export BODACC en masse (endpoint /exports, SANS plafond d'offset) -> toutes les cessions
    avec prix de la fenêtre. Pour l'ingestion locale (cf. fr.ingest). `until` borne haute de
    dateparution (ex ingestion année par année pour limiter la taille des réponses)."""
    where = _build_where(departement, terms, since)
    if until:
        where += f" and dateparution <= date'{until}'"
    session = cache.get_session()
    resp = session.get(BODACC_EXPORT_URL, params={"where": where}, headers=_HEADERS, timeout=timeout)
    resp.raise_for_status()
    out: list[Cession] = []
    for fields in resp.json():                          # export v2.1 : liste de champs à plat
        c = _cession_from_fields(fields)
        if c is not None:
            out.append(c)
    return out
