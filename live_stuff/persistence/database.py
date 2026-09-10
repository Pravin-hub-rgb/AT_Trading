"""Database schema and connection management.

Single responsibility: create tables, manage connections, handle transactions.
"""

import sqlite3
from pathlib import Path
from typing import Optional
from contextlib import contextmanager


DB_SCHEMA = """
-- Walker state: one row per timeframe
CREATE TABLE IF NOT EXISTS walker_state (
    tf TEXT PRIMARY KEY,
    state_json TEXT NOT NULL,
    state_hash TEXT NOT NULL,
    updated_at INTEGER NOT NULL
);

-- HTF windows: opened by 1h marks, closed by cap or opposite mark
CREATE TABLE IF NOT EXISTS htf_windows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    direction TEXT NOT NULL,
    entry_ts INTEGER NOT NULL,
    entry_price REAL NOT NULL,
    cap_ts INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('open','closed')),
    close_ts INTEGER,
    close_reason TEXT
);

-- LTF trades: opened by 15m marks, closed by SL/TP/cap
CREATE TABLE IF NOT EXISTS ltf_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    direction TEXT NOT NULL,
    entry_ts INTEGER NOT NULL,
    entry_price REAL NOT NULL,
    sl_initial REAL NOT NULL,
    sl_current REAL NOT NULL,
    tp_price REAL NOT NULL,
    cap_ts INTEGER NOT NULL,
    htf_window_id INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('open','closed')),
    exit_ts INTEGER,
    exit_price REAL,
    exit_reason TEXT,
    r_multiple REAL,
    trail_next_pivot REAL,
    trail_activation_idx INTEGER,
    trail_confirmed BOOLEAN
);

-- Marks: append-only journal (never update/delete)
CREATE TABLE IF NOT EXISTS marks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts INTEGER NOT NULL,
    tf TEXT NOT NULL,
    kind TEXT NOT NULL,
    direction TEXT NOT NULL,
    price REAL NOT NULL,
    swing_no INTEGER NOT NULL,
    swing_kind TEXT NOT NULL,
    algo_version INTEGER NOT NULL DEFAULT 1,
    journaled_at INTEGER NOT NULL,
    UNIQUE (ts, tf, kind, direction, swing_no)
);

-- Trading state: cooldown and streak halt (single row)
CREATE TABLE IF NOT EXISTS trading_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    cooldown_remaining INTEGER NOT NULL DEFAULT 0,
    consecutive_losses INTEGER NOT NULL DEFAULT 0,
    halted BOOLEAN NOT NULL DEFAULT 0,
    last_loss_bar INTEGER
);

-- Meta: miscellaneous key-value pairs
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


class Database:
    """SQLite database manager.
    
    Usage:
        db = Database("backbencher.db")
        db.connect()
        db.create_tables()
        
        with db.transaction() as conn:
            # do work
            # auto-commits on success, auto-rolls back on exception
    """

    def __init__(self, db_path: str = "backbencher.db"):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        """Create connection and enable WAL mode for better concurrency."""
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self):
        """Close the connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def create_tables(self):
        """Create all tables if they don't exist."""
        if not self._conn:
            raise RuntimeError("Not connected. Call connect() first.")
        self._conn.executescript(DB_SCHEMA)
        self._conn.commit()

    @contextmanager
    def transaction(self):
        """Context manager for atomic transactions.
        
        Usage:
            with db.transaction() as conn:
                conn.execute(...)
                conn.execute(...)
            # auto-commits if no exception
            # auto-rolls back if exception
        """
        if not self._conn:
            raise RuntimeError("Not connected. Call connect() first.")
        try:
            yield self._conn
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    @property
    def conn(self) -> sqlite3.Connection:
        """Get the raw connection."""
        if not self._conn:
            raise RuntimeError("Not connected. Call connect() first.")
        return self._conn

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.close()
