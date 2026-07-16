"""Harnais de benchmark : replique les betas S&P Capital IQ avec notre moteur.

Relançable en une commande :  .venv/bin/python -m benchmarks.beta_ciq.benchmark
Regenere  benchmarks/beta_ciq/results.csv  et  benchmarks/beta_ciq/report.md.

Contexte (confirme par l'utilisateur) :
- TOUS les exports CIQ ont ete produits en reglage DEFAUT « 5 ans / quotidien ».
  La config de reference de replication est donc « CIQ 5a quotidien », certaine.
- Le reglage « Currency » du modele etait sur Euro, mais on ignore si CIQ convertit
  les cours en EUR avant la regression -> tranche par le diagnostic devise.

N'ecrit AUCUN fichier produit ; ne modifie pas le snapshot Damodaran.
"""
from __future__ import annotations

import csv
import statistics
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd
from dateutil.relativedelta import relativedelta

from comparables import damodaran
from comparables.config import index_for, settings
from comparables.finance.beta import aligned_returns, compute_beta

from benchmarks.beta_ciq import fetch, parse_ciq
from benchmarks.beta_ciq.parse_ciq import CiqCompany

HERE = Path(__file__).resolve().parent
RESULTS_CSV = HERE / "results.csv"
REPORT_MD = HERE / "report.md"

GSPC, STOXX = "^GSPC", "^STOXX"

# (libelle config, nb annees, intervalle 'D'/'W'/'M', min_obs)
REPL_CONFIGS = [
    ("CIQ 5a quotidien", 5, "D", 200),
    ("5a hebdo", 5, "W", 120),
    ("2a hebdo", 2, "W", 52),
]
TOOL_CONFIG = ("Outil defaut (5a mensuel)", 5, "M", 24)

_RESAMPLE = {"W": "W-FRI", "M": "ME"}
_index_cache: dict[tuple[str, str], Optional[pd.Series]] = {}


def _wide_start(end: date) -> date:
    return end - relativedelta(years=5, months=5)


def get_index_prices(symbol: str, end: date) -> Optional[pd.Series]:
    key = (symbol, end.isoformat())
    if key not in _index_cache:
        _index_cache[key] = fetch.fetch_prices(symbol, _wide_start(end), end)
    return _index_cache[key]


def _slice(series: pd.Series, start: date, end: date) -> pd.Series:
    return series.loc[pd.Timestamp(start):pd.Timestamp(end)]


def _resample(series: pd.Series, interval: str) -> pd.Series:
    if interval in _RESAMPLE:
        return series.resample(_RESAMPLE[interval]).last().dropna()
    return series


def beta_config(stock_px: pd.Series, index_px: pd.Series, end: date,
                years: int, interval: str, min_obs: int):
    """Renvoie BetaResult pour une fenetre/intervalle donnes (fin = end)."""
    start = end - relativedelta(years=years)
    st = _resample(_slice(stock_px, start, end), interval)
    ix = _resample(_slice(index_px, start, end), interval)
    if st is None or ix is None or len(st) < 3 or len(ix) < 3:
        return None
    sr, ir = aligned_returns(st, ix)
    return compute_beta(sr, ir, min_obs)


@dataclass
class CompanyResult:
    company: CiqCompany
    yahoo_beta: Optional[float] = None
    industry: Optional[str] = None
    currency: Optional[str] = None
    # cle -> (config_label, index_symbol) : valeurs (beta, r2, n)
    betas: dict = field(default_factory=dict)


def run_company(c: CiqCompany, end: date, local_idx: str) -> CompanyResult:
    res = CompanyResult(company=c)
    info = fetch.fetch_info(c.yahoo_ticker)
    res.yahoo_beta = info.get("beta")
    res.industry = info.get("industry")
    res.currency = info.get("currency")

    stock = fetch.fetch_prices(c.yahoo_ticker, _wide_start(end), end)
    if stock is None:
        return res
    index_syms = {GSPC, STOXX, local_idx}
    idx_px = {sym: get_index_prices(sym, end) for sym in index_syms}

    for label, years, interval, min_obs in REPL_CONFIGS:
        for sym in (GSPC, STOXX, local_idx):
            ip = idx_px.get(sym)
            if ip is None:
                continue
            br = beta_config(stock, ip, end, years, interval, min_obs)
            if br is not None:
                res.betas[(label, sym)] = (br.beta, br.r2, br.n_obs)
    # Config outil : 5a mensuel vs indice local uniquement.
    tl, ty, ti, tmin = TOOL_CONFIG
    ip = idx_px.get(local_idx)
    if ip is not None:
        br = beta_config(stock, ip, end, ty, ti, tmin)
        if br is not None:
            res.betas[(tl, local_idx)] = (br.beta, br.r2, br.n_obs)
    return res


