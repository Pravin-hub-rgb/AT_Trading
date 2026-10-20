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



class TradingMixin:
    """trading responsibilities."""

    def on_tick(self, price: float, ts: int):
        """Process a price tick. Check SL/TP/cap for open trades.

        Phase 15: Uses cached trade (instant, no DB reads on every tick).
        Cache is updated on trade open/close/trail from DB writes.
        """
        open_trade = self._open_ltf_trade
        if not open_trade:
            return

        entry_price = float(open_trade["entry_price"])
        sl_initial = float(open_trade["sl_initial"])
        sl_current = float(open_trade["sl_current"])
        direction = open_trade["direction"]
        risk = abs(entry_price - sl_initial)
        if risk <= 0:
            return

        # Use current HTF candle's open as gap reference if available
        # Fallback to entry_price if window is tiny
        try:
            gap_open = float(self.window_15m[-1]["open"]) if self.window_15m else price
        except Exception:
            gap_open = price

        if ts >= open_trade["cap_ts"]:
            # Cap: fill at current price (time exit)
            r = self._calc_r(direction, entry_price, price, risk)
            # C1/C2: close the EXCHANGE position first; record the exit in DB
            # only after the close is confirmed. On failure, keep the trade
            # open in DB/cache — on_tick retries on the next tick.
            # H10: guard on `self.trader` only — not `is_connected` (which
            # was a live probe). If session is dead, _execute_exit returns
            # False via close_position_retry → caller retries next tick.
            if self.trader:
                if not self._execute_exit("cap", price):
                    print("[trade] Cap exit pending: exchange close failed — will retry next tick")
                    return
            closed_now = close_ltf_trade(self.db, open_trade["id"], ts, price, "cap", r)
            if closed_now == 0:
                # C4: already closed elsewhere — skip accounting, clear cache
                self._cache_ltf_trade_close()
                return
            print(f"[trade] Cap hit: {price:.2f} ({r:+.2f}R)")
            self._check_daily_loss_limit(r)
            self._cache_ltf_trade_close()
            try:
                self._persist_streak_state()
            except Exception:
                pass
            return

        sl_hit = (direction == "long" and price <= sl_current) or (direction == "short" and price >= sl_current)
        if sl_hit:
            # Conservative fill like v18: min(sl, open) for long, max(sl, open) for short
            if direction == "long":
                fill = min(sl_current, gap_open) if gap_open <= sl_current else sl_current
            else:
                fill = max(sl_current, gap_open) if gap_open >= sl_current else sl_current
            r = self._calc_r(direction, entry_price, fill, risk)
            # ATR-scaled tolerance (4.3): trail if SL has ratcheted meaningfully
            tol = max(0.01, self.atr_14 * 0.05, risk * 0.002) if self.atr_14 else max(0.01, risk * 0.002)
            reason = "trail" if abs(sl_current - sl_initial) > tol else "sl"
            # C1/C2: close the EXCHANGE position first; record the exit in DB
            # only after the close is confirmed. On failure, keep the trade
            # open in DB/cache — on_tick retries on the next tick.
            # H10: same as cap guard — always attempt exchange close.
            if self.trader:
                if not self._execute_exit(reason, fill):
                    print(f"[trade] {reason.upper()} exit pending: exchange close failed — will retry next tick")
                    return
            closed_now = close_ltf_trade(self.db, open_trade["id"], ts, fill, reason, r)
            if closed_now == 0:
                # C4: already closed elsewhere — skip accounting, clear cache
                self._cache_ltf_trade_close()
                return
            print(f"[trade] {reason.upper()} hit: {fill:.2f} (tick {price:.2f}, {r:+.2f}R)")
            self._check_daily_loss_limit(r)
            self._cache_ltf_trade_close()
            try:
                self._persist_streak_state()
            except Exception:
                pass
            return

    def _trail_sl(self, sw15: list[dict]):
        """Trail SL using _trail_events_ts — mirrors v18_streak_halt.py:234-267.

        Uses timestamp-based event activation instead of index-based,
        so trail works correctly even after window trims shift positions.

        Phase 15: Uses cached trade (instant). Updates cache on trail.
        """
        open_trade = self._open_ltf_trade
        if not open_trade or not self.window_15m:
            return

        direction = 1 if open_trade["direction"] == "long" else -1
        entry_ts = int(open_trade["entry_ts"])
        sl_initial = float(open_trade["sl_initial"])
        sl_current = float(open_trade["sl_current"])

        events = _trail_events_ts(sw15, direction)
        if not events:
            return

        # Already sorted by ts; ensure sorted
        events = sorted(events, key=lambda x: x[0])

        candle_ts = [int(c["ts"]) for c in self.window_15m]
        entry_idx = bisect.bisect_left(candle_ts, entry_ts)
        n = len(self.window_15m)
        if entry_idx < 0 or entry_idx >= n - 1:
            return

        # Forward walk: for each bar after entry, activate events whose
        # confirmed_at_ts <= bar ts. Timestamp-based = immune to window trims.
        new_sl = sl_current
        ev_idx = -1
        for j in range(entry_idx + 1, n):
            bar = self.window_15m[j]
            bar_ts = int(bar["ts"])
            lo = float(bar["low"])
            hi = float(bar["high"])
            # If price already beyond current SL, don't trail further (would have exited)
            if direction == 1 and lo <= new_sl:
                break
            if direction == -1 and hi >= new_sl:
                break
            while ev_idx + 1 < len(events) and events[ev_idx + 1][0] <= bar_ts:
                ev_idx += 1
                conf_ts, pivot_px = events[ev_idx]
                if conf_ts < entry_ts:
                    continue
                if direction == 1:
                    if new_sl < pivot_px < lo:
                        new_sl = pivot_px
                else:
                    if hi < pivot_px < new_sl:
                        new_sl = pivot_px

        if new_sl != sl_current:
            from persistence.trade_store import update_trade_sl
            update_trade_sl(self.db, open_trade["id"], new_sl)
            self._cache_ltf_trade_update_sl(new_sl)
            # Sync SL to Bybit exchange — keeps exchange-side conditional SL in sync
            bybit_synced = False
            if self.trader and self.trader.is_connected:
                for attempt in range(5):
                    try:
                        resp = self.trader.update_sl(new_sl)
                        if resp.get("retCode") == 0:
                            bybit_synced = True
                            break
                        else:
                            import time as _t
                            if attempt < 4:
                                delay = min(0.5 * (2 ** attempt) + random.uniform(0, 0.5), 8.0)
                                _t.sleep(delay)
                            else:
                                print(f"[trail] Bybit SL sync failed (5 attempts): {resp.get('retMsg', 'unknown')}")
                                if self._tg:
                                    self._tg.error(f"SL sync failed: DB={new_sl:.2f} exchange may differ")
                    except Exception as e:
                        if attempt >= 4:
                            print(f"[trail] Bybit SL sync error: {e}")
                            if self._tg:
                                self._tg.error(f"SL sync error: {e}")
            # Classify with ATR-scaled tolerance for log consistency
            tol = max(0.01, self.atr_14 * 0.05, abs(sl_initial - new_sl) * 0.001) if self.atr_14 else max(0.01, abs(sl_initial - new_sl) * 0.001)
            moved = abs(new_sl - sl_initial) > tol
            tag = "trail" if moved else "sl"
            r_gap = abs(new_sl - sl_initial) / abs(float(open_trade["entry_price"]) - sl_initial)
            sync_str = "Bybit OK" if bybit_synced else "DB only"
            print(f"[trail] SL {sl_current:.2f} -> {new_sl:.2f} ({tag}) {r_gap:.2f}R [{sync_str}]")
