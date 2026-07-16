"""Betas sectoriels de Damodaran (NYU Stern) — benchmark de fiabilite des betas.

Damodaran publie chaque debut d'annee, par secteur d'activite et par region, le beta
desendette ("unlevered beta") d'un large echantillon de societes cotees. On l'utilise
comme **etalon externe** : le beta desendette de notre echantillon de comparables doit
rester dans l'ordre de grandeur du secteur Damodaran correspondant.

Donnees : un snapshot CSV embarque (`data/damodaran_betas.csv`), rafraichi a la demande
depuis les fichiers .xls publics (annuels). Le runtime ne lit que le CSV (stdlib `csv`) ;
le rafraichissement (parsing .xls) demande pandas + xlrd (import paresseux, outil d'ops).

    python -m comparables.damodaran refresh    # retelecharge + reconstruit le CSV
    python -m comparables.damodaran status      # date du snapshot + nb d'industries
"""
from __future__ import annotations

import csv
import difflib
import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

_DATA_CSV = Path(__file__).parent / "data" / "damodaran_betas.csv"

# Region -> fichier .xls public (feuille "Industry Averages"). On charge "Global" par
# defaut (le plus representatif d'un echantillon international) ; les autres restent
# disponibles pour un futur selecteur de region.
_SOURCE_XLS = {
    "Global": "https://pages.stern.nyu.edu/~adamodar/pc/datasets/betaGlobal.xls",
    "Europe": "https://pages.stern.nyu.edu/~adamodar/pc/datasets/betaEurope.xls",
    "US": "https://pages.stern.nyu.edu/~adamodar/pc/datasets/betas.xls",
    "Emerging": "https://pages.stern.nyu.edu/~adamodar/pc/datasets/betaemerg.xls",
}
_DEFAULT_REGION = "Global"

# Lignes de total a ignorer dans la feuille Damodaran.
_SKIP_INDUSTRIES = {"grand total", "total market", "total market (without financials)"}

# Champs numeriques du CSV (le reste est texte).
_FLOAT_FIELDS = ("beta", "de_ratio", "tax_rate", "unlevered_beta", "unlevered_beta_cash")

