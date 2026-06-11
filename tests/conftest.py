"""Fixtures communes : bases SQLite isolées par test.

La persistance des jobs (backend/jobs.py), des runs (store.py) et les référentiels
locaux (fr/referentiels.py) écrivent dans des bases configurées par settings : en test,
chacune pointe vers un répertoire temporaire — jamais vers data/ du poste de travail.
"""
from __future__ import annotations

import pytest

from comparables.config import settings


@pytest.fixture(autouse=True)
def _isolated_dbs(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "history_db_path", str(tmp_path / "history.sqlite"))
    monkeypatch.setattr(settings, "referentiels_db_path",
                        str(tmp_path / "referentiels.sqlite"))
