"""Logique PURE de l'onglet PME FR : extraction du prix de cession depuis le texte
libre BODACC, extraction des SIREN, calcul du % de CA et agrégation par activité.

Aucune I/O : entièrement couvert par des tests (le texte des annonces est libre, donc
l'extraction est « best-effort » et volontairement prudente).
"""
from __future__ import annotations
import math
import re
import statistics
import unicodedata
from typing import Iterable, Optional

# Espaces possibles dans les nombres : normal, insécable ( ), fine insécable ( ).
_SP = "   "
# Nombre au format FR : point/espace = séparateur de milliers, virgule = décimale.
_NUM = r"\d[\d." + _SP + r"]*(?:,\d{1,2})?"
_CUR = r"\s*(?:€|euros?|eur\b)"
# Mots-clés signalant un prix de cession (et NON le capital social).
_KEYWORDS = (r"(?:moyennant(?:\s+un)?(?:\s+prix)?|"
             r"prix\s+(?:de\s+cession|principal|stipul\w+|de\s+vente|de|:)|"
             r"montant\s+de|cédé\w*\s+(?:moyennant|pour))")
_PRICE_RE = re.compile(_KEYWORDS + r"[^€\d]{0,40}?(" + _NUM + r")" + _CUR, re.IGNORECASE)

_SIREN_RE = re.compile(r"\d[\d" + _SP + r"]{7,}\d")


def parse_fr_amount(raw: str) -> Optional[float]:
    """Convertit un montant au format français ('124.548', '150 000,00') en float."""
    s = re.sub(r"[\s" + _SP + r"]", "", raw)
    if "," in s:                       # virgule décimale -> les points sont des milliers
        s = s.replace(".", "").replace(",", ".")
    else:                              # pas de virgule -> les points sont des milliers
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def extract_price(descriptif: Optional[str]) -> Optional[float]:
    """Extrait le prix de cession d'une annonce BODACC, ou None si introuvable/implausible."""
    if not descriptif:
        return None
    for m in _PRICE_RE.finditer(descriptif):
        amount = parse_fr_amount(m.group(1))
        if amount is not None and 100.0 <= amount <= 1e9:   # garde-fou anti-bruit
            return amount
    return None


def extract_sirens(registre) -> list[str]:
    """SIREN (9 chiffres) présents dans le champ `registre` BODACC, dédupliqués, ordre conservé."""
    if registre is None:
        return []
    items = registre if isinstance(registre, list) else [registre]
    out: list[str] = []
    for it in items:
        for tok in _SIREN_RE.findall(str(it)):
            digits = re.sub(r"[\s" + _SP + r"]", "", tok)
            if len(digits) >= 9:
                siren = digits[:9]
                if siren not in out:
                    out.append(siren)
    return out


# ---------------------------------------------------------------------------
# Termes de recherche (activité) : découpage multi-termes + synonymes métier.
#
# Le `search()` d'opendatasoft fait un ET implicite entre les mots d'une même
# chaîne : `search(acte, 'celf menuiserie')` exige les DEUX mots → quasi 0
# résultat. On découpe donc la saisie en termes indépendants combinés en OU,
# et on élargit chaque métier à ses synonymes (gisement ~×6 mesuré sur BODACC).
# ---------------------------------------------------------------------------

_STOPWORDS = {"de", "du", "des", "la", "le", "les", "un", "une", "et", "en",
              "aux", "au", "sur", "pour", "par", "dans"}
# Mots OMNIPRÉSENTS dans le texte juridique BODACC (« avis et publicité légale »…) ou déjà
# garantis par le filtre de base : les chercher revient à tout ramener (« publicité » = 93 % des
# annonces) -> bruit. On les écarte des termes de recherche (mais ils servent à détecter le NAF).
_BODACC_NOISE = {"publicite", "publication", "avis", "annonce", "legale", "legal",
                 "insertion", "fonds", "commerce", "cession", "vente"}
_QUOTED_RE = re.compile(r'"([^"]+)"')


