"""Base sectorielle : bêtas et multiples agrégés par secteur sur l'historique enregistré.

Lecture seule, alimentée automatiquement par les analyses sauvegardées (store.save_run)
— pas de capture dédiée. Voir comparables/store.py (sector_aggregates / sector_records).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend import security
from comparables import store

router = APIRouter(prefix="/sectors", tags=["sectors"])


@router.get("")
def list_sectors(user: str = Depends(security.current_user)) -> dict:
    """Synthèse par secteur (effectif, médianes/quartiles des bêtas et multiples)."""
    return {"sectors": store.sector_aggregates()}


@router.get("/{sector}")
def sector_detail(sector: str, user: str = Depends(security.current_user)) -> dict:
    """Lignes individuelles d'un secteur (sociétés, bêtas et multiples déjà utilisés)."""
    return {"sector": sector, "records": store.sector_records(sector)}
