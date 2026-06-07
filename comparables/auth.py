"""Utilitaires d'authentification (purs, sans Streamlit) : hachage bcrypt + chargement
des identifiants depuis un fichier YAML non versionne.

La porte d'authentification Streamlit elle-meme vit dans `comparables.streamlit_auth`.
Aucun secret en dur (regle 4) : les hash sont dans `auth_config.yaml` (gitignore) et la
cle de signature du cookie dans `.env`.

CLI d'aide a l'onboarding :
    python -m comparables.auth hash "MotDePasse"   # -> hash bcrypt a coller dans le YAML
    python -m comparables.auth genkey               # -> cle aleatoire pour AUTH_COOKIE_KEY
"""
from __future__ import annotations
import secrets
from pathlib import Path
from typing import Union

import bcrypt
import yaml

_HASH_PREFIXES = ("$2a$", "$2b$", "$2y$")


def hash_password(password: str) -> str:
    """Hash bcrypt d'un mot de passe (sel aleatoire)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verifie un mot de passe contre son hash bcrypt ; False si le hash est invalide."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def is_hashed(value: str) -> bool:
    """Heuristique : la valeur ressemble-t-elle a un hash bcrypt (vs un mot de passe en clair) ?"""
    return isinstance(value, str) and value.startswith(_HASH_PREFIXES) and len(value) >= 59


def generate_cookie_key() -> str:
    """Cle aleatoire pour signer le cookie de session."""
    return secrets.token_hex(32)


def load_credentials(path: Union[str, Path]) -> dict:
    """Charge les identifiants depuis un YAML et renvoie un dict {'usernames': {...}}.

    Tolerant : accepte un YAML avec une cle racine `credentials:` (format standard
    streamlit-authenticator) ou directement `usernames:`. Fichier absent/vide -> aucun
    utilisateur (la porte affichera un message d'aide plutot que de planter).
    """
    p = Path(path)
    if not p.exists():
        return {"usernames": {}}
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if "credentials" in data and isinstance(data["credentials"], dict):
        creds = data["credentials"]
    elif "usernames" in data:
        creds = data
    else:
        creds = {"usernames": {}}
    creds.setdefault("usernames", {})
    return creds


def _main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="python -m comparables.auth",
                                     description="Aide a la configuration de l'authentification.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("hash", help="Affiche le hash bcrypt d'un mot de passe.")
    h.add_argument("password")
    sub.add_parser("genkey", help="Affiche une cle aleatoire pour AUTH_COOKIE_KEY.")

    args = parser.parse_args(argv)
    if args.cmd == "hash":
        print(hash_password(args.password))
    elif args.cmd == "genkey":
        print(generate_cookie_key())
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
