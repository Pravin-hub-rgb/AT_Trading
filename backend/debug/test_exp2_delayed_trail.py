"""Exp2 — Delayed trail family sweep on v5 FULL (no UI, docs only).
Tests: immediate MB50 (current) vs delayed by bars (4/8/16/32) vs delayed by +1R/+2R.
Uses live 1.93M fine, 0.05%+2pt, ext-stop 1.5R + buf 0.25ATR held.
Implements delay by shifting _trail_events and/or gating trail until MFE >= delay_r."""
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
from src.btc.btc_routes import _compute_swings, _load_fine_1m, _trade_costs
from src.btc.btc_engine import trade_stats
from src.btc.btc_config import load_btc_df
from src.btc.engines.htf_ltf.v1_15m import simulate_htf_ltf_15m
from src.btc.engines.htf_ltf.v5_sl_buffer import simulate_htf_ltf_sl_buffer
from src.walker import FlowCandle
from src.btc.btc_engine import _collect_signals
import bisect
from collections import defaultdict

FEE=0.05
SLIP=2.0

def load_window(tf):
    df = load_btc_df(tf)
    c=[]; f=[]
    for row in df.itertuples():
        date=row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        c.append({"date":date,"ts":int(row.ts),"open":float(row.open),"high":float(row.high),"low":float(row.low),"close":float(row.close),"volume":0,"oi":0})
        f.append(FlowCandle(date=date,open=float(row.open),high=float(row.high),low=float(row.low),close=float(row.close)))
    return c,f,df

# Load once
c1h,f1h,_ = load_window("1h")
c15,f15,_ = load_window("15m")
sw1h = _compute_swings(f1h,"continuous",min_bars=20)
sw15 = _compute_swings(f15,"continuous",min_bars=50)
t0=min(c1h[0]["ts"],c15[0]["ts"]); t1=max(c1h[-1]["ts"],c15[-1]["ts"])
fine=_load_fine_1m(t0,t1)
print(f"ready: 1h {len(c1h)} 15m {len(c15)} fine {len(fine)} swings {len(sw1h)}/{len(sw15)}")

# We need a custom HTF-LTF engine with delay. Instead of forking v1_15m, we patch it:
# Simulate baseline v5 to get intervals, then run LTF walk manually with delayed events.
# Simpler: import v1_15m source and monkey-patch _trail_events to add delay.
# We'll implement a lightweight version inline that mirrors v1_15m but adds delay params.

from src.btc.btc_engine import _trail_events

