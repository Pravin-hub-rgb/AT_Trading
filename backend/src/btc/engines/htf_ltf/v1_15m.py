"""htf_ltf v1_15m — 1h Flip cap16 + 15m Decisive inside HTF window. Isolated."""
from __future__ import annotations
import bisect
from typing import Optional

def simulate_htf_ltf_15m(
    candles_htf: list[dict],
    swings_htf: list[dict],
    candles_ltf: list[dict],
    swings_ltf: list[dict],
    fine_ltf: Optional[list[dict]] = None,
    *,
    htf_entry_break: str = "flip",
    ltf_entry_break: str = "decisive",
    sl_mode: str = "swing",
    rr_target: float = 3.0,
    ltf_trailing: str = "swing",
    htf_breakeven: float = 0.0,
    ltf_breakeven: float = 0.0,
    htf_cap_days: int = 16,
    bias_timeline=None,
    day_gate=None,
    entry_selection: str = "stream",
) -> dict:
    """Run HTF 1h flip cap16 and LTF 15m decisive inside HTF windows.

    Returns dict with htf_trades, ltf_trades, combined stats.
    HTF and LTF have separate busy_until, LTF only enters when inside HTF window and dir matches.
    """
    from src.btc.engines.v7_timecap import simulate_btc_trades_v7
    from src.btc.btc_engine import simulate_btc_trades, trade_stats, _collect_signals

    # HTF trades
    htf_trades = simulate_btc_trades_v7(
        candles_htf, swings_htf,
        entry_break=htf_entry_break, sl_mode=sl_mode, rr_target=rr_target, trailing="off", breakeven_r=htf_breakeven,
        skip_first=True, bias_timeline=bias_timeline, day_gate=day_gate, fine=fine_ltf, entry_selection=entry_selection, cap_days=htf_cap_days,
    )
    # Build HTF intervals
    intervals = []
    for t in htf_trades:
        if t["outcome"] == "open":
            continue
        intervals.append((int(t["entry_ts"]), int(t["exit_ts"]), 1 if t["dir"]=="long" else -1, t["trade_no"]))
    intervals.sort(key=lambda x: x[0])
    starts = [s for s,_,_,_ in intervals]

    # LTF signals filtered by HTF window
    # We will run LTF engine but with custom gate: only signals inside intervals and dir matches
    # To avoid busy_until collision, we run LTF with its own busy, but gate before entry
    from src.btc.btc_engine import _trail_events, _exit_on_fine
    import bisect as bs

    # Collect LTF signals
    ltf_sigs = _collect_signals(swings_ltf, ltf_entry_break, skip_first=True, selection=entry_selection, candles=candles_ltf)
    # Filter by HTF window
    filtered_sigs = []
    for sig in ltf_sigs:
        bar_ts = int(candles_ltf[sig["bar"]]["ts"])
        # find HTF interval containing bar_ts
        idx = bs.bisect_right(starts, bar_ts) - 1
        if idx < 0:
            continue
        s_ts, e_ts, htf_dir, _ = intervals[idx]
        if not (s_ts < bar_ts <= e_ts):
            continue
        if sig["dir"] != htf_dir:
            continue
        filtered_sigs.append(sig)

    # Now simulate LTF trades from filtered signals (we need to run full engine but with filtered signals)
    # Instead of reusing _collect, we will directly simulate using filtered_sigs
    # We replicate simulate logic but with filtered_sigs
    n = len(candles_ltf)
    if n==0:
        return {"htf_trades": htf_trades, "ltf_trades": [], "intervals": intervals}
    candle_ts = [int(c["ts"]) for c in candles_ltf]
    fine_ts = [int(c["ts"]) for c in fine_ltf] if fine_ltf else []
    # We need to run LTF engine with filtered signals
    # Simplify: call simulate_btc_trades with a hack — temporarily replace swings_ltf breaks to only include filtered? Instead we run manual loop
    # Manual loop similar to simulate_btc_trades but using filtered_sigs
    ltf_trades = []
    busy_until = -1
    # Need trail events etc — we will just call simulate_btc_trades on filtered swings that only contain filtered signals?
    # Alternative: run simulate_btc_trades but it will re-collect signals; to force filtered, we can create a fake swings list that only has those signals?
    # Simpler: run loop directly

    from src.btc.btc_engine import _trail_events as _te
    import bisect

    # For LTF, we need to handle bias/day_gate/fine etc — for now ignore bias/day_gate for LTF (HTF already gates)
    for sig in filtered_sigs:
        i = sig["bar"]
        if i <= busy_until or i >= n-1:
            continue
        direction = int(sig["dir"])
        entry = float(candles_ltf[i]["close"])
        if direction==1:
            sl = sig["swing_start_px"]
            if sl >= entry: continue
            risk=entry-sl
            if risk < 0.0005*entry: continue
            target=entry+rr_target*risk
        else:
            sl=sig["swing_start_px"]
            if sl <= entry: continue
            risk=sl-entry
            if risk < 0.0005*entry: continue
            target=entry-rr_target*risk
        sl0=sl
        sl_cur=sl
        best=entry
        events=_te(swings_ltf, direction) if ltf_trailing=="swing" else []
        ev_idx=-1
        exit_idx=None
        exit_px=None
        outcome="open"
        exit_ts=None
        exit_date=None
        # walk HTF bars (LTF candles)
        for j in range(i+1, n if not fine_ltf else i+1):
            c=candles_ltf[j]
            hi=float(c["high"]); lo=float(c["low"])
            if direction==1:
                if lo <= sl_cur:
                    fill=min(sl_cur, float(c["open"]))
                    exit_idx,exit_px=j,fill
                    outcome="sl" if sl_cur <= sl0 else "be" if abs(sl_cur-entry)<=1e-9 else "trail"
                    break
                if ltf_trailing=="off" and hi >= target:
                    exit_idx,exit_px,outcome=j,target,"target"
                    break
                if ltf_breakeven>0 and hi >= entry+ltf_breakeven*risk and sl_cur < entry:
                    sl_cur=entry
                elif ltf_trailing=="swing":
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
                if ltf_trailing=="off" and lo <= target:
                    exit_idx,exit_px,outcome=j,target,"target"
                    break
                if ltf_breakeven>0 and lo <= entry - ltf_breakeven*risk and sl_cur > entry:
                    sl_cur=entry
                elif ltf_trailing=="swing":
                    while ev_idx+1 < len(events) and events[ev_idx+1][0] <= j:
                        ev_idx+=1
                        if events[ev_idx][0] < i: continue
                        cand=events[ev_idx][1]
                        if hi < cand < sl_cur:
                            sl_cur=cand
        if fine_ltf:
            # 1m precise
            candle_ts_ltf=candle_ts
            bar_ts=int(candles_ltf[i]["ts"])
            events_ts=[(candle_ts_ltf[min(e+1,n-1)], px) for e,px in events if candle_ts_ltf[min(e+1,n-1)] > bar_ts] if ltf_trailing=="swing" else []
            f_start=bisect.bisect_left(fine_ts, candle_ts_ltf[i+1])
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
                    if lo <= sl_cur_f:
                        fill=min(sl_cur_f, float(c["open"]))
                        fk,exit_px_f,outcome_f=k,fill,("sl" if sl_cur_f <= sl0 else "be" if abs(sl_cur_f-entry)<=1e-9 else "trail")
                        break
                    if ltf_trailing=="off" and hi >= target:
                        fk,exit_px_f,outcome_f=k,target,"target"
                        break
                    if ltf_breakeven>0 and hi >= entry+ltf_breakeven*risk and sl_cur_f < entry:
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
                    if ltf_trailing=="off" and lo <= target:
                        fk,exit_px_f,outcome_f=k,target,"target"
                        break
                    if ltf_breakeven>0 and lo <= entry - ltf_breakeven*risk and sl_cur_f > entry:
                        sl_cur_f=entry
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
        move=(exit_px-entry) if direction==1 else (entry-exit_px)  # type: ignore
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

    return {"htf_trades": htf_trades, "ltf_trades": ltf_trades, "intervals": intervals}
