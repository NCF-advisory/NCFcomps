"""Tests des utilitaires d'authentification purs (hachage bcrypt + chargement YAML).

La porte Streamlit (`comparables.streamlit_auth`) n'est pas testee ici : elle depend de
l'execution Streamlit. Ces tests couvrent la logique sans IHM (regle 7).
"""
from __future__ import annotations

from comparables import auth


def test_hash_and_verify_round_trip():
    h = auth.hash_password("MotDePasse123")
    assert auth.is_hashed(h)
    assert auth.verify_password("MotDePasse123", h) is True
    assert auth.verify_password("mauvais", h) is False


def test_hash_uses_random_salt():
    a = auth.hash_password("identique")
    b = auth.hash_password("identique")
    assert a != b                                  # sels differents
    assert auth.verify_password("identique", a)
    assert auth.verify_password("identique", b)


def test_verify_rejects_invalid_hash():
    assert auth.verify_password("x", "pas-un-hash") is False
    assert auth.verify_password("x", "") is False


def test_is_hashed_distinguishes_plaintext():
    assert auth.is_hashed(auth.hash_password("abc")) is True
    assert auth.is_hashed("motdepasseenclair") is False
    assert auth.is_hashed("") is False


def test_generate_cookie_key_is_random_and_long():
    k1, k2 = auth.generate_cookie_key(), auth.generate_cookie_key()
    assert k1 != k2 and len(k1) >= 32


def test_load_credentials_from_yaml_with_credentials_root(tmp_path):
    h = auth.hash_password("secret")
    yaml_text = (
        "credentials:\n"
        "  usernames:\n"
        "    jdupont:\n"
        "      email: jdupont@ncf-advisory.fr\n"
        "      name: Jean Dupont\n"
        f'      password: "{h}"\n'
    )
    p = tmp_path / "auth_config.yaml"
    p.write_text(yaml_text, encoding="utf-8")

    creds = auth.load_credentials(p)
    assert "jdupont" in creds["usernames"]
    assert creds["usernames"]["jdupont"]["name"] == "Jean Dupont"
    assert auth.verify_password("secret", creds["usernames"]["jdupont"]["password"])


def test_load_credentials_accepts_usernames_root(tmp_path):
    p = tmp_path / "auth_config.yaml"
    p.write_text("usernames:\n  a:\n    name: A\n    password: x\n", encoding="utf-8")
    creds = auth.load_credentials(p)
    assert "a" in creds["usernames"]


def test_load_credentials_missing_file_is_empty(tmp_path):
    creds = auth.load_credentials(tmp_path / "absent.yaml")
    assert creds == {"usernames": {}}
