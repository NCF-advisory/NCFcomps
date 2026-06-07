import numpy as np
import pandas as pd
from comparables.finance.beta import compute_beta, returns_from_prices


def test_beta_recovers_known_slope():
    rng = np.random.default_rng(0)
    x = rng.normal(0, 0.04, 300)            # rendements indice
    y = 0.001 + 1.3 * x + rng.normal(0, 0.01, 300)
    res = compute_beta(pd.Series(y), pd.Series(x), min_obs=24)
    assert res.beta is not None
    assert abs(res.beta - 1.3) < 0.1        # proche de la valeur theorique
    assert 0.0 <= res.r2 <= 1.0
    assert res.r2 > 0.8                      # bruit faible -> R2 eleve
    assert res.n_obs == 300


def test_beta_insufficient_points():
    res = compute_beta(pd.Series([0.01, 0.02]), pd.Series([0.01, 0.02]), min_obs=24)
    assert res.beta is None and res.n_obs == 2


def test_returns_from_prices():
    prices = pd.Series([100.0, 110.0, 99.0])
    r = returns_from_prices(prices)
    assert len(r) == 2
    assert abs(r.iloc[0] - 0.10) < 1e-9


def test_beta_never_returns_inf_or_nan_on_degenerate_prices():
    # Un cours qui passe par 0 cree un rendement infini : il ne doit jamais
    # ressortir un beta/R2 inf/nan (sinon il pollue la stat d'echantillon).
    rng = np.random.default_rng(1)
    idx_prices = pd.Series(100.0 * np.cumprod(1.0 + rng.normal(0, 0.03, 40)))
    stock_prices = idx_prices.copy()
    stock_prices.iloc[20] = 0.0          # krach a zero -> rendement +inf juste apres
    res = compute_beta(returns_from_prices(stock_prices),
                       returns_from_prices(idx_prices), min_obs=10)
    assert res.beta is None or np.isfinite(res.beta)
    assert res.r2 is None or (0.0 <= res.r2 <= 1.0)


def test_beta_zero_variance_index():
    # Indice plat (variance nulle) -> pas de regression possible.
    stock = pd.Series(np.linspace(0.0, 0.1, 30))
    flat = pd.Series([0.01] * 30)
    res = compute_beta(stock, flat, min_obs=10)
    assert res.beta is None and res.r2 is None
