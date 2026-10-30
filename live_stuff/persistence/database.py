"""Database schema and connection management.

Single responsibility: create tables, manage connections, handle transactions.
"""

import logging
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
    close_reason TEXT,
    sl_price REAL DEFAULT 0,
    hrisk REAL DEFAULT 0,
    lvl_1_5r REAL DEFAULT 0,
    lvl_3r REAL DEFAULT 0,
    regime TEXT NOT NULL DEFAULT 'flip'
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
    htf_window_id INTEGER,  -- M1: nullable (NULL = taken while no window open)
    status TEXT NOT NULL CHECK (status IN ('open','closed')),
    exit_ts INTEGER,
    exit_price REAL,
    exit_reason TEXT,
    r_multiple REAL,
    trail_next_pivot REAL,
    trail_activation_idx INTEGER,
    trail_confirmed BOOLEAN,
    entry_order_id TEXT,
    entry_order_link_id TEXT,
    entry_fill_price REAL,
    sl_order_id TEXT,
    sl_order_link_id TEXT,
    sl_order_status TEXT,
    exchange_state TEXT DEFAULT 'none',
    exit_order_id TEXT,
    exit_fill_price REAL,
    fee_paid REAL DEFAULT 0,
    funding_paid REAL DEFAULT 0,
     last_sync_ts INTEGER,
     origin TEXT DEFAULT 'live'
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

