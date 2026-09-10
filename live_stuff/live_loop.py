"""Live loop - FULL v18 simulation on rolling windows.

Runs the EXACT same simulate_htf_ltf_streak_halt that the backtest uses,
on rolling windows of Binance data. Produces identical trades.
"""

import sys
import time
import asyncio
from pathlib import Path
from datetime import datetime, timezone
import bisect

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from src.btc.btc_swing import compute_btc_swings
from src.btc.btc_engine import _trail_events
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.walker import FlowCandle
from src.live.persistent_swing import PersistentSwingEngine
from src.live.data_streamer import BinanceStreamer, backfill_klines

from engine.v18_params import V18, V18_ENGINE, SWING
from persistence.database import Database
from persistence.mark_store import get_marks
from persistence.trade_store import open_ltf_trade, close_ltf_trade, get_open_ltf_trade, get_ltf_trades
from persistence.state_store import get_trading_state, save_trading_state, get_last_candle_ts, set_last_candle_ts

SYMBOL = "BTCUSDT"
WINDOW_DAYS_15M = 30
WINDOW_DAYS_1H = 20
CAP_DAYS = 16


class LiveLoop:
    """Full v18 live trading loop."""

    def __init__(self, db: Database):
        self.db = db
        self._running = False
        self.window_15m: list[dict] = []
        self.window_1h: list[dict] = []
        self.trading_state = get_trading_state(db)
        # Persistent swing engines — use actual SwingEngine logic (same as backtest)
        self.swing_15m = PersistentSwingEngine("15m", db, {"minBars": SWING["min_bars_15m"]})
        self.swing_1h = PersistentSwingEngine("1h", db, {"minBars": SWING["min_bars_1h"]})
        self.all_swings_15m: list[dict] = []
        self.all_swings_1h: list[dict] = []
        # HTF window tracking
        self.htf_window_open = False
        self.htf_window_dir = None
        self.htf_window_start_ts = 0

    def run(self, max_seconds: float = 0):
        self._running = True
        started = time.time()
        # Backtest alignment — find last known swing state from historical data
        self._align_from_backtest()
        print("[live] Backbencher v18 - FULL simulation (WebSocket streams)")
        print(f"[live] 15m window: {WINDOW_DAYS_15M}d | 1h window: {WINDOW_DAYS_1H}d")
        print(f"[live] params: mode={V18['mode']} rr={V18_ENGINE['rr_target']} cd={V18['cooldown_bars']} halt={V18['max_consecutive_losses']}")

        # Start WebSocket streamer
        self.streamer = BinanceStreamer(
            on_tick=self._on_tick,
            on_15m_close=self._on_15m_close,
            on_1h_close=self._on_1h_close,
        )

        # Run asyncio event loop
        try:
            asyncio.run(self._run_loop(max_seconds, started))
        except KeyboardInterrupt:
            print("\n[live] Interrupted")
        finally:
            self._running = False
            print("[live] Loop stopped")

    async def _run_loop(self, max_seconds: float, started: float):
        """Main async loop — runs streamer and handles shutdown."""
        streamer_task = asyncio.create_task(self.streamer.start())
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
            streamer_task.cancel()
            try:
                await streamer_task
            except asyncio.CancelledError:
                pass

    def _print_status(self):
        """Print current status (HTF bias, position, etc.)."""
        # HTF bias status
        if self.htf_window_open:
            htf_str = f"HTF: {self.htf_window_dir.upper()} (since {datetime.fromtimestamp(self.htf_window_start_ts, tz=timezone.utc).strftime('%H:%M')})"
        else:
            htf_str = "HTF: NO BIAS"
        
        # Position status
        open_trade = get_open_ltf_trade(self.db)
        if open_trade:
            pos_str = f"POS: {open_trade['direction']} @ {open_trade['entry_price']:.2f} SL={open_trade['sl_current']:.2f} TP={open_trade['tp_price']:.2f}"
        else:
            pos_str = "POS: FLAT"
        
        # Cooldown status
        cd_str = f"CD: {self.trading_state['cooldown_remaining']}" if self.trading_state['cooldown_remaining'] > 0 else ""
        
        print(f"[status] {htf_str} | {pos_str} {cd_str}".strip())

    def _on_tick(self, price: float, ts_ms: int):
        """Handle real-time tick (for SL/TP monitoring)."""
        if self.window_15m:
            self.on_tick(price, ts_ms // 1000)

    def _on_15m_close(self, candle: dict):
        """Handle 15m candle close — feed to swing engine."""
        ts = candle["close_time"] // 1000
        date = datetime.fromtimestamp(candle["open_time"] // 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        self.window_15m.append({"date": date, "ts": ts, "open": candle["open"],
                                 "high": candle["high"], "low": candle["low"], "close": candle["close"]})
        # Trim window
        cutoff = int(time.time()) - WINDOW_DAYS_15M * 86400
        self.window_15m = [c for c in self.window_15m if c["ts"] >= cutoff]
        # Feed to swing engine
        fc = FlowCandle(date=date, open=candle["open"], high=candle["high"],
                        low=candle["low"], close=candle["close"])
        result = self.swing_15m.process_bar(fc, len(self.window_15m) - 1)
        if result:
            self.all_swings_15m.append(result)
            for b in result.get("breaks", []):
                print(f"[mark] 15m {b['kind']} {b['dir']} sw{b['swing_no']} @ {b['px']:.2f} ({b['time']})")
        self._run_v18_simulation()

    def _on_1h_close(self, candle: dict):
        """Handle 1h candle close — feed to swing engine."""
        ts = candle["close_time"] // 1000
        date = datetime.fromtimestamp(candle["open_time"] // 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        self.window_1h.append({"date": date, "ts": ts, "open": candle["open"],
                                "high": candle["high"], "low": candle["low"], "close": candle["close"]})
        cutoff = int(time.time()) - WINDOW_DAYS_1H * 86400
        self.window_1h = [c for c in self.window_1h if c["ts"] >= cutoff]
        fc = FlowCandle(date=date, open=candle["open"], high=candle["high"],
                        low=candle["low"], close=candle["close"])
        result = self.swing_1h.process_bar(fc, len(self.window_1h) - 1)
        if result:
            self.all_swings_1h.append(result)
            for b in result.get("breaks", []):
                print(f"[mark]  1h {b['kind']} {b['dir']} sw{b['swing_no']} @ {b['px']:.2f} ({b['time']})")
        self._run_v18_simulation()

    def stop(self):
        self._running = False

    def _align_from_backtest(self):
        """Align live engines with backtest results on startup."""
        print("[live] Running backtest alignment...")
        try:
            from src.btc.btc_config import load_btc_df
            df_15m = load_btc_df("15m")
            candles_15m = []
            for row in df_15m.itertuples():
                date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                candles_15m.append({"date": date, "ts": int(row.ts), "open": float(row.open),
                                    "high": float(row.high), "low": float(row.low), "close": float(row.close)})
            flow_15m = [FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"]) for c in candles_15m]
            swings_15m = compute_btc_swings(flow_15m, opts={"minBars": SWING["min_bars_15m"]}, max_swings=len(flow_15m) // 2)
            self.all_swings_15m = [s for s in swings_15m if s.get("break_kind")]
            self._show_recent_marks(self.all_swings_15m, candles_15m, "15m")
            # Show open swing state
            last_confirmed = swings_15m[-1] if swings_15m else None
            if last_confirmed:
                open_idx = last_confirmed["swing_index"] + 1
                print(f"[swing] 15m open: sw{open_idx} (forming, needs {SWING['min_bars_15m']} candles to confirm)")

            df_1h = load_btc_df("1h")
            candles_1h = []
            for row in df_1h.itertuples():
                date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                candles_1h.append({"date": date, "ts": int(row.ts), "open": float(row.open),
                                   "high": float(row.high), "low": float(row.low), "close": float(row.close)})
            flow_1h = [FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"]) for c in candles_1h]
            swings_1h = compute_btc_swings(flow_1h, opts={"minBars": SWING["min_bars_1h"]}, max_swings=len(flow_1h) // 2)
            self.all_swings_1h = [s for s in swings_1h if s.get("break_kind")]
            self._show_recent_marks(self.all_swings_1h, candles_1h, "1h")
            last_confirmed_h = swings_1h[-1] if swings_1h else None
            if last_confirmed_h:
                open_idx_h = last_confirmed_h["swing_index"] + 1
                print(f"[swing]  1h open: sw{open_idx_h} (forming, needs {SWING['min_bars_1h']} candles to confirm)")

            print(f"[live] Aligned: {len(self.all_swings_15m)} 15m swings, {len(self.all_swings_1h)} 1h swings")
        except Exception as e:
            print(f"[live] Alignment failed: {e}")

    def _show_recent_marks(self, swings: list[dict], candles: list[dict], tf: str):
        """Show the most recent marks from backtest alignment."""
        # Find marks in the last 7 days
        cutoff_ts = int(time.time()) - 7 * 86400
        recent_marks = []
        for s in swings:
            for b in s.get("breaks", []):
                idx = b.get("idx", -1)
                if 0 <= idx < len(candles):
                    candle_ts = candles[idx]["ts"]
                    if candle_ts >= cutoff_ts:
                        recent_marks.append({
                            "date": candles[idx]["date"],
                            "kind": b["kind"],
                            "dir": b["dir"],
                            "px": b["px"],
                            "swing_no": s["swing_index"],
                        })
        # Show last 15 marks
        if recent_marks:
            print(f"[marks] {tf} recent (last 7d):")
            for m in recent_marks[-15:]:
                print(f"  {m['date']} | {m['kind']:<4} {m['dir']:<4} sw{m['swing_no']} @ {m['px']:.2f}")

    def _tick(self):
        now = int(time.time())
        new_15m = self._fetch_new_candles("15m")
        new_1h = self._fetch_new_candles("1h")
        if not new_15m and not new_1h:
            return
        try:
            if new_15m:
                self.window_15m.extend(new_15m)
                cutoff = now - WINDOW_DAYS_15M * 86400
                self.window_15m = [c for c in self.window_15m if c["ts"] >= cutoff]
                set_last_candle_ts(self.db, "15m", max(c["ts"] for c in new_15m))
                for c in new_15m:
                    fc = FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"])
                    result = self.swing_15m.process_bar(fc, len(self.window_15m) - len(new_15m) + new_15m.index(c))
                    if result:
                        self.all_swings_15m.append(result)
                        for b in result.get("breaks", []):
                            print(f"[mark] 15m {b['kind']} {b['dir']} sw{b['swing_no']} @ {b['px']:.2f} ({b['time']})")
            if new_1h:
                self.window_1h.extend(new_1h)
                cutoff = now - WINDOW_DAYS_1H * 86400
                self.window_1h = [c for c in self.window_1h if c["ts"] >= cutoff]
                set_last_candle_ts(self.db, "1h", max(c["ts"] for c in new_1h))
                for c in new_1h:
                    fc = FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"])
                    result = self.swing_1h.process_bar(fc, len(self.window_1h) - len(new_1h) + new_1h.index(c))
                    if result:
                        self.all_swings_1h.append(result)
                        for b in result.get("breaks", []):
                            print(f"[mark]  1h {b['kind']} {b['dir']} sw{b['swing_no']} @ {b['px']:.2f} ({b['time']})")
            self._run_v18_simulation()
        except Exception as e:
            import traceback
            print(f"[live] Error in tick: {e}")
            traceback.print_exc()
        if self.window_15m:
            latest_price = self.window_15m[-1]["close"]
            self.on_tick(latest_price, now)
        if self.trading_state["cooldown_remaining"] > 0:
            self.trading_state["cooldown_remaining"] -= 1
            save_trading_state(self.db, self.trading_state)

    def _fetch_new_candles(self, tf: str) -> list[dict]:
        try:
            last_ts = get_last_candle_ts(self.db, tf)
            raw = fetch_klines(SYMBOL, tf, limit=10)
            interval_sec = 900 if tf == "15m" else 3600
            now = int(time.time())
            new = []
            for c in raw:
                if c.ts > last_ts and c.ts + interval_sec <= now:
                    d = c.to_dict()
                    if not d["date"]:
                        d["date"] = datetime.fromtimestamp(c.ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                    new.append(d)
            return sorted(new, key=lambda x: x["ts"])
        except Exception as e:
            print(f"[live] fetch error ({tf}): {e}")
            return []
    def _run_v18_simulation(self):
        if len(self.window_15m) < SWING["min_bars_15m"] + 5 or len(self.window_1h) < SWING["min_bars_1h"] + 5:
            print(f"[live] windows too small: 15m={len(self.window_15m)} 1h={len(self.window_1h)}")
            return

        sw15 = list(self.all_swings_15m)
        open15 = self.swing_15m.get_open_swing()
        if open15:
            sw15.append(open15)

        sw1h = list(self.all_swings_1h)
        open1h = self.swing_1h.get_open_swing()
        if open1h:
            sw1h.append(open1h)

        c15 = self.window_15m
        c1h = self.window_1h

        result = simulate_htf_ltf_streak_halt(
            c1h, sw1h, c15, sw15,
            fine_ltf=[],
            sl_buf_atr=V18["sl_buf_atr"],
            ext_stop_r=V18["ext_stop_r"],
            mode=V18["mode"],
            cooldown_bars=V18["cooldown_bars"],
            max_consecutive_losses=V18["max_consecutive_losses"],
        )

        ltf_trades = result["ltf_trades"]
        htf_trades = result.get("htf_trades", [])

        # Track HTF window state
        self._track_htf_windows(htf_trades, c1h)

        self._journal_marks("15m", sw15, c15)
        self._journal_marks("1h", sw1h, c1h)
        self._journal_trades(ltf_trades)
        self._trail_sl(sw15)
        
        # Log summary
        htf_status = "OPEN" if self.htf_window_open else "CLOSED"
        htf_dir = self.htf_window_dir if self.htf_window_open else "none"
        print(f"[live] v18: {len(sw15)} 15m sw, {len(sw1h)} 1h sw, {len(ltf_trades)} LTF trades | HTF: {htf_status} {htf_dir}")

    def _track_htf_windows(self, htf_trades: list[dict], c1h: list[dict]):
        """Track and log HTF window state changes."""
        if not htf_trades:
            return

        latest_htf = htf_trades[-1]
        htf_status = latest_htf.get("outcome", "open")

        # Get timestamp for logging
        entry_ts = latest_htf.get("entry_ts", 0)
        entry_date = datetime.fromtimestamp(entry_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if entry_ts else "?"

        if htf_status == "open" and not self.htf_window_open:
            self.htf_window_open = True
            self.htf_window_dir = latest_htf.get("dir")
            self.htf_window_start_ts = entry_ts
            print(f"[htf] Window OPENED: {self.htf_window_dir} @ {latest_htf.get('entry_price', 0):.2f} ({entry_date})")
        elif htf_status != "open" and self.htf_window_open:
            exit_ts = latest_htf.get("exit_ts", 0)
            exit_date = datetime.fromtimestamp(exit_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if exit_ts else "?"
            self.htf_window_open = False
            print(f"[htf] Window CLOSED: {latest_htf.get('outcome')} @ {latest_htf.get('exit_price', 0):.2f} ({exit_date}, {latest_htf.get('r_multiple', 0):+.2f}R)")
            self.htf_window_dir = None
            self.htf_window_start_ts = 0

        # Log current HTF window state
        if self.htf_window_open:
            print(f"[htf] Window OPEN: {self.htf_window_dir} (since {entry_date})")

    def _on_tick(self, price: float, ts_ms: int):
        """Handle real-time tick (for SL/TP monitoring)."""
        if self.window_15m:
            self.on_tick(price, ts_ms // 1000)

    def _on_15m_close(self, candle: dict):
        """Handle 15m candle close — feed to swing engine."""
        ts = candle["close_time"] // 1000
        date = datetime.fromtimestamp(candle["open_time"] // 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        self.window_15m.append({"date": date, "ts": ts, "open": candle["open"],
                                 "high": candle["high"], "low": candle["low"], "close": candle["close"]})
        # Trim window
        cutoff = int(time.time()) - WINDOW_DAYS_15M * 86400
        self.window_15m = [c for c in self.window_15m if c["ts"] >= cutoff]
        # Feed to swing engine
        fc = FlowCandle(date=date, open=candle["open"], high=candle["high"],
                        low=candle["low"], close=candle["close"])
        result = self.swing_15m.process_bar(fc, len(self.window_15m) - 1)
        if result:
            self.all_swings_15m.append(result)
            for b in result.get("breaks", []):
                print(f"[mark] 15m {b['kind']} {b['dir']} sw{b['swing_no']} @ {b['px']:.2f} ({b['time']})")
        self._run_v18_simulation()

    def _on_1h_close(self, candle: dict):
        """Handle 1h candle close — feed to swing engine."""
        ts = candle["close_time"] // 1000
        date = datetime.fromtimestamp(candle["open_time"] // 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        self.window_1h.append({"date": date, "ts": ts, "open": candle["open"],
                                "high": candle["high"], "low": candle["low"], "close": candle["close"]})
        cutoff = int(time.time()) - WINDOW_DAYS_1H * 86400
        self.window_1h = [c for c in self.window_1h if c["ts"] >= cutoff]
        fc = FlowCandle(date=date, open=candle["open"], high=candle["high"],
                        low=candle["low"], close=candle["close"])
        result = self.swing_1h.process_bar(fc, len(self.window_1h) - 1)
        if result:
            self.all_swings_1h.append(result)
            for b in result.get("breaks", []):
                print(f"[mark]  1h {b['kind']} {b['dir']} sw{b['swing_no']} @ {b['px']:.2f} ({b['time']})")
        self._run_v18_simulation()

    def _track_htf_windows(self, htf_trades: list[dict], c1h: list[dict]):
        """Track and log HTF window state changes."""
        if not htf_trades:
            return

        latest_htf = htf_trades[-1]
        htf_status = latest_htf.get("outcome", "open")

        # Get timestamp for logging
        entry_ts = latest_htf.get("entry_ts", 0)
        entry_date = datetime.fromtimestamp(entry_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if entry_ts else "?"

        if htf_status == "open" and not self.htf_window_open:
            self.htf_window_open = True
            self.htf_window_dir = latest_htf.get("dir")
            self.htf_window_start_ts = entry_ts
            print(f"[htf] Window OPENED: {self.htf_window_dir} @ {latest_htf.get('entry_price', 0):.2f} ({entry_date})")
        elif htf_status != "open" and self.htf_window_open:
            exit_ts = latest_htf.get("exit_ts", 0)
            exit_date = datetime.fromtimestamp(exit_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if exit_ts else "?"
            self.htf_window_open = False
            print(f"[htf] Window CLOSED: {latest_htf.get('outcome')} @ {latest_htf.get('exit_price', 0):.2f} ({exit_date}, {latest_htf.get('r_multiple', 0):+.2f}R)")
            self.htf_window_dir = None
            self.htf_window_start_ts = 0

        if self.htf_window_open:
            print(f"[htf] Window OPEN: {self.htf_window_dir} (since {entry_date})")

    def _journal_marks(self, tf: str, swings: list[dict], candles: list[dict]):
        existing = self._get_existing_marks_set(tf)
        new_marks = []
        for s in swings:
            for b in s.get("breaks", []):
                idx = b.get("idx", -1)
                if 0 <= idx < len(candles):
                    candle = candles[idx]
                    key = (candle["ts"], b["kind"], b["dir"], s["swing_index"])
                    if key not in existing:
                        mark = {"ts": candle["ts"], "date": candle["date"], "tf": tf, "kind": b["kind"], "dir": b["dir"], "px": b["px"], "swing_no": s["swing_index"], "swing_kind": s.get("dir", "")}
                        new_marks.append(mark)
                        existing.add(key)
        for mark in new_marks:
            self._insert_mark(mark)
            print(f"[mark] {tf} {mark['kind']} {mark['dir']} sw{mark['swing_no']} @ {mark['px']:.2f}")

    def _journal_trades(self, ltf_trades: list[dict]):
        existing = self._get_existing_trades_set()
        new_trades = []
        for t in ltf_trades:
            key = (t["entry_ts"], t["dir"], t["break_kind"], t["swing_no"])
            if key not in existing:
                new_trades.append(t)
                existing.add(key)
        for t in new_trades:
            cap_ts = int(t["entry_ts"]) + CAP_DAYS * 86400
            trade_id = open_ltf_trade(
                self.db,
                direction=t["dir"],
                entry_ts=int(t["entry_ts"]),
                entry_price=float(t["entry_price"]),
                sl_initial=float(t["sl"]),
                tp_price=float(t["target"]),
                cap_ts=cap_ts,
                htf_window_id=0,
            )
            if t["outcome"] != "open":
                close_ltf_trade(
                    self.db,
                    trade_id=trade_id,
                    exit_ts=int(t["exit_ts"]),
                    exit_price=float(t["exit_price"]),
                    exit_reason=t["outcome"],
                    r_multiple=float(t["r_multiple"]),
                )
                print(f"[trade] {t['dir']} sw{t['swing_no']} @ {t['entry_price']:.2f} -> {t['exit_price']:.2f} ({t['outcome']}, {t['r_multiple']:+.2f}R)")
            else:
                print(f"[trade] {t['dir']} sw{t['swing_no']} @ {t['entry_price']:.2f} OPEN (SL={t['sl']:.2f} TP={t['target']:.2f})")

    def _get_existing_marks_set(self, tf: str) -> set:
        marks = get_marks(self.db, tf)
        return {(m.ts, m.kind, m.direction, m.swing_no) for m in marks}

    def _get_existing_trades_set(self) -> set:
        trades = get_ltf_trades(self.db)
        return {(t["entry_ts"], t["direction"], t.get("break_kind", ""), t.get("swing_no", 0)) for t in trades}

    def _insert_mark(self, mark: dict):
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO marks (ts, tf, kind, direction, price, swing_no, swing_kind, algo_version, journaled_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (mark["ts"], mark["tf"], mark["kind"], mark["dir"], mark["px"], mark["swing_no"], mark.get("swing_kind", ""), 1, int(time.time())),
            )

    def _trail_sl(self, sw15: list[dict]):
        """Trail SL using _trail_events — same logic as v18 backtest.

        v18 rule (v18_streak_halt.py:260-290):
          - LONG:  ratchet SL UP to UP-swing start lows (pivot lows)
          - SHORT: ratchet SL DOWN to DOWN-swing start highs (pivot highs)
          - Only trail AFTER entry bar, only ratchet in profitable direction
          - Guard: new SL must be between current SL and current bar's extreme
        """
        open_trade = get_open_ltf_trade(self.db)
        if not open_trade or not self.window_15m:
            return

        direction = 1 if open_trade["direction"] == "long" else -1
        entry_ts = int(open_trade["entry_ts"])
        sl_current = float(open_trade["sl_current"])

        # Get direction-filtered trail events: (confirmed_at_idx, seg.start_px)
        events = _trail_events(sw15, direction)
        if not events:
            return

        # Find entry bar index
        candle_ts = [int(c["ts"]) for c in self.window_15m]
        entry_idx = bisect.bisect_left(candle_ts, entry_ts)
        n = len(self.window_15m)

        # Walk through events after entry (same logic as v18:262-290)
        new_sl = sl_current
        for conf_idx, pivot_px in events:
            # Skip events before entry bar (v18: "if events[ev_idx][0] < i: continue")
            if conf_idx < entry_idx:
                continue
            # Skip events beyond our candle window
            if conf_idx >= n:
                break
            # Get current bar's price range
            bar = self.window_15m[conf_idx]
            lo = float(bar["low"])
            hi = float(bar["high"])
            # Ratchet: new SL must be between current SL and current bar's extreme
            if direction == 1:  # LONG: trail UP to higher swing lows
                if new_sl < pivot_px < lo:
                    new_sl = pivot_px
            else:  # SHORT: trail DOWN to lower swing highs
                if hi < pivot_px < new_sl:
                    new_sl = pivot_px

        if new_sl != sl_current:
            from persistence.trade_store import update_trade_sl
            update_trade_sl(self.db, open_trade["id"], new_sl)
            print(f"[trail] SL {sl_current:.2f} -> {new_sl:.2f}")

    def on_tick(self, price: float, ts: int):
        """Process a price tick. Check SL/TP/cap for open trades.

        R multiples computed from actual exit price (not hardcoded),
        because trailing can move SL above entry (positive R).
        """
        open_trade = get_open_ltf_trade(self.db)
        if not open_trade:
            return

        entry_price = float(open_trade["entry_price"])
        sl_initial = float(open_trade["sl_initial"])
        sl_current = float(open_trade["sl_current"])
        tp_price = float(open_trade["tp_price"])
        direction = open_trade["direction"]
        risk = abs(entry_price - sl_initial)
        if risk <= 0:
            return

        # Cap check
        if ts >= open_trade["cap_ts"]:
            r = self._calc_r(direction, entry_price, price, risk)
            close_ltf_trade(self.db, open_trade["id"], ts, price, "cap", r)
            print(f"[trade] Cap hit: {price:.2f} ({r:+.2f}R)")
            return

        # SL check
        sl_hit = (direction == "long" and price <= sl_current) or (direction == "short" and price >= sl_current)
        if sl_hit:
            r = self._calc_r(direction, entry_price, price, risk)
            reason = "sl" if abs(sl_current - sl_initial) < 0.01 else "trail"
            close_ltf_trade(self.db, open_trade["id"], ts, price, reason, r)
            print(f"[trade] {reason.upper()} hit: {price:.2f} ({r:+.2f}R)")
            return

        # TP check
        tp_hit = (direction == "long" and price >= tp_price) or (direction == "short" and price <= tp_price)
        if tp_hit:
            close_ltf_trade(self.db, open_trade["id"], ts, price, "tp", 3.0)
            print(f"[trade] TP hit: {price:.2f} (+3.0R)")

    @staticmethod
    def _calc_r(direction: str, entry_price: float, exit_price: float, risk: float) -> float:
        """Calculate R multiple — mirrors v18_streak_halt.py:322-323."""
        if risk <= 0:
            return 0.0
        if direction == "long":
            return (exit_price - entry_price) / risk
        else:
            return (entry_price - exit_price) / risk


