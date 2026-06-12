"""Référentiels open data répliqués en local (SQLite) : identité Sirene + ratios INPI/BCE.

Le pipeline cessions interroge ces deux jeux par SIREN. En appels API unitaires, une
recherche balaye jusqu'à ~1 200 annonces sous limite de débit (7 req/s côté Recherche
d'entreprises) -> plusieurs minutes. Répliqués en local, les lookups sont instantanés,
sans quota ni 429. Sources gratuites, licence ouverte :

- Sirene (INSEE, stock des unités légales, data.gouv) : SIREN -> dénomination + NAF ;
- ratios_inpi_bce (data.economie.gouv) : SIREN -> CA / EBE / EBIT par exercice
  (comptes PUBLICS uniquement — les confidentiels restent absents, comme via l'API) ;
- ventes BODACC (DILA, dataset annonces-commerciales) : TOUTES les cessions de fonds
  avec un prix extractible depuis 2008 (~115 k annonces, ~141 Mo source). Jointe à
  Sirene, la recherche par activité devient une requête locale exhaustive — la
  pagination de l'API (plafond ~10 000) et les balayages par mots-clés disparaissent.

Rafraîchissement (mensuel conseillé, fichiers volumineux ~Go) :
    python -m comparables.fr.referentiels refresh [sirene|ratios|all]

Sans base locale, le pipeline retombe automatiquement sur les API unitaires : ce module
est une accélération, jamais un prérequis.
"""
from __future__ import annotations
import csv
import io
import json
import logging
import sqlite3
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

import requests

from comparables.config import settings
from comparables.fr.parsing import cedant_siren, extract_price

logger = logging.getLogger(__name__)

# URL stable data.gouv (ressource « StockUniteLegale » du jeu Sirene INSEE) : redirige
# vers le fichier du mois. L'ancien hébergement files.data.gouv.fr/insee-sirene est mort.
SIRENE_URL = "https://www.data.gouv.fr/fr/datasets/r/825f4199-cadd-486c-ac46-a65a8ea1a047"
RATIOS_EXPORT_URL = ("https://data.economie.gouv.fr/api/explore/v2.1"
                     "/catalog/datasets/ratios_inpi_bce/exports/csv")
_RATIOS_FIELDS = ("siren", "date_cloture_exercice", "chiffre_d_affaires", "ebe", "ebit")
BODACC_EXPORT_URL = ("https://bodacc-datadila.opendatasoft.com/api/explore/v2.1"
                     "/catalog/datasets/annonces-commerciales/exports/csv")
# Même périmètre que bodacc.fetch_cessions : ventes de fonds portant un prix.
_BODACC_WHERE = ("familleavis = 'vente' and search(acte, 'fonds') "
                 "and (search(acte, 'prix') or search(acte, 'moyennant'))")
_BODACC_FIELDS = ("registre", "commercant", "ville", "numerodepartement",
                  "dateparution", "acte", "url_complete", "typeavis")
_HEADERS = {"User-Agent": "ncf-comparables/0.1 (interne)"}
_BATCH = 50_000


def _db_path(db_path: Optional[str]) -> str:
    return db_path if db_path is not None else settings.referentiels_db_path


