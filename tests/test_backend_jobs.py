"""Tests de la persistance des jobs (SQLite) : un redémarrage ne perd plus les résultats."""
from __future__ import annotations

import time

from backend.jobs import JobManager
from comparables.fr.models import Cession, CessionsBatch
from comparables.models import CompanyRecord


def _wait_done(manager: JobManager, job_id: str, timeout: float = 5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = manager.get(job_id)
        if job and job.status in ("done", "error"):
            return job
        time.sleep(0.02)
    raise AssertionError("Job toujours en cours")


def _wait_persisted(job_id: str, timeout: float = 5.0):
    """Attend que le job soit relisible depuis la base par un NOUVEAU manager :
    le statut bascule en mémoire avant le commit SQLite (écriture best-effort)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = JobManager(max_workers=1).get(job_id)
        if job is not None and job.status in ("done", "error"):
            return job
        time.sleep(0.02)
    raise AssertionError("Job jamais persisté")


def test_job_cessions_persiste_et_recharge():
    batch = CessionsBatch(cessions=[Cession(siren="111222333", prix=1000.0)],
                          n_annonces=3, n_sans_ca=2, keywords=["boulangerie"])
    m1 = JobManager(max_workers=1)
    job = m1.submit("cessions", "dev", lambda j: batch, params={"contains": "boulangerie"})
    _wait_done(m1, job.id)

    loaded = _wait_persisted(job.id)            # « redémarrage » du backend
    assert loaded is not None and loaded.status == "done"
    assert loaded.params == {"contains": "boulangerie"}
    assert isinstance(loaded.result, CessionsBatch)
    assert loaded.result.n_annonces == 3
    assert loaded.result.cessions[0].siren == "111222333"


def test_job_comparables_persiste_et_recharge():
    records = [CompanyRecord(ticker="WMS", market_cap=1e9, ev_ebitda=8.5)]
    m1 = JobManager(max_workers=1)
    job = m1.submit("comparables", "dev", lambda j: records)
    _wait_done(m1, job.id)

    loaded = _wait_persisted(job.id)
    assert loaded is not None and loaded.status == "done"
    assert isinstance(loaded.result, list)
    assert loaded.result[0].ticker == "WMS" and loaded.result[0].ev_ebitda == 8.5


def test_job_en_erreur_persiste():
    def boom(_job):
        raise RuntimeError("explosion contrôlée")

    m1 = JobManager(max_workers=1)
    job = m1.submit("cessions", "dev", boom)
    _wait_done(m1, job.id)

    loaded = _wait_persisted(job.id)
    assert loaded.status == "error"
    assert "explosion contrôlée" in (loaded.error or "")


def test_job_inconnu_reste_inconnu():
    assert JobManager(max_workers=1).get("inexistant") is None
