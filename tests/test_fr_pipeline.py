"""Tests d'orchestration cessions FR (BODACC + finances INPI + identité, tout mocké)."""
from __future__ import annotations

from comparables.fr import pipeline, bodacc, entreprises, finances_inpi, referentiels
from comparables.fr.comptes import inpi_client
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
    monkeypatch.setattr(bodacc, "fetch_cessions", lambda **kwargs: _fake_cessions())
    monkeypatch.setattr(finances_inpi, "fetch_financials", _fake_financials)
    monkeypatch.setattr(entreprises, "fetch_company", _fake_company)
    # Hors-ligne même si le .env local porte des credentials INPI.
    monkeypatch.setattr(inpi_client, "configured", lambda: False)


def test_build_cessions_enriches_ca_ebe(monkeypatch):
    _patch(monkeypatch)
    batch = pipeline.build_cessions(limit=10, require_ca=False)      # garde tout
    by = {c.nom: c for c in batch.cessions}

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
    batch = pipeline.build_cessions(limit=10, require_ca=True)       # défaut : exclut sans CA
    # Seule A a un CA disponible -> les sociétés sans CA (B, C, D) sont exclues
    assert [c.siren for c in batch.cessions] == ["111111111"]
    assert all(c.ca is not None for c in batch.cessions)
    # Compteurs d'entonnoir : 4 annonces balayées, 3 écartées faute de CA
    assert batch.n_annonces == 4 and batch.n_sans_ca == 3 and batch.n_naf_exclues == 0


