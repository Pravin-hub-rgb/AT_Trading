"""1-min standalone engine — truly independent from 5min.

Loops directly over 1-min candles, own Walker, own FirstSwing, own pivots.
No 5min dependency except gap/ctx from daily.
"""

from __future__ import annotations

import pandas as pd
from collections import Counter
from .walker import WalkerEngine, FlowCandle
from .firstswing import FirstSwingEngine
from .intraday import (
    _prep_day,
    _classify_first_swing_v2,
    resolve_cfg,
    classify_case,
    ENTRY_START,
    EOD_EXIT,
    MIN_CANDLES,
    MAX_ENTRIES,
    RR_TARGET,
    COST_TO_COST_R,
    SL_MODE_MULT,
    SL_MODE_FIXED,
    SL_PIVOT_BUFFER,
    DEFAULT_CFG,
)

def simulate_day_1min(
    day_1m: pd.DataFrame,
    bias: str,
    cfg: dict | None = None,
    ctx: dict | None = None,
) -> dict:
    """1-min independent simulation. No 5min involved."""
    cfg = resolve_cfg(cfg)
    ctx = ctx or {}
    base_avg = float(ctx.get("avg_range") or 21.5)
    # Handle timestamp as string or datetime
    first_ts = day_1m["timestamp"].iloc[0]
    try:
        date_str = str(pd.to_datetime(first_ts).date())
    except:
        date_str = str(first_ts)[:10]
    result = {
        "date": date_str,
        "bias": bias,
        "effective_bias": None,
        "case": None,
        "swing_direction": None,
        "trades": [],
        "events": [],
    }

    candles = _prep_day(day_1m)
    if len(candles) < MIN_CANDLES:
        result["events"].append({"type": "skipped_thin_session", "bars": len(candles)})
        return result

    walker = WalkerEngine()
    normal_highs: list = []
    normal_lows: list = []

    # First swing from 1min only
    (swing_dir, swing_start, ev, fs_confirmed_idx,
     fs1_end_idx, fs1_end_px, fs1_end_time) = _classify_first_swing_v2(candles, result["date"])
    result["swing_direction"] = swing_dir
    result["first_swing_confirmed_idx"] = fs_confirmed_idx
    result["first_swing_end_time"] = fs1_end_time
    result["events"].extend(ev)

    if bias in ("bullish", "bearish"):
        want_dir = 1 if bias == "bullish" else -1
    elif bias == "unbiased":
        if swing_dir == "buying":
            want_dir = 1
        elif swing_dir == "selling":
            want_dir = -1
        else:
            result["events"].append({"type": "skipped_unbiased"})
            return result
        result["effective_bias"] = "bullish" if want_dir == 1 else "bearish"
        result["events"].append({
            "type": "effective_bias_from_first_swing",
            "bar": swing_start,
            "time": candles[swing_start]["time"] if swing_start >=0 else "",
            "direction": result["effective_bias"],
        })
    else:
        result["events"].append({"type": "skipped_unbiased"})
        return result

    eff_bias_for_case = "bullish" if want_dir == 1 else "bearish"
    case_id, trade_mode = classify_case(eff_bias_for_case, ctx.get("gap", "flat"), ctx.get("extreme"), swing_dir)
    result["case"] = case_id
    result["trade_mode"] = trade_mode

    if trade_mode == "skip":
        result["events"].append({"type": "skipped_unbiased_1min", "case": case_id})
        return result

    # Second swing for conservative — find FIRST OPPOSITE swing after FS1
    fs2_dir: str | None = None
    fs2_confirmed_idx: int = -1
    fs2_end_idx: int = -1
    fs2_end_px: float = float("nan")
    if trade_mode == "conservative" and swing_dir is not None and fs1_end_idx >= 0:
        from datetime import datetime, timezone, timedelta
        IST = timezone(timedelta(hours=5, minutes=30))
        search_idx = fs1_end_idx + 1
        # Loop until we find an opposite-direction swing or run out of data
        while search_idx < len(candles):
            seed_c = candles[search_idx]
            # Treat 09:33 as new 09:15: use same engine but with 14-bar min, no timeCap
            # Pass minBars=14 and timeCap 00:00 so 09:33 +14 bars = 09:47 earliest
            seed_dt = datetime.fromtimestamp(int(seed_c["ts"]), tz=IST).strftime("%Y-%m-%dT%H:%M:%S")
            seed_fc = FlowCandle(date=seed_dt, open=float(seed_c["open"]), high=float(seed_c["high"]), low=float(seed_c["low"]), close=float(seed_c["close"]))
            eng2 = FirstSwingEngine({"timeCap": "00:00", "minBars": 14})
            eng2.reset_with_candle(seed_fc, search_idx)
            declared = False
            for j in range(search_idx+1, len(candles)):
                mc = candles[j]
                dt = datetime.fromtimestamp(int(mc["ts"]), tz=IST).strftime("%Y-%m-%dT%H:%M:%S")
                fc = FlowCandle(date=dt, open=float(mc["open"]), high=float(mc["high"]), low=float(mc["low"]), close=float(mc["close"]))
                eng2.process_bar(fc, j)
                if eng2.declared:
                    declared = True
                    break
            if not declared:
                result["events"].append({"type": "no_second_swing_declared"})
                break
            cand_dir = "buying" if eng2.dir == "up" else "selling"
            # If same direction as FS1, skip this swing and continue searching from its end
            if cand_dir == swing_dir:
                result["events"].append({"type": "second_swing_same_dir_skipped", "dir": cand_dir, "bar": eng2.start_idx, "time": eng2.start_time})
                search_idx = eng2.end_idx + 1
                continue
            # Found opposite direction
            fs2_dir = cand_dir
            fs2_confirmed_idx = eng2.confirmed_at_idx
            fs2_end_idx = eng2.end_idx
            fs2_end_px = eng2.end_px
            result["events"].append({"type": "swing2_classified", "dir": fs2_dir, "bar": eng2.start_idx, "time": eng2.start_time, "first_swing": swing_dir})
            result["events"].append({"type": "fs2_segment", "dir": eng2.dir, "start_idx": eng2.start_idx, "start_px": eng2.start_px, "end_idx": fs2_end_idx, "end_px": fs2_end_px, "confirmed_at_idx": fs2_confirmed_idx, "confirmed_at_time": eng2.confirmed_at_time})
            result["events"].append({"type": "fs_breaks_2", "breaks": [{"idx": b.idx, "time": b.time, "kind": b.kind, "dir": b.dir, "px": b.px} for b in eng2.break_marks]})
            break
        result["swing2_direction"] = fs2_dir
        result["swing2_confirmed_idx"] = fs2_confirmed_idx
        result["swing2_end_idx"] = fs2_end_idx
        result["swing2_end_px"] = fs2_end_px
    else:
        result["swing2_direction"] = None
        result["swing2_confirmed_idx"] = -1
        result["swing2_end_idx"] = -1
        result["swing2_end_px"] = float("nan")

    # Gate
    if trade_mode == "conservative":
        if fs2_dir is not None and fs2_dir != swing_dir:
            result["events"].append({"type": "second_swing_armed", "dir": fs2_dir, "confirmed_at_idx": fs2_confirmed_idx, "trade_mode": "conservative"})
            entry_swing_confirmed_idx = fs2_confirmed_idx
        else:
            entry_swing_confirmed_idx = 9999999
            result["events"].append({"type": "skipped_same_direction_swing2", "fs1_dir": swing_dir, "fs2_dir": fs2_dir, "trade_mode": "conservative"})
    else:
        entry_swing_confirmed_idx = fs_confirmed_idx

    # For conservative, cur_swing should start as FS2 direction after FS2, not FS1
    # This ensures pivot break is of the second swing, not the first
    initial_cur_swing = fs2_dir if (trade_mode == "conservative" and fs2_dir is not None and fs2_dir != swing_dir) else swing_dir

    # For aggressive, ref is FS1 end; for conservative, ref is FS2 end (if available) else FS1
    ref_swing_end_time = fs1_end_time
    ref_swing_end_idx = fs1_end_idx
    ref_swing_end_dir = swing_dir
    if trade_mode == "aggressive":
        ref_swing_end_px = fs1_end_px
        ref_swing_end_dir = swing_dir
    elif trade_mode == "conservative":
        if fs2_dir is not None and fs2_end_idx >= 0:
            ref_swing_end_px = fs2_end_px
            ref_swing_end_idx = fs2_end_idx
            ref_swing_end_dir = fs2_dir
            ref_swing_end_time = eng2.end_time if 'eng2' in locals() and eng2.declared else fs1_end_time
        else:
            ref_swing_end_px = fs1_end_px
            ref_swing_end_dir = swing_dir
    else:
        ref_swing_end_px = None
        ref_swing_end_dir = None
    # New rule: first swing extreme must NEVER be breached before entry
    # For selling first swing (low): if any 1min low < ref_low after fs1_end, no further longs
    # For buying first swing (high): if any 1min high > ref_high, no further shorts
    first_swing_breached = False

    cur_swing = initial_cur_swing
    # For conservative, use second swing's start for swing extreme
    effective_swing_start = swing_start
    if trade_mode == "conservative" and fs2_dir is not None and fs2_dir != swing_dir:
        for ev in result["events"]:
            if ev.get("type") == "swing2_classified":
                effective_swing_start = ev.get("bar", swing_start)
                break
    if cur_swing is not None and effective_swing_start >=0:
        swing_extreme = max(c["high"] for c in candles[:effective_swing_start+1]) if cur_swing=="buying" else min(c["low"] for c in candles[:effective_swing_start+1])
        swing_base = min(c["low"] for c in candles[:effective_swing_start+1]) if cur_swing=="buying" else max(c["high"] for c in candles[:effective_swing_start+1])
    else:
        swing_extreme = candles[0]["high"]
        swing_base = candles[0]["low"]

    pivot_break_count = 0
    entries_done = 0
    open_trade: dict | None = None
    broken_pivot_levels: set[float] = set()
    i = 0

    def _close_trade(trade, bar_idx, price, outcome, exit_time=None, exit_ts=None):
        nonlocal open_trade
        risk = abs(trade["entry_price"] - trade["sl"])
        r = ((price - trade["entry_price"]) / risk) * (1 if trade["dir"]=="long" else -1)
        xt = exit_time or candles[bar_idx]["time"]
        xts = int(exit_ts if exit_ts is not None else candles[bar_idx]["ts"])
        trade.update(exit_time=xt, exit_ts=xts, exit_price=round(price,2), outcome=outcome, r_multiple=round(r,2))
        result["trades"].append(trade)
        result["events"].append({"type":"exit","bar":bar_idx,"time":xt,"outcome":outcome,"price":round(price,2),"r":round(r,2)})
        open_trade = None

    def _open_trade(bar_idx, dirn, ref_level, dbar, btype):
        nonlocal open_trade, entries_done
        if ref_swing_end_px is not None:
            est_entry = float(ref_level)  # direct
            # For long, ref should be selling swing low; for short, buying swing high
            # Currently ref is FS1's end, but for B7 (FS1 buying, trade long) we need selling swing low, not buying high
            # So only check if entry is on wrong side of ref based on trade_dir vs ref_dir
            if ref_swing_end_dir == "selling" and dirn==1 and est_entry <= ref_swing_end_px:
                result["events"].append({"type":"skipped_end_line","bar":bar_idx,"time":candles[bar_idx]["time"],"reason":"long_entry_below_selling_swing_end","ref_swing_end":round(ref_swing_end_px,2),"entry_price":round(est_entry,2)})
                return False
            if ref_swing_end_dir == "buying" and dirn==-1 and est_entry >= ref_swing_end_px:
                result["events"].append({"type":"skipped_end_line","bar":bar_idx,"time":candles[bar_idx]["time"],"reason":"short_entry_above_buying_swing_end","ref_swing_end":round(ref_swing_end_px,2),"entry_price":round(est_entry,2)})
                return False
        # 1min direct at pivot level
        entry = float(ref_level)
        entry_ts = int(candles[bar_idx]["ts"])
        entry_time = candles[bar_idx]["time"] + ":00"
        entry_low = float(candles[bar_idx]["low"])
        entry_high = float(candles[bar_idx]["high"])
        # SL prev_pivot
        sl_mode = cfg["sl_mode"]
        pivot_ref = None
        if sl_mode == "prev_pivot":
            pool = normal_lows if dirn==1 else normal_highs
            # only pivots strictly before entry bar
            eligible = [p for p in pool if p.idx < bar_idx]
            if eligible:
                pivot_ref = eligible[-1]
                sl = pivot_ref.px
            else:
                sl = entry_low if dirn==1 else entry_high
        else:
            if sl_mode in SL_MODE_FIXED:
                ref_dist = float(SL_MODE_FIXED[sl_mode])
            else:
                ref_dist = base_avg * SL_MODE_MULT.get(sl_mode,1.0)
            if dirn==1:
                sl = min(ref_level, candles[bar_idx]["low"]) - ref_dist
            else:
                sl = max(ref_level, candles[bar_idx]["high"]) + ref_dist
        risk = entry - sl if dirn==1 else sl - entry
        if risk <=0:
            return False
        target = entry + RR_TARGET * risk if dirn==1 else entry - RR_TARGET * risk
        direction = "long" if dirn==1 else "short"
        open_trade = {
            "dir":direction,"case":result.get("case"),"entry_time":entry_time,"entry_ts":entry_ts,
            "entry_price":round(entry,2),"sl":round(sl,2),"target":round(target,2),
            "level":round(ref_level,2),"pace_break_type":btype,"domination_time":entry_time,
            "mfe_r":0.0,"entry_bar":bar_idx,"validate_until":bar_idx+2,
            "dom_low":entry_low,"dom_high":entry_high,"validated":False,
            "sl_mode_used":sl_mode,"pivot_ref":{"px":pivot_ref.px,"time":pivot_ref.time,"kind":pivot_ref.kind,"idx":pivot_ref.idx} if pivot_ref else None,
            "_cur_sl":sl,"_init_sl":sl,"_max_profit":0.0,
        }
        entries_done+=1
        result["events"].append({"type":"entry","bar":bar_idx,"time":entry_time,"dir":direction,"price":round(entry,2),"sl":round(sl,2),"target":round(target,2)})
        return True

    while i < len(candles):
        cur = candles[i]
        # Walker
        dt_str = f"{result['date']}T{cur['time']}:00"
        fc = FlowCandle(date=dt_str, open=cur["open"], high=cur["high"], low=cur["low"], close=cur["close"])
        for p in walker.process_bar(fc, i):
            if p.kind=="H":
                normal_highs.append(p)
            else:
                normal_lows.append(p)

        # Manage open trade - per 1min bar
        if open_trade is not None:
            t = open_trade
            if cur["time"] >= EOD_EXIT:
                _close_trade(t, i, float(cur["open"]), "eod")
            else:
                green = float(cur["close"]) > float(cur["open"])
                hi, lo = float(cur["high"]), float(cur["low"])
                entry = float(t["entry_price"])
                cur_sl = float(t["_cur_sl"])
                exited=False
                if t["dir"]=="long":
                    if lo <= cur_sl:
                        _close_trade(t, i, cur_sl, "sl")
                        exited=True
                    elif hi >= float(t["target"]):
                        _close_trade(t, i, float(t["target"]), "target")
                        exited=True
                else:
                    if hi >= cur_sl:
                        _close_trade(t, i, cur_sl, "sl")
                        exited=True
                    elif lo <= float(t["target"]):
                        _close_trade(t, i, float(t["target"]), "target")
                        exited=True
                if not exited and not t["validated"] and i > t["validate_until"]:
                    t["validated"]=True
                if not exited:
                    risk = abs(entry - cur_sl) or 1e-9
                    if t["dir"]=="long":
                        t["mfe_r"] = max(t.get("mfe_r",0.0), (hi - entry)/risk)
                        if t.get("mfe_r",0.0) >= COST_TO_COST_R and lo <= entry:
                            _close_trade(t, i, entry, "cost-to-cost")
                    else:
                        t["mfe_r"] = max(t.get("mfe_r",0.0), (entry - lo)/risk)
                        if t.get("mfe_r",0.0) >= COST_TO_COST_R and hi >= entry:
                            _close_trade(t, i, entry, "cost-to-cost")
            if cur["time"] >= EOD_EXIT and open_trade is not None:
                _close_trade(open_trade, i, float(cur["close"]), "eod")

        # Check first swing breach - if low/high ever breached, no further entries
        # For conservative, check against the relevant swing's extreme (FS2), for aggressive FS1
        if ref_swing_end_px is not None and i > ref_swing_end_idx:
            if ref_swing_end_dir == "selling" and cur["low"] < ref_swing_end_px:
                if not first_swing_breached:
                    first_swing_breached = True
                    result["events"].append({"type":"first_swing_breached","bar":i,"time":cur["time"],"level":round(ref_swing_end_px,2),"price":cur["low"],"reason":"low_below_first_swing_low"})
            elif ref_swing_end_dir == "buying" and cur["high"] > ref_swing_end_px:
                if not first_swing_breached:
                    first_swing_breached = True
                    result["events"].append({"type":"first_swing_breached","bar":i,"time":cur["time"],"level":round(ref_swing_end_px,2),"price":cur["high"],"reason":"high_above_first_swing_high"})

        # Gate
        fs_gate_ok = entry_swing_confirmed_idx <0 or i > entry_swing_confirmed_idx
        entry_start = ENTRY_START
        if fs1_end_time and fs1_end_time < ENTRY_START:
            entry_start = fs1_end_time
        has_target = any(t.get("outcome") == "target" for t in result["trades"])
        # Block entries if first swing breached or already hit target (one target per day)
        can_enter = (open_trade is None and entries_done < MAX_ENTRIES and fs_gate_ok and cur["time"] < EOD_EXIT and cur["time"] >= entry_start and not first_swing_breached and not has_target)

        # Track broken pivots even when can_enter is false (so 09:39 break marks 24219.45 as already broken, so 09:40 won't re-enter)
        if i>0 and cur_swing is not None:
            # Check most recent pivot break regardless of gate, just to mark as broken
            chk_dir = -1 if cur_swing=="buying" else 1
            chk_brk = None
            if chk_dir==1 and normal_highs:
                piv = next((p for p in reversed(normal_highs) if p.idx < i), None)
                if piv and cur["high"] > piv.px:
                    chk_brk = piv.px
            elif chk_dir==-1 and normal_lows:
                piv = next((p for p in reversed(normal_lows) if p.idx < i), None)
                if piv and cur["low"] < piv.px:
                    chk_brk = piv.px
            if chk_brk is not None and chk_brk not in broken_pivot_levels:
                # Only mark as broken if it was a break, but don't count as trade if gate closed
                # We still add to broken set so next bar won't re-enter on same level
                # But only if it's the same level that would have been a trade
                # Add to broken if gate was closed (so next bar with same level will be skipped)
                if not can_enter:
                    broken_pivot_levels.add(chk_brk)
                    result["events"].append({"type":"skipped_already_broken_gate_closed","bar":i,"time":cur["time"],"level":round(chk_brk,2),"reason":"pivot_broken_while_gate_closed"})

        # Entry trigger - pivot_break
        if i>0 and cur_swing is not None and can_enter:
            trade_dir = -1 if cur_swing=="buying" else 1
            brk=None
            if trade_mode == "conservative" and fs2_dir is not None and fs2_end_idx >=0:
                # For conservative, ONLY use FS2's extreme (no fallback to recent Walker pivot)
                # This ensures we trade the second swing's pivot break, not a random recent pivot
                fs2_low = None
                fs2_high = None
                for ev in result["events"]:
                    if ev.get("type") == "fs2_segment":
                        if fs2_dir == "buying":
                            fs2_low = ev.get("start_px")
                            fs2_high = ev.get("end_px")
                        else:
                            fs2_high = ev.get("start_px")
                            fs2_low = ev.get("end_px")
                        break
                if trade_dir==1 and fs2_high is not None and cur["high"] > fs2_high:
                    brk = {"type":"pivot_break","level":fs2_high,"bar":i}
                elif trade_dir==-1 and fs2_low is not None and cur["low"] < fs2_low:
                    brk = {"type":"pivot_break","level":fs2_low,"bar":i}
                # Fallback to most recent Walker pivot if FS2 extreme not broken (e.g., 19 Aug 10:09 breaks recent low 24093.85, not FS2 low 24067.1)
                if brk is None:
                    if trade_dir==1 and normal_highs:
                        piv = next((p for p in reversed(normal_highs) if p.idx < i), None)
                        if piv and cur["high"] > piv.px:
                            brk = {"type":"pivot_break","level":piv.px,"bar":i}
                    elif trade_dir==-1 and normal_lows:
                        piv = next((p for p in reversed(normal_lows) if p.idx < i), None)
                        if piv and cur["low"] < piv.px:
                            brk = {"type":"pivot_break","level":piv.px,"bar":i}
            else:
                if trade_dir==1 and normal_highs:
                    piv = next((p for p in reversed(normal_highs) if p.idx < i), None)
                    if piv and cur["high"] > piv.px:
                        brk = {"type":"pivot_break","level":piv.px,"bar":i}
                elif trade_dir==-1 and normal_lows:
                    piv = next((p for p in reversed(normal_lows) if p.idx < i), None)
                    if piv and cur["low"] < piv.px:
                        brk = {"type":"pivot_break","level":piv.px,"bar":i}
            if brk is not None:
                # Don't re-enter on same pivot level already broken
                if brk["level"] in broken_pivot_levels:
                    result["events"].append({"type":"skipped_already_broken","bar":i,"time":cur["time"],"level":round(brk["level"],2),"reason":"pivot_already_broken_on_prev_candle"})
                    brk = None
                else:
                    broken_pivot_levels.add(brk["level"])
                    aligned = trade_dir == want_dir
                    pivot_break_count+=1
                    result["events"].append({"type":"pace_break","bar":i,"time":cur["time"],"break_type":brk["type"],"level":round(brk["level"],2),"swing_before":cur_swing,"aligned_with_bias":aligned,"pivot_break_count":pivot_break_count})
                    required = 2 if trade_mode == "conservative" else 1
                    if pivot_break_count >= required:
                        new_swing = "selling" if cur_swing=="buying" else "buying"
                        cur_swing = new_swing
                        if aligned:
                            if _open_trade(i, trade_dir, brk["level"], cur, brk["type"]):
                                pivot_break_count=0
                                result["events"].append({"type":"day_level_set","bar":i,"time":cur["time"],"ts":int(cur["ts"]),"level":round(brk["level"],2),"break_type":brk["type"]})

        i+=1

    if open_trade is not None:
        last = candles[-1]
        _close_trade(open_trade, len(candles)-1, float(last["close"]), "eod")
    return result


