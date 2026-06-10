"""Lecture de la liasse fiscale (compte de résultat) : CA, EBE, EBIT depuis les codes de lignes.

Deux régimes :
- réel normal     : formulaire 2052 (codes alphabétiques FL, FS, GG...) ;
- réel simplifié  : formulaire 2033-B (codes numériques 210, 232, 270...).

L'EBE n'est PAS une ligne de la liasse : il est recalculé selon la convention
Banque de France (même grandeur que le dataset ratios INPI/BCE) :

    EBE = CA net + production stockée + production immobilisée + subventions
          - achats (marchandises + matières, variations de stocks comprises)
          - autres achats et charges externes - impôts et taxes
          - charges de personnel (salaires + charges sociales)

Module PUR (aucune I/O), couvert par des tests. Les codes des lignes sont
déclarés en tables pour rester vérifiables face à une liasse réelle.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional

# --- Régime réel normal : 2052 (compte de résultat) ---
# Produits pris dans l'EBE / charges déduites de l'EBE.
N_CA = "FL"                                            # chiffre d'affaires net total
N_PRODUITS_EBE = ("FL", "FM", "FN", "FO")              # CA, prod. stockée, prod. immobilisée, subventions
N_CHARGES_EBE = ("FS", "FT", "FU", "FV", "FW", "FX", "FY", "FZ")
#                achats march., var. stock, achats matières, var. stock, autres achats
#                et charges externes, impôts et taxes, salaires, charges sociales
N_EBIT = "GG"                                          # résultat d'exploitation

# --- Régime réel simplifié : 2033-B ---
S_CA = ("210", "214", "218")                           # ventes march., prod. vendue biens, services
S_PRODUITS_EBE = S_CA + ("222", "224", "226")          # + prod. stockée, prod. immobilisée, subventions
S_CHARGES_EBE = ("234", "236", "238", "240", "242", "244", "250", "252")
#                achats march., var. stock, achats matières, var. stock, charges externes,
#                impôts et taxes, rémunérations, charges sociales
S_EBIT = "270"                                         # résultat d'exploitation

# Codes dont l'absence rend l'EBE trop incertain pour être publié : une société en
# exploitation a des charges externes et (presque toujours) des charges de personnel.
N_EBE_REQUIRED_ANY = ("FW", "FY")
S_EBE_REQUIRED_ANY = ("242", "250")

_AMOUNT_CLEAN_RE = re.compile(r"[\s.  ']")


@dataclass
class LiasseResult:
    ca: Optional[float] = None
    ebe: Optional[float] = None
    ebit: Optional[float] = None
    regime: Optional[str] = None          # "normal" (2052) | "simplifie" (2033-B)
    missing_codes: list[str] = field(default_factory=list)   # codes absents traités comme 0


def parse_amount(raw: str) -> Optional[float]:
    """Montant de liasse (euros entiers) : espaces/points = milliers, parenthèses = négatif."""
    s = raw.strip()
    if not s:
        return None
    negative = s.startswith("(") and s.endswith(")") or s.startswith("-")
    s = _AMOUNT_CLEAN_RE.sub("", s.strip("()-"))
    s = s.replace(",", "")                # certaines liasses séparent les milliers par des virgules
    if not s.isdigit():
        return None
    value = float(s)
    return -value if negative else value


def detect_regime(codes: dict[str, float]) -> Optional[str]:
    """Régime d'après les codes présents : alphabétiques 2052 vs numériques 2033-B."""
    if any(c in codes for c in (N_CA, N_EBIT, "FR", "FS")):
        return "normal"
    if any(c in codes for c in S_CA + (S_EBIT, "232")):
        return "simplifie"
    return None


def _somme(codes: dict[str, float], keys: tuple[str, ...],
           missing: list[str]) -> float:
    total = 0.0
    for k in keys:
        if k in codes:
            total += codes[k]
        else:
            missing.append(k)
    return total


def compute(codes: dict[str, float]) -> LiasseResult:
    """CA / EBE / EBIT depuis un dict {code: montant}. Codes absents = 0 (tracés
    dans missing_codes) ; l'EBE n'est publié que si le CA et au moins une charge
    structurante (charges externes ou personnel) sont présents."""
    regime = detect_regime(codes)
    if regime is None:
        return LiasseResult()

    missing: list[str] = []
    if regime == "normal":
        ca = codes.get(N_CA)
        produits = _somme(codes, N_PRODUITS_EBE, missing)
        charges = _somme(codes, N_CHARGES_EBE, missing)
        ebit = codes.get(N_EBIT)
        ebe_ok = ca is not None and any(c in codes for c in N_EBE_REQUIRED_ANY)
    else:
        ca_parts = [codes[c] for c in S_CA if c in codes]
        ca = sum(ca_parts) if ca_parts else None
        produits = _somme(codes, S_PRODUITS_EBE, missing)
        charges = _somme(codes, S_CHARGES_EBE, missing)
        ebit = codes.get(S_EBIT)
        ebe_ok = ca is not None and any(c in codes for c in S_EBE_REQUIRED_ANY)

    return LiasseResult(
        ca=ca,
        ebe=(produits - charges) if ebe_ok else None,
        ebit=ebit,
        regime=regime,
        missing_codes=sorted(set(missing)),
    )
