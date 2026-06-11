"""Tests du package d'extraction des comptes annuels (liasse, PDF texte, cascade, INPI).

Aucun réseau, aucune dépendance OCR/LLM requise : tout est pur ou mocké.
"""
from __future__ import annotations

import requests

from comparables.config import settings
from comparables.fr.comptes import cascade, inpi_client, liasse, llm, pdftext
from comparables.fr.comptes.liasse import LiasseResult


# --- parse_amount ---

def test_parse_amount_formats_fr():
    assert liasse.parse_amount("1 234 567") == 1234567.0
    assert liasse.parse_amount("1.234.567") == 1234567.0
    assert liasse.parse_amount("1,234,567") == 1234567.0
    assert liasse.parse_amount("(12 500)") == -12500.0
    assert liasse.parse_amount("-3 000") == -3000.0
    assert liasse.parse_amount("") is None
    assert liasse.parse_amount("abc") is None


# --- compute : régime réel normal (2052) ---

def _codes_2052() -> dict[str, float]:
    return {
        "FL": 1_000_000.0,   # CA net total
        "FM": 20_000.0,      # production stockée
        "FO": 5_000.0,       # subventions
        "FS": 300_000.0,     # achats de marchandises
        "FW": 150_000.0,     # autres achats et charges externes
        "FX": 30_000.0,      # impôts et taxes
        "FY": 250_000.0,     # salaires
        "FZ": 100_000.0,     # charges sociales
        "GG": 120_000.0,     # résultat d'exploitation
    }


def test_compute_2052():
    r = liasse.compute(_codes_2052())
    assert r.regime == "normal"
    assert r.ca == 1_000_000.0
    # EBE = (1 000 000 + 20 000 + 0 + 5 000) - (300 000 + 0 + 0 + 0 + 150 000 + 30 000
    #       + 250 000 + 100 000) = 195 000
    assert r.ebe == 195_000.0
    assert r.ebit == 120_000.0
    assert "FN" in r.missing_codes and "FT" in r.missing_codes   # absents tracés


def test_compute_2052_ca_sous_code_fj():
    """Comptes saisis INPI : la ligne CA est codée FJ (et non FL) ; CA/EBE identiques."""
    codes = dict(_codes_2052())
    codes["FJ"] = codes.pop("FL")          # même montant, sous le code structuré
    r = liasse.compute(codes)
    assert r.regime == "normal"
    assert r.ca == 1_000_000.0
    assert r.ebe == 195_000.0


def test_compute_2052_sans_charges_structurantes_pas_d_ebe():
    """CA seul (ni charges externes FW ni salaires FY) -> EBE trop incertain, non publié."""
    r = liasse.compute({"FL": 500_000.0, "GG": 50_000.0})
    assert r.ca == 500_000.0
    assert r.ebe is None
    assert r.ebit == 50_000.0


# --- compute : régime simplifié (2033-B) ---

def test_compute_2033b():
    codes = {
        "210": 200_000.0,    # ventes de marchandises
        "218": 100_000.0,    # production vendue services
        "234": 80_000.0,     # achats de marchandises
        "242": 60_000.0,     # charges externes
        "244": 8_000.0,      # impôts et taxes
        "250": 90_000.0,     # rémunérations
        "252": 35_000.0,     # charges sociales
        "270": 22_000.0,     # résultat d'exploitation
    }
    r = liasse.compute(codes)
    assert r.regime == "simplifie"
    assert r.ca == 300_000.0
    assert r.ebe == 300_000.0 - 273_000.0            # 27 000
    assert r.ebit == 22_000.0


def test_compute_codes_inconnus():
    r = liasse.compute({})
    assert r.regime is None and r.ca is None and r.ebe is None


# --- parse_codes (PDF texte) ---

# Mise en page « layout=True » : colonnes N / N-1 séparées par 2+ espaces (cf. pdftext).
_TEXTE_2052 = """
DGFiP - formulaire 2052
Chiffres d'affaires nets        FL   1 234 567   1 100 000
Production stockée              FM      12 000       8 000
Autres achats et charges ext.   FW     345 678     300 000
Salaires et traitements         FY     250 000     240 000
Charges sociales                FZ      98 000      95 000
RÉSULTAT D'EXPLOITATION         GG     156 000     120 000
"""


def test_parse_codes_2052_prend_l_exercice_n():
    codes = pdftext.parse_codes(_TEXTE_2052)
    assert codes["FL"] == 1_234_567.0      # premier montant = colonne N
    assert codes["FW"] == 345_678.0
    assert codes["FY"] == 250_000.0        # ne déborde pas sur la colonne N-1
    assert codes["GG"] == 156_000.0


def test_parse_codes_colonnes_a_espaces_simples():
    """Sans layout (espaces simples), la règle des groupes de 3 chiffres suffit quand
    les longueurs diffèrent : '1 234 567 1 100 000' -> 1 234 567 puis stop."""
    codes = pdftext.parse_codes("Chiffres d'affaires nets FL 1 234 567 1 100 000")
    assert codes["FL"] == 1_234_567.0


def test_parse_codes_numeriques_seulement_si_2033():
    texte_sans = "Ventes de marchandises 210 50 000"
    assert pdftext.parse_codes(texte_sans) == {}            # ambigu sans mention 2033
    texte_avec = "Formulaire 2033-B\nVentes de marchandises 210   50 000   45 000"
    assert pdftext.parse_codes(texte_avec)["210"] == 50_000.0


