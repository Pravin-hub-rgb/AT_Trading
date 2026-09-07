"""v10 — Flip candle strength filter (body/ATR, wick, angle)."""
from __future__ import annotations
from typing import Optional

def _atr_at(candles: list[dict], idx: int, period: int=14) -> float:
    # simple ATR at idx
    if idx < period:
        return 0
    trs=[]
    for i in range(idx-period+1, idx+1):
        if i==0:
            trs.append(float(candles[i]["high"])-float(candles[i]["low"]))
        else:
            h=float(candles[i]["high"]); l=float(candles[i]["low"]); pc=float(candles[i-1]["close"])
            trs.append(max(h-l, abs(h-pc), abs(l-pc)))
    return sum(trs)/len(trs) if trs else 0

def simulate_btc_trades_v10(
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
    min_body_atr: float=0.5,  # body must be >=0.5 ATR
    max_wick_atr: float=1.0,  # wick must be <=1.0 ATR
    min_swing_angle: float=0.0,  # swing leg angle threshold (price change / bars)
) -> list[dict]:
    n=len(candles)
    if n==0:
        return []
    from src.btc.btc_engine import _collect_signals, _trail_events, trade_stats
    import bisect
    signals=_collect_signals(swings, entry_break, skip_first=skip_first, selection=entry_selection, candles=candles if entry_selection=="stream" else None)
    # Filter by flip candle strength
    filtered=[]
    for sig in signals:
        bidx=sig["bar"]
        c=candles[bidx]
        body=abs(float(c["close"])-float(c["open"]))
        wick_hi=float(c["high"])-max(float(c["open"]), float(c["close"]))
        wick_lo=min(float(c["open"]), float(c["close"]))-float(c["low"])
        wick=max(wick_hi, wick_lo)
        atr=_atr_at(candles, bidx, 14)
        if atr==0:
            continue
        if body < min_body_atr*atr:
            continue
        if wick > max_wick_atr*atr:
            continue
        # swing angle: for this signal's swing, leg = end_px - start_px, bars = end_idx - start_idx
        # Find swing for this signal
        s=None
        for sw in swings:
            if sw["swing_index"]==sig["swing_no"]:
                s=sw
                break
        if s is not None and min_swing_angle>0:
            leg=abs(float(s["seg"]["end_px"])-float(s["seg"]["start_px"]))
            bars=max(1, int(s["seg"]["end_idx"])-int(s["seg"]["start_idx"]))
            angle=leg/bars  # price per bar
            # need ATR normalized angle?
            atr_norm=atr if atr!=0 else 1
            angle_atr=angle/atr_norm
            if angle_atr < min_swing_angle:
                continue
        filtered.append(sig)
    signals=filtered
    candle_ts=[int(c["ts"]) for c in candles]
    fine_ts=[int(c["ts"]) for c in fine] if fine else []
    interval=candle_ts[1]-candle_ts[0] if n>1 else 3600
    cap_bars=int(cap_days*86400/interval) if cap_days>0 else 10**9
    bias_ptr=-1
    bias_now=None
    trades=[]
    busy_until=-1
    for sig in signals:
        i=sig["bar"]
        if i <= busy_until or i >= n-1:
            continue
        direction=int(sig["dir"])
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
        entry=float(candles[i]["close"])
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
        events=_trail_events(swings, direction) if trailing=="swing" else []
        ev_idx=-1
        exit_idx=None
        exit_px=None
        outcome="open"
        exit_ts=None
        exit_date=None
        cap_idx=i+cap_bars
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
            f_cap_idx=bisect.bisect_left(fine_ts, candle_ts[min(cap_idx, len(candle_ts)-1)]) if cap_days>0 else None
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
