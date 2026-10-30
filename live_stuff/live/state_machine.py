"""Incremental state machine for Book 107 (Phase 1, slices 1-4)."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Optional

from _vendored.v7_timecap import simulate_btc_trades_v7
from _vendored.btc_engine import _trail_events_ts
from live.htf_windows import to_intervals


@dataclass
class Leg:
    entry_ts: int
    direction: int
    entry_price: float
    sl_initial: float
    sl_current: float
    target: float
    cap_ts: int
    swing_no: int
    htf_regime: str
    is_gray: bool = False


@dataclass
class LiveEngineState:
    prev_swing_15m: Optional[dict] = None
    cur_swing_15m: Optional[dict] = None
    prev_swing_1h: Optional[dict] = None
    cur_swing_1h: Optional[dict] = None

    open_ltf_legs: list = field(default_factory=list)
    open_htf_windows: dict = field(default_factory=dict)

    cooldown_remaining: int = 8
    consecutive_losses: int = 0
    halt_skip_next: bool = False
    daily_pnl_r: float = 0.0
    daily_halted: bool = False
    last_trade_date: str = ""
    last_loss_bar_idx: int = -999999
    busy_until_ts: int = 0

    atr_15m: list = field(default_factory=list)
    atr_pct_15m: float = 0.5
    last_closed_1h_chop: float = 50.0
    htf_chop_buf: list = field(default_factory=list)

    regime_use: Optional[str] = None
    regime_disagree: int = 0

    last_processed_ts_15m: int = 0
    last_processed_ts_1h: int = 0
    seen_marks: set = field(default_factory=set)
    entered_fs_swings: set = field(default_factory=set)
    pre_fs_used_swings: set = field(default_factory=set)
    _no_opposite_legs: list = field(default_factory=list)


def _mark_key(m, swing_no):
    return (int(swing_no), int(m.get("idx", -1)), str(m.get("kind", "")),
            str(m.get("dir", "")))


def _chop_one(buf):
    n = len(buf)
    lb = 14
    if n < lb + 1:
        return 50.0
    trs = []
    for i in range(n - lb, n):
        hi = float(buf[i]["high"]); lo = float(buf[i]["low"])
        if i == 0 or i - 1 < n - lb:
            trs.append(hi - lo)
        else:
            pc = float(buf[i - 1]["close"])
            trs.append(max(hi - lo, abs(hi - pc), abs(lo - pc)))
    tr_sum = sum(trs)
    hi_max = max(float(buf[j]["high"]) for j in range(n - lb, n))
    lo_min = min(float(buf[j]["low"]) for j in range(n - lb, n))
    rang = hi_max - lo_min
    if rang > 0 and tr_sum > 0:
        try:
            return 100 * math.log10(tr_sum / rang) / math.log10(lb)
        except (ValueError, ZeroDivisionError):
            return 50.0
    return 50.0


class StateMachine:
    def __init__(self, v18_params: dict):
        self.v18 = dict(v18_params or {})
        self.state = LiveEngineState(
            cooldown_remaining=int(self.v18.get("cooldown_bars", 8)),
        )
        self.htf_candles: list = []
        self.htf_swings: list = []
        self.htf_open_swing: Optional[dict] = None
        self.htf_trades_flip: list = []
        self.htf_trades_decisive: list = []
        self.htf_trades_b2: list = []
        self.last_htf_entry_ts_flip: int = 0
        self.last_htf_entry_ts_dec: int = 0
        self.last_htf_entry_ts_b2: int = 0
        self.swings_15m: list = []
        self.completed_trades: list = []
        self.detected_marks: list = []
        self.detected_entries: list = []
        self.gate_counts = {"marks": 0, "tradeable": 0, "prefilter": 0,
                            "cooldown": 0, "htf_window": 0, "ext_stop": 0,
                            "sl_valid": 0, "entry": 0, "fs_entry": 0, "opp_lock": 0}

    def _gate_and_enter(self, swing, kind, mark_time, use_fs, candle, g_idx, mark_idx=-1):
        v18 = self.v18
        mode = v18.get("mode", "atr_high")
        atr_high_thresh = float(v18.get("atr_high_thresh", 0.65))
        atr_low_thresh = float(v18.get("atr_low_thresh", 0.35))
        chop_thresh = float(v18.get("chop_thresh", 58.0))
        ext_stop_r = float(v18.get("ext_stop_r", 3.0))
        cooldown_bars = int(v18.get("cooldown_bars", 8))
        sl_buf_atr = float(v18.get("sl_buf_atr", 0.01))
        min_sl_pct = float(v18.get("exp_min_sl_pct", 0.0))

        prev_swing = self.state.prev_swing_15m
        prev_confirmed_time = ""
        if prev_swing is not None:
            prev_confirmed_time = str(prev_swing.get("confirmed_at_time") or "")

        atrp = self.state.atr_pct_15m
        if mode == "atr_high":
            raw_use = "decisive" if atrp > atr_high_thresh else "flip"
        elif mode == "atr_low":
            raw_use = "decisive" if atrp < atr_low_thresh else "flip"
        elif mode == "chop":
            ch = self.state.last_closed_1h_chop
            raw_use = "decisive" if ch > chop_thresh else "flip"
        else:
            raw_use = "flip"

        if self.state.regime_use is None:
            self.state.regime_use = raw_use
            use = raw_use
        else:
            exp_persist = int(v18.get("exp_persist", 7))
            if raw_use != self.state.regime_use:
                self.state.regime_disagree += 1
                if self.state.regime_disagree >= exp_persist:
                    self.state.regime_use = raw_use
                    self.state.regime_disagree = 0
            else:
                self.state.regime_disagree = 0
            use = self.state.regime_use

        bar_ts = int(candle.get("ts", 0))
        direction = 1 if (kind == "FS" and swing.get("dir") == "up") else (1 if str(swing.get("dir", "")) == "up" else -1)
        if not use_fs:
            mdir = None
            for mm in (swing.get("breaks") or []):
                if mm.get("kind") == kind and str(mm.get("time", "")) == mark_time:
                    mdir = mm.get("dir")
                    break
            if mdir is not None:
                direction = 1 if mdir == "up" else -1

        if not use_fs:
            if kind not in ("B2", "FLIP", "DECISIVE"):
                return
            self.gate_counts["tradeable"] += 1
            if prev_confirmed_time and mark_time < prev_confirmed_time:
                return
            # index-based fallback (when prev_confirmed_time is empty)
            if not prev_confirmed_time and prev_swing is not None:
                prev_confirmed_idx = int(prev_swing.get("confirmed_at_idx", -1))
                if isinstance(mark_idx, int) and mark_idx >= 0 and prev_confirmed_idx >= 0 and mark_idx < prev_confirmed_idx:
                    return
            # FCFS: first tradeable mark per swing wins
            swing_no = int(swing.get("swing_index", -1))
            if swing_no in self.state.pre_fs_used_swings:
                return
            self.state.pre_fs_used_swings.add(swing_no)
            self.gate_counts["prefilter"] += 1

        if cooldown_bars > 0 and (g_idx - self.state.last_loss_bar_idx) < cooldown_bars:
            return
        self.gate_counts["cooldown"] += 1

        # exp_no_opposite: refuse if an opposite-direction leg is open right now
        if self.v18.get("exp_no_opposite", 1):
            for ol in self.state._no_opposite_legs:
                if ol.direction != direction:
                    self.gate_counts["opp_lock"] = self.gate_counts.get("opp_lock", 0) + 1
                    return

        def _htf_window_for(regime, direction):
            ivs = self.state.open_htf_windows.get(regime, [])
            for iv in ivs:
                try:
                    s, e, d, pe, psl = iv[0], iv[1], iv[2], iv[3], iv[4]
                except (TypeError, ValueError, IndexError):
                    continue
                if not (s + 2700 < bar_ts + 900 < e):
                    continue
                if d != direction:
                    continue
                floor = s + 2700
                if not (floor < bar_ts + 900):
                    continue
                return (s, e, d, pe, psl)
            return None

        win = _htf_window_for(use, direction)
        if win is None:
            return
        self.gate_counts["htf_window"] += 1
        win_start, win_end, wdir, pe, psl = win

        hrisk = abs(pe - psl)
        if hrisk > 0 and (ext_stop_r > 0):
            close_px = float(candle.get("close", 0))
            ext = (close_px - pe) * direction / hrisk
            if ext > ext_stop_r:
                return
        self.gate_counts["ext_stop"] += 1

        entry_price = float(candle.get("close", 0))
        sl_pivot = float(swing.get("seg", {}).get("start_px") or 0)
        atr14 = 0.0
        if len(self.state.atr_15m) >= 2:
            trs = []
            b = self.state.atr_15m
            for i in range(len(b)):
                hi = float(b[i]["high"]); lo = float(b[i]["low"])
                if i == 0:
                    trs.append(hi - lo)
                else:
                    pc = float(b[i - 1]["close"])
                    trs.append(max(hi - lo, abs(hi - pc), abs(lo - pc)))
            atr14 = sum(trs) / len(trs)

        if direction == 1:
            sl = sl_pivot - sl_buf_atr * atr14 if sl_buf_atr > 0 else sl_pivot
            if sl >= entry_price:
                return
            risk = entry_price - sl
            if risk < 0.0005 * entry_price:
                return
            if min_sl_pct > 0 and risk < min_sl_pct * entry_price:
                return
            target = entry_price + 3.0 * risk
        else:
            sl = sl_pivot + sl_buf_atr * atr14 if sl_buf_atr > 0 else sl_pivot
            if sl <= entry_price:
                return
            risk = sl - entry_price
            if risk < 0.0005 * entry_price:
                return
            if min_sl_pct > 0 and risk < min_sl_pct * entry_price:
                return
            target = entry_price - 3.0 * risk

        self.gate_counts["sl_valid"] += 1

        cap_ts = int(candle.get("ts", 0)) + 16 * 86400

        entry_rec = {
            "entry_ts": int(candle.get("ts", 0)),
            "dir": "long" if direction == 1 else "short",
            "direction": direction,
            "swing_no": int(swing.get("swing_index", -1)),
            "kind": "FS" if use_fs else kind,
            "htf_regime": use,
            "entry_price": round(entry_price, 2),
            "sl": round(sl, 2),
            "target": round(target, 2),
            "win_start": int(win_start),
            "win_end": int(win_end),
        }
        self.detected_entries.append(entry_rec)

        leg = Leg(
            entry_ts=int(candle.get("ts", 0)),
            direction=direction,
            entry_price=entry_price,
            sl_initial=sl,
            sl_current=sl,
            target=target,
            cap_ts=cap_ts,
            swing_no=int(swing.get("swing_index", -1)),
            htf_regime=use,
        )
        self.state.open_ltf_legs.append(leg)
        self.state._no_opposite_legs.append(leg)
        self.gate_counts["entry"] += 1
        if use_fs:
            self.gate_counts["fs_entry"] += 1

    def on_15m_bar(self, candle, g_idx, swing_event=None, open_swing=None):
        self.state.last_processed_ts_15m = int(candle.get("ts", 0))
        # Snapshot open legs before exits (for exp_no_opposite pre-exit check)
        self.state._no_opposite_legs = list(self.state.open_ltf_legs)

        self.state.atr_15m.append(dict(candle))
        if len(self.state.atr_15m) > 14:
            self.state.atr_15m.pop(0)
        buf = self.state.atr_15m
        n = len(buf)
        if n >= 2:
            trs = []
            for i in range(n):
                hi = float(buf[i]["high"]); lo = float(buf[i]["low"])
                if i == 0:
                    trs.append(hi - lo)
                else:
                    pc = float(buf[i - 1]["close"])
                    trs.append(max(hi - lo, abs(hi - pc), abs(lo - pc)))
            atr = sum(trs) / len(trs)
            close = float(buf[-1]["close"])
            if close != 0:
                self.state.atr_pct_15m = atr / close * 100.0

        new_marks = []

        if swing_event is not None:
            self.state.prev_swing_15m = self.state.cur_swing_15m
            self.state.cur_swing_15m = swing_event
            self.swings_15m.append(swing_event)
            si = swing_event.get("swing_index")
            for m in (swing_event.get("breaks") or []):
                mm = dict(m)
                mm["swing_index"] = si
                mm["_swing"] = swing_event
                k = _mark_key(mm, si)
                if k in self.state.seen_marks:
                    continue
                self.state.seen_marks.add(k)
                mm_clean = {kk: vv for kk, vv in mm.items() if kk != "_swing"}
                self.detected_marks.append(mm_clean)
                new_marks.append(mm)

            fs_side = self.v18.get("exp_fs_entry_side", "")
            if fs_side in ("long", "both"):
                swing = swing_event
                if swing.get("dir") == "up":
                    fs_t = swing.get("fs_at_time") or swing.get("confirmed_at_time") or ""
                    si = swing.get("swing_index")
                    if fs_t and si not in self.state.entered_fs_swings:
                        if str(fs_t)[:19] == str(candle.get("date", ""))[:19]:
                            self.state.entered_fs_swings.add(si)
                            self._gate_and_enter(swing, "FS", str(fs_t), True, candle, g_idx, swing.get("fs_at_idx", -1))

            # Trailing: ratchet open legs in matching direction using completed swing
            for leg in list(self.state.open_ltf_legs):
                if (leg.direction == 1 and swing.get("dir") == "up") or \
                   (leg.direction == -1 and swing.get("dir") == "down"):
                    evs = _trail_events_ts([swing], leg.direction)
                    for ts_c, pivot in evs:
                        if ts_c <= int(candle.get("ts", 0)):
                            if leg.direction == 1:
                                if leg.sl_current < pivot < float(candle.get("low", 0)):
                                    leg.sl_current = pivot
                            else:
                                if float(candle.get("high", 0)) < pivot < leg.sl_current:
                                    leg.sl_current = pivot

        if open_swing is not None:
            self.state.cur_swing_15m = open_swing
            si = open_swing.get("swing_index")
            for m in (open_swing.get("breaks") or []):
                mm = dict(m)
                mm["swing_index"] = si
                mm["_swing"] = open_swing
                k = _mark_key(mm, si)
                if k in self.state.seen_marks:
                    continue
                self.state.seen_marks.add(k)
                mm_clean = {kk: vv for kk, vv in mm.items() if kk != "_swing"}
                self.detected_marks.append(mm_clean)
                new_marks.append(mm)

        if self.state.last_loss_bar_idx > -999999 and self.state.cooldown_remaining > 0:
            self.state.cooldown_remaining -= 1

        fs_side = self.v18.get("exp_fs_entry_side", "")

        # LTF exit evaluation
        bar_ts = int(candle.get("ts", 0))
        bar_high = float(candle.get("high", 0))
        bar_low = float(candle.get("low", 0))
        bar_close = float(candle.get("close", 0))
        still_open = []
        for leg in self.state.open_ltf_legs:
            exited = False
            outcome = None
            exit_px = None
            exit_ts = bar_ts
            if leg.direction == 1:
                if bar_low <= leg.sl_current:
                    exited = True
                    exit_px = min(leg.sl_current, float(candle.get("open", bar_close)))
                    outcome = "sl" if leg.sl_current <= leg.sl_initial else "trail"
                elif bar_high >= leg.target:
                    exited = True
                    exit_px = leg.target
                    outcome = "target"
            else:
                if bar_high >= leg.sl_current:
                    exited = True
                    exit_px = max(leg.sl_current, float(candle.get("open", bar_close)))
                    outcome = "sl" if leg.sl_current >= leg.sl_initial else "trail"
                elif bar_low <= leg.target:
                    exited = True
                    exit_px = leg.target
                    outcome = "target"
            if not exited and bar_ts >= leg.cap_ts:
                exited = True
                exit_px = bar_close
                outcome = "cap"
            if exited:
                risk = abs(leg.entry_price - leg.sl_initial)
                if risk > 0:
                    move = (exit_px - leg.entry_price) if leg.direction == 1 else (leg.entry_price - exit_px)
                    r_mult = move / risk
                else:
                    r_mult = 0.0
                self.completed_trades.append({
                    "entry_ts": leg.entry_ts,
                    "dir": "long" if leg.direction == 1 else "short",
                    "outcome": outcome,
                    "r_multiple": round(r_mult, 3),
                    "exit_ts": exit_ts,
                    "exit_price": round(exit_px, 2),
                })
                if r_mult < 0:
                    self.state.last_loss_bar_idx = g_idx
                    self.state.cooldown_remaining = int(self.v18.get("cooldown_bars", 8))
            else:
                still_open.append(leg)
        self.state.open_ltf_legs = still_open


        for m in new_marks:
            kind = str(m.get("kind", ""))
            if kind not in ("B2", "FLIP", "DECISIVE"):
                continue
            self.gate_counts["marks"] += 1
            swing = m.get("_swing", self.state.cur_swing_15m)
            if swing is None:
                continue
            swing_no = int(m.get("swing_index", swing.get("swing_index", -1)))
            if swing_no < 1:
                continue
            up = (str(m.get("dir", "")) == "up")
            use_fs = (fs_side == "both" or (fs_side == "long" and up)
                      or (fs_side == "short" and not up))
            if use_fs:
                continue
            mark_time = str(m.get("time", ""))
            if not mark_time:
                continue
            self._gate_and_enter(swing, kind, mark_time, False, candle, g_idx, m.get("idx", -1))

        return new_marks, []

    # ---- 1h side ----
    def on_1h_bar(self, candle, g_idx, swing_event=None, open_swing=None,
                  auto_recompute=True):
        self.state.last_processed_ts_1h = int(candle.get("ts", 0))
        self.htf_candles.append(dict(candle))
        self.state.htf_chop_buf.append(dict(candle))
        if len(self.state.htf_chop_buf) > 14:
            self.state.htf_chop_buf.pop(0)
        self.state.last_closed_1h_chop = _chop_one(self.state.htf_chop_buf)

        if swing_event is not None:
            self.state.prev_swing_1h = self.state.cur_swing_1h
            self.state.cur_swing_1h = swing_event
            self.htf_swings.append(swing_event)

        if open_swing is not None:
            self.state.cur_swing_1h = open_swing
            self.htf_open_swing = open_swing

        self._update_htf_trades(candle)

    def _update_htf_trades(self, candle):
        swings_for_v7 = list(self.htf_swings)
        if self.htf_open_swing and self.htf_open_swing.get("breaks"):
            swings_for_v7 = swings_for_v7 + [self.htf_open_swing]
        if not swings_for_v7 or not self.htf_candles:
            return
        v18 = self.v18
        htf_rr = float(v18.get("htf_rr", 3.0))
        exp_cap_days = int(v18.get("exp_cap_days", 16))
        pivot_rule = v18.get("pivot_rule", "leg")
        try:
            hf = simulate_btc_trades_v7(self.htf_candles, swings_for_v7,
                                        entry_break="flip", sl_mode="swing",
                                        rr_target=htf_rr, trailing="off",
                                        skip_first=True, cap_days=exp_cap_days,
                                        pivot_rule=pivot_rule)
            hd = simulate_btc_trades_v7(self.htf_candles, swings_for_v7,
                                        entry_break="decisive", sl_mode="swing",
                                        rr_target=htf_rr, trailing="off",
                                        skip_first=True, cap_days=exp_cap_days,
                                        pivot_rule=pivot_rule)
            hb = simulate_btc_trades_v7(self.htf_candles, swings_for_v7,
                                        entry_break="b2", sl_mode="swing",
                                        rr_target=htf_rr, trailing="off",
                                        skip_first=True, cap_days=exp_cap_days,
                                        pivot_rule=pivot_rule)
        except Exception:
            hf, hd, hb = [], [], []

        # Collect new entries per regime
        for regime, trades_list, last_attr, target_list in (
            ("flip", hf, "last_htf_entry_ts_flip", self.htf_trades_flip),
            ("decisive", hd, "last_htf_entry_ts_dec", self.htf_trades_decisive),
            ("b2", hb, "last_htf_entry_ts_b2", self.htf_trades_b2),
        ):
            last_ts = getattr(self, last_attr, 0)
            for t in trades_list:
                ets = int(t.get("entry_ts", 0))
                if ets <= last_ts:
                    continue
                direction = 1 if t.get("dir") == "long" else -1
                entry_price = float(t.get("entry_price", 0))
                sl = float(t.get("sl", 0))
                risk = abs(entry_price - sl)
                target = entry_price + (3.0 * risk if direction == 1 else -3.0 * risk)
                target_list.append({
                    "entry_ts": ets,
                    "dir": direction,
                    "entry_price": entry_price,
                    "sl": sl,
                    "target": target,
                    "cap_ts": ets + 16 * 86400,
                    "exit_ts": None,
                    "outcome": "open",
                })
                if ets > last_ts:
                    last_ts = ets
            setattr(self, last_attr, last_ts)

        # Evaluate exits of open HTF trades
        bar_ts = int(candle.get("ts", 0))
        hi = float(candle.get("high", 0))
        lo = float(candle.get("low", 0))
        for lst in (self.htf_trades_flip, self.htf_trades_decisive, self.htf_trades_b2):
            for t in lst:
                if t["exit_ts"] is not None:
                    continue
                if bar_ts < t["entry_ts"]:
                    continue
                d = t["dir"]
                if d == 1:
                    if lo <= t["sl"]:
                        t["exit_ts"] = bar_ts
                        t["outcome"] = "sl"
                    elif hi >= t["target"]:
                        t["exit_ts"] = bar_ts
                        t["outcome"] = "target"
                else:
                    if hi >= t["sl"]:
                        t["exit_ts"] = bar_ts
                        t["outcome"] = "sl"
                    elif lo <= t["target"]:
                        t["exit_ts"] = bar_ts
                        t["outcome"] = "target"
                if t["exit_ts"] is None and bar_ts >= t["cap_ts"]:
                    t["exit_ts"] = bar_ts
                    t["outcome"] = "time"

        # Rebuild HTF windows
        ivs_by_regime = {"flip": [], "decisive": [], "b2": []}
        last_ts = int(self.htf_candles[-1]["ts"]) if self.htf_candles else 0
        for t in self.htf_trades_flip:
            start = t["entry_ts"]
            end = (t["exit_ts"] + 3600) if t["exit_ts"] is not None else (last_ts + 3600)
            ivs_by_regime["flip"].append((start, end, t["dir"], t["entry_price"], t["sl"]))
        for t in self.htf_trades_decisive:
            start = t["entry_ts"]
            end = (t["exit_ts"] + 3600) if t["exit_ts"] is not None else (last_ts + 3600)
            ivs_by_regime["decisive"].append((start, end, t["dir"], t["entry_price"], t["sl"]))
        for t in self.htf_trades_b2:
            start = t["entry_ts"]
            end = (t["exit_ts"] + 3600) if t["exit_ts"] is not None else (last_ts + 3600)
            ivs_by_regime["b2"].append((start, end, t["dir"], t["entry_price"], t["sl"]))
        for reg in ivs_by_regime:
            ivs_by_regime[reg].sort(key=lambda x: x[0])
        self.state.open_htf_windows = ivs_by_regime

    def htf_windows_at(self, ts, regime="flip"):
        ivs = self.state.open_htf_windows.get(regime, [])
        out = []
        for iv in ivs:
            try:
                s, e, d, pe, psl = iv[0], iv[1], iv[2], iv[3], iv[4]
            except (TypeError, ValueError, IndexError):
                continue
            if s <= ts <= e:
                out.append(iv)
        return out
