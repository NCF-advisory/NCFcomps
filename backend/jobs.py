"""File de tâches : exécution en arrière-plan, progression consultable, résultats persistés.

Les jobs terminés (done/error) sont écrits dans la base d'historisation (table `jobs`,
même SQLite que les runs) : un redémarrage du backend ne perd plus les résultats —
`get()` recharge depuis la base les jobs absents de la mémoire. La file reste
mono-processus (uvicorn 1 worker) ; passer multi-workers nécessiterait une file
partagée (Redis/RQ) — l'API publique (`submit`/`get`) est minimale pour ça.
"""
from __future__ import annotations
import json
import logging
import sqlite3
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from comparables.config import settings
from comparables.fr.models import CessionsBatch
from comparables.models import CompanyRecord

logger = logging.getLogger(__name__)

_MAX_KEPT = 50                  # en mémoire : au-delà, les plus anciens sont oubliés
_MAX_KEPT_DB = 100              # en base : taille bornée (purge des plus anciens)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --- Sérialisation des résultats par type de job (rechargement après redémarrage) ---

def _serialize_result(kind: str, result: Any) -> Optional[str]:
    if result is None:
        return None
    if kind == "comparables":               # list[CompanyRecord]
        return json.dumps([r.model_dump() for r in result], default=str)
    if kind == "cessions":                  # CessionsBatch
        return result.model_dump_json()
    return None


def _deserialize_result(kind: str, raw: Optional[str]) -> Any:
    if not raw:
        return None
    if kind == "comparables":
        return [CompanyRecord.model_validate(d) for d in json.loads(raw)]
    if kind == "cessions":
        return CessionsBatch.model_validate_json(raw)
    return None


@dataclass
class Job:
    id: str
    kind: str                   # "comparables" | "cessions"
    username: str
    params: dict = field(default_factory=dict)
    status: str = "pending"     # pending | running | done | error
    progress: int = 0
    total: int = 0
    error: Optional[str] = None
    result: Any = None          # rempli quand status == "done"
    created_at: str = field(default_factory=_now)

    def to_public(self) -> dict:
        """Vue API du job (sans `result`, renvoyé par les endpoints spécifiques)."""
        return {"id": self.id, "kind": self.kind, "status": self.status,
                "progress": self.progress, "total": self.total,
                "params": self.params, "error": self.error, "created_at": self.created_at}


def _connect() -> sqlite3.Connection:
    path = settings.history_db_path
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS jobs ("
        " id TEXT PRIMARY KEY, kind TEXT NOT NULL, username TEXT, params TEXT,"
        " status TEXT NOT NULL, progress INTEGER, total INTEGER, error TEXT,"
        " result TEXT, created_at TEXT NOT NULL)"
    )
    return conn


class JobManager:
    def __init__(self, max_workers: int = 3):
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def submit(self, kind: str, username: str, fn: Callable[[Job], Any],
               params: Optional[dict] = None) -> Job:
        """Enregistre puis lance `fn(job)` en arrière-plan ; renvoie le job immédiatement."""
        job = Job(id=uuid.uuid4().hex, kind=kind, username=username, params=params or {})
        with self._lock:
            self._jobs[job.id] = job
            while len(self._jobs) > _MAX_KEPT:
                del self._jobs[next(iter(self._jobs))]
        self._executor.submit(self._run, job, fn)
        return job

    def _run(self, job: Job, fn: Callable[[Job], Any]) -> None:
        job.status = "running"
        try:
            job.result = fn(job)
            job.status = "done"
        except Exception as exc:
            logger.warning("Echec du job %s (%s) : %s", job.id, job.kind, exc)
            job.error = str(exc)
            job.status = "error"
        self._persist(job)

    def _persist(self, job: Job) -> None:
        """Écrit le job terminé en base (best-effort : un échec ne casse jamais le job)."""
        try:
            conn = _connect()
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO jobs "
                    "(id, kind, username, params, status, progress, total, error, result,"
                    " created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (job.id, job.kind, job.username,
                     json.dumps(job.params, default=str), job.status, job.progress,
                     job.total, job.error, _serialize_result(job.kind, job.result),
                     job.created_at),
                )
                conn.execute(
                    "DELETE FROM jobs WHERE id NOT IN "
                    "(SELECT id FROM jobs ORDER BY created_at DESC LIMIT ?)",
                    (_MAX_KEPT_DB,),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as exc:
            logger.warning("Persistance du job %s impossible : %s", job.id, exc)

    def _load(self, job_id: str) -> Optional[Job]:
        """Recharge un job terminé depuis la base (après redémarrage du backend)."""
        try:
            conn = _connect()
            try:
                row = conn.execute(
                    "SELECT id, kind, username, params, status, progress, total, error,"
                    " result, created_at FROM jobs WHERE id = ?", (job_id,)
                ).fetchone()
            finally:
                conn.close()
        except Exception as exc:
            logger.warning("Lecture du job %s impossible : %s", job_id, exc)
            return None
        if row is None:
            return None
        job = Job(id=row[0], kind=row[1], username=row[2] or "",
                  params=json.loads(row[3]) if row[3] else {}, status=row[4],
                  progress=row[5] or 0, total=row[6] or 0, error=row[7],
                  result=_deserialize_result(row[1], row[8]), created_at=row[9])
        return job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            job = self._jobs.get(job_id)
        if job is not None:
            return job
        job = self._load(job_id)
        if job is not None:
            with self._lock:
                self._jobs.setdefault(job_id, job)
        return job


manager = JobManager()
