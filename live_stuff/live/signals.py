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
from .state import is_gray_leg
from .retention import trim_candles_and_swings

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



class SignalsMixin:
    """signals responsibilities."""

    def _log_signal_diagnostics(self, sw15: list[dict], c15: list[dict], ltf_trades: list[dict]):
        """Phase 3: per-signal filter diagnostics — WHY each signal was skipped/taken.

        Mirrors v18's regime/window/ext_stop/cooldown gates but uses the live
        rolling HTF tracker state (htf_window_open, chop, regime, hrisk) so
        the log matches what a live operator sees.
        """
        try:
            from _vendored.btc_engine import _collect_signals
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
            try:
                sbar = int(s["bar"])
            except (TypeError, ValueError):
                date_str = str(s["bar"])
                sbar = next((i for i, c in enumerate(c15) if c.get("date") == date_str), -1)
                if sbar < 0:
                    continue
            k = (sbar, s.get("kind", ""), int(s["dir"]))
            if k not in self._logged_filter_keys:
                new_sigs.append(s)
        # On first seed, raw_sigs may be 50+ — cap to last 5 new
        if len(new_sigs) > 5:
            # Mark older as seen without logging
            for s in new_sigs[:-5]:
                try:
                    sbar = int(s["bar"])
                except (TypeError, ValueError):
                    date_str = str(s["bar"])
                    sbar = next((i for i, c in enumerate(c15) if c.get("date") == date_str), -1)
                self._logged_filter_keys.add((sbar, s.get("kind", ""), int(s["dir"])))
            new_sigs = new_sigs[-5:]
        if not new_sigs:
            return
        to_log = new_sigs
        for sig in to_log:
            try:
                bar = int(sig["bar"])
            except (TypeError, ValueError):
                # _collect_signals can carry a date string instead of an index
                date_str = str(sig["bar"])
                bar = next((i for i, c in enumerate(c15) if c.get("date") == date_str), -1)
                if bar < 0:
                    print(f"[filter] skip signal with unknown bar {date_str!r}")
                    continue
            self._logged_filter_keys.add((bar, sig.get("kind", ""), int(sig["dir"])))
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
            flag = self.regime.upper()  # engine bucket name: FLIP/B2/DECISIVE
            print(f"[filter] {outcome:6} {kind} {sdir} @ {px:.2f} bar={bar} {date} | HTF[{w['tag']}] {w['dir'] or 'none'} {ext_r_str} gate {self.v18['ext_stop_r']}R | regime {flag} chop {self.chop_index:.1f} | {reason}")

    def _run_v18_simulation(self):
        """Sync entry point — schedules the async simulation.

        If an event loop is running (live streaming), schedule the async
        version as a task so the streamer isn't blocked. If no loop is
        running (seed/recovery pre-loop), run it directly via asyncio.run.
        A guard flag prevents overlapping simulations.
        """
        if getattr(self, "_sim_running", False):
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            self._sim_running = True
            try:
                asyncio.run(self._run_v18_simulation_async())
            finally:
                self._sim_running = False
            return
        self._sim_running = True
        task = loop.create_task(self._run_v18_simulation_async())
        task.add_done_callback(lambda t: setattr(self, "_sim_running", False))

    async def _run_v18_simulation_async(self):
        if len(self.all_candles_15m) < SWING["min_bars_15m"] + 5 or len(self.all_candles_1h) < SWING["min_bars_1h"] + 5:
            print(f"[live] candles too small: 15m={len(self.all_candles_15m)} 1h={len(self.all_candles_1h)}")
            return

        c15 = list(self.all_candles_15m)
        c1h = list(self.all_candles_1h)
        # Option B: use full swing chains directly (no rebased trim)
        sw15 = list(self.all_swings_15m)
        sw1h = list(self.all_swings_1h)
        # L5: forming swing's marks are appended (idx already aligns with all_candles_*)
        try:
            open15 = self.swing_15m.get_open_swing()
            if open15 and open15.get("breaks"):
                sw15 = sw15 + [open15]
            open1h = self.swing_1h.get_open_swing()
            if open1h and open1h.get("breaks"):
                sw1h = sw1h + [open1h]
        except Exception as _oe:
            print(f"[live] open-swing append warning: {_oe}")

        # Bounded sim input: drop candles/swings older than SIM_RETENTION_DAYS.
        # Full stores + DB untouched; only the sim input is trimmed (re-indexed).
        try:
            _keep = int(getattr(config, "SIM_RETENTION_DAYS", 90))
        except Exception:
            _keep = 90
        c15, sw15, _off15 = trim_candles_and_swings(c15, sw15, keep_days=_keep)
        c1h, sw1h, _off1h = trim_candles_and_swings(c1h, sw1h, keep_days=_keep)

        try:
            result = await asyncio.to_thread(
                simulate_htf_ltf_streak_halt,
                c1h, sw1h, c15, sw15,
                fine_ltf=[],
                **self.v18,
            )
        except Exception as e:
            import traceback
            print(f"[live] simulation error: {e}")
            traceback.print_exc()
            return

        ltf_trades = result["ltf_trades"]
        htf_trades = result.get("htf_trades", [])
        htf_trades_b2 = result.get("htf_trades_b2", [])
        htf_trades_dec = result.get("htf_trades_decisive", [])

        # Track HTF window state (flip + b2 + decisive tracked independently)
        self._track_htf_windows(htf_trades, htf_trades_b2, c1h, htf_trades_dec)

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
        print(f"[live] engine: {len(sw15)} 15m sw, {len(sw1h)} 1h sw, {len(ltf_trades)} LTF trades | HTF[{w['tag']}]: {htf_status} {htf_dir}")

    def _window_id_for_regime(self, trade_regime: str):
        """Map a trade's regime stamp (htf_regime) to the tracked window id
        of the SAME family — decisive trades link to the decisive window,
        never to the flip bucket."""
        return {"flip": self.htf_window_id, "b2": self.htf_window_id_b2,
                "decisive": self.htf_window_id_dec}.get(trade_regime, self.htf_window_id)

    def _track_htf_windows(self, htf_trades: list[dict], htf_trades_b2: list[dict],
                           c1h: list[dict], htf_trades_decisive: list[dict] | None = None):
        """Track and log HTF window state changes — Phase 2 rolling record.

        Persists open/close to htf_windows table so state survives restarts.
        Flip, b2 and decisive windows are tracked INDEPENDENTLY — they come
        from separate v7 runs and can be open simultaneously. The regime rule
        (mirror of the engine's per-bar routing, state._compute_regime) selects
        which one is active for metrics/status/linkage.

        An empty trade list for a regime means no trades for it in this window
        slice — that regime's window state is preserved as-is (a truncated seed
        may miss an older entry, cap 16d).
        """
        if htf_trades:
            self._track_window_regime("flip", htf_trades)
        if htf_trades_b2:
            self._track_window_regime("b2", htf_trades_b2)
        if htf_trades_decisive:
            self._track_window_regime("decisive", htf_trades_decisive)
        self._update_htf_metrics()

    def _track_window_regime(self, regime: str, htf_trades: list[dict]):
        """Track open/close of ONE regime's HTF window (flip/b2/decisive).

        Mirrors the Phase 2 tracker but parameterized by regime so all window
        families share identical open/close/persist logic.
        """
        sfx = {"flip": "", "b2": "_b2", "decisive": "_dec"}[regime]
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

    def _at_position_limit(self) -> bool:
        """Book position gate.

        Paper honours the book's max_positions (0 = unlimited) so live paper
        trades match the researched concurrency. Live uses the verified
        per-leg partial-SL cap (10).
        """
        if not self.paper_mode:
            return len(self._open_ltf_trades) >= int(getattr(config, "LIVE_MAX_LEGS", 10))
        max_pos = int(self.v18.get("max_positions", 1) or 0)
        return max_pos > 0 and len(self._open_ltf_trades) >= max_pos

    def _close_gray_legs_from_engine(self, ltf_trades: list[dict]):
        """Close open gray shadows using the engine's own exit when available.

        Live ticks normally close them first; this is the parity/recovery path.
        """
        if not any(is_gray_leg(t) for t in self._open_ltf_trades.values()):
            return
        closed = {
            (int(t["entry_ts"]), t["dir"]): t
            for t in ltf_trades
            if t.get("outcome") != "open"
        }
        for trade_id, trade in list(self._open_ltf_trades.items()):
            if not is_gray_leg(trade):
                continue
            t = closed.get((int(trade["entry_ts"]), trade["direction"]))
            if t is None:
                continue
            self._close_gray_leg(
                trade, int(t["exit_ts"]), float(t["exit_price"]), t["outcome"])

    def _journal_trades(self, ltf_trades: list[dict]):
        self._close_gray_legs_from_engine(ltf_trades)
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
            wid = self._window_id_for_regime(trade_regime)
            htf_id = int(wid) if wid is not None else None  # M1: NULL, not 0 sentinel
            entry_ts = int(t["entry_ts"])
            is_hist = (getattr(self, "_seeding", False) or
                       entry_ts in getattr(self, "_gap_history_ts", set()))
            trade_id = open_ltf_trade(
                self.db,
                direction=t["dir"],
                entry_ts=entry_ts,
                entry_price=float(t["entry_price"]),
                sl_initial=float(t["sl"]),
                tp_price=float(t["target"]),
                cap_ts=cap_ts,
                htf_window_id=htf_id,
                origin="seed_history" if is_hist else "live",
            )
            # C3/C5: stale-entry guard — never execute a trade that is not fresh,
            # and never execute while the daily halt is active. Applies ONLY to
            # open trades; closed trades are history and always journal normally.
            # P0c: gap-backfilled (historical) trades are never sent to exchange.
            if t.get("outcome") == "open":
                in_trade = self._at_position_limit()
                stale = self._is_stale_entry(entry_ts)
                if in_trade:
                    why, exit_reason = "in-trade", "stale_skip"
                elif getattr(self, "_seeding", False):
                    why, exit_reason = "seeding", "stale_skip"
                elif is_hist:
                    why, exit_reason = "gap-history", "gap_skip"
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
                    if trade_id in self._open_ltf_trades:
                        self._cache_ltf_trade_close(trade_id)
                    continue
                if is_gray_leg(self._open_ltf_trades.get(int(trade_id))):
                    self._cache_ltf_trade_close(trade_id)
                    print(f"[gray] engine closed {t['dir']} @ {t['exit_price']:.2f} "
                          f"({r_mult:+.2f}R, no costs)")
                    continue
                # Daily loss gate only applies to live trades, not seed-history replay
                if not is_hist:
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
                # Seed-history trades must not pollute live cumulative stats
                if not is_hist:
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
