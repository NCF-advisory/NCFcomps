"""Logique PURE de l'onglet PME FR : extraction du prix de cession depuis le texte
libre BODACC, extraction des SIREN, calcul du % de CA et agrégation par activité.

Aucune I/O : entièrement couvert par des tests (le texte des annonces est libre, donc
l'extraction est « best-effort » et volontairement prudente).
"""
from __future__ import annotations
import math
import re
import statistics
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
                # "000000000" : SIREN factice vu dans certains registres BODACC
                if siren != "000000000" and siren not in out:
                    out.append(siren)
    return out


def cedant_siren(registre, descriptif: str) -> Optional[str]:
    """SIREN du cédant. Le champ `registre` donne les SIREN *validés* (cédant + cessionnaire) ;
    le cédant est nommé en premier dans le descriptif. On prend donc le 1er SIREN du descriptif
    qui figure aussi dans `registre` (évite les n° de dossier/enregistrement parasites).
    À défaut, le 1er SIREN du `registre` dans son ordre de publication (cédant en tête) —
    jamais une itération de set, non déterministe, qui pourrait retenir le cessionnaire."""
    valides_ordonnes = extract_sirens(registre)
    valides = set(valides_ordonnes)
    for s in extract_sirens(descriptif):
        if s in valides:
            return s
    return valides_ordonnes[0] if valides_ordonnes else None


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
