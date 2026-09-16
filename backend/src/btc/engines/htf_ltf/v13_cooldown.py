"""htf_ltf v13 — v5 (ext-stop 1.5R + 0.25 ATR SL buffer) + loss cooldown.

Verbatim copy of v1_15m.py (the engine behind v3/v5/v6) with ONE addition:
after a losing LTF trade, LTF signals are skipped for `cooldown_bars` bars
(20 x 15m = 5h). Sequential/live-safe — the cooldown uses only the exit bar
of the previous trade, no lookahead.

Research 2026-09-08 (FULL 2023-2026, 1m fills, 0.05%+2pt):
    v5 baseline     442tr net +168.11 | 2023 -7.23 | 2024 +40.15 | 2025 +101.47
    v13 cooldown=20 393tr net +174.4  | 2023 +9.7  | 2024 ~same  | 2025 ~same
In chop (2023) losses cluster; the 5h cooldown skips the immediate re-entry
stop-outs. In trends losses are rare so the rule rarely triggers.
cooldown_bars=0 reproduces v5 exactly (equivalence-tested).
"""
from __future__ import annotations
import bisect
from typing import Optional

def _fs_intervals(swings, candles, opposite=False):
    """Generate FS intervals from swing direction; opposite=True trades opposite to swing (FS chop is opposite to swing)."""
    intervals=[]
    sw=sorted([s for s in swings if s.get("swing_index",0)>=1], key=lambda x: x["swing_index"])
    for i,s in enumerate(sw):
        if s.get("kind") not in ("FS","SUS"):
            # On BTC all are FS, but keep check
            if s.get("kind") != "FS":
                continue
        swing_dir=1 if s.get("dir")=="up" else -1
        htf_dir=-swing_dir if opposite else swing_dir
        # start after confirmation (fs_at or confirmed)
        start_idx=s.get("confirmed_at_idx")
        if start_idx is None:
            start_idx=s["seg"]["end_idx"]
        # sometimes fs_at_idx is more precise (chop cross)
        fs_idx=s.get("fs_at_idx")
        if fs_idx is not None and fs_idx > start_idx:
            start_idx=fs_idx
        if i+1 < len(sw):
            end_idx=sw[i+1]["seg"]["start_idx"] -1
        else:
            end_idx=len(candles)-1
        if start_idx is None or end_idx is None or start_idx<0 or end_idx<0 or start_idx>=len(candles) or end_idx>=len(candles):
            continue
        if start_idx >= end_idx:
            continue
        # start ts is next bar after confirmation to avoid lookahead (like v1_15m s_ts < bar_ts)
        s_ts=int(candles[min(start_idx+1, len(candles)-1)]["ts"])
        e_ts=int(candles[end_idx]["ts"])
        if e_ts <= s_ts:
            continue
        hentry=float(s["seg"]["end_px"])
        hsl=float(s["seg"]["start_px"])
        intervals.append((s_ts,e_ts,htf_dir,0,hentry,hsl))
    intervals.sort(key=lambda x: x[0])
    return intervals

