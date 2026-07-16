"""Tests du parsing et du classement de la recherche de symboles Yahoo (sans réseau)."""
from __future__ import annotations

from comparables.sources import yahoo


def test_parse_search_keeps_only_equities():
    payload = {"quotes": [
        {"quoteType": "EQUITY", "symbol": "OR.PA", "longname": "L'Oreal", "exchange": "PAR"},
        {"quoteType": "ETF", "symbol": "SPY", "exchange": "PCX"},          # exclu
        {"quoteType": "EQUITY", "symbol": "LOR.MU", "shortname": "LOREAL", "exchange": "MUN"},
        {"quoteType": "EQUITY", "exchange": "PAR"},                         # sans symbol -> exclu
    ]}
    res = yahoo._parse_search(payload)
    assert [r["symbol"] for r in res] == ["OR.PA", "LOR.MU"]
    assert res[0]["name"] == "L'Oreal" and res[1]["name"] == "LOREAL"


def test_rank_prefers_primary_exchange():
    # Munich (secondaire) listé avant Paris -> le classement remonte Paris en tête.
    cands = [
        {"symbol": "LOR.MU", "name": "L", "exchange": "MUN"},
        {"symbol": "OR.PA", "name": "L", "exchange": "PAR"},
        {"symbol": "LRLCY", "name": "L", "exchange": "PNK"},
    ]
    assert yahoo._rank(cands)[0]["symbol"] == "OR.PA"


def test_rank_keeps_yahoo_order_within_non_priority():
    cands = [
        {"symbol": "A.XX", "name": "", "exchange": "PNK"},
        {"symbol": "B.YY", "name": "", "exchange": "IOB"},
    ]
    assert [c["symbol"] for c in yahoo._rank(cands)] == ["A.XX", "B.YY"]


def test_normalize_query_strips_accents_and_apostrophes():
    assert yahoo._normalize_query("L'Oréal") == "LOreal"
    assert yahoo._normalize_query("Hermès") == "Hermes"
    assert yahoo._normalize_query("Saint-Gobain") == "Saint-Gobain"
    assert yahoo._normalize_query("  Décathlon ’") == "Decathlon"


def test_normalize_query_transliterates_german_umlauts():
    # Yahoo indexe les umlauts en oe/ae/ue (« Klöckner » -> « Kloeckner »), pas en o/a/u.
    assert yahoo._normalize_query("Klöckner & Co SE") == "Kloeckner & Co SE"
    assert yahoo._normalize_query("Müller") == "Mueller"
    assert yahoo._normalize_query("Württembergische") == "Wuerttembergische"
    assert yahoo._normalize_query("Heidelberger Beteiligungs ß") == "Heidelberger Beteiligungs ss"


def test_rank_prefers_toronto_over_frankfurt_secondary():
    # Russel Metals : cotation principale Toronto (TOR) vs Francfort secondaire (FRA, hors priorite).
    cands = [
        {"symbol": "RMZ.F", "name": "Russel", "exchange": "FRA"},
        {"symbol": "RUS.TO", "name": "Russel", "exchange": "TOR"},
    ]
    assert yahoo._rank(cands)[0]["symbol"] == "RUS.TO"


def test_parse_search_empty():
    assert yahoo._parse_search({}) == []
    assert yahoo._parse_search(None) == []


def test_is_fetchable_symbol_rejects_multiword_labels():
    # Un vrai symbole n'a pas d'espace ; un libelle multi-mots est refuse.
    assert yahoo._is_fetchable_symbol("VOE.VI")
    assert yahoo._is_fetchable_symbol("RS")
    assert yahoo._is_fetchable_symbol("OUT1V.HE")
    assert not yahoo._is_fetchable_symbol("VOESTALPINE AG")     # libelle, pas un ticker
    assert not yahoo._is_fetchable_symbol("KLÖCKNER & CO SE")
    assert not yahoo._is_fetchable_symbol("RUSSEL METALS")
    assert not yahoo._is_fetchable_symbol("")
    assert not yahoo._is_fetchable_symbol("   ")
    assert not yahoo._is_fetchable_symbol(None)


def test_fetch_multiword_short_circuits_without_network():
    # Le garde-fou court-circuite AVANT tout appel reseau/cache : « VOESTALPINE AG »
    # ne doit plus ramener silencieusement les cours du ticker « AG ».
    src = yahoo.YahooSource()
    assert src.fetch_prices("VOESTALPINE AG", "5y", "1mo") is None
    assert src.fetch_fundamentals("SALZGITTER AG") is None


def test_strip_legal_forms():
    assert yahoo._strip_legal_forms("Voestalpine AG") == "Voestalpine"
    assert yahoo._strip_legal_forms("Klöckner & Co SE") == "Klöckner"
    assert yahoo._strip_legal_forms("Reliance Inc") == "Reliance"
    assert yahoo._strip_legal_forms("Outokumpu Oyj") == "Outokumpu"
    assert yahoo._strip_legal_forms("Jacquet Metals") == "Jacquet Metals"   # rien a retirer
    assert yahoo._strip_legal_forms("Holding") == "Holding"                 # tout retire -> garde l'original