# --------------------------------------------------------------- diagnostic devise

_EUR_FX = {  # devise locale -> paire Yahoo EUR{cur}=X (EUR par unite locale = 1/paire)
    "CHF": "EURCHF=X", "GBP": "EURGBP=X", "GBp": "EURGBP=X",
    "SEK": "EURSEK=X", "NOK": "EURNOK=X", "DKK": "EURDKK=X",
}


def currency_diagnostic(companies: list[tuple[CiqCompany, CompanyResult, date]]) -> list[dict]:
    """Pour des titres europeens hors zone euro : beta 5a quotidien vs ^STOXX en devise
    LOCALE puis en cours CONVERTIS EN EUR. Compare au beta CIQ pour trancher la devise."""
    out = []
    for c, r, end in companies:
        cur = (r.currency or "").upper()
        if cur not in {k.upper() for k in _EUR_FX}:
            continue
        pair = next(v for k, v in _EUR_FX.items() if k.upper() == cur)
        stock = fetch.fetch_prices(c.yahoo_ticker, _wide_start(end), end)
        stoxx = get_index_prices(STOXX, end)
        fx = fetch.fetch_prices(pair, _wide_start(end), end)
        if stock is None or stoxx is None or fx is None:
            continue
        # GBp (pence) : Yahoo cote parfois en pence -> ramener en GBP avant conversion.
        px_local = stock
        # cours converti en EUR : price_EUR = price_local / (EUR{cur} = cur par EUR)
        eur = (px_local / fx.reindex(px_local.index).ffill()).dropna()
        start = end - relativedelta(years=5)
        b_local = compute_beta(*aligned_returns(_slice(px_local, start, end),
                                                _slice(stoxx, start, end)), 200)
        b_eur = compute_beta(*aligned_returns(_slice(eur, start, end),
                                              _slice(stoxx, start, end)), 200)
        out.append({
            "company": c.name, "ticker": c.yahoo_ticker, "currency": cur,
            "beta_ciq": c.levered_beta,
            "beta_local": b_local.beta, "r2_local": b_local.r2,
            "beta_eur": b_eur.beta, "r2_eur": b_eur.r2,
        })
    return out


# ----------------------------------------------------------------------- utilitaires

def _fmt(x: Optional[float], d: int = 3) -> str:
    return "—" if x is None else f"{x:.{d}f}"


def _median(vals: list[Optional[float]]) -> Optional[float]:
    xs = [v for v in vals if v is not None]
    return statistics.median(xs) if xs else None


def _mae_bias(pairs: list[tuple[float, float]]) -> tuple[Optional[float], Optional[float], int]:
    """pairs = (repl, ciq). Renvoie (MAE, biais moyen repl-ciq, n)."""
    diffs = [a - b for a, b in pairs if a is not None and b is not None]
    if not diffs:
        return None, None, 0
    mae = statistics.mean(abs(d) for d in diffs)
    bias = statistics.mean(diffs)
    return mae, bias, len(diffs)


# --------------------------------------------------------------------------- main

