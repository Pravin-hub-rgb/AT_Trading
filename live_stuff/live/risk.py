"""Book 107 live engine - vendored unified simulation on rolling windows.

Runs the same vendored simulate_htf_ltf_streak_halt the backtest uses,
on rolling windows of Binance or Bybit data. Produces identical trades.
"""

import os
import sys
import time
import asyncio
import logging
import random
from pathlib import Path
from datetime import datetime, timezone, timedelta
import bisect

import config
from rate_manager import RateManager

RISK_INR_FILE = Path(__file__).resolve().parents[1] / "risk_inr.txt"


def read_risk_inr() -> float:
    """Read risk amount in INR from risk_inr.txt. Edit file to change (no restart needed)."""
    try:
        val = float(RISK_INR_FILE.read_text().strip())
        if val > 0:
            return val
    except Exception:
        pass
    return config.DEFAULT_RISK_INR

from _vendored.btc_engine import _trail_events, _trail_events_ts
from _vendored.unified import simulate_htf_ltf_streak_halt
from _vendored.walker import FlowCandle
from _vendored.persistent_swing import PersistentSwingEngine
from data_streamer import BinanceStreamer, backfill_klines
from bybit_streamer import BybitStreamer, backfill_klines_bybit

from book import BOOK_NAME, BOOK_PARAMS, SWING, SWING_1H_LABEL, get_book_params
from persistence.database import Database
from persistence.mark_store import get_marks
from persistence.trade_store import open_ltf_trade, close_ltf_trade, get_open_ltf_trade, get_ltf_trades
from persistence.state_store import get_trading_state, save_trading_state, get_last_swing_end, set_last_swing_end

logger = logging.getLogger("live_loop")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Exchange routing
EXCHANGE_BINANCE = "binance"
EXCHANGE_BYBIT = "bybit"

SYMBOL = config.SYMBOL
WINDOW_DAYS_15M = config.WINDOW_DAYS_15M
WINDOW_DAYS_1H = config.WINDOW_DAYS_1H
CAP_DAYS = config.CAP_DAYS
IST = timedelta(hours=5, minutes=30)



