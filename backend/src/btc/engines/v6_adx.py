"""v6 — ADX gate. Trail only when ADX14 >25."""
from __future__ import annotations
from typing import Optional
import bisect
from src.btc.btc_engine import _collect_signals, CandleStore

def _adx_series(candles: list[dict], period: int=14) -> list[float]:
    # Wilder ADX
    n=len(candles)
    tr=[0.0]*n
    plus_dm=[0.0]*n
    minus_dm=[0.0]*n
    for i in range(1,n):
        h=float(candles[i]["high"]); l=float(candles[i]["low"]); hc=float(candles[i-1]["close"]); ph=float(candles[i-1]["high"]); pl=float(candles[i-1]["low"])
        tr[i]= max(h-l, abs(h-hc), abs(l-hc))
        up = h - ph
        dn = pl - l
        if up > dn and up > 0:
            plus_dm[i]=up
        if dn > up and dn > 0:
            minus_dm[i]=dn
    atr=[0.0]*n
    atr_plus=[0.0]*n
    atr_minus=[0.0]*n
    adx=[0.0]*n
    # Wilder smoothing
    sum_tr=sum(tr[1:period+1])
    sum_plus=sum(plus_dm[1:period+1])
    sum_minus=sum(minus_dm[1:period+1])
    atr[period]=sum_tr/period
    atr_plus[period]=sum_plus/period
    atr_minus[period]=sum_minus/period
    dx=[0.0]*n
    for i in range(period+1, n):
        atr[i]= (atr[i-1]*(period-1)+ tr[i])/period
        atr_plus[i]= (atr_plus[i-1]*(period-1)+ plus_dm[i])/period
        atr_minus[i]= (atr_minus[i-1]*(period-1)+ minus_dm[i])/period
        plus_di= 100*atr_plus[i]/atr[i] if atr[i]!=0 else 0
        minus_di=100*atr_minus[i]/atr[i] if atr[i]!=0 else 0
        denom= plus_di+minus_di
        dx[i]= 100*abs(plus_di-minus_di)/denom if denom!=0 else 0
        if i >= 2*period:
            if i==2*period:
                adx[i]= sum(dx[period+1:2*period+1])/period
            else:
                adx[i]= (adx[i-1]*(period-1)+ dx[i])/period
    return adx

def simulate_btc_trades_v6(
    candles, swings, *,
    entry_break="decisive", sl_mode="swing", sl_pct=0.5, rr_target=3.0, trailing="swing", breakeven_r=0.0,
    skip_first=True, bias_timeline=None, day_gate=None, fine=None, entry_selection="stream",
    adx_threshold: float=25.0,
):
    n=len(candles)
    if n==0:
        return []
    signals=_collect_signals(swings, entry_break, skip_first=skip_first, selection=entry_selection, candles=candles if entry_selection=="stream" else None)
    candle_ts=[int(c["ts"]) for c in candles]
    fine_ts=[int(c["ts"]) for c in fine] if fine else []
    adx=_adx_series(candles, 14)
    # fine adx not needed (gate on entry bar)
    bias_ptr=-1
    bias_now=None
    trades=[]
    store = CandleStore(candles)
    busy_until=""
    from src.btc.btc_engine import _trail_events, _exit_on_fine
    for sig in signals:
        i=store.pos(sig["bar"])
        if i < 0 or i >= n-1: continue
        bar_ts_loop = sig["bar"]
        if busy_until and bar_ts_loop <= busy_until: continue
        # ADX gate at entry bar
        if adx[i] < adx_threshold:
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
        for j in range(i+1, n if not fine else i+1):
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
                if trailing=="swing":
                    while ev_idx+1 < len(events) and events[ev_idx+1][0] <= j:
                        ev_idx+=1
                        if events[ev_idx][0] < i:
                            continue
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
                if trailing=="swing":
                    while ev_idx+1 < len(events) and events[ev_idx+1][0] <= j:
                        ev_idx+=1
                        if events[ev_idx][0] < i:
                            continue
                        cand=events[ev_idx][1]
                        if hi < cand < sl_cur:
                            sl_cur=cand
        if fine:
            events_ts=[(candle_ts[min(e+1,n-1)], px) for e,px in events if candle_ts[min(e+1,n-1)] > bar_ts] if trailing=="swing" else []
            f_start=bisect.bisect_left(fine_ts, candle_ts[i+1])
            fk,exit_px_f,outcome_f=_exit_on_fine(fine, f_start, direction, entry, sl0, sl_cur, target, risk, trailing, 1.0, breakeven_r, events_ts)
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
        busy_until=candles[exit_idx]["date"] if exit_idx is not None and exit_idx < n else ""
    return trades
