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



class FeedMixin:
    """feed responsibilities."""

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
                Path(__file__).resolve().parents[1] / "docs" / "seed_marks.json",
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
            from _vendored.firstswing import SwingEngine as _SE
            try:
                with self.db.transaction() as _conn:
                    _conn.execute("DELETE FROM meta WHERE key IN ('swing_state_15m','swing_state_1h','swing_state_1h_htf15')")
            except Exception:
                pass
            self.swing_15m.eng = _SE(self.swing_15m.opts)
            self.swing_15m.swing_index = 0
            self.swing_15m.next_start_pos = 0
            self.swing_15m._pos = 0
            self.swing_15m._candles = {}
            self.swing_15m.ts_map = {}
            self.swing_15m._pending = []
            self.swing_1h.eng = _SE(self.swing_1h.opts)
            self.swing_1h.swing_index = 0
            self.swing_1h.next_start_pos = 0
            self.swing_1h._pos = 0
            self.swing_1h._candles = {}
            self.swing_1h.ts_map = {}
            self.swing_1h._pending = []
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

        # Pagination must reach the live tail. Clamp absurdly old seeds to the
        # fetch cap instead of stopping short and leaving a gap before "now".
        max_seed_15m_ms = now_ms - 20000 * 900000
        if seed_15m_ms < max_seed_15m_ms:
            print("[seed] 15m: seed older than 208d cap - clamping to last 208d")
            seed_15m_ms = max_seed_15m_ms
        max_seed_1h_ms = now_ms - 5000 * 3600000
        if seed_1h_ms < max_seed_1h_ms:
            print("[seed] 1h: seed older than 208d cap - clamping to last 208d")
            seed_1h_ms = max_seed_1h_ms

        # --- 15m: timestamp IS the first candle, no lookback ---
        try:
            print(f"[seed] 15m: first candle = {self._to_ist_str(seed_15m_ms)} (no lookback)")
            want_15m = min(20000, max(2000, (now_ms - seed_15m_ms) // 900000 + 50))
            raw_15m = self._fetch_klines_from_sync(self.symbol, "15m", seed_15m_ms, limit=want_15m)
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
            want_1h = min(5000, max(500, (now_ms - start_1h_ms) // 3600000 + 50))
            raw_1h = self._fetch_klines_from_sync(self.symbol, "1h", start_1h_ms, limit=want_1h)
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
            from _vendored.firstswing import SwingEngine as _SE
            try:
                with self.db.transaction() as _conn:
                    _conn.execute("DELETE FROM meta WHERE key IN ('swing_state_15m','swing_state_1h','swing_state_1h_htf15')")
            except Exception:
                pass
            self.swing_15m.eng = _SE(self.swing_15m.opts)
            self.swing_15m.swing_index = 0
            self.swing_15m.next_start_pos = 0
            self.swing_15m._pos = 0
            self.swing_15m._candles = {}
            self.swing_15m.ts_map = {}
            self.swing_15m._pending = []
            self.swing_1h.eng = _SE(self.swing_1h.opts)
            self.swing_1h.swing_index = 0
            self.swing_1h.next_start_pos = 0
            self.swing_1h._pos = 0
            self.swing_1h._candles = {}
            self.swing_1h.ts_map = {}
            self.swing_1h._pending = []
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
                want_15m = min(20000, max(2000, (now_ms - start_15m_ms) // 900000 + 50))
                raw_15m = self._fetch_klines_from_sync(self.symbol, "15m", start_15m_ms, limit=want_15m)
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
                want_1h = min(5000, max(500, (now_ms - fetch_start_1h_ms) // 3600000 + 50))
                raw_1h = self._fetch_klines_from_sync(self.symbol, "1h", fetch_start_1h_ms, limit=want_1h)
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