def simulate_htf_ltf_delayed(candles_htf, swings_htf, candles_ltf, swings_ltf, fine_ltf,
                              htf_entry_break="flip", sl_buf_atr=0.25, ext_stop_r=1.5,
                              delay_bars=0, delay_r=0.0):
    """Copied from v1_15m.py but adds delay_bars / delay_r to LTF trailing."""
    # HTF window same as v1_15m
    from src.btc.engines.v7_timecap import simulate_btc_trades_v7
    htf_trades = simulate_btc_trades_v7(candles_htf, swings_htf, entry_break=htf_entry_break, sl_mode="swing", rr_target=3.0, trailing="off", breakeven_r=0.0, skip_first=True, fine=fine_ltf, cap_days=16)
    intervals=[(t["entry_ts"], t["exit_ts"], 1 if t["dir"]=="long" else -1, t["trade_no"], t["entry_price"], t["sl"]) for t in htf_trades if t["outcome"]!="open"]
    intervals.sort(key=lambda x: x[0])
    starts=[s[0] for s in intervals]
    # LTF signals
    ltf_sigs = _collect_signals(swings_ltf, "decisive", skip_first=True, selection="stream", candles=candles_ltf)
    # Precompute ATR for SL buffer (same as v1_15m)
    atr15=[0.0]*len(candles_ltf)
    if sl_buf_atr>0:
        tr_l=[0.0]*len(candles_ltf)
        for i in range(len(candles_ltf)):
            hi=candles_ltf[i]["high"]; lo=candles_ltf[i]["low"]
            if i==0:
                tr_l[i]=hi-lo
            else:
                pc=candles_ltf[i-1]["close"]
                tr_l[i]=max(hi-lo, abs(hi-pc), abs(lo-pc))
            lo_i=max(0, i-13)
            atr15[i]= sum(tr_l[lo_i:i+1]) / (i-lo_i+1)
    # LTF walk
    n=len(candles_ltf)
    candle_ts=[c["ts"] for c in candles_ltf]
    fine_ts=[c["ts"] for c in fine_ltf] if fine_ltf else []
    # trail events base
    # Need swings_ltf structure for _trail_events: it expects swings list, we filter by dir later per trade
    # We'll generate per-trade events on fly, applying delay
    ltf_trades=[]
    busy_until=-1
    trade_no=1
    # Pre-build events for both directions once, then delay
    # Actually _trail_events uses swings list, we can call it and then delay
    events_up = _trail_events(swings_ltf, 1)  # long
    events_dn = _trail_events(swings_ltf, -1) # short
    # Apply delay_bars to events: shift confirmed_at_idx by delay_bars
    if delay_bars>0:
        events_up = [(idx+delay_bars, px) for idx,px in events_up]
        events_dn = [(idx+delay_bars, px) for idx,px in events_dn]
    for sig in ltf_sigs:
        bar=sig["bar"]
        if bar <= busy_until:
            continue
        bar_ts=candles_ltf[bar]["ts"]
        idx=bisect.bisect_right(starts, bar_ts)-1
        if idx<0:
            continue
        s_ts,e_ts,htf_dir,_,hentry,hsl = intervals[idx]
        if not (s_ts < bar_ts <= e_ts):
            continue
        if sig["dir"] != (1 if htf_dir==1 else -1):
            # sig dir is 1/-1 vs htf_dir
            # sig["dir"] is 1/-1, htf_dir same
            if sig["dir"] != htf_dir:
                continue
        if ext_stop_r>0:
            hrisk=abs(hentry - hsl)
            if hrisk>0:
                ext=(candles_ltf[bar]["close"] - hentry)*htf_dir/hrisk
                if ext > ext_stop_r:
                    continue
        # entry
        entry_px=candles_ltf[bar]["close"]
        sl_pivot=sig["swing_start_px"]
        if sl_buf_atr>0:
            atr=atr15[bar]
            if sig["dir"]==1:
                sl = sl_pivot - sl_buf_atr*atr
                if sl >= entry_px:
                    continue
                risk=entry_px - sl
            else:
                sl = sl_pivot + sl_buf_atr*atr
                if sl <= entry_px:
                    continue
                risk=sl - entry_px
        else:
            # shouldn't happen for v5
            continue
        if risk < 0.0005*entry_px:
            continue
        target = entry_px + (3.0*risk if sig["dir"]==1 else -3.0*risk)
        sl_cur=sl
        # pick events for this direction with delay already applied
        events = events_up if sig["dir"]==1 else events_dn
        # filter events to be > bar (as original does)
        # we keep as is, walk will check active_from <= j
        # Walk
        exit_idx=n-1
        exit_ts=candle_ts[-1]
        exit_px=candles_ltf[-1]["close"]
        outcome="open"
        best=entry_px  # for delay_r check
        ev_idx=0
        # find starting ev_idx where event idx > bar
        while ev_idx < len(events) and events[ev_idx][0] <= bar:
            ev_idx+=1
        # For fine walk, we handle both fine and non-fine; use fine if available
        if fine_ltf and fine_ts:
            # build events_ts for fine mapping: events with candle_ts
            # need to map event idx to ts
            events_ts=[]
            for e_idx, e_px in events:
                if e_idx < n:
                    ts=candle_ts[min(e_idx+1, n-1)]
                    if ts > bar_ts:
                        events_ts.append((ts, e_px))
            # fine start
            f_start=bisect.bisect_left(fine_ts, candle_ts[bar+1] if bar+1<n else candle_ts[bar]+1)
            # track best for delay_r
            fk=None
            for k in range(f_start, len(fine_ltf)):
                c=fine_ltf[k]
                hi=c["high"]; lo=c["low"]; op=c["open"]; ts=c["ts"]
                # update best for MFE tracking (for delay_r gate)
                if sig["dir"]==1:
                    best=max(best, hi)
                else:
                    best=min(best, lo)
                # check if delay_r not yet met: skip trail updates
                can_trail=True
                if delay_r>0:
                    cur_r=(best - entry_px)/risk if sig["dir"]==1 else (entry_px - best)/risk
                    if cur_r < delay_r:
                        can_trail=False
                # SL hit
                if sig["dir"]==1 and lo <= sl_cur:
                    exit_px=min(sl_cur, op) if op>sl_cur else sl_cur
                    exit_ts=ts
                    # outcome trail vs sl? if sl_cur != sl then trail else sl
                    outcome="trail" if sl_cur != sl else "sl"
                    fk=k
                    break
                if sig["dir"]==-1 and hi >= sl_cur:
                    exit_px=max(sl_cur, op) if op<sl_cur else sl_cur
                    exit_ts=ts
                    outcome="trail" if sl_cur != sl else "sl"
                    fk=k
                    break
                # target
                if sig["dir"]==1 and hi >= target:
                    exit_px=target
                    exit_ts=ts
                    outcome="target"
                    fk=k
                    break
                if sig["dir"]==-1 and lo <= target:
                    exit_px=target
                    exit_ts=ts
                    outcome="target"
                    fk=k
                    break
                # trail update after checks
                if can_trail:
                    while events_ts and events_ts[0][0] <= ts:
                        _, cand = events_ts.pop(0)
                        # only ratchet if beyond current sl and within bar extremes not needed for fine? but use sl_cur<cand<lo logic per original
                        if sig["dir"]==1 and sl_cur < cand < lo:
                            sl_cur=cand
                        if sig["dir"]==-1 and hi < cand < sl_cur:
                            sl_cur=cand
                if k==len(fine_ltf)-1 and outcome=="open":
                    exit_px=c["close"]
                    exit_ts=ts
            if outcome!="open":
                exit_idx=bisect.bisect_right(candle_ts, exit_ts)-1
            else:
                exit_idx=n-1
                exit_ts=candle_ts[-1]
                exit_px=candles_ltf[-1]["close"]
        else:
            # non-fine walk (should not happen as fine exists, but fallback)
            for j in range(bar+1, n):
                hi=candles_ltf[j]["high"]; lo=candles_ltf[j]["low"]; op=candles_ltf[j]["open"]
                if sig["dir"]==1:
                    best=max(best, hi)
                else:
                    best=min(best, lo)
                can_trail=True
                if delay_r>0:
                    cur_r=(best - entry_px)/risk if sig["dir"]==1 else (entry_px - best)/risk
                    if cur_r < delay_r:
                        can_trail=False
                if sig["dir"]==1 and lo <= sl_cur:
                    exit_idx=j; exit_ts=candle_ts[j]; exit_px=min(sl_cur, op); outcome="trail" if sl_cur!=sl else "sl"; break
                if sig["dir"]==-1 and hi >= sl_cur:
                    exit_idx=j; exit_ts=candle_ts[j]; exit_px=max(sl_cur, op); outcome="trail" if sl_cur!=sl else "sl"; break
                if sig["dir"]==1 and hi >= target:
                    exit_idx=j; exit_ts=candle_ts[j]; exit_px=target; outcome="target"; break
                if sig["dir"]==-1 and lo <= target:
                    exit_idx=j; exit_ts=candle_ts[j]; exit_px=target; outcome="target"; break
                if can_trail:
                    while ev_idx < len(events) and events[ev_idx][0] <= j:
                        _, cand = events[ev_idx]
                        if sig["dir"]==1 and sl_cur < cand < lo:
                            sl_cur=cand
                        if sig["dir"]==-1 and hi < cand < sl_cur:
                            sl_cur=cand
                        ev_idx+=1
        # compute R
        if sig["dir"]==1:
            r=(exit_px - entry_px)/risk
        else:
            r=(entry_px - exit_px)/risk
        ltf_trades.append({
            "trade_no": trade_no,
            "dir": "long" if sig["dir"]==1 else "short",
            "break_kind": sig["kind"],
            "entry_idx": bar,
            "entry_ts": bar_ts,
            "entry_date": candles_ltf[bar]["date"],
            "entry_price": entry_px,
            "sl": sl,
            "target": target,
            "exit_idx": exit_idx,
            "exit_ts": exit_ts,
            "exit_date": candles_ltf[exit_idx]["date"] if exit_idx<n else candles_ltf[-1]["date"],
            "exit_price": exit_px,
            "outcome": outcome,
            "r_multiple": round(r,4),
            "bars_held": exit_idx - bar,
        })
        trade_no+=1
        busy_until=exit_idx
    return {"ltf_trades": ltf_trades, "htf_trades": htf_trades, "intervals": intervals}

