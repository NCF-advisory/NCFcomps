"""Tests du garde-fou de la 2e source financière INPI RNE (sans réseau)."""
from __future__ import annotations

from comparables import config
from comparables.fr import finances_rne as r


def test_is_configured_reflects_settings(monkeypatch):
    monkeypatch.setattr(config.settings, "inpi_rne_username", None, raising=False)
    monkeypatch.setattr(config.settings, "inpi_rne_password", None, raising=False)
    assert r.is_configured() is False
    monkeypatch.setattr(config.settings, "inpi_rne_username", "u", raising=False)
    monkeypatch.setattr(config.settings, "inpi_rne_password", "p", raising=False)
    assert r.is_configured() is True


def test_fetch_returns_empty_when_unconfigured(monkeypatch):
    monkeypatch.setattr(config.settings, "inpi_rne_username", None, raising=False)
    # Pas de clé -> aucun appel réseau, renvoie [] (dormant).
    assert r.fetch_financials_rne("123456789") == []


def test_extract_financials_is_safe_noop():
    # Tant que non finalisé, n'injecte aucun chiffre non vérifié.
    assert r._extract_financials({"anything": 1}) == []
