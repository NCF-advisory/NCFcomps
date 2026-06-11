"""Schémas pydantic des requêtes/réponses de l'API."""
from __future__ import annotations
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from comparables.fr.models import Cession
from comparables.models import CompanyRecord


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    username: str
    name: Optional[str] = None


class ComparablesJobRequest(BaseModel):
    tickers: list[str] = Field(min_length=1, max_length=50)
    # Garde 0 <= IS < 1 (un IS > 1 inverserait le signe du désendettement).
    tax_rate: Optional[float] = Field(default=None, ge=0.0, lt=1.0)
    period: Optional[str] = None        # ex "5y" (défaut : settings.beta_period)
    frequency: Optional[str] = None     # "1mo" | "1wk" (défaut : settings.beta_frequency)


class ResolveRequest(BaseModel):
    """Résolution de noms de sociétés en tickers Yahoo."""
    names: list[str] = Field(min_length=1, max_length=50)


class RecordsPayload(BaseModel):
    """Sous-ensemble de comparables (sélection/exclusion côté client, sans re-fetch)."""
    records: list[CompanyRecord]


class SaveRunRequest(BaseModel):
    """Sauvegarde d'une analyse : comparables (`records`) OU cessions FR (`cessions`)."""
    records: list[CompanyRecord] = Field(default_factory=list)
    cessions: list[Cession] = Field(default_factory=list)
    label: Optional[str] = None
    params: Optional[dict] = None

    @model_validator(mode="after")
    def _un_seul_type(self) -> "SaveRunRequest":
        if bool(self.records) == bool(self.cessions):    # ni l'un ni l'autre, ou les deux
            raise ValueError("Fournir soit `records` (comparables), soit `cessions` (FR).")
        return self


class CessionsPayload(BaseModel):
    """Sous-ensemble de cessions (sélection côté client : stats / export, sans re-fetch)."""
    cessions: list[Cession] = Field(min_length=1)


class CessionsJobRequest(BaseModel):
    departement: Optional[str] = None   # ex "75"
    contains: Optional[str] = None      # ex "boulangerie"
    since: Optional[str] = None         # "YYYY-MM-DD" (défaut : fenêtre 10 ans)
    limit: int = Field(default=50, ge=1, le=300)
    require_ca: bool = True             # ne garder que les cessions dont le CA est connu
