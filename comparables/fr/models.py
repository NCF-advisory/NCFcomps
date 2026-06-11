"""Modèles cessions FR : une cession (ligne du tableau) + le lot avec ses compteurs."""
from __future__ import annotations
from typing import Optional

from pydantic import BaseModel, Field


class Cession(BaseModel):
    # Identite (depuis BODACC)
    siren: Optional[str] = None
    nom: Optional[str] = None
    ville: Optional[str] = None
    departement: Optional[str] = None
    date: Optional[str] = None              # date de parution de l'annonce
    categorie: Optional[str] = None         # categorieVente BODACC

    # Prix de cession (extrait du texte libre de l'annonce)
    prix: Optional[float] = None            # en euros

    # Enrichissement : identite (Recherche d'entreprises) + finances (ratios_inpi_bce)
    naf: Optional[str] = None               # code activite principale
    activite: Optional[str] = None          # libelle d'activite
    ca: Optional[float] = None              # chiffre d'affaires (euros)
    ebe: Optional[float] = None             # EBE, proxy d'EBITDA -> AFFICHE « EBITDA » cote UI
    ebit: Optional[float] = None            # resultat d'exploitation
    ca_annee: Optional[int] = None          # exercice retenu (cale sur la date de cession)

    # Derives
    pct_ca: Optional[float] = None          # prix / CA (ratio, ex: 0.85 = 85% du CA)
    mult_ebe: Optional[float] = None        # prix / EBE(=EBITDA) (multiple, ex: 4.2 = 4,2x)

    # Tracabilite
    descriptif: Optional[str] = None
    url: Optional[str] = None


class CessionsBatch(BaseModel):
    """Résultat d'une recherche de cessions + entonnoir de filtrage.

    Les compteurs rendent un « 0 résultat » explicable : aucune annonce trouvée,
    activité hors cible (NAF), ou CA indisponible (comptes confidentiels). Ils portent
    sur les annonces effectivement balayées (le scan s'arrête à `limit` atteint).
    """
    cessions: list[Cession] = Field(default_factory=list)
    n_annonces: int = 0                 # annonces BODACC avec prix balayées
    n_naf_exclues: int = 0              # écartées par le filtre d'activité (NAF/nom)
    n_sans_ca: int = 0                  # écartées faute de CA disponible (require_ca)
    keywords: list[str] = Field(default_factory=list)   # requête élargie exécutée (OU)
    naf_codes: list[str] = Field(default_factory=list)  # codes NAF ciblés
    naf_labels: list[str] = Field(default_factory=list)  # libellés correspondants
