"""Tests de l'extraction des comptes structurés « bilans saisis » (API RNE/INPI).

Purs (aucun réseau) : on fournit la forme réelle observée sur l'API (pages -> liasses
{code, m1..m4}) et on vérifie le choix de colonne par régime + la sélection du dépôt.
"""
from __future__ import annotations

from comparables.config import settings
from comparables.fr.comptes import bilan_saisi, inpi_client


# --- parse_saisi_amount : entiers euros zéro-paddés, signe '-' éventuel ---

def test_parse_saisi_amount():
    assert bilan_saisi.parse_saisi_amount("000001030000000") == 1_030_000_000.0
    assert bilan_saisi.parse_saisi_amount("-000000119000000") == -119_000_000.0
    assert bilan_saisi.parse_saisi_amount("000000000000000") == 0.0
    assert bilan_saisi.parse_saisi_amount("000000000020957") == 20_957.0
    assert bilan_saisi.parse_saisi_amount("") is None
    assert bilan_saisi.parse_saisi_amount("   ") is None
    assert bilan_saisi.parse_saisi_amount(None) is None
    assert bilan_saisi.parse_saisi_amount("12ab") is None


def _wrap(pages: list[dict]) -> dict:
    """Enveloppe la liste de pages dans la structure bilanSaisi réelle."""
    return {"bilan": {"identite": {"siren": "123456789"},
                      "detail": {"pages": pages}}, "version": "1.0"}


# --- régime simplifié 2033-B : exercice N = colonne m1 (m2 = N-1) ---

def test_extract_simplifie_m1():
    saisi = _wrap([
        {"numero": 1, "liasses": [          # bilan simplifié (ignoré par compute)
            {"code": "040", "m1": "000000032316", "m2": "000000000150",
             "m3": "000000032165", "m4": "000000032367"},
        ]},
        {"numero": 2, "liasses": [          # compte de résultat 2033-B
            {"code": "210", "m1": "000000001000", "m2": "000000000900"},   # ventes march.
            {"code": "214", "m1": "000000000500", "m2": "000000000400"},   # prod. biens
            {"code": "222", "m1": "000000000100", "m2": "000000000080"},   # prod. stockée
            {"code": "226", "m1": "000000000050", "m2": "000000000040"},   # subventions
            {"code": "234", "m1": "000000000300", "m2": "000000000250"},   # achats march.
            {"code": "242", "m1": "000000000200", "m2": "000000000180"},   # charges externes
            {"code": "250", "m1": "000000000400", "m2": "000000000380"},   # rémunérations
            {"code": "270", "m1": "000000000120", "m2": "000000000090"},   # résultat expl.
        ]},
    ])
    r = bilan_saisi.extract(saisi)
    assert r is not None
    assert r.regime == "simplifie"
    assert r.ca == 1_500.0                                   # 210 + 214 (m1)
    # produits EBE = 1000+500+100+50 = 1650 ; charges = 300+200+400 = 900
    assert r.ebe == 750.0
    assert r.ebit == 120.0                                   # 270 (m1, pas m2=90)


# --- régime réel normal 2052 : exercice N = colonne m3 (m1/m2 = France/Export) ---

def test_extract_normal_m3():
    saisi = _wrap([
        {"numero": 1, "liasses": [          # bilan passif 2051 : m1/m2 seuls -> écarté (pas de m3)
            {"code": "DA", "m1": "000000000169", "m2": "000000000169"},
            {"code": "EE", "m1": "000000033215", "m2": "000000033054"},
        ]},
        {"numero": 2, "liasses": [          # compte de résultat 2052
            # FL : France(m1)+Export(m2)+Total(m3) -> on doit prendre m3 = 1000, pas m1 = 800
            {"code": "FL", "m1": "000000000800", "m2": "000000000200",
             "m3": "000000001000", "m4": "000000000900"},
            {"code": "FM", "m3": "000000000100", "m4": "000000000080"},    # prod. stockée
            {"code": "FO", "m3": "000000000050", "m4": "000000000040"},    # subventions
            {"code": "FS", "m3": "000000000200", "m4": "000000000180"},    # achats march.
            {"code": "FW", "m3": "000000000300", "m4": "000000000280"},    # charges externes
            {"code": "FY", "m3": "000000000150", "m4": "000000000140"},    # salaires
            {"code": "FZ", "m3": "000000000050", "m4": "000000000045"},    # charges sociales
            {"code": "GG", "m3": "000000000120", "m4": "000000000090"},    # résultat expl.
        ]},
    ])
    r = bilan_saisi.extract(saisi)
    assert r is not None
    assert r.regime == "normal"
    assert r.ca == 1_000.0                                   # m3, pas m1=800
    # produits = 1000+100+0+50 = 1150 ; charges = 200+300+150+50 = 700
    assert r.ebe == 450.0
    assert r.ebit == 120.0


