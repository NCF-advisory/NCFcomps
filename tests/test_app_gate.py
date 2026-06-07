"""Tests de la porte d'authentification au niveau de l'appli (Streamlit AppTest).

Deterministes : on n'exerce pas le composant cookie de streamlit-authenticator (chemin
"sans identifiants" et chemin "auth desactivee"), seulement la logique de blocage du gate.
"""
from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from comparables import config

APP = str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py")


def _tool_visible(at) -> bool:
    return any(("Tickers" in (ta.label or "")) or ("Sociétés" in (ta.label or ""))
               for ta in at.text_area)


def test_gate_blocks_when_no_credentials(tmp_path, monkeypatch):
    monkeypatch.setattr(config.settings, "auth_enabled", True)
    monkeypatch.setattr(config.settings, "auth_config_path", str(tmp_path / "absent.yaml"))
    at = AppTest.from_file(APP).run(timeout=60)
    assert not at.exception
    assert not _tool_visible(at)          # l'outil ne doit pas s'afficher
    assert len(at.error) >= 1             # message d'aide (identifiants manquants)


def test_gate_allows_when_disabled(monkeypatch):
    monkeypatch.setattr(config.settings, "auth_enabled", False)
    at = AppTest.from_file(APP).run(timeout=60)
    assert not at.exception
    assert _tool_visible(at)              # acces libre -> outil visible
