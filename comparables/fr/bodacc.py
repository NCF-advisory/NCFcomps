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

BODACC_URL = ("https://bodacc-datadila.opendatasoft.com/api/explore/v2.0"
              "/catalog/datasets/annonces-commerciales/records")
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


def fetch_cessions(departement: Optional[str] = None, contains: Optional[str] = None,
                   since: Optional[str] = None, limit: int = 50) -> list[Cession]:
    """Récupère des cessions portant un prix, du plus récent au plus ancien.

    departement : code département (ex '75'). contains : terme libre (ex 'boulangerie').
    since : date min de parution 'YYYY-MM-DD' (ex 10 ans en arrière).
    Ne renvoie que les annonces dont on a su extraire un prix.
    """
    # Cessions de fonds de commerce avec un prix : 'fonds' + ('prix' ou 'moyennant').
    # 'fonds' ecarte fusions / cessions de titres ; le prix reel est extrait par extract_price,
    # et les ratios aberrants sont filtres par les bandes de plausibilite en aval.
    # (Exiger 'moyennant' seul etait trop restrictif : ~7,7k annonces vs ~58k avec 'prix'.)
    where = ["familleavis = 'vente'", "search(acte, 'fonds')",
             "(search(acte, 'prix') or search(acte, 'moyennant'))"]
    if departement:
        where.append(f"numerodepartement = '{departement}'")
    if since:
        where.append(f"dateparution >= date'{since}'")
    if contains:
        # L'activite figure souvent dans le NOM du commercant (ex. "PHARMACIE...") autant
        # que dans le texte de l'acte -> chercher dans les deux champs (bien plus de resultats).
        safe = contains.replace("'", " ")
        where.append(f"(search(acte, '{safe}') or search(commercant, '{safe}'))")

    session = cache.get_session()
    out: list[Cession] = []
    offset = 0
    page = min(100, max(limit, 10))
    while len(out) < limit and offset < 3000:           # garde-fou (API plafonne à 10000)
        params = {"where": " and ".join(where), "limit": page, "offset": offset,
                  "order_by": "dateparution desc"}
        resp = session.get(BODACC_URL, params=params, headers=_HEADERS, timeout=40)
        resp.raise_for_status()
        records = resp.json().get("records", [])
        if not records:
            break
        for rec in records:
            fields = rec.get("record", {}).get("fields", {})
            descriptif = _acte_dict(fields).get("descriptif", "") or ""
            prix = extract_price(descriptif)
            if prix is None:
                continue
            vente = _acte_dict(fields).get("vente", {})
            out.append(Cession(
                siren=_cedant_siren(fields, descriptif),
                nom=fields.get("commercant"),
                ville=fields.get("ville"),
                departement=fields.get("numerodepartement"),
                date=fields.get("dateparution"),
                categorie=vente.get("categorieVente") if isinstance(vente, dict) else None,
                prix=prix,
                descriptif=descriptif,
                url=fields.get("url_complete"),
            ))
            if len(out) >= limit:
                break
        offset += page
    return out
