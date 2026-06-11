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


# --- Qualite d'echantillon : filtre R2, beta ajuste (Blume), synthese ---

def test_reliable_beta_seuil():
    from comparables.finance.beta import reliable_beta
    assert reliable_beta(1.2, 0.30, 0.10) == 1.2
    assert reliable_beta(1.2, 0.10, 0.10) == 1.2      # egalite = retenu
    assert reliable_beta(1.2, 0.09, 0.10) is None     # sous le seuil
    assert reliable_beta(1.2, None, 0.10) is None     # pas de regression
    assert reliable_beta(None, 0.50, 0.10) is None
    assert reliable_beta(float("nan"), 0.5, 0.10) is None
    assert reliable_beta(1.2, float("nan"), 0.10) is None


def test_blume_adjusted():
    from comparables.finance.beta import blume_adjusted
    assert abs(blume_adjusted(1.0) - 1.0) < 1e-12             # beta de marche : inchange
    assert abs(blume_adjusted(1.5) - (2/3 * 1.5 + 1/3)) < 1e-12
    assert abs(blume_adjusted(0.6) - (2/3 * 0.6 + 1/3)) < 1e-12
    assert blume_adjusted(None) is None
    assert blume_adjusted(float("inf")) is None


def test_sample_summary_exclut_les_faibles_r2():
    from comparables.finance.beta import sample_summary
    triples = [
        (1.2, 0.40, 0.9),     # retenu
        (0.8, 0.20, 0.7),     # retenu
        (3.0, 0.05, 2.5),     # ecarte : R2 < 0.10 (et ne pollue pas la moyenne)
        (None, None, None),   # pas de beta : ni retenu ni ecarte
    ]
    s = sample_summary(triples, min_r2=0.10)
    assert s is not None
    assert s["n_retained"] == 2 and s["n_excluded_low_r2"] == 1
    assert abs(s["mean_levered"] - 1.0) < 1e-12               # (1.2 + 0.8) / 2
    assert abs(s["median_levered"] - 1.0) < 1e-12
    assert abs(s["mean_adjusted"] - 1.0) < 1e-12              # Blume(1.0) = 1.0
    assert abs(s["mean_unlevered"] - 0.8) < 1e-12             # (0.9 + 0.7) / 2
    assert s["min_r2"] == 0.10


def test_sample_summary_vide():
    from comparables.finance.beta import sample_summary
    assert sample_summary([], min_r2=0.10) is None
    assert sample_summary([(None, None, None)], min_r2=0.10) is None
    # que des ecartes : synthese presente, moyennes absentes
    s = sample_summary([(2.0, 0.02, 1.5)], min_r2=0.10)
    assert s["n_retained"] == 0 and s["n_excluded_low_r2"] == 1
    assert s["mean_levered"] is None and s["mean_adjusted"] is None
