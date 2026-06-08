"""Base SQLite LOCALE des cessions FR (ingestion en masse) — requêtes instantanées, hors quota.

Trois tables : `cessions` (prix + SIREN, depuis BODACC), `companies` (identité/NAF/nb étab.,
depuis Recherche d'entreprises) et `financials` (CA/EBE/EBIT par exercice, depuis Ratios INPI/BCE).
L'ingestion (cf. fr.ingest) remplit ces tables ; `load_cessions` rejoue le calcul prix/CA et
prix/EBE hors-ligne (exercice calé sur la date de cession), avec filtres NAF / activité / dept.

Sans I/O réseau ni Streamlit ; chemin de base configurable (settings.cessions_db_path) et
surchargeable par argument (tests). Conventions alignées sur comparables.store.
"""
from __future__ import annotations
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from comparables.config import settings
from comparables.fr import finances_inpi
from comparables.fr.models import Cession
from comparables.fr.parsing import compute_pct_ca, compute_mult_ebe, naf_matches

_CESSION_COLS = ["ann_id", "siren", "nom", "ville", "departement", "date", "categorie",
                 "prix", "descriptif", "url"]


def _db_path(db_path: Optional[str]) -> str:
    return db_path if db_path is not None else settings.cessions_db_path


def _connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = _db_path(db_path)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    _init(conn)
    return conn


def _init(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS cessions (
            ann_id      TEXT PRIMARY KEY,
            siren       TEXT,
            nom         TEXT,
            ville       TEXT,
            departement TEXT,
            date        TEXT,
            categorie   TEXT,
            prix        REAL,
            descriptif  TEXT,
            url         TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_cessions_siren ON cessions(siren);
        CREATE INDEX IF NOT EXISTS idx_cessions_date  ON cessions(date);
        CREATE TABLE IF NOT EXISTS companies (
            siren             TEXT PRIMARY KEY,
            nom               TEXT,
            naf               TEXT,
            nb_etablissements INTEGER,
            fetched_at        TEXT
        );
        CREATE TABLE IF NOT EXISTS financials (
            siren                  TEXT NOT NULL,
            date_cloture_exercice  TEXT NOT NULL,
            chiffre_d_affaires     REAL,
            ebe                    REAL,
            ebit                   REAL,
            resultat_net           REAL,
            fetched_at             TEXT,
            PRIMARY KEY (siren, date_cloture_exercice)
        );
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
        """
    )
    conn.commit()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _ann_id(c: Cession) -> str:
    """Identifiant stable d'une cession (clé de dédup) ; replie sur siren|date|prix si absent."""
    return c.ann_id or f"{c.siren}|{c.date}|{int(c.prix) if c.prix else 0}"


def upsert_cessions(cessions: list[Cession], db_path: Optional[str] = None) -> int:
    """Insère/met à jour des cessions (dédupliquées par ann_id). Renvoie le nb traité."""
    conn = _connect(db_path)
    try:
        conn.executemany(
            f"INSERT OR REPLACE INTO cessions ({','.join(_CESSION_COLS)}) "
            f"VALUES ({','.join('?' * len(_CESSION_COLS))})",
            [(_ann_id(c), c.siren, c.nom, c.ville, c.departement, c.date, c.categorie,
              c.prix, c.descriptif, c.url) for c in cessions],
        )
        conn.commit()
        return len(cessions)
    finally:
        conn.close()


def upsert_company(siren: str, info: Optional[dict], db_path: Optional[str] = None) -> None:
    """Enregistre l'identité d'un SIREN (même si `info` est None -> ligne marquée, évite de re-fetch)."""
    info = info or {}
    conn = _connect(db_path)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO companies (siren, nom, naf, nb_etablissements, fetched_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (siren, info.get("nom"), info.get("naf"), info.get("nb_etablissements"), _now()),
        )
        conn.commit()
    finally:
        conn.close()


def upsert_financials(siren: str, rows: list[dict], db_path: Optional[str] = None) -> None:
    """Enregistre les exercices financiers d'un SIREN (Ratios INPI/BCE)."""
    conn = _connect(db_path)
    try:
        now = _now()
        conn.executemany(
            "INSERT OR REPLACE INTO financials (siren, date_cloture_exercice, "
            "chiffre_d_affaires, ebe, ebit, resultat_net, fetched_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(siren, r.get("date_cloture_exercice"), r.get("chiffre_d_affaires"), r.get("ebe"),
              r.get("ebit"), r.get("resultat_net"), now)
             for r in rows if r.get("date_cloture_exercice")],
        )
        conn.commit()
    finally:
        conn.close()


