"""Tests d'orchestration cessions FR (BODACC + finances INPI + identité, tout mocké)."""
from __future__ import annotations

from comparables.fr import pipeline, bodacc, entreprises, finances_inpi
from comparables.fr.models import Cession


def _fake_cessions():
    return [
        Cession(siren="111111111", nom="A", prix=120000.0, date="2023-06-01"),  # CA+EBE -> pct+mult
        Cession(siren="222222222", nom="B", prix=90000.0, date="2023-06-01"),   # confidentiel -> rien
        Cession(siren="333333333", nom="C", prix=50000.0, date="2023-06-01"),   # finances lève -> isolé
        Cession(siren=None, nom="D", prix=10000.0, date="2023-06-01"),
    ]


def _fake_financials(siren):
    if siren == "111111111":
        return [
            {"date_cloture_exercice": "2022-12-31", "chiffre_d_affaires": 200000.0,
             "ebe": 30000.0, "ebit": 25000.0},
            {"date_cloture_exercice": "2021-12-31", "chiffre_d_affaires": 180000.0,
             "ebe": 28000.0, "ebit": 22000.0},
        ]
    if siren == "222222222":
        return []                                       # comptes confidentiels -> absent du jeu
    if siren == "333333333":
        raise RuntimeError("boom finances")
    return []


def _fake_company(siren):
    if siren == "111111111":
        return {"nom": "Société A", "naf": "10.71C", "ca": None, "ca_annee": None}
    return None


def _patch(monkeypatch):
    monkeypatch.setattr(bodacc, "fetch_cessions", lambda *a, **k: _fake_cessions())
    monkeypatch.setattr(finances_inpi, "fetch_financials", _fake_financials)
    monkeypatch.setattr(entreprises, "fetch_company", _fake_company)


def test_build_cessions_enriches_ca_ebe(monkeypatch):
    _patch(monkeypatch)
    cessions = pipeline.build_cessions(limit=10, require_ca=False)   # garde tout
    by = {c.nom: c for c in cessions}

    a = by["Société A"]                                 # nom écrasé par l'identité
    assert a.ca_annee == 2022                           # exercice clos avant la cession 2023-06
    assert a.ca == 200000.0 and a.ebe == 30000.0
    assert abs(a.pct_ca - 0.60) < 1e-9                  # 120000 / 200000
    assert abs(a.mult_ebe - 4.0) < 1e-9                 # 120000 / 30000
    assert a.naf == "10.71C"
    # B : absent du jeu INPI (confidentiel) -> ni CA ni EBE
    assert by["B"].ca is None and by["B"].pct_ca is None
    # C : fetch_financials lève -> isolé, cession conservée
    assert by["C"].pct_ca is None
    # D : pas de SIREN -> conservée
    assert by["D"].prix == 10000.0


def test_build_cessions_require_ca_excludes_missing(monkeypatch):
    _patch(monkeypatch)
    cessions = pipeline.build_cessions(limit=10, require_ca=True)    # défaut : exclut sans CA
    # Seule A a un CA disponible -> les sociétés sans CA (B, C, D) sont exclues
    assert [c.siren for c in cessions] == ["111111111"]
    assert all(c.ca is not None for c in cessions)


def test_to_dataframe(monkeypatch):
    _patch(monkeypatch)
    df = pipeline.to_dataframe(pipeline.build_cessions(limit=10, require_ca=False))
    assert len(df) == 4
    for col in ("siren", "prix", "ca", "ebe", "pct_ca", "mult_ebe", "naf"):
        assert col in df.columns


def test_default_since_is_ten_years_iso():
    s = pipeline.default_since(10)
    assert len(s) == 10 and s[4] == "-"                 # format YYYY-MM-DD


def test_build_cessions_fills_stats(monkeypatch):
    _patch(monkeypatch)
    stats: dict = {}
    pipeline.build_cessions(limit=10, require_ca=False, stats=stats)
    # 4 cessions examinées ; seule A (111111111) a un CA public ; A a aussi un EBE > 0.
    assert stats["n_examined"] == 4
    assert stats["n_ca_public"] == 1
    assert stats["n_ebe_public"] == 1
    assert stats["n_returned"] == 4                     # require_ca=False -> tout gardé


def test_build_cessions_naf_filter(monkeypatch):
    # 3 cessions enrichissables ; seule A est identifiée (NAF 10.71C) par _fake_company.
    _patch(monkeypatch)
    # Sans filtre NAF : A retenue (require_ca True n'en garde qu'une de toute façon).
    assert [c.siren for c in pipeline.build_cessions(limit=10, require_ca=True)] == ["111111111"]
    # Filtre NAF concordant -> A conservée.
    keep = pipeline.build_cessions(limit=10, require_ca=True, naf_filters=["10"])
    assert [c.siren for c in keep] == ["111111111"] and keep[0].naf == "10.71C"
    # Filtre NAF non concordant -> A écartée (NAF 10.71C ne commence pas par 56).
    assert pipeline.build_cessions(limit=10, require_ca=True, naf_filters=["56"]) == []


def test_build_cessions_captures_nb_etablissements(monkeypatch):
    monkeypatch.setattr(bodacc, "fetch_cessions", lambda *a, **k: _fake_cessions())
    monkeypatch.setattr(finances_inpi, "fetch_financials", _fake_financials)
    monkeypatch.setattr(entreprises, "fetch_company",
                        lambda s: {"nom": "A", "naf": "10.71C", "nb_etablissements": 2}
                        if s == "111111111" else None)
    a = pipeline.build_cessions(limit=10, require_ca=True)[0]
    assert a.nb_etablissements == 2


def test_resolve_terms_or_split_and_synonyms():
    # multi-termes -> liste (OU) ; sans expansion, pas de synonymes.
    assert pipeline.resolve_terms("celf, menuiserie", expand=False) == ["celf", "menuiserie"]
    # avec expansion : la famille menuiserie est tirée.
    expanded = pipeline.resolve_terms("menuiserie", expand=True)
    assert "menuiserie" in expanded and "charpente" in expanded and len(expanded) > 1
