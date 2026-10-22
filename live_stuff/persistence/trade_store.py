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
      -       regime: 'flip' | 'b2' | 'decisive' — window families are independent
        v7 runs and can be open simultaneously; regime stores the ENGINE
        bucket name the book's regime rule selects
    
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

    regime: 'flip' | 'b2' | 'decisive' — filter to that regime's window. None
    (default) keeps the legacy behavior: return the most recently opened open
    window regardless of regime.
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
    htf_window_id: Optional[int],
) -> int:
    """Open a new LTF trade.

    M1: htf_window_id is nullable — NULL means "taken while no window of the
    trade's regime was open" (never the 0 sentinel).

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
    exit_order_id: Optional[str] = None,
    exit_fill_price: Optional[float] = None,
    fee_paid: Optional[float] = None,
    funding_paid: Optional[float] = None,
) -> int:
    """Close an LTF trade.

    C4: guarded by status = 'open' — a second close attempt matches ZERO rows
    and can never overwrite the first close's exit values.

    Returns:
        cursor.rowcount: 1 = closed now, 0 = already closed (no-op)
    """
    sets = ["status = 'closed'", "exit_ts = ?", "exit_price = ?",
            "exit_reason = ?", "r_multiple = ?"]
    params: list = [exit_ts, exit_price, exit_reason, r_multiple]
    if exit_order_id is not None:
        sets.append("exit_order_id = ?")
        params.append(exit_order_id)
    if exit_fill_price is not None:
        sets.append("exit_fill_price = ?")
        params.append(exit_fill_price)
    if fee_paid is not None:
        sets.append("fee_paid = ?")
        params.append(fee_paid)
    if funding_paid is not None:
        sets.append("funding_paid = ?")
        params.append(funding_paid)
    params.append(trade_id)
    with db.transaction() as conn:
        cursor = conn.execute(
            f"""UPDATE ltf_trades SET {", ".join(sets)}
                WHERE id = ? AND status = 'open'""",
            params,
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


_EXCHANGE_FIELDS = {
    "entry_order_id", "entry_order_link_id", "entry_fill_price",
    "sl_order_id", "sl_order_link_id", "sl_order_status",
    "exchange_state", "exit_order_id", "exit_fill_price",
    "fee_paid", "funding_paid", "last_sync_ts",
}


def update_trade_exchange(db: Database, trade_id: int, **fields) -> int:
    """Update per-leg exchange order/fill fields."""
    unknown = set(fields) - _EXCHANGE_FIELDS
    if unknown:
        raise ValueError(f"unknown exchange fields: {sorted(unknown)}")
    if not fields:
        return 0
    sets = ", ".join(f"{name} = ?" for name in fields)
    params = list(fields.values()) + [trade_id]
    with db.transaction() as conn:
        cursor = conn.execute(
            f"UPDATE ltf_trades SET {sets} WHERE id = ?",
            params,
        )
        return cursor.rowcount


def get_ltf_trade(db: Database, trade_id: int) -> Optional[dict]:
    row = db.conn.execute(
        "SELECT * FROM ltf_trades WHERE id = ?", (trade_id,)
    ).fetchone()
    return dict(row) if row else None


def get_open_ltf_trade(db: Database) -> Optional[dict]:
    """Get the currently open LTF trade, if any."""
    row = db.conn.execute(
        "SELECT * FROM ltf_trades WHERE status = 'open' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    
    if row is None:
        return None
    
    return dict(row)


def get_open_ltf_trades(db: Database) -> list[dict]:
    """Get all currently open LTF trades, oldest first (paper multi-position)."""
    rows = db.conn.execute(
        "SELECT * FROM ltf_trades WHERE status = 'open' ORDER BY id ASC"
    ).fetchall()
    return [dict(row) for row in rows]


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