def test_extract_vide_ou_indetectable():
    assert bilan_saisi.extract(None) is None
    assert bilan_saisi.extract({}) is None
    # codes hors liasse (que des codes de bilan) -> régime indétectable
    saisi = _wrap([{"numero": 1, "liasses": [{"code": "ZZ", "m1": "000000000001"}]}])
    assert bilan_saisi.extract(saisi) is None


# --- sélection du dépôt : filtre deleted, préfère Public, exercice <= cession ---

def test_select_deposit_filtre_et_prefere_public():
    deposits = [
        {"id": "a", "dateCloture": "2024-12-31", "confidentiality": "Public", "deleted": True},
        {"id": "b", "dateCloture": "2023-12-31", "confidentiality": "Public", "deleted": False},
        {"id": "c", "dateCloture": "2024-12-31", "confidentiality": "Confidentiel", "deleted": False},
    ]
    # le plus récent non supprimé ET public = b (c est plus récent mais confidentiel)
    assert inpi_client._select_deposit(deposits, before_date=None)["id"] == "b"


def test_select_deposit_avant_date():
    deposits = [
        {"id": "n", "dateCloture": "2024-12-31", "confidentiality": "Public", "deleted": False},
        {"id": "n1", "dateCloture": "2022-12-31", "confidentiality": "Public", "deleted": False},
    ]
    out = inpi_client._select_deposit(deposits, before_date="2023-06-15")
    assert out["id"] == "n1"                                 # 2022 <= cession < 2024


def test_select_deposit_confidentiel_si_aucun_public():
    deposits = [{"id": "c", "dateCloture": "2023-12-31",
                 "confidentiality": "Confidentiel", "deleted": False}]
    assert inpi_client._select_deposit(deposits, before_date=None)["id"] == "c"


def test_select_deposit_vide():
    assert inpi_client._select_deposit([], before_date=None) is None
    assert inpi_client._select_deposit(
        [{"id": "x", "deleted": True}], before_date=None) is None


# --- fetch_comptes_saisi : voie structurée privilégiée (mockée) ---

class _SaisiSession:
    def post(self, url, **kwargs):
        return _Resp({"token": "jeton-1"})

    def get(self, url, headers=None, **kwargs):
        assert "/attachments" in url
        return _Resp({"bilans": [], "bilansSaisis": [
            {"id": "s1", "dateCloture": "2022-12-31", "confidentiality": "Public",
             "deleted": False, "bilanSaisi": {"bilan": {"detail": {"pages": []}}}},
            {"id": "s2", "dateCloture": "2023-12-31", "confidentiality": "Public",
             "deleted": False, "bilanSaisi": {"bilan": {"detail": {"pages": [
                 {"numero": 1, "liasses": [{"code": "210", "m1": "000000000500"}]}]}}}},
        ]})


class _Resp:
    def __init__(self, json_data):
        self._json = json_data
        self.status_code = 200

    def raise_for_status(self):
        pass

    def json(self):
        return self._json


def test_fetch_comptes_saisi(monkeypatch):
    monkeypatch.setattr(settings, "inpi_username", "user@cabinet.fr")
    monkeypatch.setattr(settings, "inpi_password", "secret")
    monkeypatch.setattr(settings, "inpi_min_interval_seconds", 0)
    client = inpi_client.InpiClient(session=_SaisiSession())
    out = inpi_client.fetch_comptes_saisi("123456789", before_date="2024-01-01", client=client)
    assert out is not None
    meta, saisi = out
    assert meta["id"] == "s2"                                # le plus récent <= cession
    assert bilan_saisi.extract(saisi) is not None            # contenu exploitable


def test_fetch_comptes_saisi_non_configure(monkeypatch):
    monkeypatch.setattr(settings, "inpi_username", None)
    monkeypatch.setattr(settings, "inpi_password", None)
    assert inpi_client.fetch_comptes_saisi("123456789") is None
