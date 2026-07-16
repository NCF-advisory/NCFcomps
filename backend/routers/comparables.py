"""Module 1 — comparables boursiers : job de calcul, résultats + stats, sélection, export."""
from __future__ import annotations

import math

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from backend import security
from backend.filenames import comparables_excel_filename
from backend.jobs import Job, manager
from backend.schemas import ComparablesJobRequest, RecordsPayload, ResolveRequest
from comparables import damodaran, pipeline
from comparables.config import settings
from comparables.export.excel import BETA_QUALITY_FIELDS, STATS_FIELDS, build_excel_bytes
from comparables.finance.beta import reliable_beta, sample_summary
from comparables.finance.multiples import summary_stats
from comparables.models import CompanyRecord
from comparables.sources import yahoo

router = APIRouter(prefix="/comparables", tags=["comparables"])

EXCEL_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _stats(records: list[CompanyRecord]) -> dict[str, dict[str, float]]:
    """Stats d'échantillon par champ (mêmes filtres inf/nan que l'Excel).

    Les champs bêta (régression, désendetté) excluent les R² < beta_min_r2 :
    affichés dans le tableau mais hors médiane/moyenne (pente non exploitable)."""
    out: dict[str, dict[str, float]] = {}
    for f in STATS_FIELDS:
        if f in BETA_QUALITY_FIELDS:
            values = (reliable_beta(getattr(r, f), r.r2, settings.beta_min_r2)
                      for r in records)
        else:
            values = (getattr(r, f) for r in records)
        s = summary_stats(values)
        if s:
            out[f] = s
    return out


def _beta_summary(records: list[CompanyRecord]) -> dict | None:
    """Synthèse bêta de la sélection : β moyen retenu endetté, ajusté (Blume), désendetté.

    Porte aussi le seuil d'illiquidité (`max_zero_share`, issu des settings) pour que le
    front signale les bêtas peu fiables avec le même seuil que le serveur — même canal que
    `min_r2`, mais injecté ici pour garder `sample_summary` (cœur financier) pur."""
    summary = sample_summary(
        ((r.beta_regression, r.r2, r.beta_unlevered) for r in records),
        settings.beta_min_r2,
    )
    if summary is not None:
        summary["max_zero_share"] = settings.beta_max_zero_share
    return summary


def _coverage(rec: CompanyRecord) -> str:
    """Couverture d'une ligne : ok / partielle / vide (signalement des échecs, UX analyste)."""
    has_fundamentals = rec.market_cap is not None
    has_beta = rec.beta_regression is not None
    if has_fundamentals and has_beta:
        return "ok"
    if has_fundamentals or has_beta or rec.name is not None:
        return "partielle"
    return "vide"


def sanitize(d: dict) -> dict:
    """Remplace les flottants non finis (inf/nan possibles chez Yahoo) par None :
    le JSON ne les accepte pas (starlette sérialise avec allow_nan=False)."""
    return {k: (None if isinstance(v, float) and not math.isfinite(v) else v)
            for k, v in d.items()}


def _damodaran_block(records: list[CompanyRecord]) -> dict:
    """Etalon Damodaran : industrie suggeree (vote des industries Yahoo de l'echantillon)
    + son benchmark (beta desendette sectoriel). L'utilisateur peut changer d'industrie
    cote interface ; la liste complete est servie par /api/damodaran/industries."""
    suggested = damodaran.suggest_industry([r.industry for r in records])
    return {
        "region": "Global",
        "as_of": damodaran.as_of(),
        "suggested_industry": suggested,
        "benchmark": damodaran.lookup(suggested) if suggested else None,
    }


def _records_payload(records: list[CompanyRecord]) -> dict:
    return {
        "records": [sanitize(r.model_dump()) for r in records],
        "coverage": {r.ticker: _coverage(r) for r in records},
        "stats": _stats(records),
        "beta_summary": _beta_summary(records),
        "damodaran": _damodaran_block(records),
    }


@router.post("/jobs", status_code=202)
def create_job(body: ComparablesJobRequest,
               user: str = Depends(security.current_user)) -> dict:
    tickers = [t.strip().upper() for t in body.tickers if t.strip()]
    if not tickers:
        raise HTTPException(status_code=422, detail="Aucun ticker exploitable.")
    params = {
        "tickers": tickers,
        "tax_rate": settings.tax_rate if body.tax_rate is None else body.tax_rate,
        "period": body.period or settings.beta_period,
        "frequency": body.frequency or settings.beta_frequency,
        "floor_net_debt": (settings.unlever_floor_net_debt
                           if body.floor_net_debt is None else body.floor_net_debt),
    }

    def fn(job: Job) -> list[CompanyRecord]:
        job.total = len(tickers)

        def on_progress(done: int, _total: int) -> None:
            job.progress = done

        return pipeline.build_comparables(tickers, tax_rate=params["tax_rate"],
                                          period=params["period"],
                                          frequency=params["frequency"],
                                          floor_net_debt=params["floor_net_debt"],
                                          progress=on_progress)

    job = manager.submit("comparables", user, fn, params=params)
    return job.to_public()


@router.get("/jobs/{job_id}")
def job_status(job_id: str, user: str = Depends(security.current_user)) -> dict:
    job = manager.get(job_id)
    if job is None or job.kind != "comparables":
        raise HTTPException(status_code=404, detail="Job inconnu.")
    payload = job.to_public()
    if job.status == "done":
        payload.update(_records_payload(job.result))
    return payload


@router.post("/stats")
def stats_for_selection(body: RecordsPayload,
                        user: str = Depends(security.current_user)) -> dict:
    """Recalcule les stats sur une sélection de comparables, sans aucun re-fetch réseau
    (exclusion d'un outlier = le client renvoie le sous-ensemble retenu)."""
    return {"n": len(body.records), "stats": _stats(body.records),
            "beta_summary": _beta_summary(body.records)}


@router.post("/resolve")
def resolve_names(body: ResolveRequest,
                  user: str = Depends(security.current_user)) -> dict:
    """Nom de société -> meilleur ticker Yahoo + alternatives (place principale privilégiée).

    Chaque résultat : {query, match (meilleur candidat ou None), alternatives (suivants)}
    pour permettre à l'utilisateur de corriger un choix ambigu côté interface."""
    results = []
    for name in body.names:
        try:
            results.append(yahoo.resolve_candidates(name))
        except Exception:
            results.append({"query": name, "match": None, "alternatives": []})
    return {"results": results}


@router.post("/export")
def export_excel(body: RecordsPayload,
                 user: str = Depends(security.current_user)) -> Response:
    libelle = body.libelle or "Échantillon"
    data = build_excel_bytes(body.records, libelle=libelle)
    filename = comparables_excel_filename(libelle)
    return Response(content=data, media_type=EXCEL_MEDIA_TYPE,
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})