# Correspondances industrie Yahoo -> secteur Damodaran (taxonomies differentes). Les cles
# sont normalisees au chargement (_ALIAS) : ecrire ici le libelle Yahoo tel quel. La VALEUR
# doit etre un libelle Damodaran EXACT (cf. data/damodaran_betas.csv). Tout ce qui n'est pas
# alias ni nom identique passe par un appariement flou CONSERVATEUR (cutoff 0,8).
_RAW_ALIAS = {
    # --- Luxe / habillement / distribution
    "Luxury Goods": "Apparel", "Apparel Manufacturing": "Apparel",
    "Footwear & Accessories": "Apparel", "Textile Manufacturing": "Apparel",
    "Apparel Retail": "Retail (Special Lines)", "Specialty Retail": "Retail (Special Lines)",
    "Internet Retail": "Retail (Special Lines)", "Department Stores": "Retail (General)",
    "Discount Stores": "Retail (General)", "Home Improvement Retail": "Retail (Building Supply)",
    "Grocery Stores": "Retail (Grocery and Food)", "Auto & Truck Dealerships": "Retail (Automotive)",
    "Industrial Distribution": "Retail (Distributors)",
    # --- Automobile
    "Auto Manufacturers": "Auto & Truck", "Recreational Vehicles": "Auto & Truck",
    "Tires & Rubber": "Rubber& Tires",
    # --- Pharma / sante
    "Drug Manufacturers - General": "Drugs (Pharmaceutical)",
    "Drug Manufacturers - Specialty & Generic": "Drugs (Pharmaceutical)",
    "Biotechnology": "Drugs (Biotechnology)",
    "Medical Devices": "Healthcare Products", "Medical Instruments & Supplies": "Healthcare Products",
    "Diagnostics & Research": "Healthcare Products",
    "Medical Care Facilities": "Hospitals/Healthcare Facilities",
    "Medical Distribution": "Healthcare Support Services",
    "Healthcare Plans": "Healthcare Support Services",
    "Health Information Services": "Heathcare Information and Technology",
    # --- Banques / finance / assurance
    "Banks - Regional": "Banks (Regional)", "Banks - Diversified": "Bank (Money Center)",
    "Capital Markets": "Brokerage & Investment Banking",
    "Financial Data & Stock Exchanges": "Brokerage & Investment Banking",
    "Asset Management": "Investments & Asset Management",
    "Credit Services": "Financial Svcs. (Non-bank & Insurance)",
    "Mortgage Finance": "Financial Svcs. (Non-bank & Insurance)",
    "Insurance - Life": "Insurance (Life)",
    "Insurance - Property & Casualty": "Insurance (Prop/Cas.)",
    "Insurance - Specialty": "Insurance (Prop/Cas.)",
    "Insurance - Diversified": "Insurance (General)", "Insurance Brokers": "Insurance (General)",
    "Insurance - Reinsurance": "Reinsurance",
    # --- Boissons / alimentaire / tabac
    "Beverages - Brewers": "Beverage (Alcoholic)",
    "Beverages - Wineries & Distilleries": "Beverage (Alcoholic)",
    "Beverages - Non-Alcoholic": "Beverage (Soft)",
    "Packaged Foods": "Food Processing", "Confectioners": "Food Processing",
    "Food Distribution": "Food Wholesalers", "Farm Products": "Farming/Agriculture",
    "Agricultural Inputs": "Farming/Agriculture",
    "Household & Personal Products": "Household Products",
    # --- Energie
    "Oil & Gas Integrated": "Oil/Gas (Integrated)",
    "Oil & Gas E&P": "Oil/Gas (Production and Exploration)",
    "Oil & Gas Midstream": "Oil/Gas Distribution",
    "Oil & Gas Refining & Marketing": "Oil/Gas (Integrated)",
    "Oil & Gas Equipment & Services": "Oilfield Svcs/Equip.",
    "Oil & Gas Drilling": "Oilfield Svcs/Equip.",
    "Thermal Coal": "Coal & Related Energy", "Coking Coal": "Coal & Related Energy",
    "Uranium": "Coal & Related Energy",
    "Solar": "Green & Renewable Energy", "Utilities - Renewable": "Green & Renewable Energy",
    # --- Materiaux (Damodaran separe Precious Metals des metaux de base)
    "Aluminum": "Metals & Mining", "Copper": "Metals & Mining",
    "Other Industrial Metals & Mining": "Metals & Mining",
    "Gold": "Precious Metals", "Silver": "Precious Metals",
    "Other Precious Metals & Mining": "Precious Metals",
    "Building Products & Equipment": "Building Materials",
    "Specialty Chemicals": "Chemical (Specialty)", "Chemicals": "Chemical (Basic)",
    "Paper & Paper Products": "Paper/Forest Products",
    "Lumber & Wood Production": "Paper/Forest Products",
    "Packaging & Containers": "Packaging & Container",
    # --- Industrie / transport
    "Specialty Industrial Machinery": "Machinery",
    "Farm & Heavy Construction Machinery": "Machinery", "Tools & Accessories": "Machinery",
    "Electrical Equipment & Parts": "Electrical Equipment",
    "Engineering & Construction": "Engineering/Construction",
    "Infrastructure Operations": "Engineering/Construction",
    "Airlines": "Air Transport", "Airports & Air Services": "Air Transport",
    "Integrated Freight & Logistics": "Transportation", "Railroads": "Transportation (Railroads)",
    "Marine Shipping": "Shipbuilding & Marine",
    "Waste Management": "Environmental & Waste Services",
    "Pollution & Treatment Controls": "Environmental & Waste Services",
    "Staffing & Employment Services": "Business & Consumer Services",
    "Consulting Services": "Business & Consumer Services",
    "Security & Protection Services": "Business & Consumer Services",
    "Rental & Leasing Services": "Business & Consumer Services",
    # --- Tech / communication
    "Semiconductors": "Semiconductor",
    "Semiconductor Equipment & Materials": "Semiconductor Equip",
    "Software - Application": "Software (System & Application)",
    "Software - Infrastructure": "Software (System & Application)",
    "Information Technology Services": "Computer Services",
    "Computer Hardware": "Computers/Peripherals",
    "Consumer Electronics": "Electronics (Consumer & Office)",
    "Electronic Components": "Electronics (General)",
    "Scientific & Technical Instruments": "Electronics (General)",
    "Communication Equipment": "Telecom. Equipment", "Telecom Services": "Telecom. Services",
    "Internet Content & Information": "Software (Internet)",
    "Electronic Gaming & Multimedia": "Software (Entertainment)",
    "Advertising Agencies": "Advertising", "Publishing": "Publishing & Newspapers",
    # --- Immobilier (toutes les REIT -> R.E.I.T.)
    "REIT - Retail": "R.E.I.T.", "REIT - Office": "R.E.I.T.", "REIT - Industrial": "R.E.I.T.",
    "REIT - Residential": "R.E.I.T.", "REIT - Healthcare Facilities": "R.E.I.T.",
    "REIT - Hotel & Motel": "R.E.I.T.", "REIT - Mortgage": "R.E.I.T.",
    "REIT - Specialty": "R.E.I.T.", "REIT - Diversified": "R.E.I.T.",
    "Real Estate Services": "Real Estate (Operations & Services)",
    "Real Estate - Development": "Real Estate (Development)",
    "Real Estate - Diversified": "Real Estate (General/Diversified)",
    "Residential Construction": "Homebuilding",
    # --- Consommation / loisirs / utilities
    "Restaurants": "Restaurant/Dining", "Lodging": "Hotel/Gaming",
    "Resorts & Casinos": "Hotel/Gaming", "Gambling": "Hotel/Gaming",
    "Travel Services": "Recreation", "Leisure": "Recreation",
    "Furnishings, Fixtures & Appliances": "Furn/Home Furnishings",
    "Utilities - Regulated Electric": "Utility (General)",
    "Utilities - Regulated Gas": "Utility (General)",
    "Utilities - Diversified": "Utility (General)",
    "Utilities - Independent Power Producers": "Power",
    "Utilities - Regulated Water": "Utility (Water)",
    "Education & Training Services": "Education",
}