def strip_accents(s: str) -> str:
    """Minuscule, sans accents, espaces normalisés — pour comparer/dédupliquer."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().split())


def parse_search_terms(raw: Optional[str]) -> list[str]:
    """Découpe la saisie utilisateur en termes de recherche indépendants (combinés en OU).

    - une expression entre guillemets "..." est conservée telle quelle (phrase exacte) ;
    - sinon, virgules ET espaces séparent des termes indépendants ;
    - les mots-outils (de, la, et…) et les jetons < 3 caractères (hors guillemets) sont ignorés ;
    - doublons supprimés (insensible à la casse et aux accents), ordre conservé. PURE (testée).
    """
    if not raw or not raw.strip():
        return []
    terms: list[str] = []
    for m in _QUOTED_RE.finditer(raw):              # 1) phrases exactes entre guillemets
        phrase = m.group(1).strip()
        if phrase:
            terms.append(phrase)
    rest = _QUOTED_RE.sub(" ", raw)                 # 2) le reste : virgules + espaces
    for tok in re.split(r"[,\s]+", rest):
        tok = tok.strip()
        norm = strip_accents(tok)
        if len(tok) >= 3 and norm not in _STOPWORDS and norm not in _BODACC_NOISE:
            terms.append(tok)
    out: list[str] = []
    seen: set[str] = set()
    for t in terms:
        k = strip_accents(t)
        if k and k not in seen:
            seen.add(k)
            out.append(t)
    return out


# Synonymes par métier de fonds de commerce. Clé = terme courant ; valeur = famille
# (formes non accentuées : le `search()` opendatasoft est insensible aux accents).
# Élargir librement : tout membre d'un groupe tire l'ensemble du groupe.
SECTOR_SYNONYMS: dict[str, tuple[str, ...]] = {
    "menuiserie": ("menuiserie", "menuisier", "agencement", "fermetures", "charpente",
                   "ebenisterie", "escaliers", "cuisiniste", "pose de cuisines"),
    "boulangerie": ("boulangerie", "boulanger", "patisserie", "viennoiserie", "boulange"),
    "patisserie": ("patisserie", "boulangerie", "chocolaterie", "confiserie"),
    "restaurant": ("restaurant", "restauration", "brasserie", "pizzeria", "creperie",
                   "snack", "traiteur"),
    "bar": ("bar", "tabac", "cafe", "brasserie", "pmu", "presse", "loto"),
    "coiffure": ("coiffure", "coiffeur", "salon de coiffure", "esthetique", "barbier"),
    "esthetique": ("esthetique", "institut de beaute", "onglerie", "spa", "coiffure"),
    "boucherie": ("boucherie", "boucher", "charcuterie", "traiteur", "rotisserie"),
    "pharmacie": ("pharmacie", "officine", "parapharmacie"),
    "fleuriste": ("fleuriste", "fleurs", "horticulture", "jardinerie"),
    "plomberie": ("plomberie", "plombier", "chauffagiste", "sanitaire", "chauffage"),
    "electricite": ("electricite", "electricien", "electrique", "domotique"),
    "garage": ("garage", "mecanique", "carrosserie", "reparation automobile", "automobile"),
    "maconnerie": ("maconnerie", "macon", "gros oeuvre", "batiment", "btp"),
    "peinture": ("peinture", "peintre", "ravalement", "decoration"),
    "carrelage": ("carrelage", "carreleur", "faience", "revetement"),
    "couverture": ("couverture", "couvreur", "toiture", "zinguerie", "etancheite"),
    "terrassement": ("terrassement", "tp", "travaux publics", "vrd"),
    "boulange": ("boulangerie", "boulanger"),
    "epicerie": ("epicerie", "alimentation", "superette", "alimentation generale"),
    "tabac": ("tabac", "bar", "presse", "loto", "pmu", "civette"),
    "pressing": ("pressing", "blanchisserie", "laverie", "nettoyage a sec"),
    "optique": ("optique", "opticien", "lunetterie"),
    "auto-ecole": ("auto-ecole", "auto ecole", "ecole de conduite"),
}


def parse_naf_filters(raw: Optional[str]) -> list[str]:
    """Découpe une saisie de codes NAF en motifs normalisés (sans points/espaces, majuscules).

    Accepte codes exacts ('43.32A'), préfixes ('43', '4332') et listes ('43.32A, 16.23Z').
    Ex : '43.32A, 16' -> ['4332A', '16']. PURE (testée)."""
    if not raw:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for tok in re.split(r"[,;\s]+", raw):
        norm = re.sub(r"[.\s]", "", tok).upper()
        if norm and norm not in seen:
            seen.add(norm)
            out.append(norm)
    return out


def naf_matches(naf: Optional[str], patterns: list[str]) -> bool:
    """Le code NAF correspond-il à l'un des motifs (préfixe, points/casse ignorés) ?

    Sans motif -> True (pas de filtre). PURE (testée)."""
    if not patterns:
        return True
    if not naf:
        return False
    code = re.sub(r"[.\s]", "", naf).upper()
    return any(code.startswith(p) for p in patterns)


def filter_by_naf(cessions: list, patterns: list[str]) -> list:
    """Conserve les cessions dont le NAF correspond aux motifs (cf. naf_matches)."""
    if not patterns:
        return list(cessions)
    return [c for c in cessions if naf_matches(getattr(c, "naf", None), patterns)]


def expand_synonyms(terms: list[str]) -> list[str]:
    """Élargit chaque terme à sa famille de synonymes métier (cf. SECTOR_SYNONYMS).

    Un terme appartenant à un groupe (clé OU membre) tire tout le groupe. Les termes
    inconnus sont conservés tels quels. Doublons supprimés (casse/accents), ordre conservé.
    PURE (testée)."""
    out: list[str] = []
    seen: set[str] = set()

    def add(t: str) -> None:
        k = strip_accents(t)
        if k and k not in seen:
            seen.add(k)
            out.append(t)

    for t in terms:
        add(t)
        nt = strip_accents(t)
        for key, group in SECTOR_SYNONYMS.items():
            family = {strip_accents(key), *(strip_accents(g) for g in group)}
            if nt in family:
                for g in group:
                    add(g)
    return out


# Codes NAF (rév. 2) par métier de fonds de commerce. Sert à FILTRER par secteur après
# identification (précision), pour éliminer les faux positifs du mot-clé (cf. naf_matches).
# Codes au niveau classe/sous-classe (préfixes) ; un préfixe court ('4520') capte les déclinaisons.
SECTOR_NAF: dict[str, tuple[str, ...]] = {
    "menuiserie": ("4332", "1623", "1624", "3109", "4334"),
    "boulangerie": ("1071", "4724"),
    "patisserie": ("1071", "4724"),
    "restaurant": ("5610", "5630"),
    "bar": ("5630", "4726", "4762"),
    "tabac": ("4726", "4762", "5630"),
    "coiffure": ("9602",),
    "esthetique": ("9602", "9604"),
    "boucherie": ("4722", "1013"),
    "pharmacie": ("4773",),
    "fleuriste": ("4776",),
    "plomberie": ("4322",),
    "electricite": ("4321",),
    "garage": ("4520", "4511", "4519", "4531", "4532"),
    "maconnerie": ("4399", "4120", "4391"),
    "peinture": ("4334",),
    "carrelage": ("4333",),
    "couverture": ("4391", "4322"),
    "epicerie": ("4711", "4721", "4729"),
    "pressing": ("9601",),
    "optique": ("4778",),
    "auto-ecole": ("8553",),
    "publicite": ("7311", "7312"),
    "communication": ("7311", "7312", "5819", "7021"),
}


def naf_codes_for(raw: Optional[str]) -> list[str]:
    """Codes NAF (préfixes) déduits du métier saisi, pour proposer un filtre NAF automatique.

    Détecte la famille métier dans la saisie BRUTE (y compris des mots écartés de la recherche
    texte comme « publicité ») : `agence de publicité` -> ['7311', '7312']. [] si métier inconnu.
    PURE (testée)."""
    if not raw:
        return []
    norm = strip_accents(raw)
    tokens = set(re.split(r"[,\s]+", norm))
    out: list[str] = []
    seen: set[str] = set()
    for key, codes in SECTOR_NAF.items():
        family = {key, *(strip_accents(g) for g in SECTOR_SYNONYMS.get(key, ()))}
        hit = any((" " in f and f in norm) or (" " not in f and f in tokens) for f in family)
        if hit:
            for code in codes:
                if code not in seen:
                    seen.add(code)
                    out.append(code)
    return out


# Bandes de plausibilité. prix/CA : un fonds vaut typiquement 0,05 à 4 x le CA.
# prix/EBE : multiple ~0,5 à 15 x l'EBE. Hors bande = appariement douteux (fonds = 1
# établissement d'un groupe, cession de titres, mauvais SIREN) -> exclu des médianes.
PCT_CA_BOUNDS = (0.05, 4.0)
MULT_EBE_BOUNDS = (0.5, 15.0)


def compute_pct_ca(prix: Optional[float], ca: Optional[float]) -> Optional[float]:
    """Prix de cession rapporté au CA (ratio). None si CA absent ou <= 0."""
    if prix is None or ca is None or ca <= 0:
        return None
    return prix / ca


def compute_mult_ebe(prix: Optional[float], ebe: Optional[float]) -> Optional[float]:
    """Prix de cession rapporté à l'EBE (multiple). None si EBE absent ou <= 0."""
    if prix is None or ebe is None or ebe <= 0:
        return None
    return prix / ebe