def run_backtest_1min(df_1min: pd.DataFrame, bias_labels: list[dict], cfg: dict | None = None) -> dict:
    """Run 1min engine across every labelled day."""
    cfg = resolve_cfg(cfg)
    df = df_1min.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    if "ts" in df.columns and not df["ts"].isna().all():
        df["ts"] = df["ts"].astype("int64")
    else:
        df["ts"] = (df["timestamp"].astype("int64") // 1_000_000_000).astype("int64")
    df = df.sort_values("timestamp").drop_duplicates(subset="ts", keep="last")
    dates = df["timestamp"].dt.strftime("%Y-%m-%d")
    groups = {d: g for d, g in df.groupby(dates, sort=True)}
    # Need daily for gap - use 5min open vs prev close? For 1min, gap still from daily prev close vs 1min open
    # For now reuse same gap logic as 5min: need prev close from daily or 5min
    # We'll compute gap from 1min open vs prev day's 1min close
    ordered = sorted(groups)
    prev_close_by_date: dict[str,float] = {}
    for idx in range(1, len(ordered)):
        prev_g = groups[ordered[idx-1]]
        prev_close_by_date[ordered[idx]] = float(prev_g["close"].iloc[-1])
    # Need bias map
    bias_map = {l["date"]: l["bias"] for l in bias_labels}
    zone_map = {l["date"]: (l.get("overview") or {}).get("zone") for l in bias_labels}
    def _extreme_of(z): return "highs" if z in ("new_high","highs_extreme") else "lows" if z in ("new_low","lows_extreme") else None
    # Simplified avg: use 1min ranges
    def _q_ranges(g):
        rows=g.reset_index(drop=True)
        return [float(r["high"])-float(r["low"]) for _,r in rows.iloc[1:].iterrows() if r["timestamp"].strftime("%H:%M") < EOD_EXIT]
    day_ranges = {d: _q_ranges(groups[d]) for d in ordered}
    avg_by_date={}
    for idx,d in enumerate(ordered):
        flat=[]
        for j in range(max(0,idx-10), idx):
            flat.extend(day_ranges[ordered[j]])
        avg_by_date[d]= sum(flat)/len(flat) if flat else None
    import pandas as _pd
    traded_dates = set(groups) & set(bias_map)
    days=[]
    for d in sorted(traded_dates):
        g = groups[d]
        gap_val = float(g["open"].iloc[0])
        gap = "flat"
        pc = prev_close_by_date.get(d)
        if pc:
            frac=abs(gap_val-pc)/pc
            gap = "flat" if frac<=cfg["gap_pct"] else "gap-up" if gap_val>pc else "gap-down"
        ctx={"gap":gap,"extreme":_extreme_of(zone_map.get(d)),"avg_range":avg_by_date.get(d)}
        days.append(simulate_day_1min(g, bias_map[d], cfg=cfg, ctx=ctx))
    all_trades=[t for dy in days for t in dy["trades"]]
    wins=[t for t in all_trades if t["r_multiple"]>0]
    from collections import Counter
    outcomes=Counter(t["outcome"] for t in all_trades)
    stats={"days_total":len(days),"days_traded":sum(1 for dy in days if dy["trades"]),"trades":len(all_trades),"wins":len(wins),"win_rate":round(len(wins)/len(all_trades)*100,1) if all_trades else 0.0,"total_r":round(sum(t["r_multiple"] for t in all_trades),2),"avg_r":round(sum(t["r_multiple"] for t in all_trades)/len(all_trades),2) if all_trades else 0.0,"outcomes":dict(outcomes),"longs":sum(1 for t in all_trades if t["dir"]=="long"),"shorts":sum(1 for t in all_trades if t["dir"]=="short")}
    case_agg={}
    for dy in days:
        c=dy.get("case")
        if c:
            slot=case_agg.setdefault(c,{"trades":0,"wins":0,"total_r":0.0})
            for t in dy["trades"]:
                slot["trades"]+=1
                slot["wins"]+=1 if t["r_multiple"]>0 else 0
                slot["total_r"]+=t["r_multiple"]
    for v in case_agg.values():
        v["total_r"]=round(v["total_r"],2)
    stats["cases"]=dict(sorted(case_agg.items()))
    return {"stats":stats,"days":days,"config":cfg}
