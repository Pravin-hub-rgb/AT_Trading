"""v3 — HTF 1h pivot trail. 15m entries, 1h swing pivots ratchet."""
from __future__ import annotations
from typing import Optional
import bisect
from src.btc.btc_engine import _collect_signals, _outcome_counts, trade_stats

def _trail_events_htf(swings_htf: list[dict], direction: int) -> list[tuple[int,float]]:
    want="up" if direction==1 else "down"
    ev=[(int(s["confirmed_at_idx"]), float(s["seg"]["start_px"])) for s in swings_htf if s.get("dir")==want and int(s.get("confirmed_at_idx",-1))>=0]
    ev.sort(key=lambda x: x[0])
    return ev

def simulate_btc_trades_v3(
    candles: list[dict],
    swings: list[dict],
    swings_htf: list[dict] | None,
    candle_ts_htf: list[int] | None,
    *,
    entry_break: str="decisive",
    sl_mode: str="swing",
    sl_pct: float=0.5,
    rr_target: float=3.0,
    trailing: str="swing",
    breakeven_r: float=0.0,
    skip_first: bool=True,
    bias_timeline=None,
    day_gate=None,
    fine: Optional[list[dict]]=None,
    entry_selection: str="stream",
) -> list[dict]:
    n=len(candles)
    if n==0:
        return []
    signals=_collect_signals(swings, entry_break, skip_first=skip_first, selection=entry_selection, candles=candles if entry_selection=="stream" else None)
    candle_ts=[int(c["ts"]) for c in candles]
    fine_ts=[int(c["ts"]) for c in fine] if fine else []
    # HTF events mapped to main window ts
    # swings_htf confirmed idx is in HTF window, need to map via candle_ts_htf
    # For simplicity, caller passes swings_htf already with confirmed_at_idx in HTF coords; we map to ts via candle_ts_htf
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
        # HTF trail events
        events=[]
        if trailing=="swing" and swings_htf is not None and candle_ts_htf is not None:
            raw=_trail_events_htf(swings_htf, direction)
            # raw idx is HTF idx, map to ts
            events=[(candle_ts_htf[min(e, len(candle_ts_htf)-1)], px) for e,px in raw]
            # only events after entry bar
            events=[(ts,px) for ts,px in events if ts > bar_ts]
            events.sort(key=lambda x: x[0])
        else:
            # fallback to normal swing events on same TF
            from src.btc.btc_engine import _trail_events
            raw0=_trail_events(swings, direction)
            # raw0 idx is main window idx, map to ts
            events=[(candle_ts[min(e+1,n-1)], px) for e,px in raw0 if e >= i]
            events.sort(key=lambda x: x[0])
        ev_idx=-1
        exit_idx=None
        exit_px=None
        outcome="open"
        exit_ts=None
        exit_date=None
        for j in range(i+1, n if not fine else i+1):
            c=candles[j]
            hi=float(c["high"]); lo=float(c["low"])
            ts=int(c["ts"])
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
                # HTF ratchet: trigger when HTF pivot ts <= current bar ts
                while ev_idx+1 < len(events) and events[ev_idx+1][0] <= ts:
                    ev_idx+=1
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
                while ev_idx+1 < len(events) and events[ev_idx+1][0] <= ts:
                    ev_idx+=1
                    cand=events[ev_idx][1]
                    if hi < cand < sl_cur:
                        sl_cur=cand
        if fine:
            # 1m precise with HTF events
            f_start=bisect.bisect_left(fine_ts, candle_ts[i+1])
            best_f=entry
            sl_cur_f=sl_cur
            ev_idx_f=ev_idx
            fk=None
            exit_px_f=None
            outcome_f="open"
            for k in range(f_start, len(fine)):
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
                    while ev_idx_f+1 < len(events) and events[ev_idx_f+1][0] <= ts:
                        ev_idx_f+=1
                        cand=events[ev_idx_f][1]
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
                    while ev_idx_f+1 < len(events) and events[ev_idx_f+1][0] <= ts:
                        ev_idx_f+=1
                        cand=events[ev_idx_f][1]
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
