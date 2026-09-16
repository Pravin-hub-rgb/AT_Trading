"""Trade store - CRUD for HTF windows and LTF trades.

Single responsibility: manage trade lifecycle in SQLite.
"""

import time
from typing import Optional
from .database import Database


# --- HTF Windows ---

def open_htf_window(
    db: Database,
    direction: str,
    entry_ts: int,
    entry_price: float,
    cap_ts: int,
    sl_price: float = 0.0,
    hrisk: float = 0.0,
    lvl_1_5r: float = 0.0,
    lvl_3r: float = 0.0,
    regime: str = "flip",
) -> int:
    """Open a new HTF window with full matrix.
    
    Stores everything at entry time:
      - sl_price: HTF stop loss
      - hrisk: risk per unit (abs(entry - sl))
      - lvl_1_5r: 1.5R gate price
      - lvl_3r: 3R target price
      - regime: 'flip' or 'b2' — flip and b2 windows are independent v7 runs
        and can be open simultaneously
    
    Returns:
        The window id
    """
    with db.transaction() as conn:
        cursor = conn.execute(
            """INSERT INTO htf_windows 
               (direction, entry_ts, entry_price, cap_ts, status, sl_price, hrisk, lvl_1_5r, lvl_3r, regime)
               VALUES (?, ?, ?, ?, 'open', ?, ?, ?, ?, ?)""",
            (direction, entry_ts, entry_price, cap_ts, sl_price, hrisk, lvl_1_5r, lvl_3r, regime),
        )
        return cursor.lastrowid


def close_htf_window(db: Database, window_id: int, close_ts: int, reason: str):
    """Close an HTF window."""
    with db.transaction() as conn:
        conn.execute(
            """UPDATE htf_windows 
               SET status = 'closed', close_ts = ?, close_reason = ?
               WHERE id = ?""",
            (close_ts, reason, window_id),
        )


def get_open_htf_window(db: Database, regime: Optional[str] = None) -> Optional[dict]:
    """Get the currently open HTF window, if any.

    regime: 'flip' | 'b2' — filter to that regime's window. None (default)
    keeps the legacy behavior: return the most recently opened open window
    regardless of regime.
    """
    if regime is not None:
        row = db.conn.execute(
            """SELECT * FROM htf_windows WHERE status = 'open' AND regime = ?
               ORDER BY id DESC LIMIT 1""",
            (regime,),
        ).fetchone()
    else:
        row = db.conn.execute(
            "SELECT * FROM htf_windows WHERE status = 'open' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    
    if row is None:
        return None
    
    return dict(row)


def get_htf_windows(db: Database, from_ts: int = 0, to_ts: int = 0) -> list[dict]:
    """Get all HTF windows within a time range."""
    query = "SELECT * FROM htf_windows WHERE 1=1"
    params: list = []
    
    if from_ts > 0:
        query += " AND entry_ts >= ?"
        params.append(from_ts)
    
    if to_ts > 0:
        query += " AND entry_ts <= ?"
        params.append(to_ts)
    
    query += " ORDER BY entry_ts ASC"
    
    rows = db.conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


# --- LTF Trades ---

def open_ltf_trade(
    db: Database,
    direction: str,
    entry_ts: int,
    entry_price: float,
    sl_initial: float,
    tp_price: float,
    cap_ts: int,
    htf_window_id: int,
) -> int:
    """Open a new LTF trade.
    
    Returns:
        The trade id
    """
    with db.transaction() as conn:
        cursor = conn.execute(
            """INSERT INTO ltf_trades 
               (direction, entry_ts, entry_price, sl_initial, sl_current, tp_price, cap_ts, htf_window_id, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open')""",
            (direction, entry_ts, entry_price, sl_initial, sl_initial, tp_price, cap_ts, htf_window_id),
        )
        return cursor.lastrowid


def close_ltf_trade(
    db: Database,
    trade_id: int,
    exit_ts: int,
    exit_price: float,
    exit_reason: str,
    r_multiple: float,
) -> int:
    """Close an LTF trade.

    C4: guarded by status = 'open' — a second close attempt matches ZERO rows
    and can never overwrite the first close's exit values.

    Returns:
        cursor.rowcount: 1 = closed now, 0 = already closed (no-op)
    """
    with db.transaction() as conn:
        cursor = conn.execute(
            """UPDATE ltf_trades
               SET status = 'closed', exit_ts = ?, exit_price = ?, exit_reason = ?, r_multiple = ?
               WHERE id = ? AND status = 'open'""",
            (exit_ts, exit_price, exit_reason, r_multiple, trade_id),
        )
        return cursor.rowcount


def update_trade_sl(db: Database, trade_id: int, new_sl: float):
    """Update the current SL for a trade (trailing)."""
    with db.transaction() as conn:
        conn.execute(
            "UPDATE ltf_trades SET sl_current = ? WHERE id = ?",
            (new_sl, trade_id),
        )


def update_trade_qty(db: Database, trade_id: int, actual_qty: float):
    """Update the actual filled qty (partial fill correction)."""
    with db.transaction() as conn:
        conn.execute(
            "UPDATE ltf_trades SET qty = ? WHERE id = ?",
            (actual_qty, trade_id),
        )


def get_open_ltf_trade(db: Database) -> Optional[dict]:
    """Get the currently open LTF trade, if any."""
    row = db.conn.execute(
        "SELECT * FROM ltf_trades WHERE status = 'open' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    
    if row is None:
        return None
    
    return dict(row)


def get_ltf_trades(db: Database, from_ts: int = 0, to_ts: int = 0) -> list[dict]:
    """Get all LTF trades within a time range."""
    query = "SELECT * FROM ltf_trades WHERE 1=1"
    params: list = []
    
    if from_ts > 0:
        query += " AND entry_ts >= ?"
        params.append(from_ts)
    
    if to_ts > 0:
        query += " AND entry_ts <= ?"
        params.append(to_ts)
    
    query += " ORDER BY entry_ts ASC"
    
    rows = db.conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_trade_count(db: Database, status: str = "") -> int:
    """Get total number of trades, optionally filtered by status."""
    if status:
        row = db.conn.execute(
            "SELECT COUNT(*) FROM ltf_trades WHERE status = ?",
            (status,)
        ).fetchone()
    else:
        row = db.conn.execute("SELECT COUNT(*) FROM ltf_trades").fetchone()
    
    return row[0]
