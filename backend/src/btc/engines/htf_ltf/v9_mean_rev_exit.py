"""v9_mean_rev_exit — v5 entry (1h Flip cap16 + 15m B2/FLIP same dir, 0.25ATR ext-stop1.5) but EXIT via Ghost RCHB exhaustion (not MB50).
Entry: same as v5 (ghostHTF not, normal Flip HTF intervals 355). Exit: track color-specific 1m highs/lows post-entry (RED highs for LONG, GREEN lows for SHORT) per doc official.md:437 RCHB, shift on lower high / higher low, break = exit.
Separate engine, never disturb v5. For full testing vs v5 442 +168.
"""
from __future__ import annotations
import bisect
from typing import Optional

def simulate_htf_ltf_rchb_exit(
    candles_htf: list[dict],
    swings_htf: list[dict],
    candles_ltf: list[dict],
    swings_ltf: list[dict],
    fine_ltf: Optional[list[dict]] = None,
    *,
    sl_buf_atr: float = 0.25,
    ext_stop_r: float = 1.5,
) -> dict:
    from src.btc.engines.v7_timecap import simulate_btc_trades_v7
    from src.btc.btc_engine import _collect_signals, CandleStore
    # HTF Flip intervals same as v5
    htf_trades = simulate_btc_trades_v7(candles_htf, swings_htf, entry_break="flip", sl_mode="swing", rr_target=3.0, trailing="off", breakeven_r=0.0, skip_first=True, fine=fine_ltf, cap_days=16)
    intervals=[]
    for t in htf_trades:
        if t["outcome"]=="open": continue
        intervals.append((int(t["entry_ts"]), int(t["exit_ts"]), 1 if t["dir"]=="long" else -1, float(t["entry_price"]), float(t["sl"])))
    intervals.sort(key=lambda x: x[0])
    starts=[s for s,_,_,_,_ in intervals]
    ltf_sigs=_collect_signals(swings_ltf, "decisive", skip_first=True, selection="stream", candles=candles_ltf)
    filtered=[]
    for sig in ltf_sigs:
        bar_ts=int(candles_ltf[sig["bar"]]["ts"])
        idx=bisect.bisect_right(starts, bar_ts)-1
        if idx<0: continue
        s,e,d,pe,psl = intervals[idx]
        if not (s < bar_ts <= e): continue
        if sig["dir"] != d: continue
        if ext_stop_r>0:
            hrisk=abs(pe - psl)
            if hrisk>0:
                ext=(float(candles_ltf[sig["bar"]]["close"])-pe)*d/hrisk
                if ext > ext_stop_r: continue
        filtered.append(sig)
    n=len(candles_ltf)
    if n==0:
        return {"htf_trades": htf_trades, "ltf_trades": [], "intervals": intervals}
    candle_ts=[int(c["ts"]) for c in candles_ltf]
    atr15=None
    if sl_buf_atr>0:
        tr_l=[0.0]*n
        for _i in range(n):
            _c=candles_ltf[_i]
            if _i==0: tr_l[_i]=float(_c["high"])-float(_c["low"])
            else:
                _pc=float(candles_ltf[_i-1]["close"])
                tr_l[_i]=max(float(_c["high"])-float(_c["low"]), abs(float(_c["high"])-_pc), abs(float(_c["low"])-_pc))
        atr15=[0.0]*n
        for _i in range(n):
            _lo=max(0,_i-13)
            atr15[_i]=sum(tr_l[_lo:_i+1])/(_i-_lo+1)
    fine_ts=[int(c["ts"]) for c in fine_ltf] if fine_ltf else []
    ltf_trades=[]
    store = CandleStore(candles_ltf)
    busy_until=""
    import bisect as bs
    for sig in filtered:
        i=store.pos(sig["bar"])
        if i < 0 or i >= n-1: continue
        bar_ts_loop = sig["bar"]
        if busy_until and bar_ts_loop <= busy_until: continue
        direction=int(sig["dir"])
        entry=float(candles_ltf[i]["close"])
        sl_pivot=sig["swing_start_px"]
        if direction==1:
            sl=sl_pivot - sl_buf_atr*atr15[i] if sl_buf_atr>0 and atr15 else sl_pivot
            if sl>=entry: continue
            risk=entry-sl
            if risk<0.0005*entry: continue
        else:
            sl=sl_pivot + sl_buf_atr*atr15[i] if sl_buf_atr>0 and atr15 else sl_pivot
            if sl<=entry: continue
            risk=sl-entry
            if risk<0.0005*entry: continue
        sl0=sl
        sl_cur=sl
        # RCHB exit state: track color-specific 1m ref
        # For LONG: track RED 1m highs (close<open), ref_high initial = first RED high after entry, shift down if lower high
        # For SHORT: track GREEN lows (close>open), ref_low initial = first GREEN low, shift up if higher low
        # Exit when close breaks ref (LONG: close > ref_high, SHORT: close < ref_low)
        # Use fine 1m for precise RCHB
        exit_idx=None; exit_px=None; outcome="open"; exit_ts=None; exit_date=None
        if fine_ltf and fine_ts:
            f_start=bs.bisect_left(fine_ts, candle_ts[i+1])
            ref_high=None; ref_low=None
            # need to find first RED/GREEN after entry to init ref
            for k in range(f_start, len(fine_ltf)):
                c=fine_ltf[k]
                hi=float(c["high"]); lo=float(c["low"]); op=float(c["open"]); cl=float(c["close"]); ts=int(c["ts"])
                is_red = cl < op
                is_green = cl > op
                # init ref if not set
                if direction==1:
                    if is_red:
                        if ref_high is None:
                            ref_high=hi
                        else:
                            # lower high shifts down (exhaustion)
                            if hi < ref_high:
                                ref_high=hi
                        # check break above ref_high
                        if cl > ref_high and ref_high is not None:
                            # need to ensure this is not the same bar that set ref? Require break after shift
                            # Simple: if close > ref_high, exit
                            # But avoid immediate exit on same bar that set ref: require k > f_start and cl > ref_high
                            if k > f_start:
                                exit_px=cl
                                exit_ts=ts
                                outcome="trail"  # RCHB break
                                exit_idx=bs.bisect_right(candle_ts, ts)-1
                                break
                    # also check SL hit
                    if lo <= sl_cur:
                        fill=min(sl_cur, op)
                        exit_px=fill
                        exit_ts=ts
                        outcome="sl" if sl_cur <= sl0 else "trail"
                        exit_idx=bs.bisect_right(candle_ts, ts)-1
                        break
                else: # short
                    if is_green:
                        if ref_low is None:
                            ref_low=lo
                        else:
                            if lo > ref_low:
                                ref_low=lo
                        if cl < ref_low and ref_low is not None:
                            if k > f_start:
                                exit_px=cl
                                exit_ts=ts
                                outcome="trail"
                                exit_idx=bs.bisect_right(candle_ts, ts)-1
                                break
                    if hi >= sl_cur:
                        fill=max(sl_cur, op)
                        exit_px=fill
                        exit_ts=ts
                        outcome="sl" if sl_cur >= sl0 else "trail"
                        exit_idx=bs.bisect_right(candle_ts, ts)-1
                        break
            if exit_idx is None:
                exit_idx=n-1
                exit_px=float(fine_ltf[-1]["close"])
                exit_ts=int(fine_ltf[-1]["ts"])
                exit_date=fine_ltf[-1].get("date") or candles_ltf[-1]["date"]
                outcome="open"
            else:
                exit_idx=max(0, min(exit_idx, n-1))
                exit_date=fine_ltf[fk].get("date") if 'fk' in locals() and fk is not None else candles_ltf[exit_idx]["date"] if exit_idx < n else candles_ltf[-1]["date"]
                # above exit_date logic may be wrong, use fine date if available
                try:
                    exit_date=fine_ltf[k].get("date") if 'k' in locals() else candles_ltf[exit_idx]["date"]
                except:
                    exit_date=candles_ltf[exit_idx]["date"]
        else:
            # fallback to MB50 if no fine (should not happen, fine always)
            from src.btc.btc_engine import _trail_events as _te
            events=_te(swings_ltf, direction)
            ev_idx=-1
            for j in range(i+1, n):
                c=candles_ltf[j]
                hi=float(c["high"]); lo=float(c["low"])
                if direction==1:
                    if lo <= sl_cur:
                        fill=min(sl_cur, float(c["open"]))
                        exit_idx,exit_px=j,fill
                        outcome="sl" if sl_cur <= sl0 else "trail"
                        break
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
            if exit_idx is None:
                exit_idx=n-1
                exit_px=float(candles_ltf[-1]["close"])
                outcome="open"
        if exit_idx is None:
            exit_idx=n-1
            exit_px=float(candles_ltf[-1]["close"])
            outcome="open"
            exit_ts=int(candles_ltf[-1]["ts"])
            exit_date=candles_ltf[-1]["date"]
        if not fine_ltf or 'exit_ts' not in locals() or exit_ts is None:
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
            "target": 0,
            "exit_idx": exit_idx,
            "exit_ts": int(exit_ts),
            "exit_date": exit_date,
            "exit_price": round(float(exit_px),2),
            "outcome": outcome,
            "r_multiple": round(float(r_multiple),3),
            "bars_held": exit_idx - i,
        })
        busy_until=candles_ltf[exit_idx]["date"] if exit_idx is not None and exit_idx < n else ""
    return {"htf_trades": htf_trades, "ltf_trades": ltf_trades, "intervals": intervals}
