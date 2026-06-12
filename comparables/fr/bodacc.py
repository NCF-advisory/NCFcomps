"""Accès BODACC : annonces de cessions de fonds de commerce (familleavis = 'vente').

API publique opendatasoft, sans clé. On extrait le prix (texte libre) et le SIREN du
cédant, et on renvoie des Cession partiellement remplies (CA ajouté ensuite par le pipeline).
"""
from __future__ import annotations
import json
from typing import Optional

from comparables import cache
from comparables.fr.models import Cession
from comparables.fr.parsing import cedant_siren, extract_price

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
    """SIREN du cédant (logique pure dans parsing.cedant_siren, partagée avec la
    réplique locale des ventes — cf. fr/referentiels.py)."""
    return cedant_siren(fields.get("registre"), descriptif)


def fetch_cessions(departement: Optional[str] = None, contains: Optional[str] = None,
                   since: Optional[str] = None, limit: int = 50,
                   keywords: Optional[list[str]] = None,
                   search_in: tuple[str, ...] = ("acte", "commercant"),
                   until: Optional[str] = None) -> list[Cession]:
    """Récupère des cessions portant un prix, du plus récent au plus ancien.

    departement : code département (ex '75'). contains : terme libre (ex 'boulangerie').
    keywords : variantes du terme (synonymes) combinées en OU — prime sur `contains`.
    search_in : champs où chercher les termes. Le nom du commerçant seul
    (('commercant',)) est bien plus précis que le texte de l'acte (inventaires…).
    since / until : bornes de parution 'YYYY-MM-DD' (min incluse, max exclue) — le
    balayage par tranches contourne le plafond de pagination de l'API (~10 000).
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
    if until:
        where.append(f"dateparution < date'{until}'")
    terms = [t.strip() for t in (keywords if keywords else [contains] if contains else [])
             if t and t.strip()]
    if terms:
        # L'activite figure souvent dans le NOM du commercant (ex. "PHARMACIE...") autant
        # que dans le texte de l'acte -> par defaut, chercher dans les deux champs.
        # NB : search() exige TOUS les mots d'un terme -> les variantes se combinent en OU.
        ors = []
        for t in terms:
            safe = t.replace("'", " ")
            for field in search_in:
                ors.append(f"search({field}, '{safe}')")
        where.append("(" + " or ".join(ors) + ")")

    session = cache.get_session()
    out: list[Cession] = []
    seen: set[tuple] = set()
    offset = 0
    page = min(100, max(limit, 10))
    while len(out) < limit and offset < 6000:           # garde-fou (API plafonne à 10000)
        params = {"where": " and ".join(where), "limit": page, "offset": offset,
                  "order_by": "dateparution desc"}
        resp = session.get(BODACC_URL, params=params, headers=_HEADERS, timeout=40)
        resp.raise_for_status()
        records = resp.json().get("records", [])
        if not records:
            break
        for rec in records:
            fields = rec.get("record", {}).get("fields", {})
            # Rectificatifs / annulations : republient un acte déjà compté -> exclus.
            typeavis = (fields.get("typeavis") or "").strip().lower()
            if typeavis.startswith(("rectificatif", "annulation")):
                continue
            descriptif = _acte_dict(fields).get("descriptif", "") or ""
            prix = extract_price(descriptif)
            if prix is None:
                continue
            siren = _cedant_siren(fields, descriptif)
            # Dédoublonnage (additifs, republications) : même cédant + même prix = même acte.
            key = (siren or fields.get("commercant"), prix)
            if key in seen:
                continue
            seen.add(key)
            vente = _acte_dict(fields).get("vente", {})
            out.append(Cession(
                siren=siren,
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
