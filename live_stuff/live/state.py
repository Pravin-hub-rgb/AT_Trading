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


def is_gray_leg(trade: dict | None) -> bool:
    return bool(trade and trade.get("exchange_state") == "gray")


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
from persistence.trade_store import open_ltf_trade, close_ltf_trade, get_open_ltf_trade, get_open_ltf_trades, get_ltf_trades
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



class StateMixin:
    """state responsibilities."""

    def _compute_chop(self) -> float:
        """Chop index for current 1h window (Dreiss, 14-bar). Mirrors v18_streak_halt.py:_chop_series_1h."""
        n = len(self.window_1h)
        if n < 15:
            return 50.0
        import math
        tr = [0.0] * n
        for i in range(n):
            hi = float(self.window_1h[i]["high"]); lo = float(self.window_1h[i]["low"])
            if i == 0:
                tr[i] = hi - lo
            else:
                pc = float(self.window_1h[i - 1]["close"])
                tr[i] = max(hi - lo, abs(hi - pc), abs(lo - pc))
        # Only need last chop value
        tr_sum = sum(tr[n - 14:n])
        hi_max = max(float(c["high"]) for c in self.window_1h[n - 14:n])
        lo_min = min(float(c["low"]) for c in self.window_1h[n - 14:n])
        rang = hi_max - lo_min
        if rang > 0 and tr_sum > 0:
            try:
                return 100 * math.log10(tr_sum / rang) / math.log10(14)
            except Exception:
                return 50.0
        return 50.0

    def _compute_atr_14(self) -> float:
        """ATR(14) for current 15m window in price units (mirrors v18 ATR)."""
        n = len(self.window_15m)
        if n == 0:
            return 0.0
        tr = [0.0] * n
        for i in range(n):
            hi = float(self.window_15m[i]["high"]); lo = float(self.window_15m[i]["low"])
            if i == 0:
                tr[i] = hi - lo
            else:
                pc = float(self.window_15m[i - 1]["close"])
                tr[i] = max(hi - lo, abs(hi - pc), abs(lo - pc))
        lo_i = max(0, n - 14)
        window = tr[lo_i:n]
        return sum(window) / len(window) if window else 0.0

    def _compute_regime(self) -> str:
        """Engine regime rule, mirrored from vendored unified (regime chain).

        The engine routes each bar into the window set by bucket NAME: mode
        atr_high → 'decisive' if ATR%(15m) > atr_high_thresh else 'flip',
        atr_low the opposite, chop modes by the chop index. Live mirrors the
        last closed bar so status/linkage describe the SAME window family the
        engine gates with, named the way the engine stamps it.
        """
        mode = (self.v18 or {}).get("mode", "chop")
        if mode == "atr_high":
            if self.atr_14 > 0 and self.window_15m:
                atrp = self.atr_14 / float(self.window_15m[-1]["close"]) * 100.0
                return "decisive" if atrp > float(self.v18.get("atr_high_thresh", 0.65)) else "flip"
            return "flip"
        if mode == "atr_low":
            if self.atr_14 > 0 and self.window_15m:
                atrp = self.atr_14 / float(self.window_15m[-1]["close"]) * 100.0
                return "decisive" if atrp < float(self.v18.get("atr_low_thresh", 0.65)) else "flip"
            return "flip"
        if mode == "b2_vs_flip_chop":
            return "b2" if self.chop_index > self._chop_thresh else "flip"
        return "decisive" if self.chop_index > self._chop_thresh else "flip"

    def _update_htf_metrics(self, price: float | None = None):
        """Recompute rolling HTF metrics: chop, ATR, regime, unrealized R."""
        # Only recompute chop/ATR when explicitly called (candle close)
        # On tick, only update unrealized R (price-dependent)
        if not hasattr(self, '_chop_stale') or self._chop_stale:
            try:
                self.chop_index = self._compute_chop()
            except Exception:
                self.chop_index = 50.0
            try:
                self.atr_14 = self._compute_atr_14()
            except Exception:
                self.atr_14 = 0.0
            self.regime = self._compute_regime()
            self._chop_stale = False
        # Unrealized R of each 1h window (flip and b2 tracked independently).
        # Consumers select the regime-appropriate one via self.regime.
        if self.htf_window_open and self.htf_hrisk > 1e-9:
            if price is None:
                price = float(self.window_15m[-1]["close"]) if self.window_15m else self.htf_entry_px
            d = 1 if self.htf_window_dir == "long" else -1
            self.htf_current_r = (float(price) - self.htf_entry_px) * d / self.htf_hrisk
        else:
            self.htf_current_r = 0.0
        if self.htf_window_open_b2 and self.htf_hrisk_b2 > 1e-9:
            if price is None:
                price = float(self.window_15m[-1]["close"]) if self.window_15m else self.htf_entry_px_b2
            d = 1 if self.htf_window_dir_b2 == "long" else -1
            self.htf_current_r_b2 = (float(price) - self.htf_entry_px_b2) * d / self.htf_hrisk_b2
        else:
            self.htf_current_r_b2 = 0.0
        if self.htf_window_open_dec and self.htf_hrisk_dec > 1e-9:
            if price is None:
                price = float(self.window_15m[-1]["close"]) if self.window_15m else self.htf_entry_px_dec
            d = 1 if self.htf_window_dir_dec == "long" else -1
            self.htf_current_r_dec = (float(price) - self.htf_entry_px_dec) * d / self.htf_hrisk_dec
        else:
            self.htf_current_r_dec = 0.0

    def _active_htf(self) -> dict:
        """Active (regime-selected) HTF window fields.

        The engine gates each signal against the window set chosen by its
        per-bar regime rule (unified's regime chain: chop/atr_high/... bucket
        names decisive/flip/b2). This returns whichever window family the
        CURRENT regime selects, named like the engine's own buckets, so
        status/gate/diagnostics always describe the window the sim would
        actually use.
        """
        if self.regime == "decisive":
            return {
                "open": self.htf_window_open_dec, "dir": self.htf_window_dir_dec,
                "entry_px": self.htf_entry_px_dec, "sl": self.htf_sl_dec,
                "hrisk": self.htf_hrisk_dec, "r": self.htf_current_r_dec,
                "id": self.htf_window_id_dec, "tag": "DECISIVE",
            }
        if self.regime == "b2":
            return {
                "open": self.htf_window_open_b2, "dir": self.htf_window_dir_b2,
                "entry_px": self.htf_entry_px_b2, "sl": self.htf_sl_b2,
                "hrisk": self.htf_hrisk_b2, "r": self.htf_current_r_b2,
                "id": self.htf_window_id_b2, "tag": "B2",
            }
        return {
            "open": self.htf_window_open, "dir": self.htf_window_dir,
            "entry_px": self.htf_entry_px, "sl": self.htf_sl,
            "hrisk": self.htf_hrisk, "r": self.htf_current_r,
            "id": self.htf_window_id, "tag": "FLIP",
        }

    def _mark_htf_metrics_stale(self):
        """Mark chop/ATR as needing recomputation (call on candle close)."""
        self._chop_stale = True

    def _restore_htf_state(self):
        """Restore persisted HTF windows on boot (Phase 2.5 + Phase 15: full matrix).

        Restores ALL regime windows — flip, b2 and decisive are independent
        v7 runs and can be open simultaneously. The regime rule selects which
        one is active for metrics/status/linkage.
        """
        try:
            from persistence.trade_store import get_open_htf_window
            for regime in ("flip", "b2", "decisive"):
                row = get_open_htf_window(self.db, regime=regime)
                if not row:
                    continue
                sfx = {"flip": "", "b2": "_b2", "decisive": "_dec"}[regime]
                # M3: a window whose 16d cap passed while we were down cannot
                # still be alive — close it in the DB, never restore it.
                if time.time() > int(row["entry_ts"]) + CAP_DAYS * 86400:
                    from persistence.trade_store import close_htf_window
                    close_htf_window(self.db, int(row["id"]),
                                     int(row["entry_ts"]) + CAP_DAYS * 86400, "stale_cap")
                    print(f"[htf] {regime.upper()} window id={int(row['id'])} STALE-CAP at boot "
                          f"(started {self._to_ist_short(int(row['entry_ts']))}, 16d cap passed "
                          f"while down) — closed, not restored")
                    continue
                setattr(self, f"htf_window_open{sfx}", True)
                setattr(self, f"htf_window_dir{sfx}", row["direction"])
                setattr(self, f"htf_window_start_ts{sfx}", int(row["entry_ts"]))
                setattr(self, f"htf_window_id{sfx}", int(row["id"]))
                setattr(self, f"htf_entry_px{sfx}", float(row["entry_price"]))
                # Phase 15: read full matrix from DB (instant, no backfill needed)
                setattr(self, f"htf_sl{sfx}", float(row["sl_price"]))
                setattr(self, f"htf_hrisk{sfx}", float(row["hrisk"]))
                self._chop_stale = True
                self._update_htf_metrics()
                w = self._active_htf()
                print(f"[htf] Restored open {regime.upper()} window from DB: {row['direction']} @ {float(row['entry_price']):.2f} SL={float(row['sl_price']):.2f} hrisk={float(row['hrisk']):.2f} (id={int(row['id'])}) | active={w['tag']}")
        except Exception as e:
            print(f"[htf] restore failed: {e}")

    def _restore_ltf_trade(self):
        """Phase 15: Load all open LTF trades from DB on boot.

        Called once at startup. Subsequent reads use self._open_ltf_trades
        (instant). Cache is updated when trades open/close — no DB reads on
        every tick.
        """
        try:
            rows = get_open_ltf_trades(self.db)
            self._open_ltf_trades = {int(r["id"]): r for r in rows}
            self._open_ltf_trade = rows[-1] if rows else None
            if rows:
                print(f"[ltf] Restored {len(rows)} open trade(s) from DB")
                for row in rows:
                    tag = " GRAY" if self._is_gray_leg(row) else ""
                    print(f"[ltf]   {row['direction']} @ {row['entry_price']:.2f} "
                          f"SL={row['sl_current']:.2f} TP={row['tp_price']:.2f}{tag} (id={row['id']})")
        except Exception as e:
            print(f"[ltf] restore failed: {e}")

    @staticmethod
    def _is_gray_leg(trade: dict | None) -> bool:
        return is_gray_leg(trade)

    def _cache_ltf_trade_open(self, trade_id: int, direction: str, entry_ts: int,
                               entry_price: float, sl_initial: float, tp_price: float,
                               cap_ts: int, htf_window_id: int):
        """Phase 15: Update cache when trade opens."""
        rec = {
            "id": trade_id,
            "direction": direction,
            "entry_ts": entry_ts,
            "entry_price": entry_price,
            "sl_initial": sl_initial,
            "sl_current": sl_initial,
            "tp_price": tp_price,
            "cap_ts": cap_ts,
            "htf_window_id": htf_window_id,
            "status": "open",
            "qty": 0.0,
            "entry_order_id": None,
            "entry_order_link_id": None,
            "entry_fill_price": None,
            "sl_order_id": None,
            "sl_order_link_id": None,
            "sl_order_status": None,
            "exchange_state": "none",
            "exit_order_id": None,
            "exit_fill_price": None,
            "fee_paid": 0.0,
            "funding_paid": 0.0,
            "last_sync_ts": None,
        }
        self._open_ltf_trades[int(trade_id)] = rec
        self._open_ltf_trade = rec

    def _cache_ltf_trade_close(self, trade_id: int | None = None):
        """Phase 15: Clear one cached trade (default: primary), keep the rest."""
        if trade_id is None and self._open_ltf_trade:
            trade_id = int(self._open_ltf_trade["id"])
        if trade_id is not None:
            self._open_ltf_trades.pop(int(trade_id), None)
        if self._open_ltf_trades:
            self._open_ltf_trade = list(self._open_ltf_trades.values())[-1]
        else:
            self._open_ltf_trade = None

    def _cache_ltf_trade_exchange(self, trade_id: int, **fields):
        """Update cached per-leg exchange fields for one trade."""
        trade_id = int(trade_id)
        rec = self._open_ltf_trades.get(trade_id)
        if rec is None:
            return
        rec.update(fields)
        if self._open_ltf_trade and int(self._open_ltf_trade["id"]) == trade_id:
            self._open_ltf_trade = rec

    def _cache_ltf_trade_update_sl(self, new_sl: float, trade_id: int | None = None):
        """Phase 15: Update cached SL for one trade (default: primary)."""
        if trade_id is None and self._open_ltf_trade:
            trade_id = int(self._open_ltf_trade["id"])
        if trade_id is not None and int(trade_id) in self._open_ltf_trades:
            self._open_ltf_trades[int(trade_id)]["sl_current"] = new_sl
            if self._open_ltf_trade and int(self._open_ltf_trade["id"]) == int(trade_id):
                self._open_ltf_trade["sl_current"] = new_sl

    def _print_status(self):
        """Print current status (HTF bias, position, etc.) — Phase 2 rolling record."""
        # Refresh rolling metrics before printing (uses latest tick/close price)
        # NOTE: _chop_stale NOT set here — chop only recomputes on 1h candle close
        try:
            self._update_htf_metrics()
        except Exception:
            pass

        # Active (regime-selected) window: b2 when chop > thresh, else flip.
        w = self._active_htf()
        if w["open"]:
            # Show bias + entry + SL + R depth + chop + regime + levels
            # Levels: -1R = SL, 1.5R = ext_stop gate, 3R = target
            hrisk = w["hrisk"] if w["hrisk"] > 0 else 0.0
            d = 1 if w["dir"] == "long" else -1
            lvl_sl = w["sl"]
            lvl_15 = w["entry_px"] + 1.5 * hrisk * d if hrisk else 0.0
            lvl_3r = w["entry_px"] + 3.0 * hrisk * d if hrisk else 0.0
            htf_str = (
                f"HTF[{w['tag']}]: {w['dir'].upper()} @ {w['entry_px']:.2f} "
                f"SL={lvl_sl:.2f} (-1R) R={w['r']:+.2f} "
                f"[1.5R={lvl_15:.2f} 3R={lvl_3r:.2f}] "
                f"CHOP={self.chop_index:.1f} REGIME={self.regime.upper()} ATR={self.atr_14:.1f}"
            )
        else:
            htf_str = f"HTF: NO BIAS | CHOP={self.chop_index:.1f} REGIME={self.regime.upper()} ATR={self.atr_14:.1f}"

        trades = list(self._open_ltf_trades.values())
        if trades:
            legs = [f"{'GRAY ' if self._is_gray_leg(t) else ''}"
                    f"{t['direction']} @ {t['entry_price']:.2f} "
                    f"SL={t['sl_current']:.2f} TP={t['tp_price']:.2f}"
                    for t in trades]
            pos_str = f"POS: {len(legs)} open | " + " | ".join(legs)
        else:
            pos_str = "POS: FLAT"

        cd_str = f"CD: {self.trading_state['cooldown_remaining']}" if self.trading_state["cooldown_remaining"] > 0 else ""

        print(f"[status] {htf_str} | {pos_str} {cd_str}".strip())
        # Also log gate status (regime-appropriate window)
        if w["open"]:
            gate = "BLOCKED (>1.5R)" if w["r"] > 1.5 else "OPEN"
            print(f"[gate] {w['tag']} ext_stop 1.5R: {gate} (current {w['r']:+.2f}R)")
        # Cost summary
        if self._trade_count > 0:
            print(f"[cost] {self._trade_count} trades | cum cost: {self._cum_cost_r:.2f}R | cum net: {self._cum_net_r:+.2f}R | avg cost: {self._cum_cost_r/self._trade_count:.3f}R")

    def _print_open_marks(self, tf: str, engine):
        """Print new breaks from the open (unconfirmed) swing — deduped."""
        try:
            open_sw = engine.get_open_swing()
            if not open_sw:
                return
            for b in open_sw.get("breaks", []):
                key = (tf, b.get("idx", -1), b.get("kind", ""), b.get("dir", ""), open_sw.get("swing_index", -1))
                if key not in self._printed_marks:
                    self._printed_marks.add(key)
                    print(f"[mark] {tf} {b['kind']} {b['dir']} sw{open_sw['swing_index']} @ {b['px']:.2f} ({b['time']}) [OPEN]")
        except Exception:
            pass

    def _get_existing_trades_set(self) -> set:
        trades = get_ltf_trades(self.db)
        return {(t["entry_ts"], t["direction"]) for t in trades}

    def _get_existing_marks_set(self, tf: str) -> set:
        from persistence.mark_store import get_marks
        marks = get_marks(self.db, tf)
        return {(m.ts, m.kind, m.direction, m.swing_no) for m in marks}

    def _insert_mark(self, mark: dict):
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO marks (ts, tf, kind, direction, price, swing_no, swing_kind, algo_version, journaled_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (mark["ts"], mark["tf"], mark["kind"], mark["dir"], mark["px"], mark["swing_no"], mark.get("swing_kind", ""), 1, int(time.time())),
            )