-- Candle history: persisted from seed + live closes so the trading
-- simulation can run on the FULL candle chain (not just the trimmed
-- rolling window). See .kilo/plans/1792658668907-rolling-window-data-loss-plan.md
CREATE TABLE IF NOT EXISTS candles (
    tf TEXT NOT NULL,
    ts INTEGER NOT NULL,
    date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    PRIMARY KEY (tf, ts)
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
        # H7: WAL checkpoint + integrity check on startup
        try:
            self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            pass  # non-critical, WAL will compact eventually
        try:
            result = self._conn.execute("PRAGMA integrity_check").fetchone()
            if result and result[0] != "ok":
                import logging
                logging.getLogger("database").error(f"DB integrity check failed: {result[0]}")
        except Exception:
            pass  # non-critical
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
        self._migrate_htf_windows()
        self._migrate_trading_state()
        self._migrate_ltf_trades()
        self._migrate_ltf_exchange_fields()
        self._migrate_ltf_origin()
        self._create_indexes()  # M4 — after migrations (rebuild drops ltf indexes)
        self._conn.commit()

    def _migrate_htf_windows(self):
        """Add new columns to htf_windows if missing (safe for existing DBs)."""
        cursor = self._conn.execute("PRAGMA table_info(htf_windows)")
        existing = {row[1] for row in cursor.fetchall()}
        migrations = [
            ("sl_price", "REAL DEFAULT 0"),
            ("hrisk", "REAL DEFAULT 0"),
            ("lvl_1_5r", "REAL DEFAULT 0"),
            ("lvl_3r", "REAL DEFAULT 0"),
            ("regime", "TEXT NOT NULL DEFAULT 'flip'"),
        ]
        for col, typedef in migrations:
            if col not in existing:
                self._conn.execute(f"ALTER TABLE htf_windows ADD COLUMN {col} {typedef}")

    def _migrate_trading_state(self):
        """Add daily P&L columns to trading_state if missing (safe for existing DBs)."""
        cursor = self._conn.execute("PRAGMA table_info(trading_state)")
        existing = {row[1] for row in cursor.fetchall()}
        migrations = [
            ("daily_pnl_r", "REAL DEFAULT 0"),
            ("daily_halted", "BOOLEAN DEFAULT 0"),
            ("last_trade_date", "TEXT DEFAULT ''"),
        ]
        for col, typedef in migrations:
            if col not in existing:
                self._conn.execute(f"ALTER TABLE trading_state ADD COLUMN {col} {typedef}")

    def _migrate_ltf_trades(self):
        """Add qty column + M1: make htf_window_id nullable (table rebuild).

        SQLite cannot drop a NOT NULL constraint in place — rebuild the table
        with the current schema (htf_window_id INTEGER, no NOT NULL, incl. the
        qty column) and copy all rows. Transactional DDL: all-or-nothing.
        Idempotent: only rebuilds while the constraint exists.
        """
        cursor = self._conn.execute("PRAGMA table_info(ltf_trades)")
        cols = {row[1]: row for row in cursor.fetchall()}
        if "qty" not in cols:
            self._conn.execute("ALTER TABLE ltf_trades ADD COLUMN qty REAL DEFAULT 0")
        if cols.get("htf_window_id") is not None and cols["htf_window_id"][3]:  # notnull flag
            self._conn.execute("""CREATE TABLE ltf_trades_rebuild (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                direction TEXT NOT NULL,
                entry_ts INTEGER NOT NULL,
                entry_price REAL NOT NULL,
                sl_initial REAL NOT NULL,
                sl_current REAL NOT NULL,
                tp_price REAL NOT NULL,
                cap_ts INTEGER NOT NULL,
                htf_window_id INTEGER,
                status TEXT NOT NULL CHECK (status IN ('open','closed')),
                exit_ts INTEGER,
                exit_price REAL,
                exit_reason TEXT,
                r_multiple REAL,
                trail_next_pivot REAL,
                trail_activation_idx INTEGER,
                trail_confirmed BOOLEAN,
                qty REAL DEFAULT 0
            )""")
            self._conn.execute("""INSERT INTO ltf_trades_rebuild
                (id, direction, entry_ts, entry_price, sl_initial, sl_current,
                 tp_price, cap_ts, htf_window_id, status, exit_ts, exit_price,
                 exit_reason, r_multiple, trail_next_pivot, trail_activation_idx,
                 trail_confirmed, qty)
                SELECT id, direction, entry_ts, entry_price, sl_initial, sl_current,
                       tp_price, cap_ts, htf_window_id, status, exit_ts, exit_price,
                       exit_reason, r_multiple, trail_next_pivot, trail_activation_idx,
                       trail_confirmed, qty
                FROM ltf_trades""")
            self._conn.execute("DROP TABLE ltf_trades")
            self._conn.execute("ALTER TABLE ltf_trades_rebuild RENAME TO ltf_trades")
            logging.getLogger("database").info(
                "M1: ltf_trades rebuilt — htf_window_id is now nullable")

    def _migrate_ltf_exchange_fields(self):
        """Add per-leg exchange order/fill fields to ltf_trades."""
        cursor = self._conn.execute("PRAGMA table_info(ltf_trades)")
        existing = {row[1] for row in cursor.fetchall()}
        migrations = [
            ("entry_order_id", "TEXT"),
            ("entry_order_link_id", "TEXT"),
            ("entry_fill_price", "REAL"),
            ("sl_order_id", "TEXT"),
            ("sl_order_link_id", "TEXT"),
            ("sl_order_status", "TEXT"),
            ("exchange_state", "TEXT DEFAULT 'none'"),
            ("exit_order_id", "TEXT"),
            ("exit_fill_price", "REAL"),
            ("fee_paid", "REAL DEFAULT 0"),
            ("funding_paid", "REAL DEFAULT 0"),
            ("last_sync_ts", "INTEGER"),
        ]
        for col, typedef in migrations:
            if col not in existing:
                self._conn.execute(f"ALTER TABLE ltf_trades ADD COLUMN {col} {typedef}")

    def _migrate_ltf_origin(self):
        """M5: add origin column to distinguish seed-history trades from live."""
        cursor = self._conn.execute("PRAGMA table_info(ltf_trades)")
        cols = {row[1] for row in cursor.fetchall()}
        if "origin" not in cols:
            self._conn.execute("ALTER TABLE ltf_trades ADD COLUMN origin TEXT DEFAULT 'live'")

    def _create_indexes(self):
        """M4: query-path indexes. Created AFTER migrations because the M1
        table rebuild drops ltf_trades' indexes (DROP TABLE drops them)."""
        for stmt in [
            "CREATE INDEX IF NOT EXISTS idx_ltf_entry_ts ON ltf_trades(entry_ts)",
            "CREATE INDEX IF NOT EXISTS idx_ltf_status_entry ON ltf_trades(status, entry_ts)",
            "CREATE INDEX IF NOT EXISTS idx_htf_status_regime ON htf_windows(status, regime)",
            "CREATE INDEX IF NOT EXISTS idx_marks_tf_ts ON marks(tf, ts)",
            "CREATE INDEX IF NOT EXISTS idx_candles_tf_ts ON candles(tf, ts)",
        ]:
            self._conn.execute(stmt)

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
