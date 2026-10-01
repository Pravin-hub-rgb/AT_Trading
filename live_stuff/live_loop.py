"""Live loop - FULL v18 simulation on rolling windows.

Runs the EXACT same simulate_htf_ltf_streak_halt that the backtest uses,
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

RISK_INR_FILE = Path(__file__).resolve().parent / "risk_inr.txt"


def read_risk_inr() -> float:
    """Read risk amount in INR from risk_inr.txt. Edit file to change (no restart needed)."""
    try:
        val = float(RISK_INR_FILE.read_text().strip())
        if val > 0:
            return val
    except Exception:
        pass
    return config.DEFAULT_RISK_INR

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from src.btc.btc_engine import _trail_events, _trail_events_ts
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.walker import FlowCandle
from src.live.persistent_swing import PersistentSwingEngine
from src.live.data_streamer import BinanceStreamer, backfill_klines
from bybit_streamer import BybitStreamer, backfill_klines_bybit

from engine.v18_params import V18, V18_ENGINE, SWING, get_v18_params, SYMBOL_PARAMS
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


class LiveLoop:
    """Full v18 live trading loop."""

    def __init__(self, db: Database, exchange: str = EXCHANGE_BINANCE, symbol: str = SYMBOL,
                 paper_mode: bool = True, v18_instrument: str = None):
        self.db = db
        self._running = False
        self.exchange = exchange
        self.symbol = symbol
        self.v18_instrument = v18_instrument or symbol
        self.paper_mode = paper_mode
        self.window_15m: list[dict] = []
        self.window_1h: list[dict] = []
        self.trading_state = get_trading_state(db)
        # C9: v18 params are keyed by INSTRUMENT (the dataset they were tuned
        # on), NOT the exchange trading symbol. Bybit perp trading must bind
        # BTCUSDT_BYBIT (chop 58, cooldown 0, sl_buf 0.10, halt 3 — the
        # validated 261-trade config); binding the bare "BTCUSDT" silently ran
        # spot params (chop 61.8, cooldown 20, sl_buf 0.25, halt 5) — a
        # completely different strategy than the backtest.
        self.v18 = get_v18_params(self.v18_instrument)
        self._chop_thresh = self.v18.get("chop_thresh", 61.8)
        print(f"[live] v18 params: instrument={self.v18_instrument} "
              f"chop={self._chop_thresh} cooldown={self.v18.get('cooldown_bars')} "
              f"sl_buf={self.v18.get('sl_buf_atr')} halt={self.v18.get('max_consecutive_losses')}")
        self._cum_cost_r = 0.0
        self._cum_net_r = 0.0
        self._trade_count = 0
        # Persistent swing engines — use actual SwingEngine logic (same as backtest)
        self.swing_15m = PersistentSwingEngine("15m", db, {"minBars": SWING["min_bars_15m"], "timeCap": "00:00"})
        self.swing_1h = PersistentSwingEngine("1h", db, {"minBars": SWING["min_bars_1h"], "timeCap": "00:00"})
        self.all_swings_15m: list[dict] = []
        self.all_swings_1h: list[dict] = []
        # HTF window tracking — rolling record (Phase 2)
        self.htf_window_open = False
        self.htf_window_dir = None          # 'long' | 'short'
        self.htf_window_start_ts = 0
        self.htf_window_id: int | None = None
        self.htf_entry_px = 0.0
        self.htf_sl = 0.0
        self.htf_current_r = 0.0            # unrealized R of the 1h leg vs current 15m close
        self.htf_hrisk = 0.0                # abs(entry - sl) for R calc
        # B2 window tracking — independent v7 run, can be open simultaneously
        # with the flip window. `self.regime` (chop > thresh) selects which
        # window is ACTIVE for metrics/status/linkage.
        self.htf_window_open_b2 = False
        self.htf_window_dir_b2 = None       # 'long' | 'short'
        self.htf_window_start_ts_b2 = 0
        self.htf_window_id_b2: int | None = None
        self.htf_entry_px_b2 = 0.0
        self.htf_sl_b2 = 0.0
        self.htf_current_r_b2 = 0.0         # unrealized R of the b2 1h leg
        self.htf_hrisk_b2 = 0.0             # abs(entry - sl) for b2 R calc
        self.chop_index = 50.0              # current 1h chop (last value)
        self._chop_stale = True              # recompute on next _update_htf_metrics
        self.atr_14 = 0.0                   # current 15m ATR(14) in price units
        self.regime = 'flip'                # 'flip' or 'b2' (chop > thresh ? b2 : flip)
        # Dedup for open-swing mark printing (Phase 1.6)
        self._printed_marks: set = set()
        # Dedup for filter diagnostics (Phase 3)
        self._logged_filter_keys: set = set()
        # Rate manager (singleton, background refresh, disk cache)
        self.rate_manager = RateManager()
        # Seed file flag — when True, _journal_marks suppresses bulk historical print
        self._seeding = False
        self._session_dead_flag = False     # H6: background session health probe
        # Order execution (Bybit demo/live)
        self.trader = None
        if exchange == EXCHANGE_BYBIT and not paper_mode:
            try:
                from bybit_order import BybitTrader
                self.trader = BybitTrader()
                if self.trader.is_connected:
                    logger.info(f"Bybit trader connected — demo={self.trader.demo}")
                else:
                    logger.warning("Bybit trader init failed — order execution disabled")
            except Exception as e:
                logger.warning(f"BybitTrader import failed: {e}")
        # Telegram alerts
        self._tg = None
        try:
            from telegram_alert import TelegramAlert
            self._tg = TelegramAlert()
        except Exception:
            pass
        # Phase 15: Cached LTF trade (in-memory, no DB reads on every tick)
        self._open_ltf_trade: dict | None = None
        # Monotonic counters for g_idx (never decrease across window trims)
        self._bar_counter_15m: int = 0
        self._bar_counter_1h: int = 0
        # Daily loss limit tracking — restored from DB if available
        self._daily_pnl_r: float = self.trading_state.get("daily_pnl_r", 0.0)
        self._daily_halted: bool = self.trading_state.get("daily_halted", False)
        self._last_trade_date: str | None = self.trading_state.get("last_trade_date", "") or None
        # 1h boundary synchronization — atomic processing of 15m + 1h candles
        self._got_15m_boundary = False
        self._got_1h_boundary = False
        self._boundary_ts: int | None = None
        self._boundary_deadline: float | None = None
        # Restore persisted HTF window if any (Phase 2.5 + Phase 15: full matrix)
        self._restore_htf_state()
        # Phase 15: Load cached LTF trade from DB
        self._restore_ltf_trade()
        # Phase 15: Reconcile with Bybit position on startup
        self._reconcile_bybit_position()
        # C3: boot-time SL sync — if we're in a trade, force the exchange SL
        # to match the DB (closes the H9 gap: a pre-crash trail sync failure
        # would otherwise never self-correct, since the trail walk skips
        # updates when new_sl == sl_current).
        self._boot_sync_sl()
        # C5: time-based daily reset on boot (restart-after-midnight deadlock)
        self._maybe_reset_daily()

    def _boot_sync_sl(self):
        """One-shot exchange SL sync after restore + reconcile (C3/H9)."""
        if not (self._open_ltf_trade and self.trader and self.trader.is_connected):
            return
        try:
            sl_now = float(self._open_ltf_trade.get("sl_current", 0) or 0)
            if sl_now <= 0:
                return
            resp = self.trader.update_sl(sl_now)
            ok = resp.get("retCode") == 0
            print(f"[restore] SL synced to Bybit: {sl_now:.2f} -> {'OK' if ok else resp.get('retMsg', 'failed')}")
            if not ok and self._tg:
                self._tg.error(f"Boot SL sync FAILED: DB={sl_now:.2f} exchange may differ")
        except Exception as e:
            print(f"[restore] SL sync failed: {e}")

    async def _session_watch(self):
        """H6: Background session health probe — every 30s, alert on prolonged failure."""
        while self._running:
            await asyncio.sleep(30)
            if not self.trader:
                continue
            try:
                # M9: refresh the INR/USDT rate OFF the event loop. update()
                # does blocking HTTP (worst case ~20s for both sources) —
                # to_thread keeps the tick path responsive.
                await asyncio.to_thread(self.rate_manager.update)
            except Exception as e:
                logger.error(f"Rate refresh error: {e}")
            try:
                if not self.trader._probe():
                    if not self._session_dead_flag:
                        self._session_dead_flag = True
                        logger.warning("SESSION DOWN — attempting reconnect")
                        if self._tg:
                            self._tg.error("SESSION DOWN — attempting reconnect")
                        ok = self.trader._reconnect()
                        if ok:
                            self._session_dead_flag = False
                            logger.info("SESSION RECONNECTED")
                            if self._tg:
                                self._tg.error("SESSION RECONNECTED")
                        else:
                            logger.error("SESSION RECONNECT FAILED — check connection")
                            if self._tg:
                                self._tg.error("SESSION RECONNECT FAILED — check connection")
                else:
                    self._session_dead_flag = False
            except Exception as e:
                logger.error(f"Session watch error: {e}")

    async def _run_loop(self, max_seconds: float, started: float):
        """Main async loop — runs streamer and handles shutdown."""
        streamer_task = asyncio.create_task(self.streamer.start())
        session_watch_task = asyncio.create_task(self._session_watch())  # H6
        last_status = 0
        try:
            while self._running:
                if max_seconds and (time.time() - started) > max_seconds:
                    print(f"[live] Test window over ({max_seconds:.0f}s) - bye")
                    break
                # Print status every 30 seconds
                now = time.time()
                if now - last_status >= 30:
                    self._print_status()
                    last_status = now
                await asyncio.sleep(1)
        finally:
            # Graceful shutdown to avoid SSL errors
            await self.streamer.stop()
            session_watch_task.cancel()
            streamer_task.cancel()
            try:
                await session_watch_task
            except asyncio.CancelledError:
                pass
            try:
                await streamer_task
            except asyncio.CancelledError:
                pass

    # ------------------------------------------------------------------
    # Phase 2: HTF rolling record helpers — chop / ATR / regime / R depth
    # ------------------------------------------------------------------

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
            self.regime = "b2" if self.chop_index > self._chop_thresh else "flip"
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

    def _active_htf(self) -> dict:
        """Active (regime-selected) HTF window fields.

        v18 gates each signal against the window set chosen by chop at the
        signal bar: chop > thresh → b2 window, else flip window. This returns
        whichever window the CURRENT regime selects, so status/gate/diagnostics
        always describe the window the sim would actually use.
        """
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

        Restores BOTH regime windows — flip and b2 are independent v7 runs and
        can be open simultaneously. The regime switch selects which one is
        active for metrics/status/linkage.
        """
        try:
            from persistence.trade_store import get_open_htf_window
            for regime in ("flip", "b2"):
                row = get_open_htf_window(self.db, regime=regime)
                if not row:
                    continue
                sfx = "" if regime == "flip" else "_b2"
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
        """Phase 15: Load cached LTF trade from DB on boot.
        
        Called once at startup. Subsequent reads use self._open_ltf_trade (instant).
        Cache is updated when trades open/close — no DB reads on every tick.
        """
        try:
            row = get_open_ltf_trade(self.db)
            self._open_ltf_trade = row
            if row:
                print(f"[ltf] Restored open trade from DB: {row['direction']} @ {row['entry_price']:.2f} SL={row['sl_current']:.2f} TP={row['tp_price']:.2f} (id={row['id']})")
        except Exception as e:
            print(f"[ltf] restore failed: {e}")

    def _cache_ltf_trade_open(self, trade_id: int, direction: str, entry_ts: int,
                               entry_price: float, sl_initial: float, tp_price: float,
                               cap_ts: int, htf_window_id: int):
        """Phase 15: Update cache when trade opens."""
        self._open_ltf_trade = {
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
        }

    def _cache_ltf_trade_close(self):
        """Phase 15: Clear cache when trade closes."""
        self._open_ltf_trade = None

    def _cache_ltf_trade_update_sl(self, new_sl: float):
        """Phase 15: Update cached SL when trailing."""
        if self._open_ltf_trade:
            self._open_ltf_trade["sl_current"] = new_sl

    def _reconcile_bybit_position(self):
        """Phase 15: Reconcile DB trade state with Bybit exchange position on startup.
        
        Handles 4 cases:
          DB open + Bybit has position -> resume (OK)
          DB open + Bybit flat -> Bybit SL/TP hit during crash -> close DB record
          DB flat + Bybit has position -> orphan position -> close on Bybit
          DB flat + Bybit flat -> OK
        """
        if not self.trader or not self.trader.is_connected:
            return

        try:
            exchange_pos = self.trader.get_position()
        except Exception as e:
            print(f"[reconcile] Bybit position query failed: {e}")
            return

        db_trade = self._open_ltf_trade

        if db_trade and exchange_pos:
            # Both have positions — verify direction matches
            db_dir = db_trade["direction"]
            ex_dir = "long" if exchange_pos["side"] == "Buy" else "short"
            if db_dir == ex_dir:
                print(f"[reconcile] OK — DB and Bybit both have {db_dir} position")
            else:
                print(f"[reconcile] MISMATCH — DB={db_dir} but Bybit={ex_dir}. Closing DB record.")
                exit_price = float(db_trade["sl_current"])
                r = self._calc_r(
                    db_trade["direction"],
                    float(db_trade["entry_price"]),
                    exit_price,
                    float(db_trade["sl_initial"]),
                )
                close_ltf_trade(
                    self.db, db_trade["id"], int(time.time()),
                    exit_price, "reconcile", r,
                )
                self._cache_ltf_trade_close()


        elif db_trade and not exchange_pos:
            # DB says open but Bybit is flat — SL/TP hit during crash
            exit_price = float(db_trade["sl_current"])
            entry_price = float(db_trade["entry_price"])
            sl_initial = float(db_trade["sl_initial"])
            risk = abs(entry_price - sl_initial)
            direction = db_trade["direction"]
            r = self._calc_r(direction, entry_price, exit_price, risk) if risk > 0 else 0.0
            print(f"[reconcile] DB has open trade but Bybit is flat. Closing DB record (exit≈{exit_price:.2f}, {r:+.2f}R).")
            close_ltf_trade(
                self.db, db_trade["id"], int(time.time()),
                exit_price, "reconcile", r,
            )
            self._cache_ltf_trade_close()

        elif not db_trade and exchange_pos:
            # Orphan position on Bybit — close it
            ex_dir = "long" if exchange_pos["side"] == "Buy" else "short"
            print(f"[reconcile] Bybit has orphan {ex_dir} position (size={exchange_pos['size']}). Closing.")
            try:
                self.trader.close_position()
            except Exception as e:
                print(f"[reconcile] Failed to close orphan position: {e}")

        else:
            # Both flat — OK
            pass

    def _log_signal_diagnostics(self, sw15: list[dict], c15: list[dict], ltf_trades: list[dict]):
        """Phase 3: per-signal filter diagnostics — WHY each signal was skipped/taken.

        Mirrors v18's regime/window/ext_stop/cooldown gates but uses the live
        rolling HTF tracker state (htf_window_open, chop, regime, hrisk) so
        the log matches what a live operator sees.
        """
        try:
            from src.btc.btc_engine import _collect_signals
        except Exception:
            return
        # Filtered signals from _collect_signals (filter_pre_fs=True by default)
        try:
            raw_sigs = _collect_signals(sw15, "decisive", skip_first=True, selection="stream", candles=c15)
        except Exception as e:
            print(f"[filter] _collect_signals failed: {e}")
            return
        if not raw_sigs:
            return
        # Build set of taken entry_ts for quick lookup
        taken_ts = {int(t["entry_ts"]) for t in ltf_trades}
        # Cooldown state
        cd_rem = int(self.trading_state.get("cooldown_remaining", 0) or 0)
        # Only log signals that are new since last call, to avoid spam on full seed replay
        new_sigs = []
        for s in raw_sigs:
            k = (int(s["bar"]), s.get("kind", ""), int(s["dir"]))
            if k not in self._logged_filter_keys:
                new_sigs.append(s)
        # On first seed, raw_sigs may be 50+ — cap to last 5 new
        if len(new_sigs) > 5:
            # Mark older as seen without logging
            for s in new_sigs[:-5]:
                self._logged_filter_keys.add((int(s["bar"]), s.get("kind", ""), int(s["dir"])))
            new_sigs = new_sigs[-5:]
        if not new_sigs:
            return
        to_log = new_sigs
        for sig in to_log:
            self._logged_filter_keys.add((int(sig["bar"]), sig.get("kind", ""), int(sig["dir"])))
            bar = int(sig["bar"])
            if bar >= len(c15):
                continue
            candle = c15[bar]
            ts = int(candle["ts"])
            date = candle.get("date", str(ts))
            kind = sig.get("kind", "?")
            sdir = "long" if int(sig["dir"]) == 1 else "short"
            px = float(candle["close"])
            # Compute ext R using the ACTIVE (regime-selected) HTF window —
            # v18 gates each signal against the window set chosen by chop at
            # the signal bar (b2 when chop > thresh, else flip).
            w = self._active_htf()
            ext_r_str = "n/a"
            ext_r_val = None
            if w["open"] and w["hrisk"] > 1e-9:
                d = 1 if w["dir"] == "long" else -1
                ext_r_val = (px - w["entry_px"]) * d / w["hrisk"]
                ext_r_str = f"{ext_r_val:+.2f}R"
            # Gate checks in order (same order as v18: window, dir, ext_stop, cooldown)
            reason = None
            outcome = "PASS"
            if not w["open"]:
                outcome = "REJECT"
                reason = f"no {w['tag']} HTF window"
            elif sdir != w["dir"]:
                outcome = "REJECT"
                reason = f"dir mismatch (sig {sdir} vs HTF {w['dir']})"
            elif ext_r_val is not None and ext_r_val > self.v18["ext_stop_r"]:
                outcome = "REJECT"
                reason = f"ext_stop {ext_r_str} > {self.v18['ext_stop_r']}R (late)"
            elif cd_rem > 0:
                # Cooldown: need to check per-signal bar distance, but for live we show remaining
                # We approximate: if cooldown >0, next signals are blocked
                # The v18 exact check is  bar - last_loss_bar < cooldown_bars
                # For live rolling log we just surface the remaining count
                outcome = "REJECT"
                reason = f"cooldown {cd_rem} bars left"
            elif ts in taken_ts or any(abs(ts - t) < 5 for t in taken_ts):
                outcome = "TAKEN"
                reason = "entered"
            else:
                # Passed all gates but not taken — likely busy_until (already in trade) or simulation chose not to enter
                # For live we treat as PASS (would be taken if flat)
                if any(t.get("outcome") == "open" for t in ltf_trades):
                    outcome = "REJECT"
                    reason = "already in trade (busy_until)"
                else:
                    outcome = "PASS"
                    reason = f"regime {self.regime} chop {self.chop_index:.1f}"
            # Also include regime info in log even when rejected, for observability
            flag = "B2" if self.regime == "b2" else "FLIP"
            print(f"[filter] {outcome:6} {kind} {sdir} @ {px:.2f} bar={bar} {date} | HTF[{w['tag']}] {w['dir'] or 'none'} {ext_r_str} gate {V18['ext_stop_r']}R | regime {flag} chop {self.chop_index:.1f} | {reason}")

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

        open_trade = self._open_ltf_trade
        if open_trade:
            pos_str = f"POS: {open_trade['direction']} @ {open_trade['entry_price']:.2f} SL={open_trade['sl_current']:.2f} TP={open_trade['tp_price']:.2f}"
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

    # ------------------------------------------------------------------
    # 1h boundary synchronization
    # ------------------------------------------------------------------
    _BOUNDARY_TIMEOUT = 2.5  # seconds — force fire if one candle missing

    @staticmethod
    def _is_1h_boundary(ts: int) -> bool:
        """True when a candle closes at a whole UTC hour (XX:00:00)."""
        return ts % 3600 == 0

    def _try_fire_boundary(self):
        """Run simulation only when BOTH 15m + 1h boundary candles have arrived.
        Has a hard timeout so the bot never gets stuck."""
        now = time.monotonic()

        # Timeout safety (one candle missing or delayed)
        if self._boundary_deadline and now > self._boundary_deadline:
            print(f"[boundary] TIMEOUT at {self._boundary_ts} | "
                  f"15m={self._got_15m_boundary} 1h={self._got_1h_boundary} → forcing simulation")
            self._fire_boundary_simulation()
            return

        # Both arrived → perfect
        if self._got_15m_boundary and self._got_1h_boundary:
            self._fire_boundary_simulation()

    def _fire_boundary_simulation(self):
        """Run simulation once with complete data and reset state."""
        self._update_htf_metrics()
        self._run_v18_simulation()
        # Reset
        self._got_15m_boundary = False
        self._got_1h_boundary = False
        self._boundary_ts = None
        self._boundary_deadline = None

    # ------------------------------------------------------------------
    # WebSocket callbacks
    # ------------------------------------------------------------------

    def _on_tick(self, price: float, ts_ms: int):
        """Handle real-time tick (for SL/TP monitoring) + rolling R update."""
        if self.window_15m:
            try:
                self.on_tick(price, ts_ms // 1000)
                # Rolling R update on every tick so status/gate is live
                # (either regime window — metrics computes the right one)
                if self.htf_window_open or self.htf_window_open_b2:
                    try:
                        self._update_htf_metrics(price=float(price))
                    except Exception:
                        pass
            except Exception as e:
                print(f"[live] on_tick error: {e}")

    def _on_15m_close(self, candle: dict):
        """Handle 15m candle close — feed to swing engine."""
        try:
            self._maybe_reset_daily()  # C5: midnight reset before sim/journal
            ts = candle["close_time"] // 1000
            date = self._to_ist_str(candle["open_time"])
            self.window_15m.append({"date": date, "ts": ts, "open": candle["open"],
                                     "high": candle["high"], "low": candle["low"], "close": candle["close"]})
            # Trim window
            cutoff = int(time.time()) - WINDOW_DAYS_15M * 86400
            self.window_15m = [c for c in self.window_15m if c["ts"] >= cutoff]
            # Cooldown decrement (Phase 3.4 — moved from dead _tick)
            if self.trading_state.get("cooldown_remaining", 0) > 0:
                self.trading_state["cooldown_remaining"] -= 1
                try:
                    save_trading_state(self.db, self.trading_state)
                except Exception:
                    pass
            # Feed to swing engine
            fc = FlowCandle(date=date, open=candle["open"], high=candle["high"],
                            low=candle["low"], close=candle["close"])
            g_idx = self._bar_counter_15m
            self._bar_counter_15m += 1
            result = self.swing_15m.process_bar(fc, g_idx)
            if result:
                self.all_swings_15m.append(result)
                # Save swing endpoint timestamp (use end_time, not end_idx — end_idx is a counter)
                try:
                    end_time = result["seg"].get("end_time", "")
                    if end_time:
                        from datetime import datetime as _dt
                        end_ts = int(_dt.strptime(end_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())
                        set_last_swing_end(self.db, "15m", end_ts)
                except Exception:
                    pass
                for b in result.get("breaks", []):
                    print(f"[mark] 15m {b['kind']} {b['dir']} sw{b['swing_no']} @ {b['px']:.2f} ({b['time']})")
            # Phase 1.6: print new marks from the open (unconfirmed) swing instantly
            self._print_open_marks("15m", self.swing_15m)
            self._chop_stale = True
            # 1h boundary: wait for 1h candle before running simulation
            if self._is_1h_boundary(ts):
                self._got_15m_boundary = True
                self._boundary_ts = ts
                self._boundary_deadline = time.monotonic() + self._BOUNDARY_TIMEOUT
                self._try_fire_boundary()
            else:
                self._update_htf_metrics()
                self._run_v18_simulation()
        except Exception as e:
            import traceback
            print(f"[live] _on_15m_close error: {e}")
            traceback.print_exc()

    def _on_1h_close(self, candle: dict):
        """Handle 1h candle close — feed to swing engine."""
        try:
            self._maybe_reset_daily()  # C5: midnight reset before sim/journal
            ts = candle["close_time"] // 1000
            date = self._to_ist_str(candle["open_time"])
            self.window_1h.append({"date": date, "ts": ts, "open": candle["open"],
                                    "high": candle["high"], "low": candle["low"], "close": candle["close"]})
            cutoff = int(time.time()) - WINDOW_DAYS_1H * 86400
            self.window_1h = [c for c in self.window_1h if c["ts"] >= cutoff]
            fc = FlowCandle(date=date, open=candle["open"], high=candle["high"],
                            low=candle["low"], close=candle["close"])
            g_idx = self._bar_counter_1h
            self._bar_counter_1h += 1
            result = self.swing_1h.process_bar(fc, g_idx)
            if result:
                self.all_swings_1h.append(result)
                # Save swing endpoint timestamp (use end_time, not end_idx — end_idx is a counter)
                try:
                    end_time = result["seg"].get("end_time", "")
                    if end_time:
                        from datetime import datetime as _dt
                        end_ts = int(_dt.strptime(end_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())
                        set_last_swing_end(self.db, "1h", end_ts)
                except Exception:
                    pass
                for b in result.get("breaks", []):
                    print(f"[mark]  1h {b['kind']} {b['dir']} sw{b['swing_no']} @ {b['px']:.2f} ({b['time']})")
            self._print_open_marks("1h", self.swing_1h)
            self._chop_stale = True
            # 1h boundary: wait for 15m candle before running simulation
            if self._is_1h_boundary(ts):
                self._got_1h_boundary = True
                self._boundary_ts = ts
                self._boundary_deadline = time.monotonic() + self._BOUNDARY_TIMEOUT
                self._try_fire_boundary()
            else:
                self._update_htf_metrics()
                self._run_v18_simulation()
        except Exception as e:
            import traceback
            print(f"[live] _on_1h_close error: {e}")
            traceback.print_exc()

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

    def stop(self):
        self._running = False

    # ------------------------------------------------------------------
    # Seeding — Phase 1.4
    # ------------------------------------------------------------------

    def _normalize_candles(self, raw: list[dict]) -> list[dict]:
        """Convert backfill_klines() output to normalized candle dicts.

        Uses IST wall-clock date strings to match the CSV convention
        (csv timestamps are IST wall-clock, e.g. '2025-01-01 05:30:00').
        ts is the real UTC epoch seconds (matching csv_config's derivation).
        """
        candles = []
        for c in raw:
            ts = int(c["close_time"]) // 1000
            utc_dt = datetime.fromtimestamp(int(c["open_time"]) // 1000, tz=timezone.utc)
            ist_dt = utc_dt + IST
            date = ist_dt.strftime("%Y-%m-%d %H:%M:%S")
            candles.append({
                "date": date, "ts": ts,
                "open": float(c["open"]), "high": float(c["high"]),
                "low": float(c["low"]), "close": float(c["close"]),
            })
        # Ensure sorted ascending
        candles.sort(key=lambda x: x["ts"])
        return candles

    def _try_load_seed_file(self) -> bool:
        """Load seed marks from docs/seed_marks.json if present.

        File says: 'these are marks, this is where it ends, now fetch data till now and be active'.
        Populates all_swings from file (source of truth) and primes _printed dedup so bulk isn't re-blasted.
        Returns True if file was used.
        """
        try:
            import json as _json
            candidates = [
                Path(__file__).resolve().parent / "docs" / "seed_marks.json",
                # seed_marks.json is backtest research, it moved to backtest/docs.
                # The second candidate used to be parents[1]/"live_stuff"/"docs",
                # which resolved to live_stuff/live_stuff/docs and never existed.
                Path(__file__).resolve().parents[1] / "backtest" / "docs" / "seed_marks.json",
            ]
            seed_path = None
            for p in candidates:
                if p.exists():
                    seed_path = p
                    break
            if not seed_path:
                return False
            data = _json.loads(seed_path.read_text())
            # Populate all_swings from file — convert to live format
            def _to_swings(lst):
                out = []
                for s in lst:
                    # Keep file's break idx as stored (relative to file's candle list, but live uses g_idx)
                    # Live g_idx will be re-aligned during replay, but breaks' idx will be offset.
                    # So we just keep swings as file gives them; live simulation uses them as-is for history,
                    # and open swing is built via engine replay.
                    out.append(s)
                return out
            file_sw = _to_swings(data.get("swings_15m", []))
            file_sw1h = _to_swings(data.get("swings_1h", []))
            if file_sw:
                self.all_swings_15m = file_sw
                print(f"[seed] Loaded {len(file_sw)} 15m swings from {seed_path.name} (cutoff {data.get('cutoff','?')})")
                # Prime dedup so file's marks aren't blasted as 'new' by _journal_marks
                for s in file_sw:
                    for b in s.get("breaks", []):
                        self._printed_marks.add(("15m", b.get("idx", -1), b.get("kind",""), b.get("dir",""), s.get("swing_index",-1)))
                        self._logged_filter_keys.add((int(b.get("idx",-1)), b.get("kind",""), 1 if b.get("dir")=="up" else -1))
            if file_sw1h:
                self.all_swings_1h = file_sw1h
                print(f"[seed] Loaded {len(file_sw1h)} 1h swings from {seed_path.name}")
            print(f"[seed] {data.get('note','')}")
            # Store cutoff for tail-only replay
            try:
                from datetime import datetime as _dt, timezone as _tz
                cutoff_str = data.get("cutoff", "")
                if cutoff_str:
                    dt = _dt.strptime(cutoff_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=_tz.utc)
                    self._seed_cutoff_ts = int(dt.timestamp())
                else:
                    self._seed_cutoff_ts = 0
            except Exception:
                self._seed_cutoff_ts = 0
            return bool(file_sw or file_sw1h)
        except Exception as e:
            print(f"[seed] file load skipped: {e}")
            return False



    def _seed_from_timestamps(self, ts_1h: str, ts_15m: str) -> dict:
        """Seed swing engines from user-provided timestamps.

        Design:
        - 15m: timestamp IS the first candle. No lookback. Fetch forward to now.
        - 1h:  timestamp IS the first candle for swing engine. But fetch 14 bars
              BEFORE it for chop calculation (14-bar Dreiss formula needs history).
        - Filter out live/incomplete candles (close_time > now).

        Returns summary dict with per-TF candle/swing counts.
        """
        print(f"[seed] Seeding: 1h={ts_1h}, 15m={ts_15m}")
        self._seeding = True

        # Reset engines to clean slate
        try:
            from src.firstswing import SwingEngine as _SE
            try:
                with self.db.transaction() as _conn:
                    _conn.execute("DELETE FROM meta WHERE key IN ('swing_state_15m','swing_state_1h')")
            except Exception:
                pass
            self.swing_15m.eng = _SE(self.swing_15m.opts)
            self.swing_15m.swing_index = 0
            self.swing_15m.next_start_pos = 0
            self.swing_1h.eng = _SE(self.swing_1h.opts)
            self.swing_1h.swing_index = 0
            self.swing_1h.next_start_pos = 0
            self.all_swings_15m = []
            self.all_swings_1h = []
            self._printed_marks = set()
            self._logged_filter_keys = set()
            self._bar_counter_15m = 0
            self._bar_counter_1h = 0
        except Exception as _e:
            print(f"[seed] engine reset warning: {_e}")

        result = {}

        # Parse timestamps to ms — IST wall-clock → UTC epoch
        def _to_ms(ts_str: str) -> int:
            dt_naive = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            dt_utc = dt_naive - IST
            return int(dt_utc.replace(tzinfo=timezone.utc).timestamp() * 1000)

        try:
            seed_15m_ms = _to_ms(ts_15m)
            seed_1h_ms = _to_ms(ts_1h)
        except ValueError as e:
            print(f"[seed] timestamp parse error: {e}")
            self._seeding = False
            return {"error": str(e)}

        now_ms = int(time.time() * 1000)

        # --- 15m: timestamp IS the first candle, no lookback ---
        try:
            print(f"[seed] 15m: first candle = {self._to_ist_str(seed_15m_ms)} (no lookback)")
            raw_15m = self._fetch_klines_from_sync(self.symbol, "15m", seed_15m_ms, limit=2000)
            # Filter out live/incomplete candle (close_time > now)
            raw_15m = [c for c in raw_15m if c.get("close_time", c.get("open_time", 0)) <= now_ms]
            print(f"[seed] 15m: {len(raw_15m)} candles (filtered live)")
            candles_15m = self._normalize_candles(raw_15m)
            if not candles_15m:
                print("[seed] 15m: NO candles returned — check exchange/time range")
                result["15m"] = {"error": "no candles"}
            else:
                first_ist = candles_15m[0].get("date", "?")
                last_ist = candles_15m[-1].get("date", "?")
                print(f"[seed] 15m range: {first_ist} -> {last_ist}")
                cutoff = int(time.time()) - WINDOW_DAYS_15M * 86400
                self.window_15m = [c for c in candles_15m if c["ts"] >= cutoff] or candles_15m
                for c in candles_15m:
                    fc = FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"])
                    g_idx = self._bar_counter_15m
                    self._bar_counter_15m += 1
                    result_15m = self.swing_15m.process_bar(fc, g_idx)
                    if result_15m:
                        self.all_swings_15m.append(result_15m)
                self._show_recent_marks(self.all_swings_15m, candles_15m, "15m")
                open15 = self.swing_15m.get_open_swing()
                if open15:
                    for b in open15.get("breaks", []):
                        key = ("15m", b.get("idx", -1), b.get("kind", ""), b.get("dir", ""), open15.get("swing_index", -1))
                        self._printed_marks.add(key)
                    print(f"[swing] 15m open: sw{open15['swing_index']} dir={open15['dir']} breaks={len(open15.get('breaks',[]))}")
                print(f"[seed] 15m: {len(candles_15m)} candles, {len(self.all_swings_15m)} swings")
                result["15m"] = {"candles": len(candles_15m), "swings": len(self.all_swings_15m),
                                 "open": {"dir": open15["dir"], "breaks": len(open15.get("breaks", []))} if open15 else None}
        except Exception as e:
            import traceback
            print(f"[seed] 15m seeding failed: {e}")
            traceback.print_exc()
            result["15m"] = {"error": str(e)}

        # --- 1h: fetch 14 bars BEFORE timestamp for chop, then process from there ---
        chop_lookback_ms = 15 * 3600 * 1000  # 15 bars × 1h (14-bar Dreiss + 1 for TR prev close)
        start_1h_ms = seed_1h_ms - chop_lookback_ms
        try:
            print(f"[seed] 1h: chop lookback = {self._to_ist_str(start_1h_ms)} -> seed = {self._to_ist_str(seed_1h_ms)}")
            raw_1h = self._fetch_klines_from_sync(self.symbol, "1h", start_1h_ms, limit=500)
            # Filter out live/incomplete candle
            raw_1h = [c for c in raw_1h if c.get("close_time", c.get("open_time", 0)) <= now_ms]
            print(f"[seed] 1h: {len(raw_1h)} candles (filtered live)")
            candles_1h = self._normalize_candles(raw_1h)
            if not candles_1h:
                print("[seed] 1h: NO candles returned")
                result["1h"] = {"error": "no candles"}
            else:
                first_ist = candles_1h[0].get("date", "?")
                last_ist = candles_1h[-1].get("date", "?")
                print(f"[seed] 1h range: {first_ist} -> {last_ist}")
                cutoff = int(time.time()) - WINDOW_DAYS_1H * 86400
                self.window_1h = [c for c in candles_1h if c["ts"] >= cutoff] or candles_1h
                # Find seed point index — lookback bars are for chop ONLY, not the swing engine
                seed_1h_sec = seed_1h_ms // 1000
                engine_start = 0
                for idx, c in enumerate(candles_1h):
                    if c["ts"] >= seed_1h_sec:
                        engine_start = idx
                        break
                print(f"[seed]  1h: engine starts at bar {engine_start} ({candles_1h[engine_start]['date']}), "
                      f"lookback {engine_start} bars for chop only")
                for i in range(engine_start, len(candles_1h)):
                    c = candles_1h[i]
                    fc = FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"])
                    g_idx = self._bar_counter_1h
                    self._bar_counter_1h += 1
                    result_1h = self.swing_1h.process_bar(fc, g_idx)
                    if result_1h:
                        self.all_swings_1h.append(result_1h)
                self._show_recent_marks(self.all_swings_1h, candles_1h, "1h")
                open1h = self.swing_1h.get_open_swing()
                if open1h:
                    for b in open1h.get("breaks", []):
                        key = ("1h", b.get("idx", -1), b.get("kind", ""), b.get("dir", ""), open1h.get("swing_index", -1))
                        self._printed_marks.add(key)
                    print(f"[swing]  1h open: sw{open1h['swing_index']} dir={open1h['dir']} breaks={len(open1h.get('breaks',[]))}")
                print(f"[seed]  1h: {len(candles_1h)} candles, {len(self.all_swings_1h)} swings")
                result["1h"] = {"candles": len(candles_1h), "swings": len(self.all_swings_1h),
                                "open": {"dir": open1h["dir"], "breaks": len(open1h.get("breaks", []))} if open1h else None}
        except Exception as e:
            import traceback
            print(f"[seed]  1h seeding failed: {e}")
            traceback.print_exc()
            result["1h"] = {"error": str(e)}

        self._seeding = False
        print(f"[seed] Seeded total: {len(self.all_swings_15m)} 15m swings, {len(self.all_swings_1h)} 1h swings")

        # Prime rolling metrics + initial v18 simulation
        try:
            self._chop_stale = True
            self._update_htf_metrics()
            if len(self.window_15m) >= SWING["min_bars_15m"] + 5 and len(self.window_1h) >= SWING["min_bars_1h"] + 5:
                self._seeding = True
                try:
                    self._run_v18_simulation()
                finally:
                    self._seeding = False
        except Exception as _e:
            print(f"[seed] post-seed prime warning: {_e}")
            self._seeding = False

        return result

    def _recover_from_crash(self) -> bool:
        """Recover state after crash by backfilling from last swing endpoint.

        Reads the rolling swing endpoint pair from DB (last_15m_swing_1/2 and
        last_1h_swing_1/2). Fetches candles from end_ts + 1 bar to now,
        replays through swing engine, re-runs v18 simulation.

        Returns True if recovery succeeded, False if no previous state exists.
        """
        last_15m_ts, prev_15m_ts = get_last_swing_end(self.db, "15m")
        last_1h_ts, prev_1h_ts = get_last_swing_end(self.db, "1h")

        if last_15m_ts == 0 and last_1h_ts == 0:
            return False  # No previous state — need timestamps from user

        print(f"[recover] Last swing endpoints: 15m={last_15m_ts} 1h={last_1h_ts}")
        if last_15m_ts == 0 and prev_15m_ts > 0:
            print(f"[recover] 15m: using backup swing_2 = {prev_15m_ts}")
            last_15m_ts = prev_15m_ts
        if last_1h_ts == 0 and prev_1h_ts > 0:
            print(f"[recover] 1h: using backup swing_2 = {prev_1h_ts}")
            last_1h_ts = prev_1h_ts

        self._seeding = True
        now_ms = int(time.time() * 1000)

        # Reset engines to clean slate
        try:
            from src.firstswing import SwingEngine as _SE
            try:
                with self.db.transaction() as _conn:
                    _conn.execute("DELETE FROM meta WHERE key IN ('swing_state_15m','swing_state_1h')")
            except Exception:
                pass
            self.swing_15m.eng = _SE(self.swing_15m.opts)
            self.swing_15m.swing_index = 0
            self.swing_15m.next_start_pos = 0
            self.swing_1h.eng = _SE(self.swing_1h.opts)
            self.swing_1h.swing_index = 0
            self.swing_1h.next_start_pos = 0
            self.all_swings_15m = []
            self.all_swings_1h = []
            self._printed_marks = set()
            self._logged_filter_keys = set()
            self._bar_counter_15m = 0
            self._bar_counter_1h = 0
        except Exception as _e:
            print(f"[recover] engine reset warning: {_e}")

        # --- 15m: fetch from swing_end + 1 bar to now ---
        if last_15m_ts > 0:
            try:
                step_ms = 900000  # 15 min
                start_15m_ms = (last_15m_ts * 1000) + step_ms
                ist_start = self._to_ist_str(start_15m_ms)
                print(f"[recover] 15m: fetching from {ist_start} (swing_end + 1 bar) to now")
                raw_15m = self._fetch_klines_from_sync(self.symbol, "15m", start_15m_ms, limit=2000)
                raw_15m = [c for c in raw_15m if c.get("close_time", c.get("open_time", 0)) <= now_ms]
                print(f"[recover] 15m: {len(raw_15m)} candles (filtered live)")
                candles_15m = self._normalize_candles(raw_15m)
                if candles_15m:
                    cutoff = int(time.time()) - WINDOW_DAYS_15M * 86400
                    self.window_15m = [c for c in candles_15m if c["ts"] >= cutoff] or candles_15m
                    for c in candles_15m:
                        fc = FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"])
                        g_idx = self._bar_counter_15m
                        self._bar_counter_15m += 1
                        result = self.swing_15m.process_bar(fc, g_idx)
                        if result:
                            self.all_swings_15m.append(result)
                    open15 = self.swing_15m.get_open_swing()
                    if open15:
                        for b in open15.get("breaks", []):
                            key = ("15m", b.get("idx", -1), b.get("kind", ""), b.get("dir", ""), open15.get("swing_index", -1))
                            self._printed_marks.add(key)
                        print(f"[recover] 15m open: sw{open15['swing_index']} dir={open15['dir']} breaks={len(open15.get('breaks',[]))}")
                    print(f"[recover] 15m: {len(candles_15m)} candles, {len(self.all_swings_15m)} swings")
            except Exception as e:
                import traceback
                print(f"[recover] 15m recovery failed: {e}")
                traceback.print_exc()

        # --- 1h: fetch from swing_end + 1 bar to now, with 15-bar lookback for chop ---
        if last_1h_ts > 0:
            try:
                step_ms = 3600000  # 1 hour
                chop_lookback_ms = 15 * 3600 * 1000  # 15 bars for chop (14-bar Dreiss + 1 TR prev close)
                start_1h_ms = (last_1h_ts * 1000) + step_ms
                fetch_start_1h_ms = start_1h_ms - chop_lookback_ms
                ist_start = self._to_ist_str(start_1h_ms)
                print(f"[recover] 1h: fetching from {ist_start} (swing_end + 1 bar + 15 lookback) to now")
                raw_1h = self._fetch_klines_from_sync(self.symbol, "1h", fetch_start_1h_ms, limit=500)
                raw_1h = [c for c in raw_1h if c.get("close_time", c.get("open_time", 0)) <= now_ms]
                print(f"[recover] 1h: {len(raw_1h)} candles (filtered live)")
                candles_1h = self._normalize_candles(raw_1h)
                if candles_1h:
                    cutoff = int(time.time()) - WINDOW_DAYS_1H * 86400
                    self.window_1h = [c for c in candles_1h if c["ts"] >= cutoff] or candles_1h
                    # Find engine start — lookback bars for chop only, not the swing engine
                    start_1h_sec = start_1h_ms // 1000
                    engine_start = 0
                    for idx, c in enumerate(candles_1h):
                        if c["ts"] >= start_1h_sec:
                            engine_start = idx
                            break
                    print(f"[recover]  1h: engine starts at bar {engine_start} ({candles_1h[engine_start]['date']}), "
                          f"lookback {engine_start} bars for chop only")
                    for i in range(engine_start, len(candles_1h)):
                        c = candles_1h[i]
                        fc = FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"])
                        g_idx = self._bar_counter_1h
                        self._bar_counter_1h += 1
                        result = self.swing_1h.process_bar(fc, g_idx)
                        if result:
                            self.all_swings_1h.append(result)
                    open1h = self.swing_1h.get_open_swing()
                    if open1h:
                        for b in open1h.get("breaks", []):
                            key = ("1h", b.get("idx", -1), b.get("kind", ""), b.get("dir", ""), open1h.get("swing_index", -1))
                            self._printed_marks.add(key)
                        print(f"[recover]  1h open: sw{open1h['swing_index']} dir={open1h['dir']} breaks={len(open1h.get('breaks',[]))}")
                    print(f"[recover]  1h: {len(candles_1h)} candles, {len(self.all_swings_1h)} swings")
            except Exception as e:
                import traceback
                print(f"[recover] 1h recovery failed: {e}")
                traceback.print_exc()

        self._seeding = False
        print(f"[recover] Seeded total: {len(self.all_swings_15m)} 15m swings, {len(self.all_swings_1h)} 1h swings")

        # Prime rolling metrics + initial v18 simulation
        try:
            self._chop_stale = True
            self._update_htf_metrics()
            if len(self.window_15m) >= SWING["min_bars_15m"] + 5 and len(self.window_1h) >= SWING["min_bars_1h"] + 5:
                self._seeding = True
                try:
                    self._run_v18_simulation()
                finally:
                    self._seeding = False
        except Exception as _e:
            print(f"[recover] post-recover prime warning: {_e}")
            self._seeding = False

        return True

    def _fetch_klines_from_sync(self, symbol: str, interval: str, start_ms: int, limit: int = 500) -> list[dict]:
        """Fetch klines from the configured exchange, starting from start_ms.

        Routes to Bybit or Binance based on self.exchange.
        """
        if self.exchange == EXCHANGE_BYBIT:
            from bybit_streamer import backfill_klines_bybit
            tf_map = {"1m": "1", "5m": "5", "15m": "15", "1h": "60", "4h": "240"}
            bybit_interval = tf_map.get(interval, interval)
            return backfill_klines_bybit(symbol, bybit_interval, limit=limit, demo=True, start_ms=start_ms)
        else:
            from data_streamer import fetch_klines_from
            import inspect as _inspect
            import asyncio as _asyncio
            res = fetch_klines_from(symbol, interval, start_ms, limit=limit)
            if _inspect.isawaitable(res):
                try:
                    loop = _asyncio.get_event_loop()
                    if loop.is_running():
                        import concurrent.futures as _cf
                        with _cf.ThreadPoolExecutor(max_workers=1) as _pool:
                            fut = _pool.submit(_asyncio.run, res)
                            return fut.result(timeout=30)
                    else:
                        return loop.run_until_complete(res)
                except RuntimeError:
                    return _asyncio.run(res)
            return res

    def _show_recent_marks(self, swings: list[dict], candles: list[dict], tf: str):
        """Show the most recent marks from seeding."""
        cutoff_ts = int(time.time()) - 7 * 86400
        # Build lookup by date string (stable across window trims, unlike idx)
        date_to_candle = {c["date"]: c for c in candles}
        recent_marks = []
        for s in swings:
            for b in s.get("breaks", []):
                mark_time = b.get("time", "")
                candle = date_to_candle.get(mark_time)
                if candle and candle["ts"] >= cutoff_ts:
                    recent_marks.append({
                        "date": candle["date"],
                        "kind": b["kind"],
                        "dir": b["dir"],
                        "px": b["px"],
                        "swing_no": s["swing_index"],
                    })
        if recent_marks:
            print(f"[marks] {tf} recent (last 7d):")
            for m in recent_marks[-15:]:
                print(f"  {m['date']} | {m['kind']:<4} {m['dir']:<4} sw{m['swing_no']} @ {m['px']:.2f}")

    @staticmethod
    def _to_ist_str(epoch_ms: int) -> str:
        """Convert epoch ms to IST display string (wall-clock for all logs)."""
        utc_dt = datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)
        ist_dt = utc_dt + IST
        return ist_dt.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _to_ist_short(epoch_s: int) -> str:
        """Convert epoch seconds to IST short string (YYYY-MM-DD HH:MM)."""
        utc_dt = datetime.fromtimestamp(epoch_s, tz=timezone.utc)
        ist_dt = utc_dt + IST
        return ist_dt.strftime("%Y-%m-%d %H:%M")

    # ------------------------------------------------------------------
    # v18 simulation + journaling
    # ------------------------------------------------------------------

    def _rebase_swings_to_window(self, swings: list[dict], window: list[dict]) -> list[dict]:
        """L3: rebase swing indices from g_idx space into `window` positions.

        all_swings_* carry monotonic g_idx (seed counters). window_* is a
        trimmed rolling list whose positions restart on every trim. Passing
        the two spaces into the sim silently drops every signal (C10 L3).
        Times on PSE swings are the natural keys — remap idx fields via them.
        """
        if not window or not swings:
            return list(swings or [])
        date_to_pos = {c["date"]: i for i, c in enumerate(window)}
        w0 = window[0]["date"]
        w1 = window[-1]["date"]
        n = len(window)
        out: list[dict] = []
        for s in swings:
            s2 = dict(s)
            seg = dict(s.get("seg") or {})

            st = str(seg.get("start_time") or "")
            if st:
                if st in date_to_pos:
                    seg["start_idx"] = date_to_pos[st]
                elif st < w0:
                    seg["start_idx"] = 0
                elif st > w1:
                    continue
                else:
                    seg["start_idx"] = 0

            et = str(seg.get("end_time") or "")
            if et:
                if et in date_to_pos:
                    seg["end_idx"] = date_to_pos[et]
                elif et < w0:
                    # ended before window — keep for prev_end/pre_fs context
                    seg["end_idx"] = -1
                elif et > w1:
                    seg["end_idx"] = n - 1
                else:
                    seg["end_idx"] = n - 1
            elif seg.get("end_idx") is None:
                seg["end_idx"] = -1

            if seg.get("start_idx") is None:
                continue

            ct = s.get("confirmed_at_time")
            if ct:
                ct = str(ct)
                if ct in date_to_pos:
                    s2["confirmed_at_idx"] = date_to_pos[ct]
                elif ct < w0:
                    s2["confirmed_at_idx"] = 0
                elif ct > w1:
                    s2["confirmed_at_idx"] = n - 1

            ft = s.get("fs_at_time")
            if ft:
                ft = str(ft)
                if ft in date_to_pos:
                    s2["fs_at_idx"] = date_to_pos[ft]

            nb = []
            for b in s.get("breaks") or []:
                bt = str(b.get("time") or "")
                if bt and bt in date_to_pos:
                    b2 = dict(b)
                    b2["idx"] = date_to_pos[bt]
                    nb.append(b2)
            s2["breaks"] = nb
            s2["seg"] = seg
            out.append(s2)
        return out

    def _run_v18_simulation(self):
        if len(self.window_15m) < SWING["min_bars_15m"] + 5 or len(self.window_1h) < SWING["min_bars_1h"] + 5:
            print(f"[live] windows too small: 15m={len(self.window_15m)} 1h={len(self.window_1h)}")
            return

        c15 = self.window_15m
        c1h = self.window_1h
        # L3: indices must live in the same space as the trimmed windows
        sw15 = self._rebase_swings_to_window(self.all_swings_15m, c15)
        sw1h = self._rebase_swings_to_window(self.all_swings_1h, c1h)
        # L5: forming swing's marks are invisible to the declared-only chain
        try:
            open15 = self.swing_15m.get_open_swing()
            if open15 and open15.get("breaks"):
                rebased_open = self._rebase_swings_to_window([open15], c15)
                if rebased_open:
                    sw15 = sw15 + rebased_open
            open1h = self.swing_1h.get_open_swing()
            if open1h and open1h.get("breaks"):
                rebased_open1h = self._rebase_swings_to_window([open1h], c1h)
                if rebased_open1h:
                    sw1h = sw1h + rebased_open1h
        except Exception as _oe:
            print(f"[live] open-swing append warning: {_oe}")

        try:
            result = simulate_htf_ltf_streak_halt(
                c1h, sw1h, c15, sw15,
                fine_ltf=[],
                sl_buf_atr=self.v18["sl_buf_atr"],
                ext_stop_r=self.v18["ext_stop_r"],
                mode=self.v18["mode"],
                chop_thresh=self.v18["chop_thresh"],
                cooldown_bars=self.v18["cooldown_bars"],
                max_consecutive_losses=self.v18["max_consecutive_losses"],
            )
        except Exception as e:
            import traceback
            print(f"[live] v18 simulation error: {e}")
            traceback.print_exc()
            return

        ltf_trades = result["ltf_trades"]
        htf_trades = result.get("htf_trades", [])
        htf_trades_b2 = result.get("htf_trades_b2", [])

        # Track HTF window state (flip + b2 tracked independently)
        self._track_htf_windows(htf_trades, htf_trades_b2, c1h)

        self._journal_marks("15m", sw15, c15)
        self._journal_marks("1h", sw1h, c1h)
        self._journal_trades(ltf_trades)
        self._persist_streak_state()
        self._trail_sl(sw15)
        # Phase 3: per-signal filter diagnostics (regime/window/ext_stop/cooldown)
        try:
            self._log_signal_diagnostics(sw15, c15, ltf_trades)
        except Exception as _e:
            print(f"[filter] diagnostics warning: {_e}")

        # Log summary — active (regime-selected) window
        w = self._active_htf()
        htf_status = "OPEN" if w["open"] else "CLOSED"
        htf_dir = w["dir"] if w["open"] else "none"
        print(f"[live] v18: {len(sw15)} 15m sw, {len(sw1h)} 1h sw, {len(ltf_trades)} LTF trades | HTF[{w['tag']}]: {htf_status} {htf_dir}")

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

    def _track_htf_windows(self, htf_trades: list[dict], htf_trades_b2: list[dict],
                           c1h: list[dict]):
        """Track and log HTF window state changes — Phase 2 rolling record.

        Persists open/close to htf_windows table so state survives restarts.
        Flip and b2 windows are tracked INDEPENDENTLY — they come from separate
        v7 runs and can be open simultaneously. The regime switch (chop vs
        thresh) selects which one is active for metrics/status/linkage.

        An empty trade list for a regime means no trades for it in this window
        slice — that regime's window state is preserved as-is (a truncated seed
        may miss an older entry, cap 16d).
        """
        if htf_trades:
            self._track_window_regime("flip", htf_trades)
        if htf_trades_b2:
            self._track_window_regime("b2", htf_trades_b2)
        self._update_htf_metrics()

    def _track_window_regime(self, regime: str, htf_trades: list[dict]):
        """Track open/close of ONE regime's HTF window (flip or b2).

        Mirrors the Phase 2 tracker but parameterized by regime so both window
        families share identical open/close/persist logic.
        """
        sfx = "" if regime == "flip" else "_b2"
        latest_htf = htf_trades[-1]
        htf_status = latest_htf.get("outcome", "open")
        entry_ts = int(latest_htf.get("entry_ts", 0))
        entry_date = self._to_ist_short(entry_ts) if entry_ts else "?"
        entry_px = float(latest_htf.get("entry_price", 0.0))
        sl_px = float(latest_htf.get("sl", 0.0))
        hrisk = abs(entry_px - sl_px) if sl_px else 0.0

        open_flag = getattr(self, f"htf_window_open{sfx}")
        win_id = getattr(self, f"htf_window_id{sfx}")

        if htf_status == "open" and not open_flag:
            setattr(self, f"htf_window_open{sfx}", True)
            setattr(self, f"htf_window_dir{sfx}", latest_htf.get("dir"))
            setattr(self, f"htf_window_start_ts{sfx}", entry_ts)
            setattr(self, f"htf_entry_px{sfx}", entry_px)
            setattr(self, f"htf_sl{sfx}", sl_px)
            setattr(self, f"htf_hrisk{sfx}", hrisk)
            d = 1 if latest_htf.get("dir") == "long" else -1
            lvl_15 = entry_px + 1.5 * hrisk * d if hrisk else 0.0
            lvl_3r = entry_px + 3.0 * hrisk * d if hrisk else 0.0
            # Persist open window with full matrix (Phase 15)
            try:
                from persistence.trade_store import open_htf_window
                cap_ts = entry_ts + CAP_DAYS * 86400
                new_id = open_htf_window(
                    self.db, latest_htf.get("dir"), entry_ts, entry_px, cap_ts,
                    sl_price=sl_px, hrisk=hrisk, lvl_1_5r=lvl_15, lvl_3r=lvl_3r,
                    regime=regime,
                )
                setattr(self, f"htf_window_id{sfx}", new_id)
            except Exception as e:
                print(f"[htf] persist open failed: {e}")
            # Compute metrics right after open
            self._chop_stale = True
            self._update_htf_metrics()
            print(f"[htf] {regime.upper()} Window OPENED: {latest_htf.get('dir')} @ {entry_px:.2f} SL={sl_px:.2f} (-1R) 1.5R={lvl_15:.2f} 3R={lvl_3r:.2f} ({entry_date}) CHOP={self.chop_index:.1f} {self.regime.upper()}")
        elif htf_status != "open" and open_flag:
            exit_ts = int(latest_htf.get("exit_ts", 0))
            exit_date = self._to_ist_short(exit_ts) if exit_ts else "?"
            try:
                from persistence.trade_store import close_htf_window
                if win_id is not None:
                    close_htf_window(self.db, win_id, exit_ts or int(time.time()), latest_htf.get("outcome", "closed"))
            except Exception as e:
                print(f"[htf] persist close failed: {e}")
            print(f"[htf] {regime.upper()} Window CLOSED: {latest_htf.get('outcome')} @ {latest_htf.get('exit_price', 0):.2f} ({exit_date}, {latest_htf.get('r_multiple', 0):+.2f}R)")
            setattr(self, f"htf_window_open{sfx}", False)
            setattr(self, f"htf_window_dir{sfx}", None)
            setattr(self, f"htf_window_start_ts{sfx}", 0)
            setattr(self, f"htf_entry_px{sfx}", 0.0)
            setattr(self, f"htf_sl{sfx}", 0.0)
            setattr(self, f"htf_hrisk{sfx}", 0.0)
            setattr(self, f"htf_window_id{sfx}", None)
            setattr(self, f"htf_current_r{sfx}", 0.0)
        elif open_flag:
            # Both the sim and our state show an open window. If it is the SAME
            # window (entry_ts matches), just refresh metrics. If the entry_ts
            # differs, our window ended while we were away (crash/reseed close+
            # reopen) and a NEW window opened — close the old one with real sim
            # exit data where available, then adopt the new window (M3).
            if entry_ts == getattr(self, f"htf_window_start_ts{sfx}"):
                # Same window — refresh entry/sl/hrisk (in case SL drift, but v18 SL is fixed) and metrics
                setattr(self, f"htf_entry_px{sfx}", entry_px)
                setattr(self, f"htf_sl{sfx}", sl_px)
                setattr(self, f"htf_hrisk{sfx}", hrisk)
                self._update_htf_metrics()
                # No duplicate OPEN log here — status line already shows it
            else:
                old_start = getattr(self, f"htf_window_start_ts{sfx}")
                # (a) try to find the old window's close in the sim list — real exit data
                old_close = next(
                    (t for t in htf_trades
                     if int(t.get("entry_ts", 0)) == old_start and t.get("outcome") != "open"),
                    None,
                )
                try:
                    from persistence.trade_store import close_htf_window
                    if old_close is not None:
                        close_htf_window(
                            self.db, win_id,
                            int(old_close.get("exit_ts", 0)) or int(time.time()),
                            old_close.get("outcome", "closed"),
                        )
                        print(f"[htf] {regime.upper()} OLD Window CLOSED (sim): "
                              f"{old_close.get('outcome')} @ {float(old_close.get('exit_price', 0)):.2f} "
                              f"({float(old_close.get('r_multiple', 0)):+.2f}R) — replaced by newer window")
                    else:
                        # (b) old window's lifecycle fell outside the sim's 1h
                        # slice (started >20d ago) — the 16d cap provably fired
                        cap_ts = old_start + CAP_DAYS * 86400
                        close_htf_window(self.db, win_id, min(cap_ts, int(time.time())), "stale_cap")
                        print(f"[htf] {regime.upper()} OLD Window STALE-CAP (outside sim slice) — "
                              f"closed, replaced by newer window")
                except Exception as e:
                    print(f"[htf] persist old-window close failed: {e}")
                # adopt the new window — same fields the open branch sets
                d = 1 if latest_htf.get("dir") == "long" else -1
                lvl_15 = entry_px + 1.5 * hrisk * d if hrisk else 0.0
                lvl_3r = entry_px + 3.0 * hrisk * d if hrisk else 0.0
                setattr(self, f"htf_window_dir{sfx}", latest_htf.get("dir"))
                setattr(self, f"htf_window_start_ts{sfx}", entry_ts)
                setattr(self, f"htf_entry_px{sfx}", entry_px)
                setattr(self, f"htf_sl{sfx}", sl_px)
                setattr(self, f"htf_hrisk{sfx}", hrisk)
                try:
                    from persistence.trade_store import open_htf_window
                    cap_ts = entry_ts + CAP_DAYS * 86400
                    new_id = open_htf_window(
                        self.db, latest_htf.get("dir"), entry_ts, entry_px, cap_ts,
                        sl_price=sl_px, hrisk=hrisk, lvl_1_5r=lvl_15, lvl_3r=lvl_3r,
                        regime=regime,
                    )
                    setattr(self, f"htf_window_id{sfx}", new_id)
                except Exception as e:
                    print(f"[htf] persist new-window open failed: {e}")
                self._chop_stale = True
                self._update_htf_metrics()
                print(f"[htf] {regime.upper()} Window REPLACED: new {latest_htf.get('dir')} @ {entry_px:.2f} "
                      f"SL={sl_px:.2f} 1.5R={lvl_15:.2f} 3R={lvl_3r:.2f} ({entry_date}) — "
                      f"id {win_id} -> {getattr(self, f'htf_window_id{sfx}')}")
        else:
            # No window for this regime — refresh metrics (chop/regime)
            self._update_htf_metrics()

    def _journal_marks(self, tf: str, swings: list[dict], candles: list[dict]):
        existing = self._get_existing_marks_set(tf)
        # Build lookup by date string (stable across window trims, unlike idx)
        date_to_candle = {c["date"]: c for c in candles}
        new_marks = []
        for s in swings:
            for b in s.get("breaks", []):
                mark_time = b.get("time", "")
                candle = date_to_candle.get(mark_time)
                if candle:
                    key = (candle["ts"], b["kind"], b["dir"], s["swing_index"])
                    if key not in existing:
                        mark = {"ts": candle["ts"], "date": candle["date"], "tf": tf, "kind": b["kind"], "dir": b["dir"], "px": b["px"], "swing_no": s["swing_index"], "swing_kind": s.get("dir", "")}
                        new_marks.append(mark)
                        existing.add(key)
        for mark in new_marks:
            self._insert_mark(mark)
            # During initial seeding, suppress bulk historical blast — _show_recent already showed recent, and live [OPEN] will show active
            if getattr(self, "_seeding", False):
                continue
            print(f"[mark] {tf} {mark['kind']} {mark['dir']} sw{mark['swing_no']} @ {mark['px']:.2f}")

    def _is_stale_entry(self, entry_ts: int, max_bars: int = 2) -> bool:
        """C3: entry older than max_bars LTF closes is stale.

        Live entry_ts is the signal bar's CLOSE time, so a fresh trade's age
        at journal time is seconds. Anything older than 2 x 15m (30 min) is
        not the trade the backtest took — never execute it at market.
        """
        return (int(time.time()) - entry_ts) > max_bars * 900

    def _journal_trades(self, ltf_trades: list[dict]):
        existing = self._get_existing_trades_set()
        new_trades = []
        for t in ltf_trades:
            key = (t["entry_ts"], t["dir"])
            if key not in existing:
                new_trades.append(t)
                existing.add(key)
        for t in new_trades:
            cap_ts = int(t["entry_ts"]) + CAP_DAYS * 86400
            # Link to the trade's OWN regime window — v18 tags every trade with
            # the regime at its signal bar (htf_regime). Using the CURRENT
            # self.regime here could mis-link if chop crossed the threshold
            # between signal and journal.
            trade_regime = t.get("htf_regime", "flip")
            wid = self.htf_window_id_b2 if trade_regime == "b2" else self.htf_window_id
            htf_id = int(wid) if wid is not None else None  # M1: NULL, not 0 sentinel
            trade_id = open_ltf_trade(
                self.db,
                direction=t["dir"],
                entry_ts=int(t["entry_ts"]),
                entry_price=float(t["entry_price"]),
                sl_initial=float(t["sl"]),
                tp_price=float(t["target"]),
                cap_ts=cap_ts,
                htf_window_id=htf_id,
            )
            # C3/C5: stale-entry guard — never execute a trade that is not fresh,
            # and never execute while the daily halt is active. Applies ONLY to
            # open trades; closed trades are history and always journal normally.
            if t.get("outcome") == "open":
                in_trade = self._open_ltf_trade is not None
                stale = self._is_stale_entry(int(t["entry_ts"]))
                if in_trade:
                    why, exit_reason = "in-trade", "stale_skip"
                elif getattr(self, "_seeding", False):
                    why, exit_reason = "seeding", "stale_skip"
                elif stale:
                    why, exit_reason = "stale", "stale_skip"
                elif self._daily_halted:
                    why, exit_reason = "daily-halt", "halted_skip"
                else:
                    why = None
                if why:
                    close_ltf_trade(
                        self.db,
                        trade_id=trade_id,
                        exit_ts=int(time.time()),
                        exit_price=float(t.get("entry_price", 0.0)),
                        exit_reason=exit_reason,
                        r_multiple=0.0,
                    )
                    print(f"[trade] SKIP ({why}): {t['dir']} "
                          f"{t.get('entry_date', '?')} — journaled, NOT executed")
                    continue
            if t["outcome"] != "open":
                r_mult = float(t["r_multiple"])
                closed_now = close_ltf_trade(
                    self.db,
                    trade_id=trade_id,
                    exit_ts=int(t["exit_ts"]),
                    exit_price=float(t["exit_price"]),
                    exit_reason=t["outcome"],
                    r_multiple=r_mult,
                )
                if closed_now == 0:
                    # C4: already closed elsewhere — never double-count
                    # daily loss, cost accounting, or trade stats.
                    print(f"[trade] {t['dir']} entry {t.get('entry_date', '?')} already closed — skipping duplicate journal")
                    if self._open_ltf_trade and self._open_ltf_trade["id"] == trade_id:
                        self._cache_ltf_trade_close()
                    continue
                self._check_daily_loss_limit(r_mult)
                # Cost calculation (peer model: asymmetric % slippage)
                r_mult = float(t["r_multiple"])
                risk = abs(float(t["entry_price"]) - float(t["sl"]))
                if risk > 0:
                    fee_rate = config.TAKER_FEE_RATE
                    entry_px = abs(float(t["entry_price"]))
                    exit_px = abs(float(t["exit_price"]))
                    fee_r = (entry_px * fee_rate + exit_px * fee_rate) / risk
                    slip_r = (entry_px * config.ENTRY_SLIP_PCT / 100.0
                              + exit_px * config.EXIT_SLIP_PCT / 100.0) / risk
                    cost_r = fee_r + slip_r
                else:
                    cost_r = 0.0
                net_r = r_mult - cost_r
                self._cum_cost_r += cost_r
                self._cum_net_r += net_r
                self._trade_count += 1
                print(f"[trade] {t['dir']} sw{t['swing_no']} @ {t['entry_price']:.2f} -> {t['exit_price']:.2f} ({t['outcome']}, {r_mult:+.2f}R, cost {cost_r:.2f}R, net {net_r:+.2f}R)")
            else:
                print(f"[trade] {t['dir']} sw{t['swing_no']} @ {t['entry_price']:.2f} OPEN (SL={t['sl']:.2f} TP={t['target']:.2f})")
                # Phase 15: Cache the open trade (instant, no DB reads on every tick)
                self._cache_ltf_trade_open(
                    trade_id=trade_id,
                    direction=t["dir"],
                    entry_ts=int(t["entry_ts"]),
                    entry_price=float(t["entry_price"]),
                    sl_initial=float(t["sl"]),
                    tp_price=float(t["target"]),
                    cap_ts=cap_ts,
                    htf_window_id=htf_id,
                )
                # --- LIVE ORDER EXECUTION ---
                if self.trader and self.trader.is_connected:
                    self._execute_entry(t, trade_id)

    def _execute_entry(self, trade: dict, trade_id: int):
        """Place market order on Bybit for a new open trade."""
        # Daily loss limit check — don't enter if halted
        if self._daily_halted:
            print(f"[order] SKIPPED — daily loss limit breached, trading halted until tomorrow")
            return
        try:
            direction = trade["dir"]
            side = "Buy" if direction == "long" else "Sell"
            entry_price = float(trade["entry_price"])
            sl_price = float(trade["sl"])
            tp_price = float(trade["target"])

            # Position sizing: risk INR -> USDT -> qty
            qty = self._calculate_qty(entry_price, sl_price)
            if qty <= 0:
                print(f"[order] SKIPPED -- qty={qty} (check balance/risk)")
                return

            # Format using exchange precision
            qty_prec = self.trader.qty_precision if self.trader else config.QTY_PRECISION
            sl_str = f"{sl_price:.2f}"
            tp_str = f"{tp_price:.2f}"
            qty_str = f"{qty:.{qty_prec}f}"
            stop_distance = abs(entry_price - sl_price)
            notional = qty * entry_price
            risk_inr = read_risk_inr()
            rate = self.rate_manager.get_rate()
            risk_usdt = risk_inr / rate

            # Detailed entry log
            print(f"[trade] ENTRY {direction} sw{trade.get('swing_no', '?')} @ {entry_price:.2f}")
            print(f"  SL={sl_str} TP={tp_str} dist={stop_distance:.2f}")
            print(f"  Risk: INR {risk_inr:.0f} = ${risk_usdt:.2f} (rate INR {rate:.2f})")
            print(f"  Qty: {qty_str} BTC (notional ${notional:.2f})")
            print(f"  Fee buffer: ${notional * config.TAKER_FEE_RATE * 2:.4f}")
            # C8: NO exchange TP on LTF orders. The sim NEVER target-exits LTF
            # (trailing="swing" -> trail-only exits; _exit_on_fine checks target
            # only when trailing=="off"; D2: 186 trail / 0 target, avg winner
            # +5.02R). A 3R exchange TP would cap every live runner at +3R while
            # the backtest rides to +5R+ ? the biggest live-vs-backtest gap found.
            # SL stays attached (downtime protection). DB tp_price kept for audit.
            print(f"  Bybit PLACING: {side} {qty_str} BTC SL={sl_str} (no TP ? trail-only, C8)")

            link_id = f"bb_{trade_id}_{int(time.time() * 1000)}"
            resp = self.trader.place_market_order_retry(side, qty_str, stop_loss=sl_str,
                                                        take_profit=None, order_link_id=link_id)

            if resp.get("retCode") != 0:
                # C7: response lost or rejected — the order may have LANDED
                # (lost response / duplicate orderLinkId). Verify before
                # declaring failure: adopt / confirm-flat / hold-open.
                state, info = self.trader.verify_entry_order(link_id, expected_side=direction)
                if state == "filled":
                    actual_qty = float(info["qty"])
                    print(f"[trade] ENTRY ADOPTED after lost response: {actual_qty} BTC @ ~{info.get('avgPrice', 0) or 0:.2f}")
                    if self._tg:
                        self._tg.error(f"ENTRY ADOPTED after lost response — {actual_qty} BTC (fill px {info.get('avgPrice', 0) or 0:.2f})")
                    try:
                        from persistence.trade_store import update_trade_qty
                        update_trade_qty(self.db, trade_id, actual_qty)
                    except Exception:
                        pass
                    if self._tg:
                        self._tg.trade_entry(direction, entry_price, sl_price, qty_str,
                                             risk_inr, risk_usdt, rate)
                    return
                if state == "flat":
                    print(f"[trade] ENTRY FAILED (confirmed flat): {resp.get('retMsg', 'unknown')}")
                    if self._tg:
                        self._tg.error(f"ENTRY FAILED: {resp.get('retMsg', 'unknown')}")
                    try:
                        close_ltf_trade(self.db, trade_id=trade_id,
                                        exit_ts=int(time.time()), exit_price=entry_price,
                                        exit_reason="order_failed", r_multiple=0.0)
                        self._open_ltf_trade = None
                    except Exception:
                        pass
                    return
                # unknown — cannot determine. Keep DB open + cache: if a position
                # exists, its exchange-side SL is armed (bounded risk). Operator
                # must verify; next-boot reconcile resolves the books.
                print(f"[trade] ENTRY UNKNOWN: {resp.get('retMsg', 'unknown')} — DB kept OPEN, VERIFY POSITION MANUALLY")
                if self._tg:
                    self._tg.error("ENTRY UNKNOWN — could not verify order. VERIFY POSITION MANUALLY.")
                return

            order_id = resp["result"]["orderId"]
            # H4 (folded into C7): poll the position instead of a single
            # sleep(0.3) check — a slow fill would previously false-fail.
            intended_qty = float(qty_str)
            actual_qty = 0.0
            for _ in range(3):
                pos = self.trader.get_position()
                if pos and pos.get("side") == side:
                    actual_qty = pos["size"]
                    break
                time.sleep(0.3)
            if actual_qty == 0:
                # C7: no position after polling — a lost response may have
                # landed. Verify before declaring failure.
                state, info = self.trader.verify_entry_order(link_id, expected_side=direction)
                if state == "filled":
                    actual_qty = float(info["qty"])
                    print(f"[trade] ENTRY FILLED (late fill confirmed): {actual_qty} BTC")
                else:
                    print(f"[trade] PARTIAL FILL WARNING: 0/{intended_qty} filled — closing DB trade")
                    if self._tg:
                        self._tg.error(f"ORDER FILLED 0/{intended_qty} — closing")
                    try:
                        close_ltf_trade(self.db, trade_id=trade_id,
                                        exit_ts=int(time.time()), exit_price=entry_price,
                                        exit_reason="order_failed", r_multiple=0.0)
                        self._open_ltf_trade = None
                    except Exception:
                        pass
                    return
            if actual_qty < intended_qty * 0.99:
                print(f"[trade] PARTIAL FILL: {actual_qty}/{intended_qty} filled — updating DB")
                if self._tg:
                    self._tg.error(f"PARTIAL FILL: {actual_qty}/{intended_qty} BTC")
                try:
                    from persistence.trade_store import update_trade_qty
                    update_trade_qty(self.db, trade_id, actual_qty)
                except Exception:
                    pass
            else:
                print(f"[trade] ENTRY FILLED: {order_id} ({actual_qty} BTC)")
                try:
                    from persistence.trade_store import update_trade_qty
                    update_trade_qty(self.db, trade_id, actual_qty)
                except Exception:
                    pass
            if self._tg:
                self._tg.trade_entry(direction, entry_price, sl_price, qty_str,
                                      risk_inr, risk_usdt, rate)
        except Exception as e:
            print(f"[trade] ENTRY ERROR: {e}")
            if self._tg:
                self._tg.error(f"ENTRY ERROR: {e}")
            # Close the orphan DB trade — no position on exchange
            try:
                close_ltf_trade(self.db, trade_id=trade_id,
                                exit_ts=int(time.time()), exit_price=0.0,
                                exit_reason="order_error", r_multiple=0.0)
                self._open_ltf_trade = None
            except Exception:
                pass

    def _execute_exit(self, reason: str, fill_price: float) -> bool:
        """Close the exchange position for the open trade (C1/C2 fix).

        Returns:
            True  — exchange position confirmed closed (or was already flat).
                    Caller may record the exit in DB and clear the cache.
            False — close failed or state unknown. Caller MUST keep the DB
                    trade open and the cache intact; on_tick retries on the
                    next tick.
        """
        try:
            # Get current rate for PnL logging
            rate = self.rate_manager.get_rate()
            print(f"[trade] EXIT reason={reason} @ {fill_price:.2f} (rate INR {rate:.2f})")
            # Get trade info for alert
            direction = ""
            entry_price = 0.0
            r_mult = 0.0
            if self._open_ltf_trade:
                direction = self._open_ltf_trade.get("direction", "")
                entry_price = float(self._open_ltf_trade.get("entry_price", 0))
                sl_initial = float(self._open_ltf_trade.get("sl_initial", 0))
                risk = abs(entry_price - sl_initial)
                if risk > 0:
                    r_mult = (fill_price - entry_price) / risk if direction == "long" else (entry_price - fill_price) / risk
            resp = self.trader.close_position_retry()
            if resp.get("retCode") == 0:
                print(f"[trade] EXIT FILLED: {reason}")
                self._exit_fail_count = 0
                if self._tg:
                    self._tg.trade_exit(reason, fill_price, r_mult, direction, entry_price)
                return True
            # Throttle alerts: first failure + every 10th retry
            self._exit_fail_count = getattr(self, "_exit_fail_count", 0) + 1
            print(f"[trade] EXIT FAILED: {resp.get('retMsg', 'unknown')} — DB kept open, retrying next tick")
            if self._tg and (self._exit_fail_count == 1 or self._exit_fail_count % 10 == 0):
                self._tg.error(f"EXIT FAILED (retry {self._exit_fail_count}): {resp.get('retMsg', 'unknown')}")
            return False
        except Exception as e:
            self._exit_fail_count = getattr(self, "_exit_fail_count", 0) + 1
            print(f"[trade] EXIT ERROR: {e}")
            if self._tg and (self._exit_fail_count == 1 or self._exit_fail_count % 10 == 0):
                self._tg.error(f"EXIT ERROR: {e}")
            return False

    def _calculate_qty(self, entry_price: float, sl_price: float) -> float:
        """Calculate BTC quantity based on risk.

        Reads risk from risk_inr.txt (edit file to change, no restart needed).
        Converts INR -> USDT via cached rate (0ms, no network on trade).
        Formula: qty = risk_usdt / (|entry - sl| + fee_buffer)
        Uses trader.qty_step for precision (fetched from Bybit API).
        Rejects trade if implied leverage > MAX_LEVERAGE.
        """
        risk_inr = read_risk_inr()
        # M9: update() does blocking requests.get (up to ~20s across both rate
        # sources) — it must NEVER run on the tick/entry path. _session_watch
        # refreshes it off-loop every 30s (asyncio.to_thread). Here we size
        # with the cached rate and warn if it is stale.
        if self.rate_manager.is_stale():
            print(f"[order] WARNING: rate cache stale ({self.rate_manager.age_min():.0f} min) — "
                  f"sizing with cached INR {self.rate_manager.get_rate():.2f}/USDT")
        inr_usdt = self.rate_manager.get_rate()
        risk_usdt = risk_inr / inr_usdt

        stop_distance = abs(entry_price - sl_price)
        if stop_distance <= 0:
            return 0.0

        # Fee buffer: taker fee * 2 sides * entry price
        fee_buffer = entry_price * config.TAKER_FEE_RATE * 2
        qty = risk_usdt / (stop_distance + fee_buffer)

        # Round to exchange qty_step precision
        qty_step = self.trader.qty_step if self.trader else 10 ** (-config.QTY_PRECISION)
        min_qty = self.trader.min_qty if self.trader else config.MIN_BTC_QTY
        qty = round(qty / qty_step) * qty_step
        # M10: never force up to the exchange minimum — that silently multiplies
        # real risk (min_qty / computed can be several x risk_usdt on wide stops).
        # Reject instead; the caller skips the trade on qty <= 0.
        if qty < min_qty:
            forced_risk = min_qty * (stop_distance + fee_buffer)
            mult = forced_risk / risk_usdt if risk_usdt > 0 else float("inf")
            print(f"[order] REJECTED: computed qty {qty} < exchange min {min_qty} "
                  f"— forcing min would risk ${forced_risk:.2f} vs planned ${risk_usdt:.2f} ({mult:.1f}x planned)")
            return 0.0

        # Check available balance
        if self.trader and self.trader.is_connected:
            balance = self.trader.get_wallet_balance()
            available = balance.get("available", 0)
            required = qty * entry_price
            if required > available * config.BALANCE_SAFETY_MARGIN:
                qty = round(available * config.SIZED_DOWN_FRACTION / entry_price / qty_step) * qty_step
                if qty < min_qty:
                    # M10: balance-sized qty below exchange min — forcing min could
                    # exceed available balance (margin rejection) and inflates risk.
                    print(f"[order] REJECTED: balance-sized qty {qty} < exchange min {min_qty} "
                          f"(available={available:.2f} USDT) — trade skipped")
                    return 0.0
                print(f"[order] Position sized down: balance={available:.2f} USDT, qty={qty}")

            # Implied leverage check
            if available > 0:
                implied_lev = (qty * entry_price) / available
                if implied_lev > config.MAX_LEVERAGE:
                    print(f"[order] REJECTED: implied leverage {implied_lev:.1f}x > max {config.MAX_LEVERAGE}x")
                    return 0.0

        print(f"[order] Risk: INR {risk_inr:.0f} = ${risk_usdt:.2f} USDT (rate INR {inr_usdt:.2f}/USDT) qty={qty}")
        return qty

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

    @staticmethod
    def _calc_r(direction: str, entry_price: float, exit_price: float, risk: float) -> float:
        """Calculate R multiple — mirrors v18_streak_halt.py:322-323."""
        if risk <= 0:
            return 0.0
        if direction == "long":
            return (exit_price - entry_price) / risk
        else:
            return (entry_price - exit_price) / risk