def eval_nested(nested):
    ltf=nested["ltf_trades"]
    _trade_costs(ltf,FEE,SLIP)
    stats=trade_stats(ltf)
    net=stats.get("net_total_r", sum(float(t["r_multiple"])-float(t.get("cost_r",0)) for t in ltf if t["outcome"]!="open"))
    # per-year net
    yearly=defaultdict(float)
    for t in ltf:
        if t["outcome"]=="open": continue
        yearly[t["exit_date"][:4]] += float(t["r_multiple"])-float(t.get("cost_r",0))
    return {"tr":stats["closed"],"win":stats["win_rate"],"base":stats["total_r"],"net":net,"pf":stats["profit_factor"],"dd":stats["max_drawdown_r"],"maxL":stats["max_consecutive_losses"],"yearly":dict(yearly),"stats":stats,"ltf":ltf}

# sweep configs
configs=[
    ("A current MB50 immediate (delay 0)", 0, 0.0),
    ("B delay 4 bars", 4, 0.0),
    ("B delay 8 bars", 8, 0.0),
    ("B delay 16 bars", 16, 0.0),
    ("B delay 32 bars", 32, 0.0),
    ("B delay +1R", 0, 1.0),
    ("B delay +2R", 0, 2.0),
    ("B delay 8 bars +1R", 8, 1.0),
    ("B delay 16 bars +1R", 16, 1.0),
]