def main() -> None:
    files = parse_ciq.parse_all()
    europe_rows = damodaran._parse_xls(
        (Path(__file__).resolve().parents[2] / "betaEurope.xls").read_bytes(), "Europe")
    europe_by_norm = {damodaran._norm(r["industry"]): r for r in europe_rows}

    all_results: list[tuple[parse_ciq.CiqFile, list[CompanyResult]]] = []
    csv_rows: list[dict] = []
    diag_input: list[tuple[CiqCompany, CompanyResult, date]] = []

    for cf in files:
        resolved = [c for c in cf.companies if c.yahoo_ticker]
        print(f"[{cf.filename}] {len(resolved)} societes resolues...", flush=True)
        results: list[CompanyResult] = []
        for c in resolved:
            local_idx = index_for(c.yahoo_ticker)
            r = run_company(c, cf.end_date, local_idx)
            results.append(r)
            diag_input.append((c, r, cf.end_date))
            # lignes CSV
            for (label, sym), (beta, r2, n) in r.betas.items():
                csv_rows.append({
                    "fichier": cf.filename, "label": cf.label,
                    "ticker_ciq": c.ciq_ticker, "ticker_yahoo": c.yahoo_ticker,
                    "societe": c.name, "config": label, "indice": sym,
                    "n_points": n, "beta": round(beta, 4) if beta is not None else "",
                    "r2": round(r2, 4) if r2 is not None else "",
                    "beta_ciq": round(c.levered_beta, 4) if c.levered_beta is not None else "",
                    "delta_ciq": round(beta - c.levered_beta, 4)
                    if (beta is not None and c.levered_beta is not None) else "",
                    "r2_ciq": round(c.r2, 4) if c.r2 is not None else "",
                })
            # ligne indicative beta Yahoo publie
            csv_rows.append({
                "fichier": cf.filename, "label": cf.label,
                "ticker_ciq": c.ciq_ticker, "ticker_yahoo": c.yahoo_ticker,
                "societe": c.name, "config": "Yahoo publie (indicatif)", "indice": "-",
                "n_points": "", "beta": r.yahoo_beta if r.yahoo_beta is not None else "",
                "r2": "", "beta_ciq": round(c.levered_beta, 4) if c.levered_beta is not None else "",
                "delta_ciq": "", "r2_ciq": "",
            })
        all_results.append((cf, results))

    # ---- ecriture results.csv
    fields = ["fichier", "label", "ticker_ciq", "ticker_yahoo", "societe", "config",
              "indice", "n_points", "beta", "r2", "beta_ciq", "delta_ciq", "r2_ciq"]
    with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(csv_rows)
    print(f"-> {RESULTS_CSV} ({len(csv_rows)} lignes)")

    # ---- diagnostic devise
    diag = currency_diagnostic(diag_input)

    # ---- rapport
    write_report(files, all_results, europe_by_norm, diag)
    print(f"-> {REPORT_MD}")


def _best_index(r: CompanyResult, ciq_beta: Optional[float], local_idx: str):
    """Indice (parmi GSPC/STOXX/local) dont le beta 5a quotidien colle le mieux au CIQ."""
    if ciq_beta is None:
        return None, None, None
    best = None
    for sym in (GSPC, STOXX, local_idx):
        v = r.betas.get(("CIQ 5a quotidien", sym))
        if v and v[0] is not None:
            d = abs(v[0] - ciq_beta)
            if best is None or d < best[0]:
                best = (d, sym, v[0], v[1])
    if best is None:
        return None, None, None
    return best[1], best[2], best[3]


def _rule_index(yahoo_ticker: str) -> str:
    """Regle candidate : cotation US -> ^GSPC, sinon (Europe/UK) -> ^STOXX."""
    return GSPC if "." not in yahoo_ticker else STOXX


