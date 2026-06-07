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


def test_parse_search_empty():
    assert yahoo._parse_search({}) == []
    assert yahoo._parse_search(None) == []
