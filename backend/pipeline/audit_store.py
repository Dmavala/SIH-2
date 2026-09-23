"""
Tamper-Evident Evidence Store (SQLite) with Cryptographic Hash Chain.

Why this exists:
  The previous audit log was an in-memory Python list — it vanished on every
  restart and could be edited by anyone with process access. Under Section 63
  BSA 2023, chain-of-custody must be verifiable and durable.

Design:
  - Every audit event embeds the SHA-256 of the previous event -> any deletion
    or retro-active edit breaks the chain and is detectable via verify_chain().
  - Challenges (OTP state machine) and generated dossiers are persisted too.
  - Stdlib sqlite3 only; thread-safe via a per-operation connection + WAL.
  - Postgres can be swapped in later behind the same interface.
"""

import hashlib
import json
import os
import sqlite3
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from backend.config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    event_uid    TEXT NOT NULL UNIQUE,
    ts           REAL NOT NULL,
    time_str     TEXT NOT NULL,
    event_type   TEXT NOT NULL,
    session_id   TEXT NOT NULL,
    severity     TEXT NOT NULL,
    details      TEXT NOT NULL,
    prev_hash    TEXT NOT NULL,
    entry_hash   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_events(ts);

CREATE TABLE IF NOT EXISTS challenges (
    session_id   TEXT PRIMARY KEY,
    challenge_id TEXT NOT NULL,
    record       TEXT NOT NULL,          -- full challenge JSON (incl. salted OTP hash)
    status       TEXT NOT NULL,
    updated_at   REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS dossiers (
    dossier_id   TEXT PRIMARY KEY,
    session_id   TEXT NOT NULL,
    created_at   REAL NOT NULL,
    payload      TEXT NOT NULL           -- full certificate JSON
);
"""


def _hash_entry(prev_hash: str, payload: Dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")) + prev_hash
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class _LockedConnection:
    """
    Context manager over a shared sqlite connection (for :memory: mode).
    Commits on success, rolls back on error, and ALWAYS releases the lock.
    """

    def __init__(self, conn: sqlite3.Connection, lock: threading.Lock):
        self._conn = conn
        self._lock = lock

    def __enter__(self) -> sqlite3.Connection:
        self._lock.acquire()
        return self._conn

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                self._conn.commit()
            else:
                self._conn.rollback()
        finally:
            self._lock.release()
        return False


class _FileConnection:
    """
    Context manager for per-operation file connections.
    Unlike `with sqlite3.connect(...)`, this CLOSES the connection on exit
    (avoiding leaked file handles that lock the DB file on Windows).
    """

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def __enter__(self) -> sqlite3.Connection:
        self._conn = sqlite3.connect(self._db_path, timeout=10.0)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")
        return self._conn

    def __exit__(self, exc_type, exc, tb):
        if self._conn is not None:
            try:
                if exc_type is None:
                    self._conn.commit()
                else:
                    self._conn.rollback()
            finally:
                self._conn.close()
                self._conn = None
        return False


class AuditStore:
    """
    Durable, tamper-evident evidence store.

    Usage:
        store = AuditStore()                       # uses settings.db
        store.log_event("DEFENSE_TRIGGERED", "SES-X", "details", "CRITICAL")
        events = store.get_audit_log(limit=100)
        ok, cursor = store.verify_chain()          # -> (True, 152)
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            if settings.db.backend == "memory":
                db_path = ":memory:"
            else:
                db_path = settings.db.sqlite_path
        self.db_path = db_path
        self._memory_conn: Optional[sqlite3.Connection] = None
        self._lock = threading.Lock()
        if db_path == ":memory:":
            # In-memory DBs vanish per-connection; keep ONE shared connection
            # (thread-guarded) so tests/tools can use backend='memory' safely.
            self._memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._memory_conn.executescript(_SCHEMA)
        else:
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
            self._init_schema()

    def _cursor(self):
        """Context manager yielding a sqlite connection (shared for :memory:, per-op + closed for files)."""
        if self._memory_conn is not None:
            return _LockedConnection(self._memory_conn, self._lock)
        return _FileConnection(self.db_path)

    def _init_schema(self) -> None:
        with self._cursor() as conn:
            conn.executescript(_SCHEMA)

    # ------------------------------------------------------------------ audit
    def log_event(self, event_type: str, session_id: str, details: str,
                  severity: str = "INFO") -> Dict[str, Any]:
        now = time.time()
        event_uid = f"EVT-{uuid.uuid4().hex[:12].upper()}"
        time_str = time.strftime("%H:%M:%S")
        with self._cursor() as conn:
            row = conn.execute(
                "SELECT entry_hash FROM audit_events ORDER BY id DESC LIMIT 1"
            ).fetchone()
            prev_hash = row[0] if row else "GENESIS"
            payload = {
                "event_uid": event_uid, "ts": now, "event_type": event_type,
                "session_id": session_id, "severity": severity, "details": details,
            }
            entry_hash = _hash_entry(prev_hash, payload)
            conn.execute(
                "INSERT INTO audit_events (event_uid, ts, time_str, event_type, session_id,"
                " severity, details, prev_hash, entry_hash) VALUES (?,?,?,?,?,?,?,?,?)",
                (event_uid, now, time_str, event_type, session_id, severity,
                 details, prev_hash, entry_hash),
            )
        return {
            "id": event_uid, "timestamp": now, "time_str": time_str,
            "event_type": event_type, "session_id": session_id,
            "details": details, "severity": severity,
            "entry_hash": entry_hash, "prev_hash": prev_hash,
        }

    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 1000))
        with self._cursor() as conn:
            rows = conn.execute(
                "SELECT event_uid, ts, time_str, event_type, session_id, details,"
                " severity, entry_hash, prev_hash FROM audit_events"
                " ORDER BY id DESC LIMIT ?", (limit,),
            ).fetchall()
        return [
            {
                "id": r[0], "timestamp": r[1], "time_str": r[2], "event_type": r[3],
                "session_id": r[4], "details": r[5], "severity": r[6],
                "entry_hash": r[7], "prev_hash": r[8],
            }
            for r in rows
        ]

    def verify_chain(self) -> Dict[str, Any]:
        """
        Recomputes the full hash chain. Returns integrity report:
        {"valid": True, "events": 152} or {"valid": False, "events": n,
        "broken_at": event_uid, "reason": "..."}
        """
        with self._cursor() as conn:
            rows = conn.execute(
                "SELECT event_uid, ts, event_type, session_id, severity, details,"
                " prev_hash, entry_hash FROM audit_events ORDER BY id ASC"
            ).fetchall()
        prev = "GENESIS"
        for r in rows:
            uid, ts, etype, sid, sev, details, stored_prev, stored_hash = r
            if stored_prev != prev:
                return {"valid": False, "events": len(rows), "broken_at": uid,
                        "reason": "prev_hash mismatch (event inserted/deleted)"}
            payload = {"event_uid": uid, "ts": ts, "event_type": etype,
                       "session_id": sid, "severity": sev, "details": details}
            if _hash_entry(prev, payload) != stored_hash:
                return {"valid": False, "events": len(rows), "broken_at": uid,
                        "reason": "entry hash mismatch (content altered)"}
            prev = stored_hash
        return {"valid": True, "events": len(rows)}

    # ------------------------------------------------------------- challenges
    def save_challenge(self, session_id: str, record: Dict[str, Any]) -> None:
        with self._cursor() as conn:
            conn.execute(
                "INSERT INTO challenges (session_id, challenge_id, record, status, updated_at)"
                " VALUES (?,?,?,?,?) ON CONFLICT(session_id) DO UPDATE SET"
                " challenge_id=excluded.challenge_id, record=excluded.record,"
                " status=excluded.status, updated_at=excluded.updated_at",
                (session_id, record.get("challenge_id", ""),
                 json.dumps(record), record.get("status", "PENDING"), time.time()),
            )

    def load_challenge(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._cursor() as conn:
            row = conn.execute(
                "SELECT record FROM challenges WHERE session_id = ?", (session_id,)
            ).fetchone()
        return json.loads(row[0]) if row else None

    def list_active_challenges(self) -> Dict[str, Dict[str, Any]]:
        with self._cursor() as conn:
            rows = conn.execute(
                "SELECT session_id, record FROM challenges"
                " WHERE status IN ('PENDING','FAILED')"
            ).fetchall()
        return {r[0]: json.loads(r[1]) for r in rows}

    # --------------------------------------------------------------- dossiers
    def save_dossier(self, dossier_id: str, session_id: str, payload: Dict[str, Any]) -> None:
        with self._cursor() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO dossiers (dossier_id, session_id, created_at, payload)"
                " VALUES (?,?,?,?)",
                (dossier_id, session_id, time.time(), json.dumps(payload)),
            )

    def get_dossier(self, dossier_id: str) -> Optional[Dict[str, Any]]:
        with self._cursor() as conn:
            row = conn.execute(
                "SELECT payload FROM dossiers WHERE dossier_id = ?", (dossier_id,)
            ).fetchone()
        return json.loads(row[0]) if row else None
