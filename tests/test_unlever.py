from comparables.finance.unlever import unlever_beta, relever_beta


def test_unlever_basic():
    # beta_l=1.10, DN=9e9, E=320e9, IS=25%
    bu = unlever_beta(1.10, 9e9, 320e9, 0.25)
    assert abs(bu - 1.0773) < 1e-3


def test_unlever_relever_roundtrip():
    bu = unlever_beta(1.20, 18e9, 35e9, 0.25)
    bl = relever_beta(bu, 18e9, 35e9, 0.25)
    assert abs(bl - 1.20) < 1e-9


def test_net_cash_floor_option():
    # tresorerie nette : sans plancher beta_u > beta_l ; avec plancher beta_u == beta_l
    no_floor = unlever_beta(0.90, -7e9, 90e9, 0.25, floor_net_debt_at_zero=False)
    floored = unlever_beta(0.90, -7e9, 90e9, 0.25, floor_net_debt_at_zero=True)
    assert no_floor > 0.90
    assert abs(floored - 0.90) < 1e-9


def test_unlever_handles_missing():
    assert unlever_beta(None, 1e9, 1e9, 0.25) is None
    assert unlever_beta(1.0, 1e9, 0, 0.25) is None


def test_unlever_rejects_non_finite():
    assert unlever_beta(float("inf"), 30.0, 100.0, 0.25) is None
    assert unlever_beta(float("nan"), 30.0, 100.0, 0.25) is None
    assert unlever_beta(1.0, float("nan"), 100.0, 0.25) is None
    assert unlever_beta(1.0, 30.0, float("inf"), 0.25) is None


def test_unlever_rejects_zero_denominator():
    # 1 + (1-IS)*(DN/E) == 0 quand IS=0 et DN=-E -> division impossible.
    assert unlever_beta(1.0, -100.0, 100.0, 0.0) is None


def test_relever_basic():
    # 1.0 * (1 + 0.75 * 0.30) = 1.225
    assert abs(relever_beta(1.0, 30.0, 100.0, 0.25) - 1.225) < 1e-9


def test_relever_handles_missing_and_non_finite():
    assert relever_beta(None, 1.0, 1.0, 0.25) is None
    assert relever_beta(1.0, 1.0, 0.0, 0.25) is None       # equity nul
    assert relever_beta(float("inf"), 1.0, 1.0, 0.25) is None
