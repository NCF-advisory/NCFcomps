"""Modèle d'une cession de fonds de commerce (une ligne du tableau PME FR)."""
from __future__ import annotations
from typing import Optional

from pydantic import BaseModel


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
    ebe: Optional[float] = None             # excedent brut d'exploitation (~EBITDA)
    ebit: Optional[float] = None            # resultat d'exploitation
    ca_annee: Optional[int] = None          # exercice retenu (cale sur la date de cession)

    # Derives
    pct_ca: Optional[float] = None          # prix / CA (ratio, ex: 0.85 = 85% du CA)
    mult_ebe: Optional[float] = None        # prix / EBE (multiple, ex: 4.2 = 4,2x l'EBE)

    # Tracabilite
    descriptif: Optional[str] = None
    url: Optional[str] = None
