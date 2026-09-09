"""v8_ghost_htf_bias — HTF Ghost mean-reversion streak bias + LTF B2/FLIP same dir.
HTF 1h: 3 same-color -> subscribe, 4th same-color CLOSE -> activate mean-reversion window opposite dir, window = 4th close + 4h (240m), State1 continuation shifts window end, State4 failure ignored for now.
LTF 15m: decisive B2/FLIP inside HTF ghost window and dir == ghost_dir, same v5 SL 0.25ATR ext-stop1.5 MB50.
Costs 0.05%+2pt, 1m fine, stream, one-swing-one-trade.
Separate engine, never disturb v5 (v1_15m).
Ref: BTC_GhostStreak/files/doc official.md:57 4 same-color -> reversal, Phase1 3rd, Phase2 4th, Window +15m(5m)/+45m(15m) scaled to +240m for 1h, State1 shift doc:167, HTF Open pause doc:356.
"""
from __future__ import annotations
import bisect
from typing import Optional

def _ghost_intervals_1h(candles_1h: list[dict], window_hours: int = 4) -> list[tuple[int,int,int,float,float]]:
    """Generate ghost mean-reversion windows on 1h.
    Color: close > open = GREEN (up) = 1, close < open = RED (down) = -1, doji skip (0).
    Streak: consecutive same-color closes.
    Subscribe at 3rd, Activate at 4th close -> window (entry_ts, exit_ts, dir) where dir is opposite streak (RED streak -> LONG +1, GREEN -> SHORT -1).
    Window exit = activation close ts + window_hours*3600, shifted if streak continues (State1).
    Returns list of (entry_ts, exit_ts, dir, protection_px) where protection is frozen high/low at activation.
    """
    intervals=[]
    n=len(candles_1h)
    if n<4:
        return intervals
    # precompute color
    colors=[]
    for c in candles_1h:
        o=float(c["open"]); cl=float(c["close"])
        if cl>o: colors.append(1)
        elif cl<o: colors.append(-1)
        else: colors.append(0)
    # iterate, track streak
    active=None  # (s_ts, e_ts, dir, protection, streak_color)
    for i in range(n):
        col=colors[i]
        if col==0:
            continue
        # count streak ending at i
        streak=1
        for j in range(i-1, -1, -1):
            if colors[j]==col:
                streak+=1
            else:
                break
        ts=int(candles_1h[i]["ts"])
        # State1: if we have active window and this is continuation same-color beyond activation, shift window
        if active is not None:
            # active streak_color is opposite of dir? For RED streak (-1) -> LONG (1), streak_color = -1
            # continuation means same streak color as active's original streak
            active_streak_col = -active[2]  # dir is opposite, so streak col = -dir
            if col == active_streak_col and streak >=4:
                # shift window end to this close + window_hours*3600
                # keep s_ts same, update e_ts
                new_e = ts + window_hours*3600
                # only extend, not shrink
                if new_e > active[1]:
                    active = (active[0], new_e, active[2], active[3])
                    # update last interval in list
                    if intervals:
                        intervals[-1]=(active[0], new_e, active[2], active[3])
                continue
        # Activation: 4th same-color close
        if streak>=4:
            # check if this is the 4th (previous streak at i-1 was 3)
            # we want to activate only at the 4th, not every 5th+ beyond (but we already handle shift above)
            # So if streak ==4, new window
            if streak==4:
                # direction opposite streak
                ghost_dir = -col
                # protection: for LONG (RED streak) protection = low of activation? For ghost, protection is high for SHORT etc.
                # Use activation candle's high/low as frozen protection
                hi=float(candles_1h[i]["high"]); lo=float(candles_1h[i]["low"])
                protection = hi if ghost_dir==-1 else lo
                s_ts = ts  # window starts at activation close (exclusive for LTF bar_ts > s_ts)
                e_ts = ts + window_hours*3600
                active=(s_ts, e_ts, ghost_dir, protection)
                intervals.append((s_ts, e_ts, ghost_dir, protection))
            # else 5th+ already handled as shift, no new interval
        # For opposite color (reversal), freeze protection (do not shift) — nothing to do, keep active as is
        # If active window expired (ts > active[1]), clear active
        if active is not None and ts > active[1]:
            active=None
    # Now intervals may have overlapping due to shift? Merge overlapping same dir?
    # Keep as is, but ensure sorted and non-overlapping by merging
    if not intervals:
        return []
    intervals.sort(key=lambda x: x[0])
    merged=[]
    for s,e,d,p in intervals:
        if not merged:
            merged.append([s,e,d,p])
        else:
            ps,pe,pd,pp = merged[-1]
            # if overlapping and same dir, merge to max e
            if s <= pe and d==pd:
                merged[-1][1]=max(pe,e)
            elif s <= pe and d!=pd:
                # opposite dir overlapping (rare due to reversal), keep both but truncate earlier? keep as is
                merged.append([s,e,d,p])
            else:
                merged.append([s,e,d,p])
    # return as (s_ts, e_ts, dir, protection)
    return [(s,e,d,p) for s,e,d,p in merged]

