"""Tests du parsing de l'API Recherche d'entreprises (sans réseau)."""
from __future__ import annotations

from comparables.fr import entreprises as e


def test_latest_ca_picks_most_recent_positive():
    fin = {"2021": {"ca": 100000, "resultat_net": 1}, "2023": {"ca": 250000}, "2022": {"ca": 0}}
    ca, year = e.latest_ca(fin)
    assert ca == 250000.0 and year == 2023


def test_latest_ca_ignores_zero_and_null():
    assert e.latest_ca({"2024": {"ca": 0}}) == (None, None)       # holding -> 0
    assert e.latest_ca(None) == (None, None)                      # comptes confidentiels
    assert e.latest_ca({}) == (None, None)


def test_parse_company():
    result = {"nom_complet": "LE SLIP FRANCAIS", "activite_principale": "47.91B",
              "finances": {"2023": {"ca": 18754140, "resultat_net": -1692858}}}
    info = e.parse_company(result)
    assert info["nom"] == "LE SLIP FRANCAIS"
    assert info["naf"] == "47.91B"
    assert info["ca"] == 18754140.0 and info["ca_annee"] == 2023


# --- garde-fou de débit (7 req/s + retry sur 429) ---

class _Resp:
    def __init__(self, status_code, payload=None, from_cache=False):
        self.status_code = status_code
        self._payload = payload or {}
        self.from_cache = from_cache

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class _Session:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls += 1
        return self._responses.pop(0)


def test_throttled_get_retries_sur_429(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr(e.time, "sleep", sleeps.append)
    session = _Session([_Resp(429), _Resp(200, {"results": []})])
    resp = e._throttled_get(session, {"q": "123"})
    assert resp.status_code == 200 and session.calls == 2
    assert any(s >= 1.0 for s in sleeps)            # back-off appliqué après le 429


def test_throttled_get_leve_apres_retries(monkeypatch):
    monkeypatch.setattr(e.time, "sleep", lambda s: None)
    session = _Session([_Resp(429)] * 3)
    try:
        e._throttled_get(session, {"q": "123"})
        raise AssertionError("aurait dû lever")
    except RuntimeError as exc:
        assert "429" in str(exc)
    assert session.calls == 3                       # 1 essai + 2 retries, pas plus


def test_throttled_get_cadence_les_appels_reseau(monkeypatch):
    """Deux appels réseau rapprochés -> une attente d'au moins l'intervalle minimal."""
    sleeps: list[float] = []
    monkeypatch.setattr(e.time, "sleep", sleeps.append)
    monkeypatch.setattr(e, "_last_call", 0.0)
    monkeypatch.setattr(e.time, "monotonic", lambda: 1000.0)    # horloge figée
    session = _Session([_Resp(200, {"results": []}), _Resp(200, {"results": []})])
    e._throttled_get(session, {"q": "1"})           # cale _last_call sur l'horloge
    e._throttled_get(session, {"q": "2"})           # même instant -> doit attendre
    assert any(0 < s <= e._MIN_INTERVAL_SECONDS for s in sleeps)
