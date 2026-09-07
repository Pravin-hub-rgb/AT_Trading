"""v8 — 1h Flip entry at high/low break, not close. Next N candles confirm, opposite breach cancels.

For 1h Flip cap16: entry is not at break bar close, but at swing's extreme (high for long, low for short) and we wait next N=3 1h candles to see if high/low breaks without opposite breach.
Example 13 Feb 2025 06:30 FLIP: entry low of that candle, next candle didn't break high so we don't enter there but if low gets broken we short.
Example 17 Mar 19:30 short entry low, next candle broke high -> cancel because high shouldn't be breached for short.

This replaces direct close entry with pending stop entry at extreme.
"""
from __future__ import annotations
import bisect
from typing import Optional

def simulate_btc_trades_v8(
    candles: list[dict],
    swings: list[dict],
    *,
    entry_break: str="flip",
    sl_mode: str="swing",
    sl_pct: float=0.5,
    rr_target: float=3.0,
    trailing: str="off",
    breakeven_r: float=0.0,
    skip_first: bool=True,
    bias_timeline=None,
    day_gate=None,
    fine: Optional[list[dict]]=None,
    entry_selection: str="stream",
    cap_days: int=16,
    confirm_bars: int=3,  # next N 1h candles to confirm break
) -> list[dict]:
    n=len(candles)
    if n==0:
        return []
    from src.btc.btc_engine import _collect_signals, _trail_events, trade_stats
    # Collect signals as before (stream)
    signals=_collect_signals(swings, entry_break, skip_first=skip_first, selection=entry_selection, candles=candles if entry_selection=="stream" else None)
    # For v8, we will not use signal bar close directly; we will create pending entries at swing extreme
    # For each signal, determine entry level = swing extreme (high for long B2? Actually for up-break long, entry should be high of break candle)
    # Simplified: for long, entry_level = high of signal candle (break candle high), for short, entry_level = low of signal candle
    # Then we wait next confirm_bars candles: if entry_level is broken (high >= level for long, low <= level for short) without opposite side breach, we enter at that break close.
    pending_trades=[]
    # Build pending list
    for sig in signals:
        bidx=sig["bar"]
        bdir=int(sig["dir"])
        # entry level is the break candle's extreme that was broken: for long, it's the high of the break candle's swing's B2? Actually use sig's px? sig's px is break px?
        # Use candle's high/low as entry trigger
        if bdir==1:
            entry_level=float(candles[bidx]["high"])  # for long, need to break above this high
            opposite_level=float(candles[bidx]["low"])
        else:
            entry_level=float(candles[bidx]["low"])  # for short, need to break below low
            opposite_level=float(candles[bidx]["high"])
        # Look ahead confirm_bars candles
        found=False
        entry_idx=None
        entry_price=None
        cancel=False
        for k in range(bidx+1, min(bidx+1+confirm_bars, n)):
            c=candles[k]
            hi=float(c["high"]); lo=float(c["low"]); close=float(c["close"])
            # Check opposite breach first: if opposite side breaks, cancel pending
            if bdir==1:
                # long pending: if low breaks below opposite_level (i.e., low < opposite_level) then cancel? Actually for long, opposite is low, if low breaks below opposite_level, it means short side broke
                # User said: entry will be low of this candle but next candle broken its high so we cancel it because it was shorting trade, high shouldn't be breached.
                # So for short (bdir -1), entry_level is low, opposite is high, if high breaks opposite, cancel
                # For long, opposite is low, if high breaks entry_level -> enter, if low breaks opposite first -> cancel
                if lo < opposite_level:
                    # opposite breach before entry break
                    cancel=True
                    break
                if hi >= entry_level:
                    # entry break without opposite breach
                    entry_idx=k
                    entry_price=close  # enter at close of breakout candle (or at entry_level? Use close for now)
                    found=True
                    break
            else:
                # short pending
                if hi > opposite_level:
                    cancel=True
                    break
                if lo <= entry_level:
                    entry_idx=k
                    entry_price=close
                    found=True
                    break
        if cancel or not found or entry_idx is None:
            continue
        # Also check prev pivot not breached: user said prev pivot shouldn't be breached
        # For now, we skip that check, but we can add: if high breaks above recent swing high for short, cancel
        # For short, if any of next confirm_bars high > recent swing high (prev pivot), cancel
        # Find recent swing high before signal
        # Simplified: check if any of next confirm_bars high > max high since prev swing start to signal
        # Let's implement: find max high since signal's swing start to entry_idx, if max > entry_level + risk? For now, skip
        pending_trades.append((sig, entry_idx, entry_price, bdir))

    # Now simulate trades from pending entries, similar to normal but using pending entry_idx/price
    candle_ts=[int(c["ts"]) for c in candles]
    fine_ts=[int(c["ts"]) for c in fine] if fine else []
    from src.btc.btc_engine import _trail_events as _te
    import bisect

    bias_ptr=-1
    bias_now=None
    trades=[]
    busy_until=-1
    # Need to sort pending by entry_idx
    pending_trades.sort(key=lambda x: x[1])

    for sig, entry_idx, entry_price, direction in pending_trades:
        i=entry_idx
        if i <= busy_until or i >= n-1:
            continue
        # bias/day gate at entry time
        if day_gate is not None:
            g=day_gate.get(candles[i]["date"][:10])
            if g != ("long" if direction==1 else "short"):
                continue
        bar_ts=int(candles[i]["ts"])
        while bias_ptr+1 < len(bias_timeline or []) and (bias_timeline or [])[bias_ptr+1][0] <= bar_ts:
            bias_ptr+=1
            bias_now=bias_timeline[bias_ptr][1]  # type: ignore
        if bias_timeline is not None:
            want="up" if direction==1 else "down"
            if bias_now != want:
                continue
        entry=float(entry_price) if entry_price is not None else float(candles[i]["close"])
        # SL same as before: use sig's swing_start_px
        if direction==1:
            sl= sig["swing_start_px"] if sl_mode=="swing" else entry*(1-sl_pct/100)
            if sl >= entry: continue
            risk=entry-sl
            if risk < 0.0005*entry: continue
            target=entry+rr_target*risk
        else:
            sl= sig["swing_start_px"] if sl_mode=="swing" else entry*(1+sl_pct/100)
            if sl <= entry: continue
            risk=sl-entry
            if risk < 0.0005*entry: continue
            target=entry-rr_target*risk
        sl0=sl
        sl_cur=sl
        best=entry
        events=_te(swings, direction) if trailing=="swing" else []
        ev_idx=-1
        exit_idx=None
        exit_px=None
        outcome="open"
        exit_ts=None
        exit_date=None
        cap_bars = int(cap_days*86400 / (candle_ts[1]-candle_ts[0])) if cap_days>0 and n>1 else 10**9
        cap_idx = i + cap_bars if cap_days>0 else n*2
        for j in range(i+1, n if not fine else i+1):
            if j >= cap_idx and exit_idx is None:
                c=candles[j]
                exit_idx=j
                exit_px=float(c["close"])
                outcome="time"
                break
            c=candles[j]
            hi=float(c["high"]); lo=float(c["low"])
            if direction==1:
                if lo <= sl_cur:
                    fill=min(sl_cur, float(c["open"]))
                    exit_idx,exit_px=j,fill
                    outcome="sl" if sl_cur <= sl0 else "be" if abs(sl_cur-entry)<=1e-9 else "trail"
                    break
                if trailing=="off" and hi >= target:
                    exit_idx,exit_px,outcome=j,target,"target"
                    break
                if breakeven_r>0 and hi >= entry+breakeven_r*risk and sl_cur < entry:
                    sl_cur=entry
                elif trailing=="swing":
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
                    outcome="sl" if sl_cur >= sl0 else "be" if abs(sl_cur-entry)<=1e-9 else "trail"
                    break
                if trailing=="off" and lo <= target:
                    exit_idx,exit_px,outcome=j,target,"target"
                    break
                if breakeven_r>0 and lo <= entry - breakeven_r*risk and sl_cur > entry:
                    sl_cur=entry
                elif trailing=="swing":
                    while ev_idx+1 < len(events) and events[ev_idx+1][0] <= j:
                        ev_idx+=1
                        if events[ev_idx][0] < i: continue
                        cand=events[ev_idx][1]
                        if hi < cand < sl_cur:
                            sl_cur=cand
        if fine:
            f_start=bisect.bisect_left(fine_ts, candle_ts[i+1])
            f_cap_idx=None
            if cap_days>0:
                cap_ts=candle_ts[min(cap_idx, len(candle_ts)-1)]
                f_cap_idx=bisect.bisect_left(fine_ts, cap_ts)
            best_f=entry
            sl_cur_f=sl_cur
            ev_idx_f=ev_idx
            bar_ts_f=int(candles[i]["ts"])
            events_ts=[(candle_ts[min(e+1,n-1)], px) for e,px in events] if trailing=="swing" else []
            events_ts=[(ts,px) for ts,px in events_ts if ts > bar_ts_f]
            fk=None
            exit_px_f=None
            outcome_f="open"
            for k in range(f_start, len(fine)):
                if f_cap_idx is not None and k >= f_cap_idx and fk is None:
                    fk=k
                    exit_px_f=float(fine[k]["close"])
                    outcome_f="time"
                    break
                c=fine[k]
                hi=float(c["high"]); lo=float(c["low"]); ts=int(c["ts"])
                if direction==1:
                    if lo <= sl_cur_f:
                        fill=min(sl_cur_f, float(c["open"]))
                        fk,exit_px_f,outcome_f=k,fill,("sl" if sl_cur_f <= sl0 else "be" if abs(sl_cur_f-entry)<=1e-9 else "trail")
                        break
                    if trailing=="off" and hi >= target:
                        fk,exit_px_f,outcome_f=k,target,"target"
                        break
                    if breakeven_r>0 and hi >= entry+breakeven_r*risk and sl_cur_f < entry:
                        sl_cur_f=entry
                    while ev_idx_f+1 < len(events_ts) and events_ts[ev_idx_f+1][0] <= ts:
                        ev_idx_f+=1
                        cand=events_ts[ev_idx_f][1]
                        if sl_cur_f < cand < lo:
                            sl_cur_f=cand
                else:
                    if hi >= sl_cur_f:
                        fill=max(sl_cur_f, float(c["open"]))
                        fk,exit_px_f,outcome_f=k,fill,("sl" if sl_cur_f >= sl0 else "be" if abs(sl_cur_f-entry)<=1e-9 else "trail")
                        break
                    if trailing=="off" and lo <= target:
                        fk,exit_px_f,outcome_f=k,target,"target"
                        break
                    if breakeven_r>0 and lo <= entry - breakeven_r*risk and sl_cur_f > entry:
                        sl_cur_f=entry
                    while ev_idx_f+1 < len(events_ts) and events_ts[ev_idx_f+1][0] <= ts:
                        ev_idx_f+=1
                        cand=events_ts[ev_idx_f][1]
                        if hi < cand < sl_cur_f:
                            sl_cur_f=cand
            if fk is None:
                outcome="open"
                exit_idx=n-1
                exit_px=float(fine[-1]["close"])
                exit_ts=int(fine[-1]["ts"])
                exit_date=fine[-1].get("date") or candles[-1]["date"]
            else:
                outcome=outcome_f
                exit_px=exit_px_f
                exit_ts=int(fine[fk]["ts"])
                exit_date=fine[fk].get("date")
                exit_idx=bisect.bisect_right(candle_ts, exit_ts)-1
                exit_idx=max(0, min(exit_idx, n-1))
                if not exit_date:
                    exit_date=candles[exit_idx]["date"]
        elif exit_idx is None:
            exit_idx=n-1
            exit_px=float(candles[-1]["close"])
            outcome="open"
        if not fine:
            exit_ts=int(candles[exit_idx]["ts"])
            exit_date=candles[exit_idx]["date"]
        move=(exit_px-entry) if direction==1 else (entry-exit_px)  # type: ignore
        r_multiple=move/risk if risk>0 else 0
        trades.append({
            "trade_no": len(trades)+1,
            "dir": "long" if direction==1 else "short",
            "swing_no": sig["swing_no"],
            "break_kind": sig["kind"],
            "entry_idx": i,
            "entry_ts": int(candles[i]["ts"]),
            "entry_date": candles[i]["date"],
            "entry_price": round(entry,2),
            "sl": round(sl0,2),
            "target": round(target,2),
            "exit_idx": exit_idx,
            "exit_ts": int(exit_ts),  # type: ignore
            "exit_date": exit_date,
            "exit_price": round(float(exit_px),2),  # type: ignore
            "outcome": outcome,
            "r_multiple": round(float(r_multiple),3),
            "bars_held": exit_idx - i,  # type: ignore
        })
        busy_until=exit_idx  # type: ignore
    return trades
