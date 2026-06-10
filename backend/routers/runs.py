"""Historisation des analyses (réutilise comparables/store.py) + ré-export Excel."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from backend import security
from backend.schemas import SaveRunRequest
from comparables import store
from comparables.export.excel import build_excel_bytes

router = APIRouter(prefix="/runs", tags=["runs"])

EXCEL_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("")
def list_runs(user: str = Depends(security.current_user)) -> dict:
    return {"runs": store.list_runs()}


@router.post("", status_code=201)
def save_run(body: SaveRunRequest, user: str = Depends(security.current_user)) -> dict:
    if not body.records:
        raise HTTPException(status_code=422, detail="Aucun enregistrement à sauvegarder.")
    run_id = store.save_run(body.records, username=user, label=body.label, params=body.params)
    return {"id": run_id}


@router.get("/{run_id}")
def get_run(run_id: int, user: str = Depends(security.current_user)) -> dict:
    records = store.load_run(run_id)
    if not records:
        raise HTTPException(status_code=404, detail="Analyse inconnue.")
    return {"id": run_id, "records": [r.model_dump() for r in records]}


@router.delete("/{run_id}", status_code=204)
def delete_run(run_id: int, user: str = Depends(security.current_user)) -> None:
    store.delete_run(run_id)


@router.get("/{run_id}/export")
def export_run(run_id: int, user: str = Depends(security.current_user)) -> Response:
    records = store.load_run(run_id)
    if not records:
        raise HTTPException(status_code=404, detail="Analyse inconnue.")
    data = build_excel_bytes(records)
    return Response(content=data, media_type=EXCEL_MEDIA_TYPE,
                    headers={"Content-Disposition":
                             f'attachment; filename="comparables_run_{run_id}.xlsx"'})
