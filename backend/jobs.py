"""File de tâches en mémoire : calculs longs en arrière-plan, progression consultable.

Suffisant pour un outil interne mono-processus (uvicorn 1 worker). Si le backend passe
un jour en multi-workers, remplacer par une file partagée (Redis/RQ) — l'API publique
(`submit`/`get`) est volontairement minimale pour rendre ce remplacement indolore.
"""
from __future__ import annotations
import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

_MAX_KEPT = 50                  # au-delà, les jobs les plus anciens sont oubliés


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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


class JobManager:
    def __init__(self, max_workers: int = 2):
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

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)


manager = JobManager()
