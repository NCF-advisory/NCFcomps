"""Module 2 — cessions de fonds de commerce FR : job de recherche + résultats agrégés."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend import security
from backend.jobs import Job, manager
from backend.routers.comparables import sanitize
from backend.schemas import CessionsJobRequest
from comparables.fr import pipeline as fr_pipeline
from comparables.fr.models import Cession
from comparables.fr.parsing import summarize_by_activity

router = APIRouter(prefix="/cessions", tags=["cessions"])


@router.post("/jobs", status_code=202)
def create_job(body: CessionsJobRequest,
               user: str = Depends(security.current_user)) -> dict:
    params = body.model_dump(exclude_none=True)

    def fn(job: Job) -> list[Cession]:
        return fr_pipeline.build_cessions(departement=body.departement,
                                          contains=body.contains, since=body.since,
                                          limit=body.limit, require_ca=body.require_ca)

    job = manager.submit("cessions", user, fn, params=params)
    return job.to_public()


@router.get("/jobs/{job_id}")
def job_status(job_id: str, user: str = Depends(security.current_user)) -> dict:
    job = manager.get(job_id)
    if job is None or job.kind != "cessions":
        raise HTTPException(status_code=404, detail="Job inconnu.")
    payload = job.to_public()
    if job.status == "done":
        cessions: list[Cession] = job.result
        payload["cessions"] = [sanitize(c.model_dump()) for c in cessions]
        payload["summary"] = summarize_by_activity(cessions)
    return payload