def test_build_cessions_interprete_l_activite(monkeypatch):
    """Texte libre -> mots-clés élargis (OU) passés au BODACC + NAF cibles tracés."""
    captured: dict = {}

    def fake_fetch(**kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(bodacc, "fetch_cessions", fake_fetch)
    batch = pipeline.build_cessions(contains="conseil en informatique", limit=10)
    assert "informatique" in captured["keywords"]
    assert "logiciel" in captured["keywords"]           # synonyme ajouté
    assert set(batch.naf_codes) == {"62.01Z", "62.02A", "62.02B", "62.03Z", "62.09Z"}
    assert batch.cessions == [] and batch.n_annonces == 0


def test_build_cessions_filtre_naf(monkeypatch):
    """Filtre d'activité : NAF cible gardé, NAF hors cible exclu (sauf nom de la cédante
    évocateur — jamais le champ BODACC, qui mêle cédant et cessionnaire), et les finances
    INPI ne sont interrogées que pour les annonces pertinentes."""
    pool = [
        Cession(siren="111111111", nom="DUPONT CONSEIL", prix=120000.0, date="2023-06-01"),
        Cession(siren="555555555", nom="LE BISTROT", prix=80000.0, date="2023-06-01"),
        Cession(siren="666666666", nom="ATOUT SARL", prix=60000.0, date="2023-06-01"),
        # L'ACHETEUR s'appelle « X INFORMATIQUE » (champ commercant pollué) : la cédante
        # est une agence immobilière -> doit être exclue malgré le mot-clé dans le champ.
        Cession(siren="777777777", nom="JTTC IMMO, X INFORMATIQUE", prix=40000.0,
                date="2023-06-01"),
    ]
    companies = {
        "111111111": {"nom": "Dupont Conseil SAS", "naf": "62.02A", "ca": None, "ca_annee": None},
        "555555555": {"nom": "Le Bistrot SARL", "naf": "56.10A", "ca": None, "ca_annee": None},
        "666666666": {"nom": "ATOUT INFORMATIQUE", "naf": "47.41Z", "ca": None, "ca_annee": None},
        "777777777": {"nom": "JTTC IMMO", "naf": "68.20B", "ca": None, "ca_annee": None},
    }
    fin_calls: list[str] = []

    def fake_fin(siren):
        fin_calls.append(siren)
        return [{"date_cloture_exercice": "2022-12-31", "chiffre_d_affaires": 200000.0,
                 "ebe": 30000.0, "ebit": 25000.0}]

    monkeypatch.setattr(bodacc, "fetch_cessions",
                        lambda **kwargs: pool if kwargs.get("search_in") == ("commercant",)
                        else [])
    monkeypatch.setattr(entreprises, "fetch_company", companies.get)
    monkeypatch.setattr(finances_inpi, "fetch_financials", fake_fin)
    monkeypatch.setattr(inpi_client, "configured", lambda: False)

    batch = pipeline.build_cessions(contains="conseil en informatique", limit=10,
                                    require_ca=True)
    # 62.02A gardée ; bistrot (56.10A) exclu ; 47.41Z repêchée par le nom officiel de la
    # cédante ; l'immobilière au commercant pollué par l'acheteur exclue.
    assert [c.siren for c in batch.cessions] == ["111111111", "666666666"]
    assert "555555555" not in fin_calls                 # économie d'appels INPI
    assert "777777777" not in fin_calls
    assert batch.n_annonces == 4 and batch.n_naf_exclues == 2 and batch.n_sans_ca == 0


def test_build_cessions_progress(monkeypatch):
    """Le callback de progression suit l'enrichissement : (0, total) puis chaque annonce."""
    _patch(monkeypatch)
    calls: list[tuple[int, int]] = []
    pipeline.build_cessions(limit=10, require_ca=True,
                            progress=lambda d, t: calls.append((d, t)))
    assert calls[0] == (0, 4)                           # 4 annonces balayées
    assert calls[-1] == (4, 4)                          # toutes traitées
    assert [d for d, _ in calls] == sorted(d for d, _ in calls)


def test_build_cessions_referentiels_locaux(monkeypatch):
    """Référentiels locaux chargés -> aucun appel aux API unitaires (identité + finances)."""
    pool = [Cession(siren="111111111", nom="A", prix=120000.0, date="2023-06-01")]
    monkeypatch.setattr(bodacc, "fetch_cessions", lambda **kwargs: [c.model_copy()
                                                                    for c in pool])
    monkeypatch.setattr(inpi_client, "configured", lambda: False)
    monkeypatch.setattr(referentiels, "available", lambda table, db_path=None: True)
    monkeypatch.setattr(referentiels, "lookup_company",
                        lambda siren, db_path=None: {"nom": "ALPHA SAS", "naf": "62.02A",
                                                     "ca": None, "ca_annee": None})
    monkeypatch.setattr(referentiels, "lookup_financials",
                        lambda siren, db_path=None: [
                            {"date_cloture_exercice": "2022-12-31",
                             "chiffre_d_affaires": 200000.0, "ebe": 30000.0,
                             "ebit": 25000.0}])

    def _interdit(*args, **kwargs):
        raise AssertionError("API unitaire appelée alors que le référentiel local est chargé")

    monkeypatch.setattr(entreprises, "fetch_company", _interdit)
    monkeypatch.setattr(finances_inpi, "fetch_financials", _interdit)

    batch = pipeline.build_cessions(limit=10, require_ca=True)
    assert [c.siren for c in batch.cessions] == ["111111111"]
    c = batch.cessions[0]
    assert c.nom == "ALPHA SAS" and c.naf == "62.02A"
    assert c.ca == 200000.0 and abs(c.pct_ca - 0.6) < 1e-9


def test_build_cessions_deux_passes_bodacc(monkeypatch):
    """Filtre NAF actif -> passe « nom du commerçant » (précision) avant le texte de
    l'acte (rappel), avec dédoublonnage entre les deux."""
    doublon = Cession(siren="111111111", nom="DUPONT INFORMATIQUE", prix=100000.0,
                      date="2023-06-01")
    pools = {
        ("commercant",): [doublon],
        ("acte",): [doublon.model_copy(),
                    Cession(siren="222222222", nom="LE BISTROT", prix=50000.0,
                            date="2023-06-01")],
    }
    calls: list[tuple] = []

    def fake_fetch(**kwargs):
        calls.append(kwargs.get("search_in"))
        return [c.model_copy() for c in pools[kwargs["search_in"]]]

    companies = {
        "111111111": {"nom": "Dupont SAS", "naf": "62.02A", "ca": None, "ca_annee": None},
        "222222222": {"nom": "Le Bistrot SARL", "naf": "56.10A", "ca": None, "ca_annee": None},
    }
    monkeypatch.setattr(bodacc, "fetch_cessions", fake_fetch)
    monkeypatch.setattr(entreprises, "fetch_company", companies.get)
    monkeypatch.setattr(finances_inpi, "fetch_financials",
                        lambda s: [{"date_cloture_exercice": "2022-12-31",
                                    "chiffre_d_affaires": 400000.0, "ebe": 60000.0,
                                    "ebit": 50000.0}])
    monkeypatch.setattr(inpi_client, "configured", lambda: False)

    batch = pipeline.build_cessions(contains="conseil en informatique", limit=10,
                                    require_ca=True)
    assert calls == [("commercant",), ("acte",)]    # le nom d'abord
    assert batch.n_annonces == 2                    # le doublon nom/acte compté une fois
    assert [c.siren for c in batch.cessions] == ["111111111"]


def test_to_dataframe(monkeypatch):
    _patch(monkeypatch)
    df = pipeline.to_dataframe(pipeline.build_cessions(limit=10, require_ca=False).cessions)
    assert len(df) == 4
    for col in ("siren", "prix", "ca", "ebe", "pct_ca", "mult_ebe", "naf"):
        assert col in df.columns


def test_default_since_is_ten_years_iso():
    s = pipeline.default_since(10)
    assert len(s) == 10 and s[4] == "-"                 # format YYYY-MM-DD


def test_build_cessions_fallback_comptes_deposes(monkeypatch):
    """Quand le dataset ratios n'a rien (comptes confidentiels exclus du jeu mais bilan
    déposé), la cascade sur les comptes INPI comble le CA/EBE — si credentials présents."""
    from comparables.fr.comptes import cascade as comptes_cascade
    from comparables.fr.comptes.cascade import ExtractionResult

    _patch(monkeypatch)
    monkeypatch.setattr(inpi_client, "configured", lambda: True)
    monkeypatch.setattr(inpi_client, "InpiClient", lambda: None)
    monkeypatch.setattr(inpi_client, "fetch_comptes_saisi",
                        lambda siren, before_date=None, client=None: None)
    monkeypatch.setattr(
        inpi_client, "fetch_comptes_pdf",
        lambda siren, before_date=None, client=None:
            ({"id": "b1", "dateCloture": "2022-12-31"}, b"%PDF-fake") if siren == "222222222"
            else None)
    monkeypatch.setattr(
        comptes_cascade, "extract_comptes",
        lambda pdf: ExtractionResult(ca=300000.0, ebe=45000.0, ebit=30000.0,
                                     method="pdf_texte", regime="normal", missing_codes=[]))

    batch = pipeline.build_cessions(limit=10, require_ca=True)
    by = {c.siren: c for c in batch.cessions}

    # B (222...) absente du dataset ratios mais comblée par les comptes déposés
    assert "222222222" in by
    b = by["222222222"]
    assert b.ca == 300000.0 and b.ebe == 45000.0
    assert b.ca_annee == 2022
    assert abs(b.pct_ca - 0.30) < 1e-9                  # 90000 / 300000
    # A vient toujours du dataset ratios (pas écrasée par la cascade)
    assert by["111111111"].ca == 200000.0


def test_build_cessions_fallback_inactif_sans_credentials(monkeypatch):
    """Sans credentials INPI, le fallback est sauté : comportement historique inchangé."""
    _patch(monkeypatch)
    monkeypatch.setattr(inpi_client, "configured", lambda: False)
    batch = pipeline.build_cessions(limit=10, require_ca=True)
    assert [c.siren for c in batch.cessions] == ["111111111"]
