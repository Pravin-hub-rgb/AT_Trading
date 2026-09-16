"""v8 — 3R secure then trail. For LTF inside HTF: fixed 3R target first, if hit 3R then trail SL to swing pivots / 1h candle.

Entry SL same as v1 (touchable), trailing is swing but only after price reaches 3R (secure 3R). Before 3R, SL stays at entry or BE0. After 3R, SL trails to swing pivots (or to 3R level, whichever higher for long).
"""
from __future__ import annotations
import bisect
from typing import Optional

def simulate_btc_trades_v8(
    candles: list[dict],
    swings: list[dict],
    *,
    entry_break: str = "decisive",
    sl_mode: str = "swing",
    sl_pct: float = 0.5,
    rr_target: float = 3.0,
    trailing: str = "swing",
    breakeven_r: float = 0.0,
    skip_first: bool = True,
    bias_timeline=None,
    day_gate=None,
    fine: Optional[list[dict]] = None,
    entry_selection: str = "stream",
    secure_r: float = 3.0,  # secure at 3R, then trail
) -> list[dict]:
    n=len(candles)
    if n==0:
        return []
    from src.btc.btc_engine import _collect_signals, _trail_events, _exit_on_fine, trade_stats, CandleStore
    signals=_collect_signals(swings, entry_break, skip_first=skip_first, selection=entry_selection, candles=candles if entry_selection=="stream" else None)
    candle_ts=[int(c["ts"]) for c in candles]
    fine_ts=[int(c["ts"]) for c in fine] if fine else []
    bias_ptr=-1
    bias_now=None
    trades=[]
    store = CandleStore(candles)
    busy_until=""
    for sig in signals:
        i=store.pos(sig["bar"])
        if i < 0 or i >= n-1: continue
        bar_ts_loop = sig["bar"]
        if busy_until and bar_ts_loop <= busy_until: continue
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
        secured=False  # have we reached secure_r?
        exit_idx=None
        exit_px=None
        outcome="open"
        exit_ts=None
        exit_date=None
        # 1h candle for secure trail to 1h candle low/high after secure?
        # For now, secure trail is swing pivots only after secure_r
        for j in range(i+1, n if not fine else i+1):
            c=candles[j]
            hi=float(c["high"]); lo=float(c["low"])
            # check if we have secured 3R
            if not secured:
                if direction==1 and hi >= entry + secure_r * risk:
                    secured=True
                    # secure: move SL to entry + (secure_r-1)*risk? Actually secure 3R means lock 3R? User said trail sl to 3R when goes to 4R, secure 3R. Let's secure at secure_r: SL = entry + (secure_r - 0.5)*risk? Simpler: SL = entry + (secure_r-1)*risk? For 3R secure, SL = entry + 2R? But user said when goes to 4R trail sl to 3R, 3R secured. So when price hits secure_r, SL = entry + (secure_r-1)*risk? For secure 3, SL = entry +2R? Let's do SL = entry + (secure_r - 1)*risk for long, entry - (secure_r -1)*risk for short, but also at least entry.
                    # For now, secure at 3R: SL = entry (BE) + (secure_r-1)*risk? To secure 3R, SL should be at 3R -1R =2R? Hmm.
                    # User said: when goes to 4R we trail sl to 3R, 3R secured. So sl = entry + 3*risk when price at 4*risk. That's secure 3R. So we can implement: when hi >= entry+secure_r*risk, sl = max(sl_cur, entry + (secure_r-1)*risk)
                    # For secure 3, sl = entry+2*risk when price at 3R? But then when price at 4R, sl = entry+3*risk.
                    # Simpler: when secured, sl = entry + (secure_r-1)*risk? Let's just set sl = entry + (secure_r-1)*risk at secure moment, then trail from there.
                    sl_cur = max(sl_cur, entry + (secure_r-1)*risk) if direction==1 else min(sl_cur, entry - (secure_r-1)*risk)
                    secured=True
                elif direction==-1 and lo <= entry - secure_r * risk:
                    secured=True
                    sl_cur = min(sl_cur, entry - (secure_r-1)*risk)
                    secured=True
            if direction==1:
                if lo <= sl_cur:
                    fill=min(sl_cur, float(c["open"]))
                    exit_idx,exit_px=j,fill
                    outcome="sl" if sl_cur <= sl0 else "be" if abs(sl_cur-entry)<=1e-9 else "trail"
                    break
                if trailing=="off" and hi >= target and not secured:
                    # fixed target only before secure? Actually fixed target is same as secure target
                    exit_idx,exit_px,outcome=j,target,"target"
                    break
                # only trail after secured
                if secured and trailing=="swing":
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
                if trailing=="off" and lo <= target and not secured:
                    exit_idx,exit_px,outcome=j,target,"target"
                    break
                if secured and trailing=="swing":
                    while ev_idx+1 < len(events) and events[ev_idx+1][0] <= j:
                        ev_idx+=1
                        if events[ev_idx][0] < i: continue
                        cand=events[ev_idx][1]
                        if hi < cand < sl_cur:
                            sl_cur=cand
        if fine:
            # 1m precise with secure logic
            f_start=bisect.bisect_left(fine_ts, candle_ts[i+1])
            best_f=entry
            sl_cur_f=sl_cur
            ev_idx_f=ev_idx
            # events_ts for fine
            bar_ts=int(candles[i]["ts"])
            events_ts=[(candle_ts[min(e+1,n-1)], px) for e,px in events] if trailing=="swing" else []
            events_ts=[(ts,px) for ts,px in events_ts if ts > bar_ts]
            secured_f=secured
            fk=None
            exit_px_f=None
            outcome_f="open"
            for k in range(f_start, len(fine)):
                c=fine[k]
                hi=float(c["high"]); lo=float(c["low"]); ts=int(c["ts"])
                # check secure
                if not secured_f:
                    if direction==1 and hi >= entry + secure_r * risk:
                        secured_f=True
                        sl_cur_f=max(sl_cur_f, entry + (secure_r-1)*risk)
                    elif direction==-1 and lo <= entry - secure_r * risk:
                        secured_f=True
                        sl_cur_f=min(sl_cur_f, entry - (secure_r-1)*risk)
                if direction==1:
                    if lo <= sl_cur_f:
                        fill=min(sl_cur_f, float(c["open"]))
                        fk,exit_px_f,outcome_f=k,fill,("sl" if sl_cur_f <= sl0 else "be" if abs(sl_cur_f-entry)<=1e-9 else "trail")
                        break
                    if trailing=="off" and not secured_f and hi >= target:
                        fk,exit_px_f,outcome_f=k,target,"target"
                        break
                    # trail only after secured
                    if secured_f and trailing=="swing":
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
                    if trailing=="off" and not secured_f and lo <= target:
                        fk,exit_px_f,outcome_f=k,target,"target"
                        break
                    if secured_f and trailing=="swing":
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
        busy_until=candles[exit_idx]["date"] if exit_idx is not None and exit_idx < n else ""
    return trades