def is_plausible_pct(pct: Optional[float]) -> bool:
    """Le ratio prix/CA est-il dans une fourchette défendable pour un fonds mono-établissement ?"""
    return pct is not None and PCT_CA_BOUNDS[0] <= pct <= PCT_CA_BOUNDS[1]


def is_plausible_mult_ebe(mult: Optional[float]) -> bool:
    """Le multiple prix/EBE est-il dans une fourchette défendable ?"""
    return mult is not None and MULT_EBE_BOUNDS[0] <= mult <= MULT_EBE_BOUNDS[1]


# Règle d'or des médianes : exclure les multiples extrêmes.
MIN_N_FOR_TRIM = 8          # en deçà, échantillon trop petit pour un trim statistique fiable
MODIFIED_Z_THRESHOLD = 3.5  # seuil du z-score modifié (Iglewicz & Hoaglin)


def robust_mask(values: list, bounds: tuple[float, float]) -> list[bool]:
    """Masque booléen aligné sur `values` : True si la valeur est gardée par le filtre
    robuste (dans les bornes métier ET non-outlier statistique). Couches :

    1. garde-fou métier : valeur dans `bounds` (hors fourchette = erreur d'appariement) ;
    2. exclusion des extrêmes restants : z-score modifié via la MAD, en log (médiane + MAD
       = robustes ; log = adapté aux ratios), seulement si n >= 8.
    """
    lo, hi = bounds
    in_bounds = [v is not None and math.isfinite(v) and lo <= v <= hi for v in values]
    idx = [i for i, ok in enumerate(in_bounds) if ok]
    if len(idx) < MIN_N_FOR_TRIM:
        return in_bounds
    logs = [math.log(float(values[i])) for i in idx]
    med = statistics.median(logs)
    mad = statistics.median([abs(x - med) for x in logs])
    if mad == 0:                                   # valeurs trop concentrées -> pas de trim
        return in_bounds
    mask = list(in_bounds)
    for i, x in zip(idx, logs):
        if abs(0.6745 * (x - med) / mad) > MODIFIED_Z_THRESHOLD:
            mask[i] = False
    return mask


