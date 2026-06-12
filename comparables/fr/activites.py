"""Interprétation du texte libre « activité » : mots-clés BODACC élargis + codes NAF cibles.

L'utilisateur tape un domaine (« conseil en informatique ») sans connaître le code NAF.
Ce module traduit ce texte en deux artefacts complémentaires :

1. des **mots-clés simples** (tokens distinctifs + synonymes) combinés en OU dans la
   requête plein-texte BODACC — un ET de phrase exacte ne trouve presque rien ;
2. des **codes NAF cibles** (nomenclature INSEE rev. 2 embarquée, données ouvertes)
   pour filtrer ensuite les annonces par l'activité réelle de la société cédante.
   Le libellé est cherché à TOUS les niveaux (division -> sous-classe) : « conseil en
   informatique » matche la division 62 (« Programmation, conseil et autres activités
   informatiques ») donc cible toute la famille 62.xx, pas seulement 62.02A.

Module pur (pas de réseau) : seulement la lecture du CSV embarqué `data/naf_rev2.csv`.
"""
from __future__ import annotations
import csv
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

_NAF_CSV = Path(__file__).parent / "data" / "naf_rev2.csv"

# Mots-outils ignorés dans toutes les comparaisons.
_STOPWORDS = {
    "de", "du", "des", "le", "la", "les", "l", "d", "et", "en", "a", "au", "aux", "ou",
    "pour", "par", "sur", "sous", "dans", "avec", "sans", "un", "une", "nca", "type",
}
# Tokens trop génériques pour servir de mot-clé BODACC seuls (ils restent utilisés pour
# cibler les NAF : « conseil » + « informatique » doivent tous deux figurer au libellé).
_GENERIQUES = {
    "conseil", "conseils", "commerce", "vente", "ventes", "service", "services",
    "activite", "activites", "exploitation", "entreprise", "entreprises", "societe",
    "travaux", "gestion", "detail", "gros", "autre", "autres", "magasin", "magasins",
    "specialise", "specialisee", "general", "generale", "fabrication", "production",
    "fonds", "produits", "articles", "etablissement", "agence", "cabinet",
}
# Synonymes métier (clés normalisées sans accent) : élargissent le rappel BODACC et le
# ciblage NAF. Volontairement courts et courants — la précision vient du filtre NAF.
_SYNONYMES: dict[str, tuple[str, ...]] = {
    "informatique": ("logiciel", "numerique", "ssii", "esn"),
    "logiciel": ("informatique", "numerique"),
    "numerique": ("informatique", "logiciel"),
    "restaurant": ("restauration", "brasserie", "pizzeria"),
    "restauration": ("restaurant", "brasserie", "traiteur"),
    "boulangerie": ("patisserie",),
    "patisserie": ("boulangerie",),
    "coiffure": ("coiffeur",),
    "esthetique": ("beaute", "institut"),
    "automobile": ("garage", "carrosserie", "vehicules"),
    "garage": ("automobile", "carrosserie"),
    "batiment": ("construction", "maconnerie", "btp"),
    "construction": ("batiment", "btp"),
    "transport": ("transports", "logistique", "demenagement"),
    "hotel": ("hotellerie", "hebergement"),
    "tabac": ("presse", "loto"),
    "optique": ("opticien", "lunetterie"),
    "boucherie": ("charcuterie",),
    "charcuterie": ("boucherie", "traiteur"),
    "pharmacie": ("officine", "pharmaceutique"),
    "fleuriste": ("fleurs",),
    "comptable": ("comptabilite", "expertise comptable"),
    "securite": ("surveillance", "gardiennage"),
    "nettoyage": ("proprete", "entretien"),
    "formation": ("enseignement",),
    "menuiserie": ("ebenisterie", "agencement"),
    "plomberie": ("chauffage", "sanitaire"),
    "electricite": ("electricien",),
    "peintre": ("peinture", "vitrerie"),
    "peinture": ("peintre", "vitrerie"),
}

_MAX_KEYWORDS = 8
_MIN_STEM = 4               # longueur mini pour un appariement par préfixe (pluriels…)
_NAF_CODE_RE = re.compile(r"^\d{2}(\d{2}[a-z]?)?$")


@dataclass(frozen=True)
class ActivityQuery:
    """Requête interprétée : ce qui part au BODACC + ce qui filtre les NAF."""
    raw: str
    keywords: list[str] = field(default_factory=list)
    naf_codes: list[str] = field(default_factory=list)
    naf_labels: list[str] = field(default_factory=list)