def write_report(files, all_results, europe_by_norm, diag) -> None:
    L: list[str] = []
    L.append("# Benchmark des betas — réplication S&P Capital IQ\n")
    L.append(f"_Généré le {date.today().isoformat()} par "
             "`benchmarks/beta_ciq/benchmark.py`._\n")
    L.append("Méthode CIQ (confirmée) : régression OLS brute, **5 ans, fréquence "
             "quotidienne**, fin de fenêtre = date d'export. Notre moteur "
             "(`comparables/finance/beta.py`) applique la même régression OLS "
             "(rendements simples, dates appariées). Configs candidates de notre outil : "
             "5 ans et 2 ans en hebdomadaire, et le **défaut de l'outil** "
             f"(période={settings.beta_period}, fréquence={settings.beta_frequency}, "
             "indice local du registre).\n")

    # agregats globaux
    glob_pairs: dict[str, list[tuple[float, float]]] = {}

    for cf, results in all_results:
        L.append(f"\n## {cf.filename} — {cf.label}")
        L.append(f"\nFin de fenêtre : **{cf.end_date.isoformat()}** — "
                 f"{len(results)} sociétés résolues.\n")
        # table par societe
        L.append("| Société | β CIQ | R² CIQ | β répl. (meilleur indice) | indice | R² répl. "
                 "| β local | β 5a hebdo (local) | β 2a hebdo (local) | β outil (5a mens.) |")
        L.append("|---|---|---|---|---|---|---|---|---|---|")
        rows_for_median: dict[str, list[Optional[float]]] = {
            "repl_best": [], "repl_local": [], "hebdo5": [], "hebdo2": [], "outil": [],
            "ciq": [],
        }
        for r in results:
            c = r.company
            local_idx = index_for(c.yahoo_ticker)
            b_sym, b_beta, b_r2 = _best_index(r, c.levered_beta, local_idx)
            repl_local = r.betas.get(("CIQ 5a quotidien", local_idx))
            hebdo5 = r.betas.get(("5a hebdo", local_idx))
            hebdo2 = r.betas.get(("2a hebdo", local_idx))
            outil = r.betas.get(("Outil defaut (5a mensuel)", local_idx))
            L.append("| {name} | {bc} | {r2c} | {bb} | {sym} | {br2} | {bl} | {h5} | {h2} | {ou} |".format(
                name=(c.name or c.yahoo_ticker)[:34],
                bc=_fmt(c.levered_beta), r2c=_fmt(c.r2),
                bb=_fmt(b_beta), sym=b_sym or "—", br2=_fmt(b_r2),
                bl=_fmt(repl_local[0] if repl_local else None),
                h5=_fmt(hebdo5[0] if hebdo5 else None),
                h2=_fmt(hebdo2[0] if hebdo2 else None),
                ou=_fmt(outil[0] if outil else None),
            ))
            rows_for_median["ciq"].append(c.levered_beta)
            rows_for_median["repl_best"].append(b_beta)
            rows_for_median["repl_local"].append(repl_local[0] if repl_local else None)
            rows_for_median["hebdo5"].append(hebdo5[0] if hebdo5 else None)
            rows_for_median["hebdo2"].append(hebdo2[0] if hebdo2 else None)
            rows_for_median["outil"].append(outil[0] if outil else None)
            # collecte agregats globaux
            if c.levered_beta is not None:
                if b_beta is not None:
                    glob_pairs.setdefault("CIQ répl. (meilleur indice)", []).append((b_beta, c.levered_beta))
                if repl_local and repl_local[0] is not None:
                    glob_pairs.setdefault("CIQ répl. @indice local", []).append((repl_local[0], c.levered_beta))
                gv = r.betas.get(("CIQ 5a quotidien", GSPC))
                if gv and gv[0] is not None:
                    glob_pairs.setdefault("CIQ répl. @^GSPC", []).append((gv[0], c.levered_beta))
                sv = r.betas.get(("CIQ 5a quotidien", STOXX))
                if sv and sv[0] is not None:
                    glob_pairs.setdefault("CIQ répl. @^STOXX", []).append((sv[0], c.levered_beta))
                rule = r.betas.get(("CIQ 5a quotidien", _rule_index(c.yahoo_ticker)))
                if rule and rule[0] is not None:
                    glob_pairs.setdefault("CIQ répl. @règle US/Europe", []).append((rule[0], c.levered_beta))
                if hebdo5 and hebdo5[0] is not None:
                    glob_pairs.setdefault("5a hebdo @local", []).append((hebdo5[0], c.levered_beta))
                if hebdo2 and hebdo2[0] is not None:
                    glob_pairs.setdefault("2a hebdo @local", []).append((hebdo2[0], c.levered_beta))
                if outil and outil[0] is not None:
                    glob_pairs.setdefault("Outil défaut @local", []).append((outil[0], c.levered_beta))
        # medianes echantillon
        L.append("| **Médiane échantillon** | {ciq} | | {rb} | | | {rl} | {h5} | {h2} | {ou} |".format(
            ciq=_fmt(_median(rows_for_median["ciq"])),
            rb=_fmt(_median(rows_for_median["repl_best"])),
            rl=_fmt(_median(rows_for_median["repl_local"])),
            h5=_fmt(_median(rows_for_median["hebdo5"])),
            h2=_fmt(_median(rows_for_median["hebdo2"])),
            ou=_fmt(_median(rows_for_median["outil"])),
        ))
        # non couvertes
        uncov = [c for c in cf.companies if not c.yahoo_ticker]
        if uncov:
            L.append("\nNon couvertes : " + ", ".join(
                f"{c.name or c.ciq_ticker} ({c.map_note})" for c in uncov) + ".")

        # bande Damodaran
        industries = [r.industry for r in results]
        dam_ind = damodaran.suggest_industry(industries, "Global") \
            or parse_ciq.FILE_DAMODARAN_FALLBACK.get(cf.filename)
        L.append(_damodaran_block(dam_ind, europe_by_norm, industries))

    # ---- synthese globale
    L.append("\n## Synthèse globale\n")
    L.append("### MAE et biais par configuration (vs β endetté CIQ)\n")
    L.append("| Configuration | n | MAE | Biais moyen (répl. − CIQ) |")
    L.append("|---|---|---|---|")
    order = ["CIQ répl. @indice local", "CIQ répl. @^GSPC", "CIQ répl. @^STOXX",
             "CIQ répl. @règle US/Europe", "CIQ répl. (meilleur indice)",
             "5a hebdo @local", "2a hebdo @local", "Outil défaut @local"]
    for name in order:
        pairs = glob_pairs.get(name, [])
        mae, bias, n = _mae_bias(pairs)
        L.append(f"| {name} | {n} | {_fmt(mae)} | {_fmt(bias)} |")

    L.append("\n### Indice identifié par société (config CIQ 5a quotidien)\n")
    L.append("Pour chaque société, l'indice (^GSPC / ^STOXX / indice local) dont le β "
             "5a quotidien colle le mieux au β CIQ, et l'écart de R² associé.\n")
    L.append("| Société | ticker | β CIQ | R² CIQ | indice retenu | β | R² | règle US/Eu ? |")
    L.append("|---|---|---|---|---|---|---|---|")
    rule_hits = rule_total = 0
    for cf, results in all_results:
        for r in results:
            c = r.company
            local_idx = index_for(c.yahoo_ticker)
            sym, beta, r2 = _best_index(r, c.levered_beta, local_idx)
            if sym is None:
                continue
            rule_sym = _rule_index(c.yahoo_ticker)
            ok = (sym == rule_sym) or (rule_sym == local_idx == sym)
            rule_total += 1
            rule_hits += 1 if ok else 0
            L.append(f"| {(c.name or '')[:28]} | {c.yahoo_ticker} | {_fmt(c.levered_beta)} "
                     f"| {_fmt(c.r2)} | {sym} | {_fmt(beta)} | {_fmt(r2)} | {'oui' if ok else 'non'} |")
    if rule_total:
        L.append(f"\n**Règle « US→^GSPC, Europe→^STOXX » vérifiée pour "
                 f"{rule_hits}/{rule_total} sociétés ({100*rule_hits/rule_total:.0f} %).**")

    # ---- diagnostic devise
    L.append("\n### Diagnostic devise (local vs EUR-converti, β 5a quotidien vs ^STOXX)\n")
    if diag:
        L.append("| Société | devise | β CIQ | β local | R² local | β EUR | R² EUR | plus proche CIQ |")
        L.append("|---|---|---|---|---|---|---|---|")
        local_wins = eur_wins = 0
        for d in diag:
            closer = "—"
            if d["beta_ciq"] is not None and d["beta_local"] is not None and d["beta_eur"] is not None:
                dl = abs(d["beta_local"] - d["beta_ciq"])
                de = abs(d["beta_eur"] - d["beta_ciq"])
                closer = "local" if dl <= de else "EUR"
                local_wins += 1 if dl <= de else 0
                eur_wins += 0 if dl <= de else 1
            L.append(f"| {d['company'][:26]} | {d['currency']} | {_fmt(d['beta_ciq'])} "
                     f"| {_fmt(d['beta_local'])} | {_fmt(d['r2_local'])} | {_fmt(d['beta_eur'])} "
                     f"| {_fmt(d['r2_eur'])} | {closer} |")
        L.append(f"\n**Verdict devise : cours locaux plus proches du CIQ pour {local_wins} "
                 f"société(s), EUR-converti pour {eur_wins}.** "
                 "Voir interprétation ci-dessous.")
    else:
        L.append("_Aucune société hors zone euro exploitable pour le diagnostic._")

    REPORT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")


def _damodaran_block(industry: Optional[str], europe_by_norm: dict,
                     yahoo_industries: list) -> str:
    if not industry:
        return "\n_Bande Damodaran : industrie non déterminée._\n"
    g = damodaran.lookup(industry, "Global")
    e = europe_by_norm.get(damodaran._norm(industry))
    lines = [f"\n**Bande sectorielle Damodaran** (industrie retenue : *{industry}*, "
             f"snapshot au {damodaran.as_of('Global')}) :\n"]
    lines.append("| Région | β endetté | β désendetté | β désend. corrigé du cash | n sociétés |")
    lines.append("|---|---|---|---|---|")
    if g:
        lines.append(f"| Global | {_fmt(g['beta'])} | {_fmt(g['unlevered_beta'])} "
                     f"| {_fmt(g['unlevered_beta_cash'])} | {g.get('n_firms') or '—'} |")
    if e:
        lines.append(f"| Europe | {_fmt(e['beta'])} | {_fmt(e['unlevered_beta'])} "
                     f"| {_fmt(e['unlevered_beta_cash'])} | {e.get('n_firms') or '—'} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