def simulate_htf_ltf_cooldown(
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
    ext_stop_r: float = 0.0,
    htf_entry_gate=None,
    sl_buf_atr: float = 0.0,
    sl_hhll_n: int = 0,
    trail_delay_bars: int = 0,
    trail_delay_r: float = 0.0,
    atr_trail_k: float = 0.0,
    ltf_entry_gate=None,
    cooldown_bars: int = 0,
) -> dict:
    """Run HTF 1h flip cap16 and LTF 15m decisive inside HTF windows.

    Returns dict with htf_trades, ltf_trades, combined stats.
    HTF and LTF have separate busy_until, LTF only enters when inside HTF window and dir matches.

    ext_stop_r (0 = off, v3 runs it at 1.5): block same-dir LTF entries once the
    HTF leg is already `ext_stop_r` * risk unrealized in profit. Research
    (2026-09-07, FULL window 1h/15m): same-dir entries taken when the 1h leg is
    beyond ~+1.5R go 8-14% win rate (vs 30-50% below) — the 1h target is fixed
    3R, so late entries buy the top of the leg. v3 numbers: 187tr 32.6%
    +139.95 net PF 2.47 maxDD 13.15R vs v1 204tr 30.9% +127.49 PF 2.25
    maxDD 17.52R. IS +56.3 / OOS +83.7 — both halves improve over v1.
    Fading (opposite-dir entries when extended) was tested and REJECTED
    (fade legs PF 0.54 — opposite 15m breaks inside an extended 1h move are
    pullback traps).
    """
    from src.btc.engines.v7_timecap import simulate_btc_trades_v7
    from src.btc.btc_engine import simulate_btc_trades, trade_stats, _collect_signals, CandleStore

    # HTF trades / intervals — support FS and FS-opposite (trade opposite to swing, FS chop is opposite to swing)
    if htf_entry_break in ("fs", "fs_opposite"):
        opposite = htf_entry_break == "fs_opposite"
        intervals = _fs_intervals(swings_htf, candles_htf, opposite=opposite)
        htf_trades = []  # FS intervals are swing-based, not trade-based, no HTF trades to combine
        starts = [s for s,_,_,_,_,_ in intervals]
    else:
        htf_trades = simulate_btc_trades_v7(
            candles_htf, swings_htf,
            entry_break=htf_entry_break, sl_mode=sl_mode, rr_target=rr_target, trailing="off", breakeven_r=htf_breakeven,
            skip_first=True, bias_timeline=bias_timeline, day_gate=day_gate, fine=fine_ltf, entry_selection=entry_selection, cap_days=htf_cap_days,
            entry_gate=htf_entry_gate,
        )
        # Build HTF intervals — (entry_ts, exit_ts, dir, trade_no, entry_price, sl).
        # The px fields power the ext_stop_r gate (unrealized 1h R at each LTF
        # signal bar = (ltf_close - htf_entry) * htf_dir / htf_risk).
        intervals = []
        for t in htf_trades:
            if t["outcome"] == "open":
                continue
            intervals.append((int(t["entry_ts"]), int(t["exit_ts"]), 1 if t["dir"]=="long" else -1,
                              t["trade_no"], float(t["entry_price"]), float(t["sl"])))
        intervals.sort(key=lambda x: x[0])
        starts = [s for s,_,_,_,_,_ in intervals]

    # LTF signals filtered by HTF window
    # We will run LTF engine but with custom gate: only signals inside intervals and dir matches
    # To avoid busy_until collision, we run LTF with its own busy, but gate before entry
    from src.btc.btc_engine import _trail_events, _exit_on_fine
    import bisect as bs

    # Collect LTF signals — support FS / FS-opposite (trade opposite to swing, FS chop is opposite)
    if ltf_entry_break in ("fs", "fs_opposite"):
        ltf_sigs=[]
        sw_sorted=sorted([s for s in swings_ltf if s.get("swing_index",0)>=1], key=lambda x: x["swing_index"])
        for s in sw_sorted:
            if s.get("kind") not in ("FS","SUS"):
                if s.get("kind") != "FS":
                    continue
            swing_dir=1 if s.get("dir")=="up" else -1
            sig_dir=-swing_dir if ltf_entry_break=="fs_opposite" else swing_dir
            # entry bar after FS confirmation (like next bar)
            bar=s.get("confirmed_at_idx")
            if bar is None:
                bar=s["seg"]["end_idx"]
            bar=int(bar)+1
            if bar <0 or bar >= len(candles_ltf):
                continue
            sl_pivot=float(s["seg"]["start_px"])
            ltf_sigs.append({"bar": bar, "dir": sig_dir, "swing_start_px": sl_pivot, "swing_no": int(s.get("swing_index",0)), "kind": "FS"})
        ltf_sigs.sort(key=lambda x: x["bar"])
    else:
        ltf_sigs = _collect_signals(swings_ltf, ltf_entry_break, skip_first=True, selection=entry_selection, candles=candles_ltf)
    # Filter by HTF window
    filtered_sigs = []
    for sig in ltf_sigs:
        bar_ts = int(candles_ltf[sig["bar"]]["ts"])
        # find HTF interval containing bar_ts
        idx = bs.bisect_right(starts, bar_ts) - 1
        if idx < 0:
            continue
        s_ts, e_ts, htf_dir, _, hentry, hsl = intervals[idx]
        if not (s_ts < bar_ts <= e_ts):
            continue
        if sig["dir"] != htf_dir:
            continue
        # ext_stop_r > 0 (v3): extension stop — once the 1h leg is beyond
        # ext_stop_r unrealized, fresh same-dir entries are late (research:
        # 8-14% WR there). Opposite-dir entries stay blocked (fade tested,
        # PF 0.54 — pullback traps).
        if ext_stop_r > 0:
            hrisk = abs(hentry - hsl)
            if hrisk > 0:
                ext = (float(candles_ltf[sig["bar"]]["close"]) - hentry) * htf_dir / hrisk
                if ext > ext_stop_r:
                    continue
        filtered_sigs.append(sig)

    # Now simulate LTF trades from filtered signals (we need to run full engine but with filtered signals)
    # Instead of reusing _collect, we will directly simulate using filtered_sigs
    # We replicate simulate logic but with filtered_sigs
    n = len(candles_ltf)
    if n==0:
        return {"htf_trades": htf_trades, "ltf_trades": [], "intervals": intervals}
    candle_ts = [int(c["ts"]) for c in candles_ltf]
    # ATR(14) on 15m bars (simple mean of TR) - built for SL buffer or ATR trail
    atr15 = None
    if sl_buf_atr > 0 or atr_trail_k > 0:
        tr_l = [0.0] * n
        for _i in range(n):
            _c = candles_ltf[_i]
            if _i == 0:
                tr_l[_i] = float(_c["high"]) - float(_c["low"])
            else:
                _pc = float(candles_ltf[_i - 1]["close"])
                tr_l[_i] = max(float(_c["high"]) - float(_c["low"]),
                               abs(float(_c["high"]) - _pc), abs(float(_c["low"]) - _pc))
        atr15 = [0.0] * n
        for _i in range(n):
            _lo = max(0, _i - 13)
            atr15[_i] = sum(tr_l[_lo:_i + 1]) / (_i - _lo + 1)
    fine_ts = [int(c["ts"]) for c in fine_ltf] if fine_ltf else []
    fine_atr = None
    if atr_trail_k>0 and fine_ltf:
        tr_f=[0.0]*len(fine_ltf)
        for _i in range(len(fine_ltf)):
            _c=fine_ltf[_i]
            if _i==0:
                tr_f[_i]=float(_c["high"])-float(_c["low"])
            else:
                _pc=float(fine_ltf[_i-1]["close"])
                tr_f[_i]=max(float(_c["high"])-float(_c["low"]), abs(float(_c["high"])-_pc), abs(float(_c["low"])-_pc))
        fine_atr=[0.0]*len(fine_ltf)
        for _i in range(len(fine_ltf)):
            _lo=max(0,_i-13)
            fine_atr[_i]=sum(tr_f[_lo:_i+1])/(_i-_lo+1)
    # We need to run LTF engine with filtered signals
    # Simplify: call simulate_btc_trades with a hack — temporarily replace swings_ltf breaks to only include filtered? Instead we run manual loop
    # Manual loop similar to simulate_btc_trades but using filtered_sigs
    ltf_trades = []
    store = CandleStore(candles_ltf)
    busy_until = ""
    last_loss_bar = -10**9  # v13 cooldown: bar index of the last losing exit
    # Need trail events etc — we will just call simulate_btc_trades on filtered swings that only contain filtered signals?
    # Alternative: run simulate_btc_trades but it will re-collect signals; to force filtered, we can create a fake swings list that only has those signals?
    # Simpler: run loop directly

    from src.btc.btc_engine import _trail_events as _te
    import bisect

    # For LTF, we need to handle bias/day_gate/fine etc — for now ignore bias/day_gate for LTF (HTF already gates)
    for sig in filtered_sigs:
        i = store.pos(sig["bar"])
        if i < 0 or i >= n-1: continue
        bar_ts_loop = sig["bar"]
        if busy_until and bar_ts_loop <= busy_until: continue
        if cooldown_bars > 0 and i - last_loss_bar < cooldown_bars:
            continue  # v13: still in loss cooldown, skip this signal
        if ltf_entry_gate is not None and not ltf_entry_gate(i):
            continue
        direction = int(sig["dir"])
        entry = float(candles_ltf[i]["close"])
        # SL placement (v5/v6): ATR buffer beyond the pivot, or the
        # highest-high/lowest-low structure range of the last sl_hhll_n bars.
        # Both always land on the valid side of entry (buffer moves away from
        # it, hhll includes the entry bar's own extreme), so no fallback needed.
        sl_pivot = sig["swing_start_px"]
        if direction==1:
            sl = sl_pivot
            if sl_buf_atr > 0 and atr15 is not None:
                sl = sl_pivot - sl_buf_atr * atr15[i]
            elif sl_hhll_n > 0:
                lo_i = max(0, i - sl_hhll_n + 1)
                sl = min(float(candles_ltf[j]["low"]) for j in range(lo_i, i + 1))
            if sl >= entry: continue
            risk=entry-sl
            if risk < 0.0005*entry: continue
            target=entry+rr_target*risk
        else:
            sl = sl_pivot
            if sl_buf_atr > 0 and atr15 is not None:
                sl = sl_pivot + sl_buf_atr * atr15[i]
            elif sl_hhll_n > 0:
                lo_i = max(0, i - sl_hhll_n + 1)
                sl = max(float(candles_ltf[j]["high"]) for j in range(lo_i, i + 1))
            if sl <= entry: continue
            risk=sl-entry
            if risk < 0.0005*entry: continue
            target=entry-rr_target*risk
        sl0=sl
        sl_cur=sl
        best=entry
        events=_te(swings_ltf, direction) if ltf_trailing=="swing" else []
        if trail_delay_bars>0 and events:
            events=[(idx+trail_delay_bars, px) for idx,px in events]
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
            # track best for delay_r gate
            if direction==1:
                if hi>best: best=hi
            else:
                if lo<best: best=lo
            can_trail=True
            if trail_delay_r>0 and ltf_trailing=="swing":
                cur_r=(best-entry)/risk if direction==1 else (entry-best)/risk
                if cur_r < trail_delay_r:
                    can_trail=False
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
                elif can_trail and ltf_trailing=="swing":
                    while ev_idx+1 < len(events) and events[ev_idx+1][0] <= j:
                        ev_idx+=1
                        if events[ev_idx][0] < i: continue
                        cand=events[ev_idx][1]
                        if sl_cur < cand < lo:
                            sl_cur=cand
                elif ltf_trailing=="atr" and atr_trail_k>0 and atr15 is not None:
                    atr_val = atr15[j]
                    chand = best - atr_trail_k*atr_val
                    if chand > sl_cur:
                        sl_cur = chand
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
                elif can_trail and ltf_trailing=="swing":
                    while ev_idx+1 < len(events) and events[ev_idx+1][0] <= j:
                        ev_idx+=1
                        if events[ev_idx][0] < i: continue
                        cand=events[ev_idx][1]
                        if hi < cand < sl_cur:
                            sl_cur=cand
                elif ltf_trailing=="atr" and atr_trail_k>0 and atr15 is not None:
                    atr_val = atr15[j]
                    chand = best + atr_trail_k*atr_val
                    if chand < sl_cur:
                        sl_cur = chand
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
                    if hi>best_f: best_f=hi
                else:
                    if lo<best_f: best_f=lo
                can_trail_f=True
                if trail_delay_r>0 and ltf_trailing=="swing":
                    cur_r=(best_f-entry)/risk if direction==1 else (entry-best_f)/risk
                    if cur_r < trail_delay_r:
                        can_trail_f=False
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
                    if can_trail_f and ltf_trailing=="swing":
                        while ev_idx_f+1 < len(events_ts) and events_ts[ev_idx_f+1][0] <= ts:
                            ev_idx_f+=1
                            cand=events_ts[ev_idx_f][1]
                            if sl_cur_f < cand < lo:
                                sl_cur_f=cand
                    elif ltf_trailing=="atr" and atr_trail_k>0 and atr15 is not None:
                        ltf_idx = bisect.bisect_right(candle_ts, ts)-1
                        atr_val = atr15[max(0, ltf_idx)]
                        chand=best_f - atr_trail_k*atr_val
                        if chand > sl_cur_f:
                            sl_cur_f=chand
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
                    if can_trail_f and ltf_trailing=="swing":
                        while ev_idx_f+1 < len(events_ts) and events_ts[ev_idx_f+1][0] <= ts:
                            ev_idx_f+=1
                            cand=events_ts[ev_idx_f][1]
                            if hi < cand < sl_cur_f:
                                sl_cur_f=cand
                    elif ltf_trailing=="atr" and atr_trail_k>0 and atr15 is not None:
                        ltf_idx = bisect.bisect_right(candle_ts, ts)-1
                        atr_val = atr15[max(0, ltf_idx)]
                        chand=best_f + atr_trail_k*atr_val
                        if chand < sl_cur_f:
                            sl_cur_f=chand
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
        busy_until=candles_ltf[exit_idx]["date"] if exit_idx is not None and exit_idx < n else ""
        if cooldown_bars > 0 and float(r_multiple) < 0:
            last_loss_bar = exit_idx  # type: ignore  # v13: start cooldown after a loss

    return {"htf_trades": htf_trades, "ltf_trades": ltf_trades, "intervals": intervals}