def _connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = _db_path(db_path)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS unites_legales (
            siren TEXT PRIMARY KEY, nom TEXT, naf TEXT
        );
        CREATE TABLE IF NOT EXISTS ratios (
            siren TEXT NOT NULL, date_cloture TEXT NOT NULL,
            ca REAL, ebe REAL, ebit REAL,
            PRIMARY KEY (siren, date_cloture)
        );
        CREATE TABLE IF NOT EXISTS ventes (
            siren TEXT, nom TEXT, ville TEXT, departement TEXT,
            date TEXT NOT NULL, categorie TEXT, prix REAL NOT NULL,
            descriptif TEXT, url TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_ventes_date ON ventes(date);
        CREATE INDEX IF NOT EXISTS idx_ventes_siren ON ventes(siren);
        CREATE TABLE IF NOT EXISTS referentiel_meta (
            table_name TEXT PRIMARY KEY, refreshed_at TEXT NOT NULL, n_rows INTEGER NOT NULL
        );
        """
    )
    return conn


def _connect_ro(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Connexion lecture seule, timeout court : ne bloque jamais un rafraîchissement
    en cours (gros INSERT) et ne pose aucun verrou d'écriture (pas de DDL)."""
    return sqlite3.connect(f"file:{_db_path(db_path)}?mode=ro", uri=True, timeout=1.0)


def _meta(conn: sqlite3.Connection, table: str) -> Optional[tuple[str, int]]:
    row = conn.execute("SELECT refreshed_at, n_rows FROM referentiel_meta "
                       "WHERE table_name = ?", (table,)).fetchone()
    return (row[0], row[1]) if row else None


def available(table: str, db_path: Optional[str] = None) -> bool:
    """La table locale est-elle chargée ET lisible ? False si la base est absente,
    verrouillée (rafraîchissement en cours) ou incomplète -> repli API du pipeline."""
    if not Path(_db_path(db_path)).exists():
        return False
    try:
        conn = _connect_ro(db_path)
        try:
            meta = _meta(conn, table)
        finally:
            conn.close()
    except sqlite3.Error:
        return False
    return bool(meta and meta[1] > 0)


def status(db_path: Optional[str] = None) -> dict:
    """État des référentiels : {table: {refreshed_at, n_rows}} (vide si non chargé)."""
    if not Path(_db_path(db_path)).exists():
        return {}
    try:
        conn = _connect_ro(db_path)
        try:
            rows = conn.execute(
                "SELECT table_name, refreshed_at, n_rows FROM referentiel_meta").fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return {}
    return {r[0]: {"refreshed_at": r[1], "n_rows": r[2]} for r in rows}


# --- Lookups (formes de retour identiques aux adaptateurs API qu'ils remplacent) ---
# Ne lèvent JAMAIS : None signale « base indisponible » -> le pipeline retombe sur l'API.

def lookup_company(siren: str, db_path: Optional[str] = None) -> Optional[dict]:
    """SIREN -> {nom, naf, ca, ca_annee} (même forme que entreprises.fetch_company).
    None si SIREN inconnu OU base indisponible (le pipeline retombe alors sur l'API)."""
    if not siren:
        return None
    try:
        conn = _connect_ro(db_path)
        try:
            row = conn.execute("SELECT nom, naf FROM unites_legales WHERE siren = ?",
                               (siren,)).fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        return None
    if row is None:
        return None
    return {"nom": row[0], "naf": row[1], "ca": None, "ca_annee": None}


def lookup_financials(siren: str, db_path: Optional[str] = None) -> Optional[list[dict]]:
    """SIREN -> exercices, du plus récent au plus ancien (même forme que finances_inpi).

    [] = SIREN absent du jeu (comptes confidentiels) ; None = base indisponible
    (verrouillée/absente) -> le pipeline doit retomber sur l'API."""
    if not siren:
        return []
    try:
        conn = _connect_ro(db_path)
        try:
            rows = conn.execute(
                "SELECT date_cloture, ca, ebe, ebit FROM ratios WHERE siren = ? "
                "ORDER BY date_cloture DESC", (siren,)).fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return None
    return [{"date_cloture_exercice": r[0], "chiffre_d_affaires": r[1],
             "ebe": r[2], "ebit": r[3]} for r in rows]


# --- Chargement (séparé du téléchargement : testable sans réseau) ---

def _swap_in(conn: sqlite3.Connection, table: str, n_rows: int) -> None:
    conn.execute("INSERT OR REPLACE INTO referentiel_meta VALUES (?, ?, ?)",
                 (table, datetime.now(timezone.utc).isoformat(timespec="seconds"), n_rows))
    conn.commit()


def load_sirene_rows(rows: Iterable[dict], db_path: Optional[str] = None) -> int:
    """Charge des lignes du stock Sirene (dictées par le CSV INSEE). Remplace la table."""
    conn = _connect(db_path)
    try:
        conn.execute("DELETE FROM unites_legales")
        batch: list[tuple] = []
        n = 0
        for row in rows:
            siren = (row.get("siren") or "").strip()
            if not siren:
                continue
            # Dénomination (personnes morales) sinon nom + prénom (personnes physiques).
            nom = (row.get("denominationUniteLegale") or "").strip()
            if not nom:
                nom = " ".join(p for p in ((row.get("prenom1UniteLegale") or "").strip(),
                                           (row.get("nomUniteLegale") or "").strip()) if p)
            naf = (row.get("activitePrincipaleUniteLegale") or "").strip() or None
            batch.append((siren, nom or None, naf))
            if len(batch) >= _BATCH:
                conn.executemany("INSERT OR REPLACE INTO unites_legales VALUES (?, ?, ?)",
                                 batch)
                n += len(batch)
                batch.clear()
        if batch:
            conn.executemany("INSERT OR REPLACE INTO unites_legales VALUES (?, ?, ?)", batch)
            n += len(batch)
        _swap_in(conn, "unites_legales", n)
        return n
    finally:
        conn.close()


def _to_float(raw: Optional[str]) -> Optional[float]:
    try:
        return float(raw) if raw not in (None, "") else None
    except ValueError:
        return None


def load_ratios_rows(rows: Iterable[dict], db_path: Optional[str] = None) -> int:
    """Charge des lignes du jeu ratios_inpi_bce. Remplace la table."""
    conn = _connect(db_path)
    try:
        conn.execute("DELETE FROM ratios")
        batch: list[tuple] = []
        n = 0
        for row in rows:
            siren = (row.get("siren") or "").strip()
            cloture = (row.get("date_cloture_exercice") or "").strip()
            if not siren or not cloture:
                continue
            batch.append((siren, cloture, _to_float(row.get("chiffre_d_affaires")),
                          _to_float(row.get("ebe")), _to_float(row.get("ebit"))))
            if len(batch) >= _BATCH:
                conn.executemany("INSERT OR REPLACE INTO ratios VALUES (?, ?, ?, ?, ?)",
                                 batch)
                n += len(batch)
                batch.clear()
        if batch:
            conn.executemany("INSERT OR REPLACE INTO ratios VALUES (?, ?, ?, ?, ?)", batch)
            n += len(batch)
        _swap_in(conn, "ratios", n)
        return n
    finally:
        conn.close()


def load_ventes_rows(rows: Iterable[dict], db_path: Optional[str] = None) -> int:
    """Charge les ventes BODACC (lignes de l'export CSV annonces-commerciales).

    Ne garde que les annonces non rectificatives dont un prix est extractible.
    Le SIREN du cédant est résolu au chargement (registre + descriptif) ; les
    republications sont dédupliquées (même cédant + même prix + même année de
    parution — les additifs paraissent à quelques jours d'écart). Remplace la table."""
    conn = _connect(db_path)
    try:
        conn.execute("DELETE FROM ventes")
        seen: set[tuple] = set()
        batch: list[tuple] = []
        n = 0
        for row in rows:
            typeavis = (row.get("typeavis") or "").strip().lower()
            if typeavis.startswith(("rectificatif", "annulation")):
                continue
            try:
                acte = json.loads(row.get("acte") or "{}")
            except json.JSONDecodeError:
                acte = {}
            if not isinstance(acte, dict):
                acte = {}
            descriptif = acte.get("descriptif") or ""
            prix = extract_price(descriptif)
            if prix is None:
                continue
            siren = cedant_siren(row.get("registre"), descriptif)
            date = (row.get("dateparution") or "").strip()
            key = (siren or row.get("commercant"), prix, date[:4])
            if key in seen:
                continue
            seen.add(key)
            vente = acte.get("vente") or {}
            categorie = vente.get("categorieVente") if isinstance(vente, dict) else None
            batch.append((siren, row.get("commercant"), row.get("ville"),
                          row.get("numerodepartement"), date, categorie, prix,
                          descriptif, row.get("url_complete")))
            if len(batch) >= _BATCH:
                conn.executemany(
                    "INSERT INTO ventes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", batch)
                n += len(batch)
                batch.clear()
        if batch:
            conn.executemany("INSERT INTO ventes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", batch)
            n += len(batch)
        _swap_in(conn, "ventes", n)
        return n
    finally:
        conn.close()


def lookup_ventes(since: str, departement: Optional[str] = None,
                  db_path: Optional[str] = None) -> Optional[list[dict]]:
    """Ventes locales (prix déjà extrait) depuis `since`, jointes à l'identité Sirene
    (nom officiel + NAF du cédant), de la plus récente à la plus ancienne.

    Colonnes légères (sans descriptif : inutile après extraction du prix).
    None si la base est indisponible (verrouillée/absente) -> repli sur l'API."""
    try:
        conn = _connect_ro(db_path)
        try:
            sql = ("SELECT v.siren, v.nom, v.ville, v.departement, v.date, v.categorie, "
                   "v.prix, v.url, u.nom, u.naf FROM ventes v "
                   "LEFT JOIN unites_legales u ON u.siren = v.siren "
                   "WHERE v.date >= ?")
            params: list = [since]
            if departement:
                sql += " AND v.departement = ?"
                params.append(departement)
            sql += " ORDER BY v.date DESC"
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return None
    return [{"siren": r[0], "nom_bodacc": r[1], "ville": r[2], "departement": r[3],
             "date": r[4], "categorie": r[5], "prix": r[6], "url": r[7],
             "nom_officiel": r[8], "naf": r[9]} for r in rows]


# --- Téléchargement + rafraîchissement (CLI ; fichiers volumineux, streaming) ---

def refresh_sirene(db_path: Optional[str] = None) -> int:
    """Télécharge le stock Sirene (~300 Mo zippé) et recharge la table locale."""
    logger.info("Téléchargement Sirene : %s", SIRENE_URL)
    resp = requests.get(SIRENE_URL, headers=_HEADERS, stream=True, timeout=120)
    resp.raise_for_status()
    buf = io.BytesIO()
    for chunk in resp.iter_content(chunk_size=1 << 20):
        buf.write(chunk)
    buf.seek(0)
    with zipfile.ZipFile(buf) as zf:
        name = next(n for n in zf.namelist() if n.endswith(".csv"))
        with zf.open(name) as f:
            reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"))
            n = load_sirene_rows(reader, db_path)
    logger.info("Sirene chargé : %s unités légales", f"{n:,}")
    return n


def refresh_ratios(db_path: Optional[str] = None) -> int:
    """Télécharge l'export CSV complet des ratios INPI/BCE et recharge la table locale."""
    params = {"select": ",".join(_RATIOS_FIELDS), "delimiter": ";"}
    logger.info("Téléchargement ratios INPI/BCE : %s", RATIOS_EXPORT_URL)
    resp = requests.get(RATIOS_EXPORT_URL, headers=_HEADERS, params=params,
                        stream=True, timeout=120)
    resp.raise_for_status()
    resp.raw.decode_content = True
    reader = csv.DictReader(io.TextIOWrapper(resp.raw, encoding="utf-8-sig"), delimiter=";")
    n = load_ratios_rows(reader, db_path)
    logger.info("Ratios chargés : %s exercices", f"{n:,}")
    return n


_BODACC_RECORDS_URL = ("https://bodacc-datadila.opendatasoft.com/api/explore/v2.1"
                       "/catalog/datasets/annonces-commerciales/records")
_BODACC_DEBUT = 2008                        # première parution du dataset


def _bodacc_year(year: int) -> list[dict]:
    """Lignes CSV d'une année de ventes, avec VÉRIFICATION du compte : l'export complet
    (~115 k lignes) se tronque silencieusement en cours de flux — les tranches annuelles
    (~5 k lignes) sont fiables, et on contrôle reçu vs attendu (retry sinon)."""
    where = (_BODACC_WHERE + f" and dateparution >= date'{year}-01-01'"
             f" and dateparution < date'{year + 1}-01-01'")
    resp = requests.get(_BODACC_RECORDS_URL, headers=_HEADERS, timeout=60,
                        params={"where": where, "limit": 0})
    resp.raise_for_status()
    attendu = int(resp.json().get("total_count", 0))
    if attendu == 0:
        return []
    rows: list[dict] = []
    for attempt in (1, 2, 3):
        try:
            resp = requests.get(BODACC_EXPORT_URL, headers=_HEADERS, stream=True,
                                timeout=300,
                                params={"where": where, "select": ",".join(_BODACC_FIELDS),
                                        "delimiter": ";"})
            resp.raise_for_status()
            resp.raw.decode_content = True
            reader = csv.DictReader(io.TextIOWrapper(resp.raw, encoding="utf-8-sig"),
                                    delimiter=";")
            rows = list(reader)
        except (requests.RequestException, OSError, csv.Error) as exc:
            # Coupure en cours de flux (ChunkedEncodingError…) : même traitement
            # qu'une troncature -> nouvelle tentative, sinon on abandonne PROPREMENT
            # (le chargement est tout-ou-rien, la table précédente reste intacte).
            logger.warning("BODACC %s : flux interrompu (%s), tentative %s",
                           year, exc, attempt)
            rows = []
            continue
        # Tolérance minime : des annonces peuvent paraître entre le comptage et l'export.
        if len(rows) >= attendu - 5:
            logger.info("BODACC %s : %s annonces", year, f"{len(rows):,}")
            return rows
        logger.warning("BODACC %s : export tronqué (%s/%s), tentative %s",
                       year, len(rows), attendu, attempt)
    raise RuntimeError(f"Export BODACC {year} tronqué ({len(rows)}/{attendu} lignes) "
                       "après 3 tentatives.")


def refresh_bodacc(db_path: Optional[str] = None) -> int:
    """Télécharge les ventes BODACC (par tranches annuelles vérifiées) et recharge la table.

    Tout-ou-rien : un échec laisse la table précédente intacte (la transaction du
    chargement n'est commitée qu'à la fin, cf. load_ventes_rows)."""
    csv.field_size_limit(10_000_000)        # certains actes (descriptif) sont très longs
    annee_max = datetime.now(timezone.utc).year
    rows = (row for year in range(_BODACC_DEBUT, annee_max + 1)
            for row in _bodacc_year(year))
    n = load_ventes_rows(rows, db_path)
    logger.info("Ventes chargées : %s annonces avec prix", f"{n:,}")
    return n


def main(argv: Optional[list[str]] = None) -> int:
    """CLI : `refresh [sirene|ratios|bodacc|all]` (défaut all) ou `status`."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = list(sys.argv[1:] if argv is None else argv)
    cmd = args[0] if args else "status"
    if cmd == "status":
        st = status()
        if not st:
            print("Aucun référentiel local chargé "
                  "(python -m comparables.fr.referentiels refresh).")
        for table, info in st.items():
            print(f"{table} : {info['n_rows']:,} lignes (rafraîchi {info['refreshed_at']})")
        return 0
    if cmd == "refresh":
        target = args[1] if len(args) > 1 else "all"
        if target in ("sirene", "all"):
            refresh_sirene()
        if target in ("ratios", "all"):
            refresh_ratios()
        if target in ("bodacc", "all"):
            refresh_bodacc()
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
