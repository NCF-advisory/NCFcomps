"""Persistance des analyses generees (SQLite) pour tracabilite / historisation.

Une "analyse" (run) = un echantillon de CompanyRecord produit a un instant donne, avec ses
parametres (taux d'IS, periode/frequence du beta, tickers) et l'utilisateur a l'origine.

Module sans I/O reseau ni Streamlit ; couvert par des tests. Le chemin de la base est
configurable (settings.history_db_path) et surchargable par argument (tests).
"""
from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from comparables.config import settings
from comparables.models import CompanyRecord


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
    conn.commit()


def save_run(records: list[CompanyRecord], username: Optional[str] = None,
             label: Optional[str] = None, params: Optional[dict] = None,
             db_path: Optional[str] = None) -> int:
    """Enregistre une analyse et renvoie son identifiant."""
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = _connect(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO runs (created_at, username, label, params, n_records) "
            "VALUES (?, ?, ?, ?, ?)",
            (created_at, username, label, json.dumps(params or {}, default=str), len(records)),
        )
        run_id = int(cur.lastrowid)
        conn.executemany(
            "INSERT INTO run_records (run_id, idx, ticker, payload) VALUES (?, ?, ?, ?)",
            [(run_id, i, r.ticker, r.model_dump_json()) for i, r in enumerate(records)],
        )
        conn.commit()
        return run_id
    finally:
        conn.close()


def list_runs(db_path: Optional[str] = None) -> list[dict]:
    """Liste les analyses enregistrees, de la plus recente a la plus ancienne."""
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT id, created_at, username, label, params, n_records "
            "FROM runs ORDER BY id DESC"
        ).fetchall()
    finally:
        conn.close()
    return [
        {"id": r[0], "created_at": r[1], "username": r[2], "label": r[3],
         "params": json.loads(r[4]) if r[4] else {}, "n_records": r[5]}
        for r in rows
    ]


def load_run(run_id: int, db_path: Optional[str] = None) -> list[CompanyRecord]:
    """Recharge les CompanyRecord d'une analyse (ordre d'origine)."""
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT payload FROM run_records WHERE run_id = ? ORDER BY idx", (run_id,)
        ).fetchall()
    finally:
        conn.close()
    return [CompanyRecord.model_validate_json(row[0]) for row in rows]


def delete_run(run_id: int, db_path: Optional[str] = None) -> None:
    """Supprime une analyse et ses lignes."""
    conn = _connect(db_path)
    try:
        conn.execute("DELETE FROM run_records WHERE run_id = ?", (run_id,))
        conn.execute("DELETE FROM runs WHERE id = ?", (run_id,))
        conn.commit()
    finally:
        conn.close()
