"""Historie der Optimierungs-Sitzungen (SQLite, stdlib).

Je Operation eigene Verbindung (Aufrufe aus Worker-Threads), nur
parametrisierte Statements.
"""
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY,
    created_at TEXT,
    updated_at TEXT,
    status TEXT CHECK(status IN ('open','done')),
    api_type TEXT,
    model TEXT,
    raw_prompt TEXT,
    optimized_prompt TEXT
);
CREATE TABLE IF NOT EXISTS turns (
    id INTEGER PRIMARY KEY,
    session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    idx INTEGER,
    role TEXT,
    content TEXT,
    created_at TEXT
);
CREATE INDEX IF NOT EXISTS turns_session ON turns(session_id, idx);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(path: Path) -> None:
    with closing(_connect(path)) as conn, conn:
        conn.executescript(_SCHEMA)


def create_session(path: Path, raw_prompt: str, api_type: str, model: str) -> int:
    now = _now()
    with closing(_connect(path)) as conn, conn:
        cur = conn.execute(
            "INSERT INTO sessions (created_at, updated_at, status, api_type, model,"
            " raw_prompt, optimized_prompt) VALUES (?, ?, 'open', ?, ?, ?, NULL)",
            (now, now, api_type, model, raw_prompt),
        )
        return cur.lastrowid


def add_turn(path: Path, session_id: int, role: str, content: str) -> None:
    now = _now()
    with closing(_connect(path)) as conn, conn:
        conn.execute(
            "INSERT INTO turns (session_id, idx, role, content, created_at)"
            " VALUES (?, (SELECT COALESCE(MAX(idx), -1) + 1 FROM turns"
            " WHERE session_id = ?), ?, ?, ?)",
            (session_id, session_id, role, content, now),
        )
        conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))


def _turns(conn: sqlite3.Connection, session_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT role, content FROM turns WHERE session_id = ? ORDER BY idx, id",
        (session_id,),
    )
    return [{"role": r["role"], "content": r["content"]} for r in rows]


def get_turns(path: Path, session_id: int) -> list[dict]:
    with closing(_connect(path)) as conn:
        return _turns(conn, session_id)


def finish_session(path: Path, session_id: int, optimized_prompt: str) -> None:
    with closing(_connect(path)) as conn, conn:
        conn.execute(
            "UPDATE sessions SET status = 'done', optimized_prompt = ?, updated_at = ?"
            " WHERE id = ?",
            (optimized_prompt, _now(), session_id),
        )


def list_sessions(path: Path, limit: int = 200) -> list[dict]:
    with closing(_connect(path)) as conn:
        rows = conn.execute(
            "SELECT id, created_at, updated_at, status, raw_prompt, model"
            " FROM sessions ORDER BY created_at DESC, id DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in rows]


def get_session(path: Path, session_id: int) -> dict | None:
    with closing(_connect(path)) as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["turns"] = _turns(conn, session_id)
        return item


def delete_session(path: Path, session_id: int) -> bool:
    with closing(_connect(path)) as conn, conn:
        cur = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        return cur.rowcount > 0