print("=== Exp2 Delayed trail family (v5 base: ext-stop1.5 + buf0.25) FULL 442tr ===")
results=[]
for label, db, dr in configs:
    nested=simulate_htf_ltf_delayed(c1h,sw1h,c15,sw15,fine, htf_entry_break="flip", sl_buf_atr=0.25, ext_stop_r=1.5, delay_bars=db, delay_r=dr)
    r=eval_nested(nested)
    yearly=r["yearly"]
    print(f"{label:22s} | tr {r['tr']:3d} | win {r['win']:4.1f}% | base {r['base']:6.1f} | net {r['net']:6.1f} | PF {r['pf']:4.2f} | DD {r['dd']:5.1f} | maxL {r['maxL']:2d} | 2023 {yearly.get('2023',0):6.1f} | 2024 {yearly.get('2024',0):6.1f} | 2025 {yearly.get('2025',0):6.1f} | 2026 {yearly.get('2026',0):6.1f}")
    # also compute runners and giveback similar to Exp1 quickly
    # runners >=3R count
    runners=[t for t in r["ltf"] if float(t["r_multiple"])-float(t.get("cost_r",0)) >=3]
    print(f"  -> runners >=3R {len(runners)}  avg held {sum(t['bars_held'] for t in r['ltf'] if t['outcome']!='open')/max(1,len([t for t in r['ltf'] if t['outcome']!='open'])):.1f} bars")
    results.append((label, r))

# also test C vol trail k*ATR and D structure? For now just B; C/D will be separate engine but placeholder
print("\nExp2 note: C volatility trail k*ATR and D structure trail will be tested as separate variants (k=2.0/3.0 chandelier) in next harness — current harness covers delayed MB50 family only.")
