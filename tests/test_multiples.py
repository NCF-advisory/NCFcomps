import math

from comparables.finance import multiples as m


def test_net_debt_and_ev():
    assert m.net_debt(10.0, 4.0) == 6.0
    assert m.net_debt(10.0, None) is None
    assert m.enterprise_value(100.0, 6.0) == 106.0


def test_safe_ratio():
    assert m.safe_ratio(100.0, 10.0) == 10.0
    assert m.safe_ratio(100.0, 0.0) is None      # denominateur nul
    assert m.safe_ratio(100.0, -5.0) is None     # denominateur negatif (EBITDA < 0)
    assert m.safe_ratio(None, 10.0) is None


def test_safe_ratio_rejects_non_finite():
    assert m.safe_ratio(float("inf"), 10.0) is None
    assert m.safe_ratio(float("nan"), 10.0) is None
    assert m.safe_ratio(100.0, float("nan")) is None
    assert m.safe_ratio(100.0, float("inf")) is None


def test_summary_stats():
    s = m.summary_stats([1.0, 2.0, 3.0, None])
    assert s["median"] == 2.0 and s["min"] == 1.0 and s["max"] == 3.0
    assert m.summary_stats([None, None]) is None


def test_summary_stats_ignores_non_finite():
    # inf et nan ne doivent pas polluer mediane/moyenne (sinon tout l'echantillon est fausse).
    s = m.summary_stats([1.0, float("inf"), float("nan"), 2.0, 3.0])
    assert s["median"] == 2.0 and s["min"] == 1.0 and s["max"] == 3.0
    assert math.isfinite(s["mean"]) and abs(s["mean"] - 2.0) < 1e-9


def test_summary_stats_all_non_finite_returns_none():
    assert m.summary_stats([float("nan"), float("inf"), float("-inf")]) is None