class RiskMixin:
    """risk responsibilities."""

    def _persist_streak_state(self):
        """Phase 5: derive consecutive_losses/halted from DB trades and persist.

        Mirrors v18_streak_halt.py:326-334 (tail-loss count, halt on 5L, resume on win).
        Called after every _journal_trades so trading_state DB matches simulation.

        Cooldown: v18 uses bar-index (i - last_loss_bar < cooldown_bars) internally.
        Live uses cooldown_remaining countdown (decremented per 15m bar).
        last_loss_bar in DB is informational only (datetime string, not used for logic).
        """
        try:
            from persistence.trade_store import get_ltf_trades
            from datetime import datetime, timezone
            trades = get_ltf_trades(self.db)
            # Count tail consecutive losses (r_multiple <=0). Open trades ignored.
            consec = 0
            last_loss_dt = None
            for t in reversed(trades):
                if t["status"] != "closed":
                    continue
                # Skip seed-history trades — historical replay, not live streak.
                # BREAK (not continue): seed-history boundary is a natural stopping
                # point; losses across the seed/live boundary don't form one streak.
                if t.get("origin") == "seed_history":
                    break
                # Skip order failures — not real trading losses
                # Skip stale_skip — not a trade at all (C3: journaled-only entry)
                # Skip halted_skip — daily halt was active (C5: never executed)
                if t.get("exit_reason") in ("order_failed", "order_error", "stale_skip", "halted_skip"):
                    continue
                rm = t.get("r_multiple")
                if rm is None:
                    continue
                if float(rm) <= 0:
                    consec += 1
                    if last_loss_dt is None:
                        exit_ts = int(t.get("exit_ts", 0) or t.get("entry_ts", 0))
                        if exit_ts:
                            last_loss_dt = self._to_ist_short(exit_ts)
                else:
                    break
            max_losses = int(self.v18.get("max_consecutive_losses", 5) or 0)
            halted = bool(max_losses and consec >= max_losses)
            old_consec = int(self.trading_state.get("consecutive_losses", 0) or 0)
            self.trading_state["consecutive_losses"] = consec
            self.trading_state["halted"] = halted
            if consec:
                self.trading_state["last_loss_bar"] = last_loss_dt
            # Arm cooldown on new loss (not already counting this loss)
            # Always arm — backtest engine sets last_loss_bar on every loss regardless of halt state
            if consec > old_consec:
                cd_bars = int(self.v18.get("cooldown_bars", 0) or 0)
                if cd_bars > 0:
                    self.trading_state["cooldown_remaining"] = cd_bars
                    print(f"[cooldown] armed: {cd_bars} bars after loss #{consec}")
            # Persist
            save_trading_state(self.db, self.trading_state)
            if halted:
                print(f"[halt] STREAK HALT: {consec} consecutive losses — trading paused until next winner")
            elif consec:
                print(f"[streak] {consec} consecutive losses (halt at {max_losses})")
        except Exception as e:
            print(f"[streak] persist warning: {e}")

    def _maybe_reset_daily(self):
        """C5: time-based daily halt reset — independent of trade close.

        The daily halt must reset at IST midnight even when no trade closes:
        otherwise a halted bot with no post-midnight closes deadlocks forever
        (entries blocked -> no closes -> reset never fires).

        Called from __init__, _on_15m_close, _on_1h_close.
        _check_daily_loss_limit keeps its own date check as belt-and-suspenders.
        """
        today = (datetime.now(timezone.utc) + IST).strftime("%Y-%m-%d")
        if self._last_trade_date and self._last_trade_date != today:
            if self._daily_pnl_r < 0:
                print(f"[daily] New day — reset (yesterday: {self._daily_pnl_r:+.2f}R)")
            self._daily_pnl_r = 0.0
            self._daily_halted = False
            self._last_trade_date = today
            # Sync + persist immediately — a crash after the reset must not
            # resurrect yesterday's halt from the DB.
            self.trading_state["daily_pnl_r"] = 0.0
            self.trading_state["daily_halted"] = False
            self.trading_state["last_trade_date"] = today
            try:
                save_trading_state(self.db, self.trading_state)
            except Exception as e:
                print(f"[daily] reset persist failed: {e}")

    def _check_daily_loss_limit(self, r_multiple: float):
        """Check daily loss limit after a trade close.

        Tracks cumulative R for the day. If total losses exceed
        risk * DAILY_LOSS_MULTIPLIER, halts trading until next day.

        Resets at midnight (detected by date change).
        """
        try:
            from datetime import datetime, timezone
            today = (datetime.now(timezone.utc) + IST).strftime("%Y-%m-%d")

            # Reset on new day
            if self._last_trade_date and self._last_trade_date != today:
                if self._daily_pnl_r < 0:
                    print(f"[daily] New day — reset (yesterday: {self._daily_pnl_r:+.2f}R)")
                self._daily_pnl_r = 0.0
                self._daily_halted = False

            self._last_trade_date = today

            # Only count losses (negative R)
            if r_multiple < 0:
                self._daily_pnl_r += r_multiple  # r_multiple is negative

                # Check limit: DAILY_LOSS_MULTIPLIER in R units
                max_loss_r = -float(config.DAILY_LOSS_MULTIPLIER)  # e.g. -5.0R
                if self._daily_pnl_r <= max_loss_r:
                    self._daily_halted = True
                    loss_abs = abs(self._daily_pnl_r)
                    limit_abs = abs(max_loss_r)
                    print(f"[daily] 🛑 DAILY LOSS LIMIT BREACHED: {loss_abs:.0f}R lost (limit {limit_abs:.0f}R = {config.DAILY_LOSS_MULTIPLIER}x risk)")
                    if self._tg:
                        self._tg.daily_halt(loss_abs, limit_abs, config.DAILY_LOSS_MULTIPLIER)
        except Exception as e:
            print(f"[daily] check warning: {e}")
        # Persist daily state so it survives crash restart
        try:
            self.trading_state["daily_pnl_r"] = self._daily_pnl_r
            self.trading_state["daily_halted"] = self._daily_halted
            self.trading_state["last_trade_date"] = self._last_trade_date or ""
            save_trading_state(self.db, self.trading_state)
        except Exception:
            pass

    @staticmethod
    def _calc_r(direction: str, entry_price: float, exit_price: float, risk: float) -> float:
        """Calculate R multiple — mirrors v18_streak_halt.py:322-323."""
        if risk <= 0:
            return 0.0
        if direction == "long":
            return (exit_price - entry_price) / risk
        else:
            return (entry_price - exit_price) / risk
