"""Tests de l'authentification API (cookie signé). Aucun réseau."""
from __future__ import annotations

import yaml
from fastapi.testclient import TestClient

from backend.main import create_app
from comparables.auth import hash_password
from comparables.config import settings

_HASH = hash_password("Secret123")      # calculé une fois (bcrypt est volontairement lent)


def _client(tmp_path, monkeypatch, enabled: bool = True) -> TestClient:
    cfg = tmp_path / "auth_config.yaml"
    cfg.write_text(yaml.safe_dump(
        {"usernames": {"alice": {"name": "Alice Martin", "password": _HASH}}}),
        encoding="utf-8")
    monkeypatch.setattr(settings, "auth_config_path", str(cfg))
    monkeypatch.setattr(settings, "auth_enabled", enabled)
    monkeypatch.setattr(settings, "auth_cookie_key", "cle-de-test")
    return TestClient(create_app())


def test_login_ok_puis_me(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    r = client.post("/api/auth/login", json={"username": "alice", "password": "Secret123"})
    assert r.status_code == 200
    assert r.json() == {"username": "alice", "name": "Alice Martin"}
    assert settings.auth_cookie_name in r.cookies
    # Le TestClient conserve le cookie -> /me repond
    r2 = client.get("/api/auth/me")
    assert r2.status_code == 200 and r2.json()["username"] == "alice"


def test_login_mauvais_mot_de_passe(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    r = client.post("/api/auth/login", json={"username": "alice", "password": "faux"})
    assert r.status_code == 401


def test_login_utilisateur_inconnu(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    r = client.post("/api/auth/login", json={"username": "bob", "password": "Secret123"})
    assert r.status_code == 401


def test_me_sans_cookie_401(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    assert client.get("/api/auth/me").status_code == 401


def test_cookie_falsifie_rejete(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    client.cookies.set(settings.auth_cookie_name, "jeton-bidon")
    assert client.get("/api/auth/me").status_code == 401


def test_auth_desactivee_bypass(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch, enabled=False)
    r = client.get("/api/auth/me")
    assert r.status_code == 200 and r.json()["username"] == "dev"


def test_logout_supprime_le_cookie(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    client.post("/api/auth/login", json={"username": "alice", "password": "Secret123"})
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401


def test_health_sans_auth(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    assert client.get("/api/health").json() == {"status": "ok"}