def test_parse_codes_texte_vide():
    assert pdftext.parse_codes("") == {}


# --- cascade ---

def test_cascade_prend_le_premier_resultat_utilisable():
    ko = ("ko", lambda b: None)
    plante = ("plante", lambda b: (_ for _ in ()).throw(RuntimeError("boom")))
    ok = ("ok", lambda b: LiasseResult(ca=100.0, ebe=20.0, regime="normal"))
    jamais = ("jamais", lambda b: LiasseResult(ca=999.0))

    res = cascade.extract_comptes(b"%PDF", extractors=[ko, plante, ok, jamais])
    assert res is not None
    assert res.method == "ok" and res.ca == 100.0 and res.ebe == 20.0


def test_cascade_sans_resultat():
    assert cascade.extract_comptes(b"%PDF", extractors=[("ko", lambda b: None)]) is None


def test_cascade_defaut_sans_credentials(monkeypatch):
    """Sans clé API ni OCR, la chaîne par défaut = PDF texte seul (pas d'étape payante)."""
    monkeypatch.setattr(settings, "anthropic_api_key", None)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(cascade.ocr, "available", lambda: False)
    names = [name for name, _ in cascade.default_extractors()]
    assert names == ["pdf_texte"]


def test_llm_inactif_sans_cle(monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", None)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert llm.configured() is False
    assert llm.extract_from_pdf(b"%PDF") is None


# --- client INPI (mocké) ---

class _FakeResponse:
    def __init__(self, json_data=None, content=b"", status_code=200):
        self._json = json_data
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._json


class _FakeSession:
    def __init__(self):
        self.logins = 0

    def post(self, url, **kwargs):
        assert url.endswith("/sso/login")
        self.logins += 1
        return _FakeResponse({"token": f"jeton-{self.logins}"})

    def get(self, url, headers=None, **kwargs):
        assert headers["Authorization"].startswith("Bearer jeton-")
        if "/attachments" in url:
            return _FakeResponse({"bilans": [
                {"id": "b1", "dateCloture": "2022-12-31"},
                {"id": "b3", "dateCloture": "2024-12-31"},
                {"id": "b2", "dateCloture": "2023-12-31"},
            ]})
        if "/bilans/" in url and url.endswith("/download"):
            return _FakeResponse(content=b"%PDF-fake")
        raise AssertionError(f"URL inattendue : {url}")


def _with_credentials(monkeypatch):
    monkeypatch.setattr(settings, "inpi_username", "user@cabinet.fr")
    monkeypatch.setattr(settings, "inpi_password", "secret")
    monkeypatch.setattr(settings, "inpi_min_interval_seconds", 0)   # pas de pause en test


def test_inpi_non_configure(monkeypatch):
    monkeypatch.setattr(settings, "inpi_username", None)
    monkeypatch.setattr(settings, "inpi_password", None)
    assert inpi_client.configured() is False
    assert inpi_client.fetch_comptes_pdf("123456789") is None


def test_inpi_bilans_tries_du_plus_recent(monkeypatch):
    _with_credentials(monkeypatch)
    client = inpi_client.InpiClient(session=_FakeSession())
    bilans = client.bilans("123456789")
    assert [b["id"] for b in bilans] == ["b3", "b2", "b1"]


def test_inpi_fetch_avant_date_de_cession(monkeypatch):
    """L'exercice retenu est le dernier clôturé AVANT la cession (même convention
    que finances_inpi.pick_for_date)."""
    _with_credentials(monkeypatch)
    client = inpi_client.InpiClient(session=_FakeSession())
    out = inpi_client.fetch_comptes_pdf("123456789", before_date="2024-06-15", client=client)
    assert out is not None
    meta, pdf = out
    assert meta["id"] == "b2"                       # clôture 2023-12-31 <= 2024-06-15
    assert pdf == b"%PDF-fake"


def test_inpi_fetch_echec_reseau_renvoie_none(monkeypatch):
    _with_credentials(monkeypatch)

    class _BrokenSession:
        def post(self, url, **kwargs):
            raise ConnectionError("panne")

    client = inpi_client.InpiClient(session=_BrokenSession())
    assert inpi_client.fetch_comptes_pdf("123456789", client=client) is None


def test_inpi_retry_sur_refus_de_connexion(monkeypatch):
    """Un refus de connexion (rafale RNE) est retenté une fois avant d'échouer."""
    _with_credentials(monkeypatch)
    monkeypatch.setattr(settings, "inpi_max_attempts", 2)
    monkeypatch.setattr(settings, "inpi_backoff_seconds", 0)     # pas d'attente en test

    class _FlakySession:
        def __init__(self):
            self.post_calls = 0

        def post(self, url, **kwargs):
            self.post_calls += 1
            if self.post_calls == 1:                            # 1er essai : refus
                raise requests.exceptions.ConnectionError("rafale")
            return _FakeResponse({"token": "jeton-ok"})         # 2e essai : OK

        def get(self, url, headers=None, **kwargs):
            return _FakeResponse({"bilans": [{"id": "b1", "dateCloture": "2023-12-31"}]})

    session = _FlakySession()
    client = inpi_client.InpiClient(session=session)
    out = inpi_client.fetch_comptes_pdf("123456789", client=client)
    assert session.post_calls == 2                              # a bien réessayé
    assert out is not None and out[0]["id"] == "b1"