@lru_cache(maxsize=1)
def load_naf_levels() -> list[tuple[int, str, str]]:
    """Nomenclature NAF rev. 2, niveaux 2 à 5 : (niveau, code, libellé), CSV embarqué."""
    with open(_NAF_CSV, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        return [(int(row["niveau"]), row["code"], row["libelle"]) for row in reader]


def load_naf() -> list[tuple[str, str]]:
    """Sous-classes NAF (niveau 5) : (code, libellé) — la granularité du filtre."""
    return [(code, lib) for niveau, code, lib in load_naf_levels() if niveau == 5]


def normalize(text: str) -> str:
    """Minuscules, sans accents, ponctuation remplacée par des espaces."""
    nfkd = unicodedata.normalize("NFKD", text or "")
    flat = "".join(ch for ch in nfkd if not unicodedata.combining(ch)).lower()
    return re.sub(r"[^a-z0-9]+", " ", flat).strip()


def tokens(text: str) -> list[str]:
    """Tokens significatifs (normalisés, hors mots-outils), ordre conservé, dédupliqués."""
    out: list[str] = []
    for tok in normalize(text).split():
        if tok not in _STOPWORDS and len(tok) >= 2 and tok not in out:
            out.append(tok)
    return out


def _token_match(a: str, b: str) -> bool:
    """Équivalence par préfixe limitée aux flexions (pluriels…) : informatique~informatiques,
    mais PAS agence~agencement (mots différents : écart de longueur > 3)."""
    if a == b:
        return True
    if abs(len(a) - len(b)) > 3:
        return False
    return (len(a) >= _MIN_STEM and b.startswith(a)) or (len(b) >= _MIN_STEM and a.startswith(b))


def _matches_any(variants: list[str], label_toks: list[str]) -> bool:
    return any(_token_match(v, lt) for v in variants for lt in label_toks)


def _concept_groups(toks: list[str]) -> list[list[str]]:
    """Un groupe par token : le token + ses synonymes mono-mot (variantes équivalentes)."""
    groups: list[list[str]] = []
    for tok in toks:
        variants = [tok] + [normalize(s) for s in _SYNONYMES.get(tok, ()) if " " not in s]
        groups.append(variants)
    return groups


def _match_naf_by_tokens(toks: list[str]) -> list[tuple[str, str]]:
    """Racines NAF (code, libellé) dont le libellé satisfait TOUS les concepts.

    Cherche à tous les niveaux (division 2 -> sous-classe 5) : un libellé de division
    qui matche cible toute sa famille. Les entrées couvertes par une racine plus
    large déjà retenue sont écartées (on garde les racines, du général au précis).
    """
    groups = _concept_groups(toks)
    matched: list[tuple[int, str, str]] = []
    for niveau, code, libelle in load_naf_levels():
        label_toks = tokens(libelle)
        if all(_matches_any(g, label_toks) for g in groups):
            matched.append((niveau, code, libelle))
    matched.sort(key=lambda e: (e[0], e[1]))        # du plus général au plus précis
    roots: list[tuple[str, str]] = []
    for _, code, libelle in matched:
        if not any(code.startswith(root) for root, _ in roots):
            roots.append((code, libelle))
    return roots


def _expand_to_sous_classes(roots: list[tuple[str, str]]) -> list[str]:
    """Codes niveau 5 couverts par les racines (le NAF d'une société est une sous-classe)."""
    return [code for code, _ in load_naf()
            if any(code.startswith(root) for root, _ in roots)]


def _match_naf_by_code(compact: str) -> list[tuple[str, str]]:
    """Entrées NAF dont le code commence par `compact` (ex '62', '6202', '6202a')."""
    target = compact.upper()
    return [(code, lib) for code, lib in load_naf()
            if code.replace(".", "").upper().startswith(target)]


def _label_keywords(entries: list[tuple[str, str]]) -> list[str]:
    """Tokens distinctifs des libellés NAF (pour cibler le BODACC quand on part d'un code)."""
    out: list[str] = []
    for _, libelle in entries:
        for tok in tokens(libelle):
            if tok not in _GENERIQUES and tok not in out:
                out.append(tok)
    return out[:_MAX_KEYWORDS]


def interpret(text: str) -> ActivityQuery:
    """Traduit le texte libre en mots-clés BODACC (OU) + codes NAF cibles.

    - code NAF (« 62 », « 62.02A ») -> codes du préfixe, mots-clés tirés des libellés ;
    - texte (« conseil en informatique ») -> familles NAF dont le libellé couvre tous les
      concepts, à n'importe quel niveau de la nomenclature (division 62 entière ici),
      mots-clés = tokens distinctifs + synonymes (les génériques ne partent pas seuls
      au BODACC mais comptent pour le ciblage NAF) ;
    - si rien n'est interprétable, le texte brut reste l'unique mot-clé (comportement
      historique) et aucun filtre NAF n'est posé.
    """
    raw = (text or "").strip()
    compact = normalize(raw).replace(" ", "")
    if _NAF_CODE_RE.match(compact):
        entries = _match_naf_by_code(compact)
        return ActivityQuery(raw=raw, keywords=_label_keywords(entries),
                             naf_codes=[c for c, _ in entries],
                             naf_labels=[lb for _, lb in entries])

    toks = tokens(raw)
    if not toks:
        return ActivityQuery(raw=raw, keywords=[raw] if raw else [])

    roots = _match_naf_by_tokens(toks)
    distinctifs = [t for t in toks if t not in _GENERIQUES] or toks
    keywords: list[str] = []
    for tok in distinctifs:
        if tok not in keywords:
            keywords.append(tok)
        for syn in _SYNONYMES.get(tok, ()):
            if syn not in keywords:
                keywords.append(syn)
    return ActivityQuery(raw=raw, keywords=keywords[:_MAX_KEYWORDS],
                         naf_codes=_expand_to_sous_classes(roots),
                         naf_labels=[lb for _, lb in roots])


def keep_cession(naf: Optional[str], nom: Optional[str], query: ActivityQuery) -> bool:
    """Le couple (NAF, nom officiel de la cédante) passe-t-il le filtre d'activité ?

    Garde si le NAF de la cédante est ciblé, OU si son nom porte un mot-clé de la
    recherche (« MULTI SERVICES INFORMATIQUES » classée 63.11Z reste une société
    informatique). `nom` doit être le nom de la CÉDANTE seule — pas le champ
    `commercant` BODACC, qui mêle cédant et cessionnaire. Sans filtre NAF (aucun
    code ciblé), tout passe — la requête BODACC a déjà trié.
    """
    if not query.naf_codes:
        return True
    if naf and naf in set(query.naf_codes):
        return True
    if nom:
        nom_toks = tokens(nom)
        for kw in query.keywords:
            kw_toks = normalize(kw).split()
            if kw_toks and all(any(_token_match(k, nt) for nt in nom_toks) for k in kw_toks):
                return True
    return False
