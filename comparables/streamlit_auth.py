"""Porte d'authentification Streamlit (streamlit-authenticator).

A appeler tout en haut de chaque entree Streamlit (page principale + pages/). Si
`settings.auth_enabled` est faux, l'acces est libre (utile en dev/tests). Sinon,
affiche le formulaire de connexion et bloque tant que l'utilisateur n'est pas authentifie.

Ce module importe Streamlit : il n'est utilise que par l'interface, jamais par le
coeur (`finance/`, `sources/`, `pipeline`) ni par les tests.
"""
from __future__ import annotations
from typing import Optional

import streamlit as st

from comparables.config import settings
from comparables import auth


def _gate_disabled() -> tuple[str, str]:
    st.sidebar.caption("🔓 Authentification désactivée (AUTH_ENABLED=false).")
    return ("dev", "Développeur")


def require_authentication() -> Optional[tuple[str, str]]:
    """Exige une connexion ; renvoie (username, nom affiché). Bloque l'exécution sinon."""
    if not settings.auth_enabled:
        return _gate_disabled()

    try:
        import streamlit_authenticator as stauth
    except ImportError:
        st.error("Module `streamlit-authenticator` absent. Installez-le ou mettez "
                 "AUTH_ENABLED=false dans `.env`.")
        st.stop()

    credentials = auth.load_credentials(settings.auth_config_path)
    if not credentials.get("usernames"):
        st.error(
            f"Authentification activée mais aucun identifiant trouvé dans "
            f"`{settings.auth_config_path}`.\n\n"
            "Créez ce fichier à partir de `auth_config.example.yaml` "
            "(hash : `python -m comparables.auth hash \"motdepasse\"`)."
        )
        st.stop()

    if settings.auth_cookie_key in ("", "CHANGE_ME"):
        st.warning("⚠️ `AUTH_COOKIE_KEY` non configurée : définissez une clé aléatoire "
                   "dans `.env` (`python -m comparables.auth genkey`).")

    authenticator = stauth.Authenticate(
        credentials,
        settings.auth_cookie_name,
        settings.auth_cookie_key,
        settings.auth_cookie_expiry_days,
        auto_hash=True,   # hache un mot de passe en clair ; ignore les hash deja presents
    )
    authenticator.login(location="main", fields={
        "Form name": "Connexion", "Username": "Identifiant",
        "Password": "Mot de passe", "Login": "Se connecter",
    })

    status = st.session_state.get("authentication_status")
    if status is True:
        name = st.session_state.get("name") or st.session_state.get("username", "")
        username = st.session_state.get("username", "")
        with st.sidebar:
            st.caption(f"Connecté : **{name}**")
            authenticator.logout("Se déconnecter", location="sidebar")
        return (username, name)
    if status is False:
        st.error("Identifiant ou mot de passe incorrect.")
        st.stop()
    st.info("Veuillez vous connecter pour accéder à l'outil.")
    st.stop()
    return None  # inatteignable (st.stop lève), mais explicite pour le typage
