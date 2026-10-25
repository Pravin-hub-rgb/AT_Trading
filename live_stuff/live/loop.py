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

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

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

from book import BOOK_NAME, BOOK_CODE, BOOK_PARAMS, SWING, SWING_1H_LABEL, get_book_params
from persistence.database import Database
from persistence.mark_store import get_marks
from persistence.trade_store import open_ltf_trade, close_ltf_trade, get_open_ltf_trade, get_ltf_trades
from persistence.state_store import get_trading_state, save_trading_state, get_last_swing_end, set_last_swing_end, insert_candle, load_candles

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



from .feed import FeedMixin
from .state import StateMixin
from .signals import SignalsMixin
from .execution import ExecutionMixin
from .risk import RiskMixin
from .trading import TradingMixin


class LiveLoop(FeedMixin, StateMixin, SignalsMixin, ExecutionMixin, RiskMixin, TradingMixin):
    """Book 107 live trading loop."""

    _BOUNDARY_TIMEOUT = 2.5  # seconds - force fire if one candle missing

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
        self.all_candles_15m: list[dict] = []
        self.all_candles_1h: list[dict] = []
        # Guard against overlapping async simulations
        self._sim_running = False
        self.trading_state = get_trading_state(db)
        # Book 107 - params are the tested book, not the old v18 symbol table.
        self.v18 = get_book_params(self.v18_instrument)
        self._chop_thresh = self.v18.get("chop_thresh", 58.0)
        print(f"[live] book {BOOK_CODE} {BOOK_NAME} | chop={self._chop_thresh} "
              f"cooldown={self.v18.get('cooldown_bars')} "
              f"sl_buf={self.v18.get('sl_buf_atr')} halt={self.v18.get('max_consecutive_losses')}")
        self._cum_cost_r = 0.0
        self._cum_net_r = 0.0
        self._trade_count = 0
        # Persistent swing engines — use actual SwingEngine logic (same as backtest)
        self.swing_15m = PersistentSwingEngine("15m", db, {"minBars": SWING["min_bars_15m"], "timeCap": "00:00"})
        self.swing_1h = PersistentSwingEngine(SWING_1H_LABEL, db, {"minBars": SWING["min_bars_1h"], "timeCap": "00:00"})
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
        # with the flip window. `self.regime` (state._compute_regime, mirror
        # of the engine's regime chain) selects which window is ACTIVE for
        # metrics/status/linkage.
        self.htf_window_open_b2 = False
        self.htf_window_dir_b2 = None       # 'long' | 'short'
        self.htf_window_start_ts_b2 = 0
        self.htf_window_id_b2: int | None = None
        self.htf_entry_px_b2 = 0.0
        self.htf_sl_b2 = 0.0
        self.htf_current_r_b2 = 0.0         # unrealized R of the b2 1h leg
        self.htf_hrisk_b2 = 0.0             # abs(entry - sl) for b2 R calc
        # DECISIVE window tracking — atr_high books (e.g. 107) route their
        # volatile bucket here; the engine result exposes it via
        # htf_trades_decisive. Tracked independently like flip/b2.
        self.htf_window_open_dec = False
        self.htf_window_dir_dec = None
        self.htf_window_start_ts_dec = 0
        self.htf_window_id_dec: int | None = None
        self.htf_entry_px_dec = 0.0
        self.htf_sl_dec = 0.0
        self.htf_current_r_dec = 0.0        # unrealized R of the decisive 1h leg
        self.htf_hrisk_dec = 0.0            # abs(entry - sl) for decisive R calc
        self.chop_index = 50.0              # current 1h chop (last value)
        self._chop_stale = True              # recompute on next _update_htf_metrics
        self.atr_14 = 0.0                   # current 15m ATR(14) in price units
        self.regime = 'flip'                # 'flip' | 'b2' | 'decisive' (engine regime rule, state._compute_regime)
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
        # Phase 15: Cached LTF trades (in-memory, no DB reads on every tick).
        # Paper mode can hold several concurrent trades (book max_positions=0).
        self._open_ltf_trade: dict | None = None
        self._open_ltf_trades: dict[int, dict] = {}
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

    def _on_tick(self, price: float, ts_ms: int):
        """Handle real-time tick (for SL/TP monitoring) + rolling R update."""
        if self.window_15m:
            try:
                self.on_tick(price, ts_ms // 1000)
                # Rolling R update on every tick so status/gate is live
                # (either regime window — metrics computes the right one)
                if self.htf_window_open or self.htf_window_open_b2 or self.htf_window_open_dec:
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
            candle_dict = {"date": date, "ts": ts, "open": candle["open"],
                             "high": candle["high"], "low": candle["low"], "close": candle["close"]}
            self.window_15m.append(candle_dict)
            # Option B: persist to full candle store for simulation
            self.all_candles_15m.append(candle_dict)
            try:
                insert_candle(self.db, "15m", candle_dict)
            except Exception:
                pass
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
            candle_dict = {"date": date, "ts": ts, "open": candle["open"],
                                    "high": candle["high"], "low": candle["low"], "close": candle["close"]}
            self.window_1h.append(candle_dict)
            # Option B: persist to full candle store for simulation
            self.all_candles_1h.append(candle_dict)
            try:
                insert_candle(self.db, "1h", candle_dict)
            except Exception:
                pass
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

    def stop(self):
        self._running = False

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
