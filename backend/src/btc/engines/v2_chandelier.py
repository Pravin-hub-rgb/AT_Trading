"""v2 — Chandelier ATR trail (k=3.0) — isolated from v1.

Entry SL same as v1 (touchable), but trailing uses ATR* k from favorable extreme instead of swing pivots.
"""
from __future__ import annotations
import bisect
from typing import Optional

from src.btc.btc_engine import _collect_signals, trade_stats, _outcome_counts

def _atr_series(candles: list[dict], period: int = 14) -> list[float]:
    # TR = max(high-low, abs(high-prev_close), abs(low-prev_close))
    atr = [0.0]*len(candles)
    trs = []
    for i in range(len(candles)):
        if i==0:
            tr = float(candles[i]["high"]) - float(candles[i]["low"])
        else:
            h = float(candles[i]["high"]); l=float(candles[i]["low"]); pc=float(candles[i-1]["close"])
            tr = max(h-l, abs(h-pc), abs(l-pc))
        trs.append(tr)
        if i < period-1:
            atr[i]= sum(trs[:i+1])/(i+1)
        else:
            # Wilder
            if i==period-1:
                atr[i]= sum(trs[:period])/period
            else:
                atr[i]= (atr[i-1]*(period-1) + tr)/period
    return atr

def simulate_btc_trades_v2(
    candles: list[dict],
    swings: list[dict],
    *,
    entry_break: str = "decisive",
    sl_mode: str = "swing",
    sl_pct: float = 0.5,
    rr_target: float = 3.0,
    trailing: str = "chandelier",
    trail_k: float = 3.0,
    atr_period: int = 14,
    breakeven_r: float = 0.0,
    skip_first: bool = True,
    bias_timeline: Optional[list[tuple[int,str]]] = None,
    day_gate: Optional[dict[str, Optional[str]]] = None,
    fine: Optional[list[dict]] = None,
    entry_selection: str = "stream",
) -> list[dict]:
    # same signal collection as v1
    from src.btc.btc_engine import _collect_signals as _cs
    n=len(candles)
    if n==0:
        return []
    signals=_cs(swings, entry_break, skip_first=skip_first, selection=entry_selection, candles=candles if entry_selection=="stream" else None)
    candle_ts=[int(c["ts"]) for c in candles]
    fine_ts=[int(c["ts"]) for c in fine] if fine else []
    atr=_atr_series(candles, atr_period)
    # also fine ATR for 1m path? use same k on fine via scaling
    fine_atr=_atr_series(fine, atr_period) if fine else []

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
        # bias advance
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
        exit_idx=None
        exit_px=None
        outcome="open"
        exit_ts=None
        exit_date=None
        # HTF walk zero-length when fine supplied, exits via fine
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
                # chandelier: SL = highest high - k*ATR
                # best tracks highest high since entry
                best=max(best, hi)
                atr_val= atr[j] if j < len(atr) else atr[-1]
                chand = best - trail_k*atr_val
                sl_cur=max(sl_cur, chand)
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
                best=min(best, lo)
                atr_val= atr[j] if j < len(atr) else atr[-1]
                chand = best + trail_k*atr_val
                sl_cur=min(sl_cur, chand)
        if fine:
            # 1m precise
            # build fine events as chandelier doesn't use swing events, so we walk fine directly with ATR
            f_start=bisect.bisect_left(fine_ts, candle_ts[i+1])
            best_f=entry
            sl_cur_f=sl_cur
            fk=None
            exit_px_f=None
            outcome_f="open"
            for k in range(f_start, len(fine)):
                c=fine[k]
                hi=float(c["high"]); lo=float(c["low"])
                if direction==1:
                    if lo <= sl_cur_f:
                        fill=min(sl_cur_f, float(c["open"]))
                        fk,exit_px_f, outcome_f = k, fill, ("sl" if sl_cur_f <= sl0 else "be" if abs(sl_cur_f-entry)<=1e-9 else "trail")
                        break
                    if trailing=="off" and hi >= target:
                        fk,exit_px_f,outcome_f=k,target,"target"
                        break
                    if breakeven_r>0 and hi >= entry+breakeven_r*risk and sl_cur_f < entry:
                        sl_cur_f=entry
                    best_f=max(best_f, hi)
                    atr_val= fine_atr[k] if k < len(fine_atr) else fine_atr[-1]
                    chand = best_f - trail_k*atr_val
                    sl_cur_f=max(sl_cur_f, chand)
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
                    best_f=min(best_f, lo)
                    atr_val= fine_atr[k] if k < len(fine_atr) else fine_atr[-1]
                    chand = best_f + trail_k*atr_val
                    sl_cur_f=min(sl_cur_f, chand)
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
        r_multiple= move/risk if risk>0 else 0
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
