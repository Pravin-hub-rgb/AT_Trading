"""State store - save and load trading state.

Single responsibility: persist cooldown/halt state to/from SQLite.
"""

import time
from typing import Optional
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

