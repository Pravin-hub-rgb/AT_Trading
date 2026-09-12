"""State store - save and load trading state.

Single responsibility: persist cooldown/halt state and swing endpoints to/from SQLite.
"""

import time
from typing import Optional, Tuple
from .database import Database


def get_trading_state(db: Database) -> dict:
    """Get the current trading state (cooldown, streak halt)."""
    row = db.conn.execute(
        "SELECT cooldown_remaining, consecutive_losses, halted, last_loss_bar FROM trading_state WHERE id = 1"
    ).fetchone()
    if row is None:
        return {"cooldown_remaining": 0, "consecutive_losses": 0, "halted": False, "last_loss_bar": None}
    return {
        "cooldown_remaining": row["cooldown_remaining"],
        "consecutive_losses": row["consecutive_losses"],
        "halted": bool(row["halted"]),
        "last_loss_bar": row["last_loss_bar"],
    }


def save_trading_state(db: Database, state: dict):
    """Save trading state (cooldown, streak halt)."""
    with db.transaction() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO trading_state (id, cooldown_remaining, consecutive_losses, halted, last_loss_bar) VALUES (1, ?, ?, ?, ?)",
            (state["cooldown_remaining"], state["consecutive_losses"], state["halted"], state.get("last_loss_bar")),
        )


def get_last_candle_ts(db: Database, tf: str) -> int:
    """Get the last processed candle timestamp for a timeframe from meta."""
    row = db.conn.execute(
        "SELECT value FROM meta WHERE key = ?", (f"last_{tf}_ts",)
    ).fetchone()
    if row is None:
        return 0
    return int(row["value"])


def set_last_candle_ts(db: Database, tf: str, ts: int):
    """Save the last processed candle timestamp for a timeframe."""
    with db.transaction() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            (f"last_{tf}_ts", str(ts)),
        )


def get_last_swing_end(db: Database, tf: str) -> Tuple[int, int]:
    """Get the last two swing endpoint timestamps for a timeframe.

    Returns (swing_1_ts, swing_2_ts) where:
      - swing_1_ts = most recent completed swing's end timestamp
      - swing_2_ts = previous completed swing's end timestamp (backup)

    Both are epoch seconds. 0 if not set.
    """
    row1 = db.conn.execute(
        "SELECT value FROM meta WHERE key = ?", (f"last_{tf}_swing_1",)
    ).fetchone()
    row2 = db.conn.execute(
        "SELECT value FROM meta WHERE key = ?", (f"last_{tf}_swing_2",)
    ).fetchone()
    ts1 = int(row1["value"]) if row1 else 0
    ts2 = int(row2["value"]) if row2 else 0
    return (ts1, ts2)


def set_last_swing_end(db: Database, tf: str, ts: int):
    """Save swing endpoint timestamp (rolling pair).

    On each call:
      swing_2 = swing_1  (shift back)
      swing_1 = ts       (push forward)

    This gives us redundancy: if swing_1 is corrupted, we have swing_2 as backup.
    """
    # Read current values
    row1 = db.conn.execute(
        "SELECT value FROM meta WHERE key = ?", (f"last_{tf}_swing_1",)
    ).fetchone()
    current_1 = int(row1["value"]) if row1 else 0

    # Shift: swing_2 = swing_1, swing_1 = new ts
    with db.transaction() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            (f"last_{tf}_swing_2", str(current_1)),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            (f"last_{tf}_swing_1", str(ts)),
        )

