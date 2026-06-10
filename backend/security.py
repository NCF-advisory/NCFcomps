"""Session par cookie signé (itsdangerous) + dépendance FastAPI `current_user`.

Réutilise les réglages existants : `auth_cookie_key` (.env), `auth_cookie_name`,
`auth_cookie_expiry_days`, `auth_enabled` (False = bypass pour le dev local).
"""
from __future__ import annotations
from typing import Optional

from fastapi import HTTPException, Request
from itsdangerous import BadSignature, URLSafeTimedSerializer

from comparables.config import settings

_SALT = "ncf-session"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.auth_cookie_key, salt=_SALT)


def sign_session(username: str) -> str:
    """Jeton de session signé (horodaté) pour le cookie."""
    return _serializer().dumps({"u": username})


def read_session(token: str) -> Optional[str]:
    """Nom d'utilisateur du jeton, ou None si signature invalide / jeton expiré."""
    max_age = int(settings.auth_cookie_expiry_days * 86400)
    try:
        data = _serializer().loads(token, max_age=max_age)
    except BadSignature:                  # englobe SignatureExpired
        return None
    return data.get("u") if isinstance(data, dict) else None


def current_user(request: Request) -> str:
    """Dépendance FastAPI : utilisateur connecté, sinon 401. AUTH_ENABLED=false -> 'dev'."""
    if not settings.auth_enabled:
        return "dev"
    token = request.cookies.get(settings.auth_cookie_name)
    user = read_session(token) if token else None
    if not user:
        raise HTTPException(status_code=401, detail="Authentification requise.")
    return user
