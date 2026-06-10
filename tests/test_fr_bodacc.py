"""Tests BODACC : choix du SIREN cédant et dédoublonnage des annonces. Aucun réseau."""
from __future__ import annotations

import json

from comparables.fr import bodacc


# --- _cedant_siren ---

def test_cedant_siren_prend_le_1er_du_descriptif_present_au_registre():
    fields = {"registre": ["111222333", "444555666"]}
    # Le descriptif cite le cessionnaire (444...) APRES le cédant (111...).
    descriptif = "Cédant : SARL A (111 222 333). Cessionnaire : SAS B (444 555 666)."
    assert bodacc._cedant_siren(fields, descriptif) == "111222333"


def test_cedant_siren_fallback_ordre_du_registre():
    """Sans SIREN exploitable dans le descriptif, on prend le 1er du registre
    (ordre de publication : cédant en tête), pas un élément arbitraire d'un set."""
    fields = {"registre": ["111222333", "444555666"]}
    assert bodacc._cedant_siren(fields, "aucun numero ici") == "111222333"


def test_cedant_siren_sans_registre():
    assert bodacc._cedant_siren({}, "rien") is None


# --- fetch_cessions : dédoublonnage + filtre rectificatifs ---

class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class _FakeSession:
    """Renvoie une page de résultats, puis des pages vides."""

    def __init__(self, records):
        self._pages = [{"records": records}, {"records": []}]
        self.calls = 0

    def get(self, url, params=None, headers=None, timeout=None):
        page = self._pages[min(self.calls, len(self._pages) - 1)]
        self.calls += 1
        return _FakeResponse(page)


def _record(siren: str, prix: str, typeavis: str = "annonce", nom: str = "BOULANGERIE X"):
    acte = {"descriptif": f"Vente de fonds moyennant le prix de {prix} euros. "
                          f"Cédant immatriculé {siren}.",
            "vente": {"categorieVente": "Vente"}}
    return {"record": {"fields": {
        "commercant": nom, "ville": "PARIS", "numerodepartement": "75",
        "dateparution": "2025-01-15", "typeavis": typeavis,
        "registre": [siren], "acte": json.dumps(acte), "url_complete": f"https://x/{siren}",
    }}}


def test_fetch_cessions_dedoublonne_meme_acte(monkeypatch):
    records = [
        _record("111222333", "150 000,00"),
        _record("111222333", "150 000,00"),          # republication du même acte
        _record("444555666", "80 000,00"),
    ]
    monkeypatch.setattr(bodacc.cache, "get_session", lambda: _FakeSession(records))
    out = bodacc.fetch_cessions(limit=10)
    assert len(out) == 2
    assert {c.siren for c in out} == {"111222333", "444555666"}


def test_fetch_cessions_ignore_rectificatifs_et_annulations(monkeypatch):
    records = [
        _record("111222333", "150 000,00"),
        _record("555666777", "90 000,00", typeavis="Rectificatif"),
        _record("888999000", "70 000,00", typeavis="Annulation"),
    ]
    monkeypatch.setattr(bodacc.cache, "get_session", lambda: _FakeSession(records))
    out = bodacc.fetch_cessions(limit=10)
    assert len(out) == 1
    assert out[0].siren == "111222333"
    assert out[0].prix == 150000.0
