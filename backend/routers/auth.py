"""Authentification : login/logout/me. Identifiants bcrypt de `auth_config.yaml` (réutilisés)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from backend import security
from backend.schemas import LoginRequest, UserOut
from comparables.auth import load_credentials, verify_password
from comparables.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


def _users() -> dict:
    return load_credentials(settings.auth_config_path).get("usernames", {})


@router.post("/login", response_model=UserOut)
def login(body: LoginRequest, response: Response) -> UserOut:
    entry = _users().get(body.username)
    if not entry or not verify_password(body.password, entry.get("password", "")):
        raise HTTPException(status_code=401, detail="Identifiants invalides.")
    response.set_cookie(
        settings.auth_cookie_name,
        security.sign_session(body.username),
        max_age=int(settings.auth_cookie_expiry_days * 86400),
        httponly=True,
        samesite="lax",                 # HTTPS terminé par Caddy en production
    )
    return UserOut(username=body.username, name=entry.get("name"))


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(settings.auth_cookie_name)
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: str = Depends(security.current_user)) -> UserOut:
    entry = _users().get(user) or {}
    return UserOut(username=user, name=entry.get("name"))
