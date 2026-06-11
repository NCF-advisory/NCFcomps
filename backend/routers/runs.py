"""Historisation des analyses (réutilise comparables/store.py) + ré-export Excel.

Deux types d'analyses : 'comparables' (CompanyRecord) et 'cessions' (FR). La liste les
mélange (badge côté client) ; consultation et ré-export dispatchés selon le type.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from backend import security
from backend.schemas import SaveRunRequest
from comparables import store
from comparables.export.excel import build_excel_bytes
from comparables.fr.export import build_cessions_excel_bytes

router = APIRouter(prefix="/runs", tags=["runs"])

EXCEL_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("")
def list_runs(user: str = Depends(security.current_user)) -> dict:
    return {"runs": store.list_runs()}


@router.post("", status_code=201)
def save_run(body: SaveRunRequest, user: str = Depends(security.current_user)) -> dict:
    if body.records:
        run_id = store.save_run(body.records, username=user, label=body.label,
                                params=body.params)
    else:
        run_id = store.save_cessions_run(body.cessions, username=user, label=body.label,
                                         params=body.params)
    return {"id": run_id}


@router.get("/{run_id}")
def get_run(run_id: int, user: str = Depends(security.current_user)) -> dict:
    kind = store.run_kind(run_id)
    if kind == "cessions":
        cessions = store.load_cessions_run(run_id)
        return {"id": run_id, "kind": kind,
                "cessions": [c.model_dump() for c in cessions]}
    records = store.load_run(run_id)
    if not records:
        raise HTTPException(status_code=404, detail="Analyse inconnue.")
    return {"id": run_id, "kind": kind or "comparables",
            "records": [r.model_dump() for r in records]}


@router.delete("/{run_id}", status_code=204)
def delete_run(run_id: int, user: str = Depends(security.current_user)) -> None:
    store.delete_run(run_id)


@router.get("/{run_id}/export")
def export_run(run_id: int, user: str = Depends(security.current_user)) -> Response:
    kind = store.run_kind(run_id)
    if kind == "cessions":
        cessions = store.load_cessions_run(run_id)
        if not cessions:
            raise HTTPException(status_code=404, detail="Analyse inconnue.")
        data = build_cessions_excel_bytes(cessions)
        filename = f"cessions_fr_run_{run_id}.xlsx"
    else:
        records = store.load_run(run_id)
        if not records:
            raise HTTPException(status_code=404, detail="Analyse inconnue.")
        data = build_excel_bytes(records)
        filename = f"comparables_run_{run_id}.xlsx"
    return Response(content=data, media_type=EXCEL_MEDIA_TYPE,
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})