def simulate_htf_ltf_ghost(
    candles_htf: list[dict],
    swings_htf: list[dict],  # unused, kept for API compat
    candles_ltf: list[dict],
    swings_ltf: list[dict],
    fine_ltf: Optional[list[dict]] = None,
    *,
    sl_buf_atr: float = 0.25,
    ext_stop_r: float = 1.5,
    window_hours: int = 4,
    htf_color_len: int = 4,
    ltf_entry_break: str = "decisive",
) -> dict:
    """Ghost HTF + LTF B2/FLIP. API compatible with v1_15m but HTF is ghost streak, not Flip."""
    from src.btc.btc_engine import _collect_signals, _trail_events, trade_stats
    import bisect as bs

    # Ghost intervals on HTF (1h)
    ghost_intervals = _ghost_intervals_1h(candles_htf, window_hours=window_hours)
    # ghost_intervals: (s_ts, e_ts, dir, protection)
    starts=[s for s,_,_,_ in ghost_intervals]
    # For ext_stop we need hentry/hsl analogy: for ghost, hentry/hsl not defined like Flip. Use ghost protection as proxy for risk?
    # For LTF ext-stop gate, we need hrisk. We can approximate hrisk as atr-based or use ghost protection distance.
    # Simplify: for ghost, hrisk = abs(ghost protection - ghost activation close) ??? Use activation candle range.
    # Instead, disable ext_stop for ghost for now (set hrisk 0 -> skip gate). But we keep ext_stop_r handling with ghost protection.
    # We'll map ghost_intervals to include hentry/hsl: hentry = activation close, hsl = protection
    # Need activation close price: find candle at s_ts
    ht_ts_to_candle={int(c["ts"]): c for c in candles_htf}
    ghost_with_entry=[]
    for s,e,d,p in ghost_intervals:
        c=ht_ts_to_candle.get(s)
        if c:
            hentry=float(c["close"])
            hsl=p
        else:
            # fallback: find nearest
            hentry=p
            hsl=p
        ghost_with_entry.append((s,e,d,p,hentry,hsl))
    # For bisect, starts already
    # LTF signals
    ltf_sigs = _collect_signals(swings_ltf, ltf_entry_break, skip_first=True, selection="stream", candles=candles_ltf)
    filtered=[]
    for sig in ltf_sigs:
        bar_ts=int(candles_ltf[sig["bar"]]["ts"])
        idx=bs.bisect_right(starts, bar_ts)-1
        if idx<0: continue
        s,e,d,p,hentry,hsl = ghost_with_entry[idx]
        if not (s < bar_ts <= e):
            continue
        if sig["dir"] != d:
            continue
        if ext_stop_r>0:
            hrisk=abs(hentry - hsl)
            if hrisk>0:
                ext=(float(candles_ltf[sig["bar"]]["close"]) - hentry)*d/hrisk
                if ext > ext_stop_r:
                    continue
        filtered.append(sig)

    # Now LTF simulation identical to v1_15m LTF walk with sl_buf_atr 0.25
    n=len(candles_ltf)
    if n==0:
        return {"htf_trades": [], "ltf_trades": [], "intervals": ghost_intervals, "ghost_intervals": ghost_intervals}
    candle_ts=[int(c["ts"]) for c in candles_ltf]
    atr15=None
    if sl_buf_atr>0:
        tr_l=[0.0]*n
        for _i in range(n):
            _c=candles_ltf[_i]
            if _i==0:
                tr_l[_i]=float(_c["high"])-float(_c["low"])
            else:
                _pc=float(candles_ltf[_i-1]["close"])
                tr_l[_i]=max(float(_c["high"])-float(_c["low"]), abs(float(_c["high"])-_pc), abs(float(_c["low"])-_pc))
        atr15=[0.0]*n
        for _i in range(n):
            _lo=max(0,_i-13)
            atr15[_i]=sum(tr_l[_lo:_i+1])/(_i-_lo+1)
    fine_ts=[int(c["ts"]) for c in fine_ltf] if fine_ltf else []
    ltf_trades=[]
    busy_until=-1
    from src.btc.btc_engine import _trail_events as _te
    import bisect
    for sig in filtered:
        i=sig["bar"]
        if i <= busy_until or i >= n-1:
            continue
        direction=int(sig["dir"])
        entry=float(candles_ltf[i]["close"])
        sl_pivot=sig["swing_start_px"]
        if direction==1:
            sl=sl_pivot - sl_buf_atr*atr15[i] if sl_buf_atr>0 and atr15 else sl_pivot
            if sl >=entry: continue
            risk=entry-sl
            if risk<0.0005*entry: continue
            target=entry+3.0*risk
        else:
            sl=sl_pivot + sl_buf_atr*atr15[i] if sl_buf_atr>0 and atr15 else sl_pivot
            if sl <=entry: continue
            risk=sl-entry
            if risk<0.0005*entry: continue
            target=entry-3.0*risk
        sl0=sl
        sl_cur=sl
        best=entry
        events=_te(swings_ltf, direction) if True else []
        ev_idx=-1
        exit_idx=None
        exit_px=None
        outcome="open"
        exit_ts=None
        exit_date=None
        for j in range(i+1, n if not fine_ltf else i+1):
            c=candles_ltf[j]
            hi=float(c["high"]); lo=float(c["low"])
            if direction==1:
                if hi>best: best=hi
            else:
                if lo<best: best=lo
            if direction==1:
                if lo <= sl_cur:
                    fill=min(sl_cur, float(c["open"]))
                    exit_idx,exit_px=j,fill
                    outcome="sl" if sl_cur <= sl0 else "trail"
                    break
                if hi >= target:
                    # For v5, trailing off not, but we keep target check as off? v5 uses swing trail, not fixed target. Actually v5 uses swing trail, not target. So ignore target for ghost? Keep as swing trail only.
                    pass
                # swing trail
                while ev_idx+1 < len(events) and events[ev_idx+1][0] <= j:
                    ev_idx+=1
                    if events[ev_idx][0] < i: continue
                    cand=events[ev_idx][1]
                    if sl_cur < cand < lo:
                        sl_cur=cand
            else:
                if hi >= sl_cur:
                    fill=max(sl_cur, float(c["open"]))
                    exit_idx,exit_px=j,fill
                    outcome="sl" if sl_cur >= sl0 else "trail"
                    break
                while ev_idx+1 < len(events) and events[ev_idx+1][0] <= j:
                    ev_idx+=1
                    if events[ev_idx][0] < i: continue
                    cand=events[ev_idx][1]
                    if hi < cand < sl_cur:
                        sl_cur=cand
        if fine_ltf:
            bar_ts=int(candles_ltf[i]["ts"])
            events_ts=[(candle_ts[min(e+1,n-1)], px) for e,px in events if candle_ts[min(e+1,n-1)] > bar_ts]
            f_start=bisect.bisect_left(fine_ts, candle_ts[i+1])
            best_f=entry
            sl_cur_f=sl_cur
            ev_idx_f=-1
            fk=None
            exit_px_f=None
            outcome_f="open"
            for k in range(f_start, len(fine_ltf)):
                c=fine_ltf[k]
                hi=float(c["high"]); lo=float(c["low"]); ts=int(c["ts"])
                if direction==1:
                    if hi>best_f: best_f=hi
                else:
                    if lo<best_f: best_f=lo
                if direction==1:
                    if lo <= sl_cur_f:
                        fill=min(sl_cur_f, float(c["open"]))
                        fk,exit_px_f,outcome_f=k,fill,("sl" if sl_cur_f <= sl0 else "trail")
                        break
                    while ev_idx_f+1 < len(events_ts) and events_ts[ev_idx_f+1][0] <= ts:
                        ev_idx_f+=1
                        cand=events_ts[ev_idx_f][1]
                        if sl_cur_f < cand < lo:
                            sl_cur_f=cand
                else:
                    if hi >= sl_cur_f:
                        fill=max(sl_cur_f, float(c["open"]))
                        fk,exit_px_f,outcome_f=k,fill,("sl" if sl_cur_f >= sl0 else "trail")
                        break
                    while ev_idx_f+1 < len(events_ts) and events_ts[ev_idx_f+1][0] <= ts:
                        ev_idx_f+=1
                        cand=events_ts[ev_idx_f][1]
                        if hi < cand < sl_cur_f:
                            sl_cur_f=cand
            if fk is None:
                outcome="open"
                exit_idx=n-1
                exit_px=float(fine_ltf[-1]["close"])
                exit_ts=int(fine_ltf[-1]["ts"])
                exit_date=fine_ltf[-1].get("date") or candles_ltf[-1]["date"]
            else:
                outcome=outcome_f
                exit_px=exit_px_f
                exit_ts=int(fine_ltf[fk]["ts"])
                exit_date=fine_ltf[fk].get("date")
                exit_idx=bisect.bisect_right(candle_ts, exit_ts)-1
                exit_idx=max(0, min(exit_idx, n-1))
                if not exit_date:
                    exit_date=candles_ltf[exit_idx]["date"]
        elif exit_idx is None:
            exit_idx=n-1
            exit_px=float(candles_ltf[-1]["close"])
            outcome="open"
        if not fine_ltf:
            exit_ts=int(candles_ltf[exit_idx]["ts"])
            exit_date=candles_ltf[exit_idx]["date"]
        move=(exit_px-entry) if direction==1 else (entry-exit_px)
        r_multiple=move/risk if risk>0 else 0
        ltf_trades.append({
            "trade_no": len(ltf_trades)+1,
            "dir": "long" if direction==1 else "short",
            "swing_no": sig["swing_no"],
            "break_kind": sig["kind"],
            "entry_idx": i,
            "entry_ts": int(candles_ltf[i]["ts"]),
            "entry_date": candles_ltf[i]["date"],
            "entry_price": round(entry,2),
            "sl": round(sl0,2),
            "target": round(target,2) if 'target' in locals() else 0,
            "exit_idx": exit_idx,
            "exit_ts": int(exit_ts),
            "exit_date": exit_date,
            "exit_price": round(float(exit_px),2),
            "outcome": outcome,
            "r_multiple": round(float(r_multiple),3),
            "bars_held": exit_idx - i,
        })
        busy_until=exit_idx
    # HTF trades not used for ghost, return empty but keep intervals for stats
    return {"htf_trades": [], "ltf_trades": ltf_trades, "intervals": ghost_intervals, "ghost_intervals": ghost_intervals}
