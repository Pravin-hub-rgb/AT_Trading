"""Live loop - FULL v18 simulation on rolling windows.

Runs the EXACT same simulate_htf_ltf_streak_halt that the backtest uses,
on rolling windows of Binance data. Produces identical trades.
"""

import sys
import time
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
import bisect

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from src.btc.btc_engine import _trail_events
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.walker import FlowCandle
from src.live.persistent_swing import PersistentSwingEngine
from src.live.data_streamer import BinanceStreamer, backfill_klines

from engine.v18_params import V18, V18_ENGINE, SWING
from persistence.database import Database
from persistence.mark_store import get_marks
from persistence.trade_store import open_ltf_trade, close_ltf_trade, get_open_ltf_trade, get_ltf_trades
from persistence.state_store import get_trading_state, save_trading_state

logger = logging.getLogger("live_loop")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

SYMBOL = "BTCUSDT"
WINDOW_DAYS_15M = 30
WINDOW_DAYS_1H = 20
SEED_15M = 500   # candles to fetch for 15m seeding (~5 days)
SEED_1H = 200    # candles to fetch for 1h seeding (~8 days)
CAP_DAYS = 16
IST = timedelta(hours=5, minutes=30)


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
        # HTF window tracking — rolling record (Phase 2)
        self.htf_window_open = False
        self.htf_window_dir = None          # 'long' | 'short'
        self.htf_window_start_ts = 0
        self.htf_window_id: int | None = None
        self.htf_entry_px = 0.0
        self.htf_sl = 0.0
        self.htf_current_r = 0.0            # unrealized R of the 1h leg vs current 15m close
        self.htf_hrisk = 0.0                # abs(entry - sl) for R calc
        self.chop_index = 50.0              # current 1h chop (last value)
        self.atr_14 = 0.0                   # current 15m ATR(14) in price units
        self.regime = 'flip'                # 'flip' or 'b2' (chop >61.8 ? b2 : flip)
        # Dedup for open-swing mark printing (Phase 1.6)
        self._printed_marks: set = set()
        # Dedup for filter diagnostics (Phase 3)
        self._logged_filter_keys: set = set()
        # Seed file flag — when True, _journal_marks suppresses bulk historical print
        self._seeding = False
        # Restore persisted HTF window if any (Phase 2.5)
        self._restore_htf_state()

    def run(self, max_seconds: float = 0):
        self._running = True
        started = time.time()
        self._seed_from_binance()
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
        try:
            self.chop_index = self._compute_chop()
        except Exception:
            self.chop_index = 50.0
        try:
            self.atr_14 = self._compute_atr_14()
        except Exception:
            self.atr_14 = 0.0
        # Regime from V18: b2_vs_flip_chop -> chop>61.8 ? b2 : flip
        thresh = V18_ENGINE.get("chop_thresh", 61.8)
        self.regime = "b2" if self.chop_index > thresh else "flip"
        # Unrealized R of the 1h leg
        if self.htf_window_open and self.htf_hrisk > 1e-9:
            if price is None:
                price = float(self.window_15m[-1]["close"]) if self.window_15m else self.htf_entry_px
            d = 1 if self.htf_window_dir == "long" else -1
            self.htf_current_r = (float(price) - self.htf_entry_px) * d / self.htf_hrisk
        else:
            self.htf_current_r = 0.0

    def _restore_htf_state(self):
        """Restore persisted HTF window on boot (Phase 2.5)."""
        try:
            from persistence.trade_store import get_open_htf_window
            row = get_open_htf_window(self.db)
            if row:
                self.htf_window_open = True
                self.htf_window_dir = row["direction"]
                self.htf_window_start_ts = int(row["entry_ts"])
                self.htf_window_id = int(row["id"])
                self.htf_entry_px = float(row["entry_price"])
                # sl not stored in htf_windows table — derive hrisk will be set on next _track
                # Keep placeholder until simulation overwrites
                print(f"[htf] Restored open window from DB: {self.htf_window_dir} @ {self.htf_entry_px:.2f} (id={self.htf_window_id})")
        except Exception as e:
            print(f"[htf] restore failed: {e}")

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
        # Raw signals from _collect_signals (same as v18 uses before filtering)
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
            # Compute ext R using rolling HTF window (if open)
            ext_r_str = "n/a"
            ext_r_val = None
            if self.htf_window_open and self.htf_hrisk > 1e-9:
                d = 1 if self.htf_window_dir == "long" else -1
                ext_r_val = (px - self.htf_entry_px) * d / self.htf_hrisk
                ext_r_str = f"{ext_r_val:+.2f}R"
            # Gate checks in order (same order as v18: window, dir, ext_stop, cooldown)
            reason = None
            outcome = "PASS"
            if not self.htf_window_open:
                outcome = "REJECT"
                reason = "no HTF window"
            elif sdir != self.htf_window_dir:
                outcome = "REJECT"
                reason = f"dir mismatch (sig {sdir} vs HTF {self.htf_window_dir})"
            elif ext_r_val is not None and ext_r_val > V18["ext_stop_r"]:
                outcome = "REJECT"
                reason = f"ext_stop {ext_r_str} > {V18['ext_stop_r']}R (late)"
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
            print(f"[filter] {outcome:6} {kind} {sdir} @ {px:.2f} bar={bar} {date} | HTF {self.htf_window_dir or 'none'} {ext_r_str} gate {V18['ext_stop_r']}R | regime {flag} chop {self.chop_index:.1f} | {reason}")

    def _print_status(self):
        """Print current status (HTF bias, position, etc.) — Phase 2 rolling record."""
        # Refresh rolling metrics before printing (uses latest tick/close price)
        try:
            self._update_htf_metrics()
        except Exception:
            pass

        if self.htf_window_open:
            # Show bias + entry + SL + R depth + chop + regime + levels
            # Levels: -1R = SL, 1.5R = ext_stop gate, 3R = target
            hrisk = self.htf_hrisk if self.htf_hrisk > 0 else 0.0
            d = 1 if self.htf_window_dir == "long" else -1
            lvl_sl = self.htf_sl
            lvl_15 = self.htf_entry_px + 1.5 * hrisk * d if hrisk else 0.0
            lvl_3r = self.htf_entry_px + 3.0 * hrisk * d if hrisk else 0.0
            htf_str = (
                f"HTF: {self.htf_window_dir.upper()} @ {self.htf_entry_px:.2f} "
                f"SL={lvl_sl:.2f} (-1R) R={self.htf_current_r:+.2f} "
                f"[1.5R={lvl_15:.2f} 3R={lvl_3r:.2f}] "
                f"CHOP={self.chop_index:.1f} REGIME={self.regime.upper()} ATR={self.atr_14:.1f}"
            )
        else:
            htf_str = f"HTF: NO BIAS | CHOP={self.chop_index:.1f} REGIME={self.regime.upper()} ATR={self.atr_14:.1f}"

        open_trade = get_open_ltf_trade(self.db)
        if open_trade:
            pos_str = f"POS: {open_trade['direction']} @ {open_trade['entry_price']:.2f} SL={open_trade['sl_current']:.2f} TP={open_trade['tp_price']:.2f}"
        else:
            pos_str = "POS: FLAT"

        cd_str = f"CD: {self.trading_state['cooldown_remaining']}" if self.trading_state["cooldown_remaining"] > 0 else ""

        print(f"[status] {htf_str} | {pos_str} {cd_str}".strip())
        # Also log gate status
        if self.htf_window_open:
            gate = "BLOCKED (>1.5R)" if self.htf_current_r > 1.5 else "OPEN"
            print(f"[gate] ext_stop 1.5R: {gate} (current {self.htf_current_r:+.2f}R)")

    # ------------------------------------------------------------------
    # WebSocket callbacks
    # ------------------------------------------------------------------

    def _on_tick(self, price: float, ts_ms: int):
        """Handle real-time tick (for SL/TP monitoring) + rolling R update."""
        if self.window_15m:
            try:
                self.on_tick(price, ts_ms // 1000)
                # Rolling R update on every tick so status/gate is live
                if self.htf_window_open:
                    try:
                        self._update_htf_metrics(price=float(price))
                    except Exception:
                        pass
            except Exception as e:
                print(f"[live] on_tick error: {e}")

    def _on_15m_close(self, candle: dict):
        """Handle 15m candle close — feed to swing engine."""
        try:
            ts = candle["close_time"] // 1000
            date = datetime.fromtimestamp(candle["open_time"] // 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
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
            result = self.swing_15m.process_bar(fc, len(self.window_15m) - 1)
            if result:
                self.all_swings_15m.append(result)
                for b in result.get("breaks", []):
                    print(f"[mark] 15m {b['kind']} {b['dir']} sw{b['swing_no']} @ {b['px']:.2f} ({b['time']})")
            # Phase 1.6: print new marks from the open (unconfirmed) swing instantly
            self._print_open_marks("15m", self.swing_15m)
            self._update_htf_metrics()
            self._run_v18_simulation()
        except Exception as e:
            import traceback
            print(f"[live] _on_15m_close error: {e}")
            traceback.print_exc()

    def _on_1h_close(self, candle: dict):
        """Handle 1h candle close — feed to swing engine."""
        try:
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
            self._print_open_marks("1h", self.swing_1h)
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

    def _fetch_backfill_sync(self, symbol: str, interval: str, limit: int) -> list[dict]:
        """Call backfill_klines regardless of whether it is async or sync (mock-friendly)."""
        import inspect as _inspect
        import asyncio as _asyncio
        res = backfill_klines(symbol, interval, limit=limit)
        if _inspect.isawaitable(res):
            try:
                loop = _asyncio.get_event_loop()
                if loop.is_running():
                    # Already inside an event loop — run in new loop via thread
                    import concurrent.futures as _cf
                    with _cf.ThreadPoolExecutor(max_workers=1) as _pool:
                        fut = _pool.submit(_asyncio.run, res)
                        return fut.result(timeout=30)
                else:
                    return loop.run_until_complete(res)
            except RuntimeError:
                return _asyncio.run(res)
        return res

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
                Path(__file__).resolve().parents[1] / "live_stuff" / "docs" / "seed_marks.json",
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

    def _seed_from_binance(self):
        """Seed swing engines from Binance Futures REST API — VPS-friendly.

        Fetches last SEED_15M / SEED_1H closed candles and replays them
        through PersistentSwingEngine so walker/extremes are correct on boot.
        If docs/seed_marks.json exists, its swings are used as file-truth and
        engine is still replayed for active open-swing tracking (file says where it ends, live starts after).
        Falls back to empty windows if REST is unavailable (first boot offline).
        """
        print(f"[live] Seeding swing engines from Binance REST (15m={SEED_15M}, 1h={SEED_1H})...")
        self._seeding = True
        # Reset engines to clean slate — Binance is source of truth, not stale SQLite state
        # (Walker/internal state has 40+ fields that _load_state cannot fully restore)
        try:
            from src.firstswing import SwingEngine as _SE
            # Clear persisted state so next boot also seeds fresh
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
        except Exception as _e:
            print(f"[live] engine reset warning: {_e}")

        # Try file seed first — file says 'these are marks, this is where it ends, now fetch till now and be active'
        self._seed_cutoff_ts = 0
        file_used = self._try_load_seed_file()
        if file_used:
            print(f"[seed] File truth kept as history — engine will be replayed FULL 500/200 for active open swing (file's cutoff is for display, engine is source of truth for live)")

        # 15m
        try:
            raw_15m = self._fetch_backfill_sync(SYMBOL, "15m", SEED_15M)
            candles_15m = self._normalize_candles(raw_15m)
            # Keep at most WINDOW_DAYS_15M for the rolling window
            cutoff = int(time.time()) - WINDOW_DAYS_15M * 86400
            self.window_15m = [c for c in candles_15m if c["ts"] >= cutoff] or candles_15m
            for i, c in enumerate(candles_15m):
                fc = FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"])
                result = self.swing_15m.process_bar(fc, i)
                if result and not file_used:
                    self.all_swings_15m.append(result)
            self._show_recent_marks(self.all_swings_15m, candles_15m, "15m")
            # Prime open-swing dedup so we don't re-print seeded marks
            open15 = self.swing_15m.get_open_swing()
            if open15:
                for b in open15.get("breaks", []):
                    key = ("15m", b.get("idx", -1), b.get("kind", ""), b.get("dir", ""), open15.get("swing_index", -1))
                    self._printed_marks.add(key)
                print(f"[swing] 15m open: sw{open15['swing_index']} dir={open15['dir']} breaks={len(open15.get('breaks',[]))}")
            print(f"[live] Seeded 15m: {len(candles_15m)} candles, {len(self.all_swings_15m)} swings")
        except Exception as e:
            import traceback
            print(f"[live] 15m seeding failed: {e}")
            traceback.print_exc()

        # 1h
        try:
            raw_1h = self._fetch_backfill_sync(SYMBOL, "1h", SEED_1H)
            candles_1h = self._normalize_candles(raw_1h)
            cutoff = int(time.time()) - WINDOW_DAYS_1H * 86400
            self.window_1h = [c for c in candles_1h if c["ts"] >= cutoff] or candles_1h
            for i, c in enumerate(candles_1h):
                fc = FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"])
                result = self.swing_1h.process_bar(fc, i)
                if result and not file_used:
                    self.all_swings_1h.append(result)
            self._show_recent_marks(self.all_swings_1h, candles_1h, "1h")
            open1h = self.swing_1h.get_open_swing()
            if open1h:
                for b in open1h.get("breaks", []):
                    key = ("1h", b.get("idx", -1), b.get("kind", ""), b.get("dir", ""), open1h.get("swing_index", -1))
                    self._printed_marks.add(key)
                print(f"[swing]  1h open: sw{open1h['swing_index']} dir={open1h['dir']} breaks={len(open1h.get('breaks',[]))}")
            print(f"[live] Seeded  1h: {len(candles_1h)} candles, {len(self.all_swings_1h)} swings")
        except Exception as e:
            import traceback
            print(f"[live]  1h seeding failed: {e}")
            traceback.print_exc()

        print(f"[live] Seeded total: {len(self.all_swings_15m)} 15m swings, {len(self.all_swings_1h)} 1h swings")
        if file_used:
            print(f"[live] Seed file active — live tracking starts AFTER cutoff. Next break will be LIVE [OPEN], not backtest wait.")
        # Phase 2: prime rolling metrics + initial HTF window without waiting for next candle
        try:
            self._update_htf_metrics()
            if len(self.window_15m) >= SWING["min_bars_15m"] + 5 and len(self.window_1h) >= SWING["min_bars_1h"] + 5:
                # During this initial prime, suppress bulk journal blast
                self._seeding = True
                try:
                    self._run_v18_simulation()
                finally:
                    self._seeding = False
        except Exception as _e:
            print(f"[live] post-seed prime warning: {_e}")
            self._seeding = False

    def _seed_from_timestamps(self, ts_1h: str, ts_15m: str) -> dict:
        """Seed swing engines from known backtest timestamps.

        Fetches candles from Binance starting BEFORE the given timestamps
        (warmup: 50 bars for 15m walker/minBars, 34 bars for 1h walker/chop)
        and replays through PersistentSwingEngine. Ensures live engine sees
        the same candles as backtest from the seed point forward.

        Returns summary dict with per-TF candle/swing counts.
        """
        print(f"[seed] Seeding from timestamps: 1h={ts_1h}, 15m={ts_15m}")
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
        except Exception as _e:
            print(f"[seed] engine reset warning: {_e}")

        result = {}

        # Parse timestamps to ms — CSV timestamps are IST wall-clock,
        # so we subtract IST offset to get the real UTC epoch for Binance.
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

        # 15m: fetch from (seed - 50*15min) to now
        warmup_15m_ms = SWING["min_bars_15m"] * 15 * 60 * 1000  # 50 * 15min in ms
        start_15m_ms = seed_15m_ms - warmup_15m_ms
        try:
            from data_streamer import fetch_klines_from as _fkf
            raw_15m = self._fetch_klines_from_sync(SYMBOL, "15m", start_15m_ms, limit=1000)
            candles_15m = self._normalize_candles(raw_15m)
            cutoff = int(time.time()) - WINDOW_DAYS_15M * 86400
            self.window_15m = [c for c in candles_15m if c["ts"] >= cutoff] or candles_15m
            for i, c in enumerate(candles_15m):
                fc = FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"])
                result_15m = self.swing_15m.process_bar(fc, i)
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

        # 1h: fetch from (seed - 34*1h) to now
        warmup_1h_ms = 34 * 3600 * 1000  # 34 hours in ms (20 minBars + 14 chop)
        start_1h_ms = seed_1h_ms - warmup_1h_ms
        try:
            raw_1h = self._fetch_klines_from_sync(SYMBOL, "1h", start_1h_ms, limit=500)
            candles_1h = self._normalize_candles(raw_1h)
            cutoff = int(time.time()) - WINDOW_DAYS_1H * 86400
            self.window_1h = [c for c in candles_1h if c["ts"] >= cutoff] or candles_1h
            for i, c in enumerate(candles_1h):
                fc = FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"])
                result_1h = self.swing_1h.process_bar(fc, i)
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

    def _fetch_klines_from_sync(self, symbol: str, interval: str, start_ms: int, limit: int = 500) -> list[dict]:
        """Call fetch_klines_from regardless of whether it is async or sync."""
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
        if recent_marks:
            print(f"[marks] {tf} recent (last 7d):")
            for m in recent_marks[-15:]:
                print(f"  {m['date']} | {m['kind']:<4} {m['dir']:<4} sw{m['swing_no']} @ {m['px']:.2f}")

    # ------------------------------------------------------------------
    # v18 simulation + journaling
    # ------------------------------------------------------------------

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

        try:
            result = simulate_htf_ltf_streak_halt(
                c1h, sw1h, c15, sw15,
                fine_ltf=[],
                sl_buf_atr=V18["sl_buf_atr"],
                ext_stop_r=V18["ext_stop_r"],
                mode=V18["mode"],
                cooldown_bars=V18["cooldown_bars"],
                max_consecutive_losses=V18["max_consecutive_losses"],
            )
        except Exception as e:
            import traceback
            print(f"[live] v18 simulation error: {e}")
            traceback.print_exc()
            return

        ltf_trades = result["ltf_trades"]
        htf_trades = result.get("htf_trades", [])

        # Track HTF window state
        self._track_htf_windows(htf_trades, c1h)

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

        # Log summary
        htf_status = "OPEN" if self.htf_window_open else "CLOSED"
        htf_dir = self.htf_window_dir if self.htf_window_open else "none"
        print(f"[live] v18: {len(sw15)} 15m sw, {len(sw1h)} 1h sw, {len(ltf_trades)} LTF trades | HTF: {htf_status} {htf_dir}")

    def _persist_streak_state(self):
        """Phase 5: derive consecutive_losses/halted from DB trades and persist.

        Mirrors v18_streak_halt.py:326-334 (tail-loss count, halt on 5L, resume on win).
        Called after every _journal_trades so trading_state DB matches simulation.
        """
        try:
            from persistence.trade_store import get_ltf_trades
            trades = get_ltf_trades(self.db)
            # Count tail consecutive losses (r_multiple <=0). Open trades ignored.
            consec = 0
            last_loss_bar = None
            for t in reversed(trades):
                if t["status"] != "closed":
                    continue
                rm = t.get("r_multiple")
                if rm is None:
                    continue
                if float(rm) <= 0:
                    consec += 1
                    if last_loss_bar is None:
                        # Use exit_ts as proxy for bar index (v18 uses exit_idx)
                        last_loss_bar = int(t.get("exit_ts", 0) or t.get("entry_ts", 0))
                else:
                    break
            max_losses = int(V18.get("max_consecutive_losses", 5) or 0)
            halted = bool(max_losses and consec >= max_losses)
            # Preserve cooldown_remaining and last_loss_bar from current state, update streak
            self.trading_state["consecutive_losses"] = consec
            self.trading_state["halted"] = halted
            # last_loss_bar: keep exit_ts of most recent loss if any, else None
            if consec:
                self.trading_state["last_loss_bar"] = last_loss_bar
            # Persist
            save_trading_state(self.db, self.trading_state)
            if halted:
                print(f"[halt] STREAK HALT: {consec} consecutive losses — trading paused until next winner")
            elif consec:
                print(f"[streak] {consec} consecutive losses (halt at {max_losses})")
        except Exception as e:
            print(f"[streak] persist warning: {e}")

    def _track_htf_windows(self, htf_trades: list[dict], c1h: list[dict]):
        """Track and log HTF window state changes — Phase 2 rolling record.

        Persists open/close to htf_windows table so state survives restarts.
        Keeps entry/sl/hrisk/chop/regime/current R in memory for status + gate.
        """
        if not htf_trades:
            # No HTF trades in this window slice — do NOT auto-close persisted window.
            # Truncated seed (200 1h candles ~8d) may miss an older HTF entry (cap 16d).
            # Keep current HTF state as is; it will be updated when next HTF trade appears.
            return

        latest_htf = htf_trades[-1]
        htf_status = latest_htf.get("outcome", "open")
        entry_ts = int(latest_htf.get("entry_ts", 0))
        entry_date = datetime.fromtimestamp(entry_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if entry_ts else "?"
        entry_px = float(latest_htf.get("entry_price", 0.0))
        sl_px = float(latest_htf.get("sl", 0.0))
        hrisk = abs(entry_px - sl_px) if sl_px else 0.0

        if htf_status == "open" and not self.htf_window_open:
            self.htf_window_open = True
            self.htf_window_dir = latest_htf.get("dir")
            self.htf_window_start_ts = entry_ts
            self.htf_entry_px = entry_px
            self.htf_sl = sl_px
            self.htf_hrisk = hrisk
            # Persist open window (Phase 2.4)
            try:
                from persistence.trade_store import open_htf_window
                cap_ts = entry_ts + CAP_DAYS * 86400
                self.htf_window_id = open_htf_window(self.db, self.htf_window_dir, entry_ts, entry_px, cap_ts)
            except Exception as e:
                print(f"[htf] persist open failed: {e}")
            # Compute metrics right after open
            self._update_htf_metrics()
            lvl_15 = entry_px + 1.5 * hrisk * (1 if self.htf_window_dir == "long" else -1) if hrisk else 0.0
            lvl_3r = entry_px + 3.0 * hrisk * (1 if self.htf_window_dir == "long" else -1) if hrisk else 0.0
            print(f"[htf] Window OPENED: {self.htf_window_dir} @ {entry_px:.2f} SL={sl_px:.2f} (-1R) 1.5R={lvl_15:.2f} 3R={lvl_3r:.2f} ({entry_date}) CHOP={self.chop_index:.1f} {self.regime.upper()}")
        elif htf_status != "open" and self.htf_window_open:
            exit_ts = int(latest_htf.get("exit_ts", 0))
            exit_date = datetime.fromtimestamp(exit_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if exit_ts else "?"
            try:
                from persistence.trade_store import close_htf_window
                if self.htf_window_id is not None:
                    close_htf_window(self.db, self.htf_window_id, exit_ts or int(time.time()), latest_htf.get("outcome", "closed"))
            except Exception as e:
                print(f"[htf] persist close failed: {e}")
            print(f"[htf] Window CLOSED: {latest_htf.get('outcome')} @ {latest_htf.get('exit_price', 0):.2f} ({exit_date}, {latest_htf.get('r_multiple', 0):+.2f}R)")
            self.htf_window_open = False
            self.htf_window_dir = None
            self.htf_window_start_ts = 0
            self.htf_entry_px = 0.0
            self.htf_sl = 0.0
            self.htf_hrisk = 0.0
            self.htf_window_id = None
            self.htf_current_r = 0.0
        elif self.htf_window_open:
            # Already open — refresh entry/sl/hrisk (in case SL drift, but v18 SL is fixed) and metrics
            self.htf_entry_px = entry_px
            self.htf_sl = sl_px
            self.htf_hrisk = hrisk
            self._update_htf_metrics()
            # No duplicate OPEN log here — status line already shows it
            pass
        else:
            # No window, still refresh metrics (chop/regime)
            self._update_htf_metrics()

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
            # During initial seeding, suppress bulk historical blast — _show_recent already showed recent, and live [OPEN] will show active
            if getattr(self, "_seeding", False):
                continue
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
            htf_id = int(self.htf_window_id) if self.htf_window_id is not None else 0
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
        """Trail SL using _trail_events — mirrors v18_streak_halt.py:234-267.

        v18 walks forward from entry+1, activating events when conf_idx <= j
        and only ratchets if pivot is between current SL and bar's extreme.
        This matches the backtest exactly (backtest-precise).
        """
        open_trade = get_open_ltf_trade(self.db)
        if not open_trade or not self.window_15m:
            return

        direction = 1 if open_trade["direction"] == "long" else -1
        entry_ts = int(open_trade["entry_ts"])
        sl_initial = float(open_trade["sl_initial"])
        sl_current = float(open_trade["sl_current"])

        events = _trail_events(sw15, direction)
        if not events:
            return

        # Already sorted by conf_idx; ensure sorted
        events = sorted(events, key=lambda x: x[0])

        candle_ts = [int(c["ts"]) for c in self.window_15m]
        entry_idx = bisect.bisect_left(candle_ts, entry_ts)
        n = len(self.window_15m)
        if entry_idx < 0 or entry_idx >= n - 1:
            return

        # Forward walk exactly like v18: for j in entry+1 .. n-1
        # activate events whose conf_idx <= j and pivot between sl and bar extreme
        new_sl = sl_current
        ev_idx = -1
        for j in range(entry_idx + 1, n):
            bar = self.window_15m[j]
            lo = float(bar["low"])
            hi = float(bar["high"])
            # If price already beyond current SL, don't trail further (would have exited)
            if direction == 1 and lo <= new_sl:
                break
            if direction == -1 and hi >= new_sl:
                break
            while ev_idx + 1 < len(events) and events[ev_idx + 1][0] <= j:
                ev_idx += 1
                conf_idx, pivot_px = events[ev_idx]
                if conf_idx < entry_idx:
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
            # Classify with ATR-scaled tolerance (4.3) for log consistency
            tol = max(0.01, self.atr_14 * 0.05, abs(sl_initial - new_sl) * 0.001) if self.atr_14 else max(0.01, abs(sl_initial - new_sl) * 0.001)
            moved = abs(new_sl - sl_initial) > tol
            tag = "trail" if moved else "sl"
            print(f"[trail] SL {sl_current:.2f} -> {new_sl:.2f} ({tag}) R gap {abs(new_sl-sl_initial)/abs(float(open_trade['entry_price'])-sl_initial):.2f}R")

    def on_tick(self, price: float, ts: int):
        """Process a price tick. Check SL/TP/cap for open trades.

        Conservative fill: gap beyond SL fills at SL (min for long, max for short),
        mirroring v18's min(sl, open) / max(sl, open) intrabar fill. Trail vs SL
        classification uses ATR-scaled tolerance, not fixed 0.01.
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

        # Use current HTF candle's open as gap reference if available
        # Fallback to entry_price if window is tiny
        try:
            gap_open = float(self.window_15m[-1]["open"]) if self.window_15m else price
        except Exception:
            gap_open = price

        if ts >= open_trade["cap_ts"]:
            # Cap: fill at current price (time exit)
            r = self._calc_r(direction, entry_price, price, risk)
            close_ltf_trade(self.db, open_trade["id"], ts, price, "cap", r)
            print(f"[trade] Cap hit: {price:.2f} ({r:+.2f}R)")
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
            close_ltf_trade(self.db, open_trade["id"], ts, fill, reason, r)
            print(f"[trade] {reason.upper()} hit: {fill:.2f} (tick {price:.2f}, {r:+.2f}R)")
            try:
                self._persist_streak_state()
                # Decay cooldown on close via next bar, but also handle immediate halt
            except Exception:
                pass
            return

        tp_hit = (direction == "long" and price >= tp_price) or (direction == "short" and price <= tp_price)
        if tp_hit:
            close_ltf_trade(self.db, open_trade["id"], ts, price, "tp", 3.0)
            print(f"[trade] TP hit: {price:.2f} (+3.0R)")
            try:
                self._persist_streak_state()
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