def test_exchange_tier_and_isin_like():
    assert yahoo._exchange_tier("VIE") == 0 and yahoo._exchange_tier("GER") == 0   # principales
    assert yahoo._exchange_tier("MUN") == 1 and yahoo._exchange_tier("FRA") == 1   # secondaires DE
    assert yahoo._exchange_tier("PNK") == 3 and yahoo._exchange_tier("IOB") == 3   # OTC / cross
    assert yahoo._exchange_tier("XXX") == 2                                        # inconnue
    assert yahoo._isin_like("AT0000A3A9Z9.VI") and not yahoo._isin_like("VOE.VI")


def test_score_candidates_rejects_wrong_company():
    # « AG » = First Majestic Silver (place principale NYQ) ne doit PAS battre
    # la bonne societe sur une place de Vienne : la ressemblance de nom prime.
    cands = [
        {"symbol": "AG", "name": "First Majestic Silver Corp", "exchange": "NYQ"},
        {"symbol": "VOE.VI", "name": "voestalpine AG", "exchange": "VIE"},
    ]
    assert yahoo._score_candidates("Voestalpine", cands)[0]["symbol"] == "VOE.VI"


def test_score_candidates_prefers_primary_over_otc_and_clean_over_isin():
    # OTC depriorise + ligne ISIN depriorisee face au ticker propre de la meme societe.
    cands = [
        {"symbol": "VLPNF", "name": "voestalpine AG", "exchange": "PNK"},
        {"symbol": "AT0000A3A9Z9.VI", "name": "voestalpine AG", "exchange": "VIE"},
        {"symbol": "VOE.VI", "name": "voestalpine AG", "exchange": "VIE"},
    ]
    assert yahoo._score_candidates("Voestalpine", cands)[0]["symbol"] == "VOE.VI"


def test_score_candidates_filters_tracker_certificates():
    # « RBI OETrackX3 voestalpine » (certificat tracker) contient « voestalpine » mais
    # est noye de tokens parasites -> ecarte au profit d'une vraie cotation de la societe.
    cands = [
        {"symbol": "AT0000A3A9Z9.VI", "name": "RBI OETrackX3 s voestalpine", "exchange": "VIE"},
        {"symbol": "VAS.F", "name": "Voestalpine AG", "exchange": "FRA"},
    ]
    assert yahoo._score_candidates("Voestalpine", cands)[0]["symbol"] == "VAS.F"


def test_score_candidates_prefers_xetra_over_regional():
    # Salzgitter : Xetra (GER, principale) avant Munich (MUN, regionale secondaire).
    cands = [
        {"symbol": "SZG.MU", "name": "Salzgitter AG", "exchange": "MUN"},
        {"symbol": "SZG.DE", "name": "Salzgitter AG", "exchange": "GER"},
    ]
    assert yahoo._score_candidates("Salzgitter", cands)[0]["symbol"] == "SZG.DE"


def test_needs_primary_probe():
    assert not yahoo._needs_primary_probe({"symbol": "KCO.DE", "exchange": "GER"})   # principale
    assert not yahoo._needs_primary_probe({"symbol": "RS", "exchange": "NYQ"})
    assert yahoo._needs_primary_probe({"symbol": "SZG.MU", "exchange": "MUN"})       # secondaire
    assert yahoo._needs_primary_probe({"symbol": "VOE.PR", "exchange": "PRA"})       # place inconnue
    assert yahoo._needs_primary_probe({"symbol": "AT0000A3A9Z9.VI", "exchange": "VIE"})  # ISIN


def test_primary_guesses_reconstructs_xetra_and_vienna():
    # Allemand : racine partagee SZG -> SZG.DE (Xetra, place principale).
    de = yahoo._primary_guesses([
        {"symbol": "SZG.MU", "name": "Salzgitter AG", "exchange": "MUN"},
        {"symbol": "SZGA.F", "name": "Salzgitter AG", "exchange": "FRA"},
    ])
    assert de[0]["symbol"] == "SZG.DE" and de[0]["exchange"] == "GER"
    # Autrichien (une place VIE presente) : VOE -> VOE.VI ; la ligne ISIN est ignoree.
    at = yahoo._primary_guesses([
        {"symbol": "VOE.PR", "name": "Voestalpine AG", "exchange": "PRA"},
        {"symbol": "AT0000A3A9Z9.VI", "name": "RBI tracker", "exchange": "VIE"},
    ])
    assert any(g["symbol"] == "VOE.VI" and g["exchange"] == "VIE" for g in at)
    # Aucune place allemande/autrichienne -> pas de reconstruction (on ne devine pas).
    assert yahoo._primary_guesses([{"symbol": "RS", "name": "Reliance", "exchange": "NYQ"}]) == []
