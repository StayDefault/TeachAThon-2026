"""Single-user local session storage."""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from state import ensure


DB_PATH = Path(os.environ.get("DYSCOVER_DB", Path(__file__).with_name("dyscover.sqlite3")))


@contextmanager
def database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    try:
        db.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, updated_at TEXT NOT NULL, data TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS usage (kind TEXT PRIMARY KEY, count INTEGER NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS material_files (session_id TEXT NOT NULL, material_id TEXT NOT NULL, name TEXT NOT NULL, kind TEXT NOT NULL, data BLOB NOT NULL, PRIMARY KEY (session_id, material_id))")
        with db:
            yield db
    finally:
        db.close()


def save(session):
    now = datetime.now(timezone.utc).isoformat()
    session["session"]["updatedAt"] = now
    with database() as db:
        db.execute("INSERT OR REPLACE INTO sessions VALUES (?, ?, ?)",
                   (session["session"]["id"], now, json.dumps(session, ensure_ascii=False)))


def get(session_id, owner_id=None):
    with database() as db:
        row = db.execute("SELECT data FROM sessions WHERE id = ?", (session_id,)).fetchone()
    session = json.loads(row[0]) if row else None
    if session:
        ensure(session)
        for node in session.get("nodes", []):
            if "userEdited" not in node and session.get("details", {}).get(node["id"], {}).get("userEdited"):
                node["userEdited"] = True
            if node.get("position") and not session.get("details", {}).get(node["id"], {}).get("userEdited"):
                node["userEdited"] = False
    return session if session and (owner_id is None or session.get("owner") == owner_id) else None


def list_sessions(owner_id=None):
    with database() as db:
        rows = db.execute("SELECT data FROM sessions ORDER BY updated_at DESC").fetchall()
    sessions = [json.loads(row[0]) for row in rows]
    return [item["session"] for item in sessions if owner_id is None or item.get("owner") == owner_id]


def delete_session(session_id, owner_id):
    with database() as db:
        row = db.execute("SELECT data FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not row or json.loads(row[0]).get("owner") != owner_id:
            return False
        db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        db.execute("DELETE FROM material_files WHERE session_id = ?", (session_id,))
        return True


def save_materials(session_id, files):
    with database() as db:
        db.executemany("INSERT INTO material_files VALUES (?, ?, ?, ?, ?)",
                       [(session_id, item["id"], item["name"], item["kind"], data) for item, data in files])


def get_material(session_id, material_id):
    with database() as db:
        return db.execute("SELECT name, kind, data FROM material_files WHERE session_id = ? AND material_id = ?",
                          (session_id, material_id)).fetchone()


def reserve(kind, limit):
    """Count attempts before external calls, across workers sharing one SQLite file."""
    with database() as db:
        db.execute("INSERT OR IGNORE INTO usage VALUES (?, 0)", (kind,))
        cursor = db.execute("UPDATE usage SET count = count + 1 WHERE kind = ? AND count < ?", (kind, limit))
        return cursor.rowcount == 1
