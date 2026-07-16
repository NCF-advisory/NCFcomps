from datetime import date

import numpy as np
import pandas as pd
from comparables.finance.beta import (
    aligned_returns, compute_beta, drop_incomplete_last_period, returns_from_prices,
)


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


def test_adjusted_beta_desendette():
    from comparables.finance.beta import adjusted_beta
    assert abs(adjusted_beta(1.0) - 1.0) < 1e-12             # beta de marche : inchange
    assert abs(adjusted_beta(0.8) - (0.67 * 0.8 + 0.33)) < 1e-12
    assert abs(adjusted_beta(1.5) - (0.67 * 1.5 + 0.33)) < 1e-12
    assert adjusted_beta(None) is None
    assert adjusted_beta(float("nan")) is None
    assert adjusted_beta(float("inf")) is None


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
    assert abs(s["mean_unlevered_adjusted"] - (0.67 * 0.8 + 0.33)) < 1e-12   # 0,67 x desend. + 0,33
    assert s["min_r2"] == 0.10


def test_sample_summary_vide():
    from comparables.finance.beta import sample_summary
    assert sample_summary([], min_r2=0.10) is None
    assert sample_summary([(None, None, None)], min_r2=0.10) is None
    # que des ecartes : synthese presente, moyennes absentes
    s = sample_summary([(2.0, 0.02, 1.5)], min_r2=0.10)
    assert s["n_retained"] == 0 and s["n_excluded_low_r2"] == 1
    assert s["mean_levered"] is None and s["mean_adjusted"] is None
    assert s["mean_unlevered"] is None and s["mean_unlevered_adjusted"] is None


# --- Chantier A : ecarte la periode calendaire EN COURS (mois/semaine/jour incomplet) ---

def test_drop_incomplete_last_period_mensuel():
    idx = pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-31"])
    s = pd.Series([1.0, 2.0, 3.0], index=idx)
    # today dans un mois ulterieur -> mars est un mois complet -> conserve
    kept = drop_incomplete_last_period(s, "1mo", today=date(2024, 5, 15))
    assert len(kept) == 3
    # today DANS le mois de la derniere obs -> mars en cours (incomplet) -> supprime
    trimmed = drop_incomplete_last_period(s, "1mo", today=date(2024, 3, 10))
    assert len(trimmed) == 2
    assert trimmed.index[-1] == pd.Timestamp("2024-02-29")
    assert len(s) == 3                       # la serie d'origine n'est pas mutee


def test_drop_incomplete_last_period_hebdo():
    # 2024-03-25 (lundi) = semaine ISO 13 ; 2024-03-27 (mercredi) meme semaine.
    idx = pd.to_datetime(["2024-03-11", "2024-03-18", "2024-03-25"])
    s = pd.Series([1.0, 2.0, 3.0], index=idx)
    trimmed = drop_incomplete_last_period(s, "1wk", today=date(2024, 3, 27))
    assert len(trimmed) == 2                  # meme semaine ISO -> derniere obs supprimee
    kept = drop_incomplete_last_period(s, "1wk", today=date(2024, 4, 3))
    assert len(kept) == 3                     # semaine ISO 14 -> semaine 13 complete


def test_drop_incomplete_last_period_journalier():
    idx = pd.to_datetime(["2024-03-18", "2024-03-19", "2024-03-20"])
    s = pd.Series([1.0, 2.0, 3.0], index=idx)
    assert len(drop_incomplete_last_period(s, "1d", today=date(2024, 3, 20))) == 2  # jour courant
    assert len(drop_incomplete_last_period(s, "1d", today=date(2024, 3, 21))) == 3  # veille close


def test_drop_incomplete_last_period_intervalle_inconnu():
    idx = pd.to_datetime(["2024-01-31", "2024-02-29"])
    s = pd.Series([1.0, 2.0], index=idx)
    out = drop_incomplete_last_period(s, "3mo", today=date(2024, 2, 15))
    assert len(out) == 2                      # intervalle inconnu -> serie inchangee


def test_drop_incomplete_last_period_tz_aware():
    idx = pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-31"]).tz_localize("America/New_York")
    s = pd.Series([1.0, 2.0, 3.0], index=idx)
    trimmed = drop_incomplete_last_period(s, "1mo", today=date(2024, 3, 10))
    assert len(trimmed) == 2                  # mois courant supprime malgre l'index tz-aware
    kept = drop_incomplete_last_period(s, "1mo", today=date(2024, 6, 1))
    assert len(kept) == 3


# --- Chantier B : alignement des PRIX avant de deriver les rendements ---

def test_aligned_returns_elimine_le_rendement_enjambant():
    dates = pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-31", "2024-04-30"])
    index_p = pd.Series([100.0, 110.0, 121.0, 133.1], index=dates)
    # Le titre n'a PAS cote en fevrier (trou de cotation) : sa serie saute fevrier.
    stock_p = pd.Series([50.0, 60.0, 66.0], index=dates[[0, 2, 3]])
    sr, ir = aligned_returns(stock_p, index_p)
    # Dates communes = jan/mars/avril -> rendements sur mars et avril, memes dates des 2 cotes.
    assert list(sr.index) == list(pd.to_datetime(["2024-03-31", "2024-04-30"]))
    assert list(ir.index) == list(sr.index)
    # Le rendement de mars couvre jan->mars des DEUX cotes : indice = 121/100 - 1 = 0.21
    # (et NON 121/110 - 1 = 0.1, ce que donnerait une jointure des rendements deja calcules).
    assert abs(ir.loc[pd.Timestamp("2024-03-31")] - 0.21) < 1e-9
    assert abs(sr.loc[pd.Timestamp("2024-03-31")] - 0.20) < 1e-9   # titre : 60/50 - 1


# --- Chantiers C/D/F : ecart-type, part de rendements nuls, fenetre effective ---

def test_compute_beta_std_err_et_fenetre():
    rng = np.random.default_rng(5)
    x = rng.normal(0, 0.04, 200)
    y = 0.001 + 1.1 * x + rng.normal(0, 0.02, 200)
    dates = pd.date_range("2010-01-01", periods=200, freq="MS")
    res = compute_beta(pd.Series(y, index=dates), pd.Series(x, index=dates), min_obs=24)
    assert res.std_err is not None and np.isfinite(res.std_err) and res.std_err > 0
    assert res.start == "2010-01-01"                 # 1re observation regressee (ISO)
    assert res.end == dates[-1].date().isoformat()   # derniere observation regressee


def test_compute_beta_zero_return_share():
    # 10 observations, 3 rendements titre strictement nuls -> part = 0.30
    x = pd.Series([0.01, -0.02, 0.03, 0.01, -0.01, 0.02, 0.015, 0.01, -0.03, 0.02])
    y = pd.Series([0.0, -0.02, 0.0, 0.01, -0.01, 0.0, 0.01, 0.01, -0.03, 0.02])
    res = compute_beta(y, x, min_obs=5)
    assert res.zero_return_share is not None
    assert abs(res.zero_return_share - 0.30) < 1e-9


def test_compute_beta_fenetre_none_si_index_non_date():
    # Index entier (tests unitaires) -> pas de dates inventees (surtout pas 1970).
    res = compute_beta(pd.Series(np.linspace(-0.02, 0.03, 40)),
                       pd.Series(np.linspace(-0.015, 0.02, 40)), min_obs=24)
    assert res.start is None and res.end is None
