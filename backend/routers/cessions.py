"""Module 2 — cessions FR : job de recherche, agrégats, sélection, export Excel."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from backend import security
from backend.jobs import Job, manager
from backend.routers.comparables import sanitize
from backend.schemas import CessionsJobRequest, CessionsPayload
from comparables.fr import pipeline as fr_pipeline
from comparables.fr.export import build_cessions_excel_bytes
from comparables.fr.models import CessionsBatch
from comparables.fr.parsing import (
    MULT_EBE_BOUNDS,
    PCT_CA_BOUNDS,
    robust_mask,
    summarize_by_activity,
)

router = APIRouter(prefix="/cessions", tags=["cessions"])

EXCEL_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.post("/jobs", status_code=202)
def create_job(body: CessionsJobRequest,
               user: str = Depends(security.current_user)) -> dict:
    params = body.model_dump(exclude_none=True)

    def fn(job: Job) -> CessionsBatch:
        def on_progress(done: int, total: int) -> None:
            job.progress, job.total = done, total

        return fr_pipeline.build_cessions(departement=body.departement,
                                          contains=body.contains, since=body.since,
                                          limit=body.limit, require_ca=body.require_ca,
                                          progress=on_progress)

    job = manager.submit("cessions", user, fn, params=params)
    return job.to_public()


@router.get("/jobs/{job_id}")
def job_status(job_id: str, user: str = Depends(security.current_user)) -> dict:
    job = manager.get(job_id)
    if job is None or job.kind != "cessions":
        raise HTTPException(status_code=404, detail="Job inconnu.")
    payload = job.to_public()
    if job.status == "done":
        batch: CessionsBatch = job.result
        payload["cessions"] = [sanitize(c.model_dump()) for c in batch.cessions]
        payload["summary"] = summarize_by_activity(batch.cessions)
        # Sélection par défaut = « règle d'or » (bornes + non-outlier), même logique
        # que Streamlit : le client décoche/recoche, les médianes se recalculent.
        pct_ok = robust_mask([c.pct_ca for c in batch.cessions], PCT_CA_BOUNDS)
        ebe_ok = robust_mask([c.mult_ebe for c in batch.cessions], MULT_EBE_BOUNDS)
        payload["retenu_defaut"] = [p or e for p, e in zip(pct_ok, ebe_ok)]
        # Entonnoir de recherche : rend un « 0 résultat » explicable côté client.
        payload["search"] = {
            "n_annonces": batch.n_annonces,
            "n_naf_exclues": batch.n_naf_exclues,
            "n_sans_ca": batch.n_sans_ca,
            "keywords": batch.keywords,
            "naf_codes": batch.naf_codes,
            "naf_labels": batch.naf_labels,
        }
    return payload


@router.post("/stats")
def stats_for_selection(body: CessionsPayload,
                        user: str = Depends(security.current_user)) -> dict:
    """Recalcule les agrégats sur une sélection de cessions, sans re-fetch réseau
    (décocher une ligne = le client renvoie le sous-ensemble retenu)."""
    return {"n": len(body.cessions), "summary": summarize_by_activity(body.cessions)}


@router.post("/export")
def export_excel(body: CessionsPayload,
                 user: str = Depends(security.current_user)) -> Response:
    data = build_cessions_excel_bytes(body.cessions)
    return Response(content=data, media_type=EXCEL_MEDIA_TYPE,
                    headers={"Content-Disposition": 'attachment; filename="cessions_fr.xlsx"'})
