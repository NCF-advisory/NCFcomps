"""Persistance des analyses generees (SQLite) pour tracabilite / historisation.

Une "analyse" (run) = un echantillon produit a un instant donne avec ses parametres et
l'utilisateur a l'origine. Deux types (`kind`) : 'comparables' (CompanyRecord) et
'cessions' (Cession FR) ; les lignes sont stockees en JSON dans run_records.

Module sans I/O reseau ni Streamlit ; couvert par des tests. Le chemin de la base est
configurable (settings.history_db_path) et surchargable par argument (tests).
"""
from __future__ import annotations
import json
import sqlite3
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from comparables import damodaran
from comparables.config import settings
from comparables.fr.models import Cession
from comparables.models import CompanyRecord

# Bêtas et multiples agrégés par secteur (base sectorielle = mémoire des valeurs déjà utilisées).
SECTOR_METRICS = ("beta_unlevered", "beta_regression", "ev_sales", "ev_ebitda",
                  "ev_ebit", "pe_trailing", "pe_forward", "pb")


def _db_path(db_path: Optional[str]) -> str:
    return db_path if db_path is not None else settings.history_db_path


def _connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = _db_path(db_path)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    _init(conn)
    return conn


def _init(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS runs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at  TEXT NOT NULL,
            username    TEXT,
            label       TEXT,
            params      TEXT,
            n_records   INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS run_records (
            run_id   INTEGER NOT NULL,
            idx      INTEGER NOT NULL,
            ticker   TEXT,
            payload  TEXT NOT NULL,
            FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
        );
        """
    )
    # Migration : colonne `kind` ajoutee apres coup (bases existantes = comparables).
    try:
        conn.execute("ALTER TABLE runs ADD COLUMN kind TEXT NOT NULL DEFAULT 'comparables'")
    except sqlite3.OperationalError:
        pass                            # colonne deja presente
    conn.commit()


def _insert_run(kind: str, lines: list[tuple[Optional[str], str]],
                username: Optional[str], label: Optional[str], params: Optional[dict],
                db_path: Optional[str]) -> int:
    """Insère un run générique : lines = [(clé d'identité, payload JSON), ...]."""
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = _connect(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO runs (created_at, username, label, params, n_records, kind) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (created_at, username, label, json.dumps(params or {}, default=str),
             len(lines), kind),
        )
        run_id = int(cur.lastrowid)
        conn.executemany(
            "INSERT INTO run_records (run_id, idx, ticker, payload) VALUES (?, ?, ?, ?)",
            [(run_id, i, key, payload) for i, (key, payload) in enumerate(lines)],
        )
        conn.commit()
        return run_id
    finally:
        conn.close()


def save_run(records: list[CompanyRecord], username: Optional[str] = None,
             label: Optional[str] = None, params: Optional[dict] = None,
             db_path: Optional[str] = None) -> int:
    """Enregistre une analyse de comparables et renvoie son identifiant."""
    return _insert_run("comparables",
                       [(r.ticker, r.model_dump_json()) for r in records],
                       username, label, params, db_path)


def save_cessions_run(cessions: list[Cession], username: Optional[str] = None,
                      label: Optional[str] = None, params: Optional[dict] = None,
                      db_path: Optional[str] = None) -> int:
    """Enregistre une recherche de cessions FR et renvoie son identifiant."""
    return _insert_run("cessions",
                       [(c.siren, c.model_dump_json()) for c in cessions],
                       username, label, params, db_path)


def list_runs(db_path: Optional[str] = None) -> list[dict]:
    """Liste les analyses enregistrees, de la plus recente a la plus ancienne."""
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT id, created_at, username, label, params, n_records, kind "
            "FROM runs ORDER BY id DESC"
        ).fetchall()
    finally:
        conn.close()
    return [
        {"id": r[0], "created_at": r[1], "username": r[2], "label": r[3],
         "params": json.loads(r[4]) if r[4] else {}, "n_records": r[5], "kind": r[6]}
        for r in rows
    ]


def run_kind(run_id: int, db_path: Optional[str] = None) -> Optional[str]:
    """Type d'une analyse ('comparables' | 'cessions'), None si inconnue."""
    conn = _connect(db_path)
    try:
        row = conn.execute("SELECT kind FROM runs WHERE id = ?", (run_id,)).fetchone()
    finally:
        conn.close()
    return row[0] if row else None


def _load_payloads(run_id: int, db_path: Optional[str]) -> list[str]:
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT payload FROM run_records WHERE run_id = ? ORDER BY idx", (run_id,)
        ).fetchall()
    finally:
        conn.close()
    return [row[0] for row in rows]


def load_run(run_id: int, db_path: Optional[str] = None) -> list[CompanyRecord]:
    """Recharge les CompanyRecord d'une analyse comparables (ordre d'origine)."""
    return [CompanyRecord.model_validate_json(p) for p in _load_payloads(run_id, db_path)]


def load_cessions_run(run_id: int, db_path: Optional[str] = None) -> list[Cession]:
    """Recharge les Cession d'une recherche FR enregistrée (ordre d'origine)."""
    return [Cession.model_validate_json(p) for p in _load_payloads(run_id, db_path)]


def delete_run(run_id: int, db_path: Optional[str] = None) -> None:
    """Supprime une analyse et ses lignes."""
    conn = _connect(db_path)
    try:
        conn.execute("DELETE FROM run_records WHERE run_id = ?", (run_id,))
        conn.execute("DELETE FROM runs WHERE id = ?", (run_id,))
        conn.commit()
    finally:
        conn.close()


# --- Base sectorielle : agrégation des analyses enregistrées par secteur ---

def _metric_stats(values: list) -> Optional[dict]:
    """Médiane + quartiles (Q1/Q3) + bornes + effectif d'une série, None ignorés.

    Quartiles en méthode 'inclusive' (restent dans la plage des données, robustes sur
    petits échantillons). Renvoie None si aucune valeur numérique."""
    vals = sorted(v for v in values if isinstance(v, (int, float)))
    if not vals:
        return None
    if len(vals) >= 2:
        q1, _, q3 = statistics.quantiles(vals, n=4, method="inclusive")
    else:
        q1 = q3 = vals[0]
    return {"median": statistics.median(vals), "q1": q1, "q3": q3,
            "min": vals[0], "max": vals[-1], "n": len(vals)}


def sector_aggregates(db_path: Optional[str] = None) -> list[dict]:
    """Bêtas et multiples agrégés par secteur sur TOUTES les analyses enregistrées.

    « Valeurs déjà utilisées » : chaque société d'un run sauvegardé compte comme un point.
    Par secteur : effectif, sociétés distinctes, dernière utilisation, et pour chaque
    métrique (cf. SECTOR_METRICS) médiane + quartiles + bornes. Trié par secteur."""
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT r.created_at, rr.payload FROM run_records rr "
            "JOIN runs r ON r.id = rr.run_id WHERE r.kind = 'comparables'"
        ).fetchall()
    finally:
        conn.close()

    buckets: dict[str, dict] = {}
    for created_at, payload in rows:
        rec = json.loads(payload)
        sector = (rec.get("sector") or "").strip()
        if not sector:
            continue
        b = buckets.setdefault(sector, {"records": [], "tickers": set(), "last_used": ""})
        b["records"].append(rec)
        if rec.get("ticker"):
            b["tickers"].add(rec["ticker"])
        if created_at and created_at > b["last_used"]:
            b["last_used"] = created_at

    out: list[dict] = []
    for sector, b in sorted(buckets.items(), key=lambda kv: kv[0].lower()):
        metrics = {m: s for m in SECTOR_METRICS
                   if (s := _metric_stats([rec.get(m) for rec in b["records"]]))}
        out.append({
            "sector": sector,
            "n_records": len(b["records"]),
            "n_companies": len(b["tickers"]),
            "last_used": b["last_used"] or None,
            "metrics": metrics,
            # Etalon Damodaran : industrie dominante du secteur (vote des industries Yahoo)
            # -> beta desendette sectoriel. None si aucune industrie ne se rattache.
            "damodaran": _damodaran_for_bucket(b["records"]),
        })
    return out


