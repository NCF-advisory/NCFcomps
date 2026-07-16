"""Betas sectoriels Damodaran : etalon externe de fiabilite des betas de l'echantillon."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend import security
from comparables import damodaran

router = APIRouter(prefix="/damodaran", tags=["damodaran"])


@router.get("/industries")
def list_industries(region: str = "Global",
                    user: str = Depends(security.current_user)) -> dict:
    """Industries Damodaran d'une region (beta desendette par secteur) pour le selecteur."""
    return {
        "region": region,
        "as_of": damodaran.as_of(region),
        "industries": damodaran.industries(region),
    }