def sirens_without_company(limit: Optional[int] = None, db_path: Optional[str] = None) -> list[str]:
    """SIREN présents dans `cessions` mais pas encore enrichis (absents de `companies`)."""
    conn = _connect(db_path)
    try:
        sql = ("SELECT DISTINCT c.siren FROM cessions c "
               "LEFT JOIN companies co ON co.siren = c.siren "
               "WHERE c.siren IS NOT NULL AND co.siren IS NULL")
        if limit:
            sql += f" LIMIT {int(limit)}"
        return [r[0] for r in conn.execute(sql).fetchall()]
    finally:
        conn.close()


def set_meta(key: str, value: str, db_path: Optional[str] = None) -> None:
    conn = _connect(db_path)
    try:
        conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
    finally:
        conn.close()


def get_stats(db_path: Optional[str] = None) -> dict:
    """Compteurs de la base locale (pour l'affichage)."""
    conn = _connect(db_path)
    try:
        def one(sql):
            return conn.execute(sql).fetchone()[0]
        return {
            "n_cessions": one("SELECT COUNT(*) FROM cessions"),
            "n_companies": one("SELECT COUNT(*) FROM companies"),
            "n_financials": one("SELECT COUNT(*) FROM financials"),
            "date_min": one("SELECT MIN(date) FROM cessions"),
            "date_max": one("SELECT MAX(date) FROM cessions"),
            "last_ingest": (conn.execute("SELECT value FROM meta WHERE key='last_ingest'")
                            .fetchone() or [None])[0],
        }
    finally:
        conn.close()


def load_cessions(terms: Optional[list[str]] = None, naf_filters: Optional[list[str]] = None,
                  departement: Optional[str] = None, since: Optional[str] = None,
                  require_financials: bool = True, limit: Optional[int] = None,
                  db_path: Optional[str] = None) -> list[Cession]:
    """Recharge des cessions depuis la base locale, ratios prix/CA et prix/EBE recalculés
    (exercice calé sur la date de cession). Filtres : activité (LIKE descriptif/nom), NAF
    (préfixe), département, fenêtre `since`. Instantané (aucun appel réseau)."""
    conn = _connect(db_path)
    try:
        sql = ("SELECT c.ann_id, c.siren, co.nom, c.ville, c.departement, c.date, c.categorie, "
               "c.prix, c.descriptif, c.url, co.naf, co.nb_etablissements "
               "FROM cessions c LEFT JOIN companies co ON co.siren = c.siren WHERE 1=1")
        args: list = []
        if departement:
            sql += " AND c.departement = ?"
            args.append(departement)
        if since:
            sql += " AND c.date >= ?"
            args.append(since)
        if terms:
            ors = []
            for t in terms:
                ors.append("(c.descriptif LIKE ? OR c.nom LIKE ?)")
                args += [f"%{t}%", f"%{t}%"]
            sql += " AND (" + " OR ".join(ors) + ")"
        sql += " ORDER BY c.date DESC"
        rows = conn.execute(sql, args).fetchall()
        # Pré-charge les exercices financiers des SIREN concernés (1 requête).
        sirens = {r[1] for r in rows if r[1]}
        fin_by_siren: dict[str, list[dict]] = {}
        if sirens:
            qmarks = ",".join("?" * len(sirens))
            for fr in conn.execute(
                "SELECT siren, date_cloture_exercice, chiffre_d_affaires, ebe, ebit, resultat_net "
                f"FROM financials WHERE siren IN ({qmarks})", list(sirens)
            ).fetchall():
                fin_by_siren.setdefault(fr[0], []).append({
                    "date_cloture_exercice": fr[1], "chiffre_d_affaires": fr[2],
                    "ebe": fr[3], "ebit": fr[4], "resultat_net": fr[5]})
    finally:
        conn.close()

    out: list[Cession] = []
    for r in rows:
        naf = r[10]
        if naf_filters and not naf_matches(naf, naf_filters):
            continue
        c = Cession(ann_id=r[0], siren=r[1], nom=r[2], ville=r[3], departement=r[4], date=r[5],
                    categorie=r[6], prix=r[7], descriptif=r[8], url=r[9],
                    naf=naf, activite=naf, nb_etablissements=r[11])
        fin = finances_inpi.pick_financials(fin_by_siren.get(c.siren, []), c.date) if c.siren else None
        if fin:
            c.ca = fin.get("chiffre_d_affaires")
            c.ebe = fin.get("ebe")
            c.ebit = fin.get("ebit")
            cloture = fin.get("date_cloture_exercice") or ""
            c.ca_annee = int(cloture[:4]) if cloture[:4].isdigit() else None
            c.pct_ca = compute_pct_ca(c.prix, c.ca)
            c.mult_ebe = compute_mult_ebe(c.prix, c.ebe)
        has_fin = c.ca is not None or (c.ebe is not None and c.ebe > 0)
        if require_financials and not has_fin:
            continue
        out.append(c)
        if limit and len(out) >= limit:
            break
    return out