def robust_values(values: Iterable[Optional[float]],
                  bounds: tuple[float, float]) -> tuple[list[float], int]:
    """Valeurs gardées par le filtre robuste (cf. robust_mask) + nb d'extrêmes exclus."""
    vals = list(values)
    mask = robust_mask(vals, bounds)
    kept = [float(v) for v, keep in zip(vals, mask) if keep]
    lo, hi = bounds
    in_bounds = sum(1 for v in vals if v is not None and math.isfinite(v) and lo <= v <= hi)
    return kept, in_bounds - len(kept)


def _median(values: Iterable[Optional[float]]) -> Optional[float]:
    vals = [v for v in values if v is not None]
    return statistics.median(vals) if vals else None


def robust_median(values: Iterable[Optional[float]],
                  bounds: tuple[float, float]) -> tuple[Optional[float], int]:
    """Médiane robuste d'une métrique : ne garde que les valeurs DANS la bande métier et
    non-aberrantes (cf. robust_values). Renvoie (médiane | None, n retenu).

    Essentiel pour des médianes cohérentes : une ligne retenue pour son %CA valide ne doit PAS
    polluer la médiane ×EBE avec un multiple hors-bande (ex. 20,6x). PURE (testée)."""
    kept, _ = robust_values(values, bounds)
    return (statistics.median(kept) if kept else None, len(kept))


def summarize_by_activity(cessions: list) -> dict:
    """Agrège les cessions : médiane du % de CA (et n) au global et par activité (NAF).

    Les médianes ne portent que sur les ratios plausibles (cf. PCT_CA_BOUNDS) pour ne pas
    être faussées par les appariements douteux.
    """
    with_pct = [c for c in cessions if getattr(c, "pct_ca", None) is not None]
    pct_kept, pct_out = robust_values([c.pct_ca for c in with_pct], PCT_CA_BOUNDS)
    ebe_kept, ebe_out = robust_values([getattr(c, "mult_ebe", None) for c in cessions],
                                      MULT_EBE_BOUNDS)
    overall = {
        "n_total": len(cessions),
        "n_avec_pct": len(with_pct),
        "n_plausible": len(pct_kept),
        "n_pct_outliers": pct_out,            # extrêmes prix/CA exclus de la médiane
        "n_avec_ebe": len(ebe_kept),
        "n_ebe_outliers": ebe_out,            # extrêmes prix/EBE exclus de la médiane
        "median_pct_ca": _median(pct_kept),
        "median_mult_ebe": _median(ebe_kept),
        "median_prix": _median([c.prix for c in cessions]),
    }
    # Groupes par activité (cessions dans la bande prix/CA), médianes robustes par groupe.
    groups: dict[str, list] = {}
    for c in with_pct:
        if is_plausible_pct(c.pct_ca):
            groups.setdefault(getattr(c, "naf", None) or "(inconnu)", []).append(c)
    by_activite = []
    for naf, items in groups.items():
        pk, _ = robust_values([c.pct_ca for c in items], PCT_CA_BOUNDS)
        ek, _ = robust_values([c.mult_ebe for c in items], MULT_EBE_BOUNDS)
        by_activite.append({
            "naf": naf,
            "activite": next((c.activite for c in items if c.activite), None),
            "n": len(items),
            "median_pct_ca": _median(pk),
            "median_mult_ebe": _median(ek),
            "median_prix": _median([c.prix for c in items]),
            "median_ca": _median([c.ca for c in items]),
        })
    by_activite.sort(key=lambda d: d["n"], reverse=True)
    return {"overall": overall, "by_activite": by_activite}