# --------------------------------------------------------------------------- lecture

@lru_cache(maxsize=1)
def load_industries() -> list[dict]:
    """Snapshot embarque : liste de dicts {region, industry, n_firms, beta, de_ratio,
    tax_rate, unlevered_beta, unlevered_beta_cash, as_of}. Vide si CSV absent."""
    if not _DATA_CSV.exists():
        return []
    out: list[dict] = []
    with open(_DATA_CSV, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rec = dict(row)
            rec["n_firms"] = int(row["n_firms"]) if row.get("n_firms") else None
            for k in _FLOAT_FIELDS:
                rec[k] = float(row[k]) if row.get(k) not in (None, "") else None
            out.append(rec)
    return out


def as_of(region: str = _DEFAULT_REGION) -> Optional[str]:
    """Date de mise a jour du snapshot pour la region (ou None)."""
    for r in load_industries():
        if r["region"] == region:
            return r.get("as_of")
    return None


def industries(region: str = _DEFAULT_REGION) -> list[dict]:
    """Industries Damodaran d'une region, triees par libelle."""
    rows = [r for r in load_industries() if r["region"] == region]
    return sorted(rows, key=lambda r: r["industry"])


def lookup(industry: str, region: str = _DEFAULT_REGION) -> Optional[dict]:
    """Benchmark Damodaran d'une industrie (insensible a la casse/espaces), ou None."""
    target = _norm(industry)
    for r in industries(region):
        if _norm(r["industry"]) == target:
            return r
    return None


# ------------------------------------------------------------------- correspondance

def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


# Alias a cles NORMALISEES (corrige le bug : « Drug Manufacturers - General » et sa
# normalisation « drug manufacturers general » doivent matcher).
_ALIAS = {_norm(k): v for k, v in _RAW_ALIAS.items()}


def _best_industry(label: str, region: str) -> Optional[str]:
    """Industrie Damodaran la plus proche d'un libelle Yahoo : alias -> nom identique ->
    ressemblance CONSERVATRICE (cutoff 0,8). Mieux vaut None qu'un mauvais rattachement
    (ex. « REIT - Retail » ne doit JAMAIS tomber sur « Precious Metals »)."""
    if not label:
        return None
    norm = _norm(label)
    if norm in _ALIAS:
        return _ALIAS[norm]
    names = [r["industry"] for r in industries(region)]
    by_norm = {_norm(n): n for n in names}
    if norm in by_norm:
        return by_norm[norm]
    match = difflib.get_close_matches(norm, list(by_norm), n=1, cutoff=0.8)
    return by_norm[match[0]] if match else None


def suggest_industry(yahoo_industries: list[Optional[str]],
                     region: str = _DEFAULT_REGION) -> Optional[str]:
    """Industrie Damodaran suggeree pour un echantillon : vote majoritaire des industries
    Yahoo des societes (mappees vers Damodaran). None si rien ne se rattache."""
    votes: dict[str, int] = {}
    for lab in yahoo_industries:
        dam = _best_industry(lab or "", region)
        if dam:
            votes[dam] = votes.get(dam, 0) + 1
    if not votes:
        return None
    return max(votes, key=lambda k: (votes[k], k))


# ----------------------------------------------------------------- rafraichissement

def _parse_xls(content: bytes, region: str) -> list[dict]:
    """Parse la feuille 'Industry Averages' d'un .xls Damodaran -> lignes du CSV."""
    import io

    import pandas as pd  # import paresseux : pandas + xlrd seulement au refresh

    raw = pd.read_excel(io.BytesIO(content), sheet_name="Industry Averages", header=None)
    hdr = next(i for i in range(len(raw)) if str(raw.iloc[i, 0]).strip() == "Industry Name")
    updated = next((str(raw.iloc[i, 1])[:10] for i in range(hdr)
                    if str(raw.iloc[i, 0]).strip().lower().startswith("date updated")), "")
    df = pd.read_excel(io.BytesIO(content), sheet_name="Industry Averages", header=hdr)
    df.columns = [str(c).strip() for c in df.columns]
    col = {
        "industry": "Industry Name", "n_firms": "Number of firms", "beta": "Beta",
        "de_ratio": "D/E Ratio", "tax_rate": "Effective Tax rate",
        "unlevered_beta": "Unlevered beta",
        "unlevered_beta_cash": "Unlevered beta corrected for cash",
    }
    rows = []
    for _, r in df.iterrows():
        name = str(r.get(col["industry"], "")).strip()
        if not name or name.lower() in _SKIP_INDUSTRIES or name == "nan":
            continue

        def num(key):
            v = r.get(col[key])
            return None if pd.isna(v) else float(v)

        rows.append({
            "region": region, "industry": name,
            "n_firms": None if pd.isna(r.get(col["n_firms"])) else int(r.get(col["n_firms"])),
            "beta": num("beta"), "de_ratio": num("de_ratio"), "tax_rate": num("tax_rate"),
            "unlevered_beta": num("unlevered_beta"),
            "unlevered_beta_cash": num("unlevered_beta_cash"),
            "as_of": updated,
        })
    return rows


def refresh(regions: tuple[str, ...] = (_DEFAULT_REGION,)) -> int:
    """Retelecharge les .xls Damodaran et reecrit le snapshot CSV. Renvoie le nb de lignes."""
    import requests

    all_rows: list[dict] = []
    for region in regions:
        url = _SOURCE_XLS[region]
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
        resp.raise_for_status()
        all_rows.extend(_parse_xls(resp.content, region))
    fields = ["region", "industry", "n_firms", "beta", "de_ratio", "tax_rate",
              "unlevered_beta", "unlevered_beta_cash", "as_of"]
    _DATA_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(_DATA_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(all_rows)
    load_industries.cache_clear()
    return len(all_rows)


def _main(argv: Optional[list[str]] = None) -> None:
    import argparse

    p = argparse.ArgumentParser(description="Betas sectoriels Damodaran (snapshot local).")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("refresh", help="retelecharge et reconstruit le snapshot CSV")
    r.add_argument("regions", nargs="*", default=[_DEFAULT_REGION],
                   help=f"regions a charger (defaut: {_DEFAULT_REGION}) parmi {list(_SOURCE_XLS)}")
    sub.add_parser("status", help="date du snapshot + nb d'industries")
    args = p.parse_args(argv)

    if args.cmd == "refresh":
        n = refresh(tuple(args.regions))
        print(f"Snapshot Damodaran reconstruit : {n} lignes -> {_DATA_CSV}")
    else:
        rows = load_industries()
        if not rows:
            print("Aucun snapshot. Lancer : python -m comparables.damodaran refresh")
            return
        regions = sorted({r["region"] for r in rows})
        for reg in regions:
            n = len([r for r in rows if r["region"] == reg])
            print(f"  {reg:10s} : {n:3d} industries (au {as_of(reg)})")


if __name__ == "__main__":
    _main()