def _damodaran_for_bucket(records: list[dict]) -> Optional[dict]:
    """Benchmark Damodaran d'un seau sectoriel : industrie dominante + beta desendette."""
    industry = damodaran.suggest_industry([rec.get("industry") for rec in records])
    bench = damodaran.lookup(industry) if industry else None
    if not bench:
        return None
    return {"industry": industry, "unlevered_beta": bench["unlevered_beta"],
            "unlevered_beta_cash": bench["unlevered_beta_cash"], "n_firms": bench["n_firms"]}


def sector_records(sector: str, db_path: Optional[str] = None) -> list[dict]:
    """Lignes individuelles d'un secteur (retrouver les valeurs précises déjà utilisées).

    Du run le plus récent au plus ancien. Le secteur est comparé sans tenir compte de
    la casse ni des espaces de bord."""
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT r.id, r.created_at, r.label, rr.payload FROM run_records rr "
            "JOIN runs r ON r.id = rr.run_id WHERE r.kind = 'comparables' "
            "ORDER BY r.id DESC, rr.idx"
        ).fetchall()
    finally:
        conn.close()

    target = (sector or "").strip().lower()
    out: list[dict] = []
    for run_id, created_at, label, payload in rows:
        rec = json.loads(payload)
        if (rec.get("sector") or "").strip().lower() != target:
            continue
        out.append({
            "run_id": run_id, "created_at": created_at, "label": label,
            "ticker": rec.get("ticker"), "name": rec.get("name"),
            "country": rec.get("country"),
            **{m: rec.get(m) for m in SECTOR_METRICS},
        })
    return out
