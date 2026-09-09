"""Exp: B2 vs Flip conditionality — walk-forward regime test
For each LTF decisive opportunity inside HTF, compute chop BEFORE signal and run BOTH HTF modes (Flip vs B2) on same interval to see crossover.
No threshold optimization, just bucket B2 R - Flip R per chop.
Also verify chop observation time is before signal (no lookahead) by using chop at bar-1.
"""
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
from src.btc.btc_routes import _compute_swings, _load_fine_1m, _trade_costs
from src.btc.btc_config import load_btc_df
from src.btc.engines.htf_ltf.v1_15m import simulate_htf_ltf_15m
from src.walker import FlowCandle
from collections import defaultdict
import bisect, math

FEE=0.05
SLIP=2.0

def load_window(tf):
    df = load_btc_df(tf)
    c=[]; f=[]
    for row in df.itertuples():
        date=row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        c.append({"date":date,"ts":int(row.ts),"open":float(row.open),"high":float(row.high),"low":float(row.low),"close":float(row.close),"volume":0,"oi":0})
        f.append(FlowCandle(date=date,open=float(row.open),high=float(row.high),low=float(row.low),close=float(row.close)))
    return c,f

c1h,f1h = load_window("1h")
c15,f15 = load_window("15m")
sw1h = _compute_swings(f1h,"continuous",min_bars=20)
sw15 = _compute_swings(f15,"continuous",min_bars=50)
t0=min(c1h[0]["ts"],c15[0]["ts"]); t1=max(c1h[-1]["ts"],c15[-1]["ts"])
fine=_load_fine_1m(t0,t1)
print(f"ready 1h {len(c1h)} 15m {len(c15)} fine {len(fine)}")

# Build chop series for 1h (lb14) as in v11
def chop_series(candles, lb=14):
    n=len(candles)
    tr=[0.0]*n
    for i in range(n):
        hi=float(candles[i]["high"]); lo=float(candles[i]["low"])
        if i==0: tr[i]=hi-lo
        else:
            pc=float(candles[i-1]["close"])
            tr[i]=max(hi-lo, abs(hi-pc), abs(lo-pc))
    chop=[50.0]*n
    for i in range(lb, n):
        tr_sum=sum(tr[i-lb+1:i+1])
        hi_max=max(float(candles[j]["high"]) for j in range(i-lb+1, i+1))
        lo_min=min(float(candles[j]["low"]) for j in range(i-lb+1, i+1))
        rang=hi_max-lo_min
        if rang>0 and tr_sum>0:
            try:
                chop[i]=100*math.log10(tr_sum/rang)/math.log10(lb)
            except: chop[i]=50.0
    return chop

chop1h=chop_series(c1h, lb=14)
c1h_ts=[c["ts"] for c in c1h]
c15_ts=[c["ts"] for c in c15]

# For each LTF bar, get chop BEFORE signal (bar-1) to ensure no lookahead
def chop_before_ltf_bar(ltf_bar_idx):
    ts=c15[ltf_bar_idx]["ts"]
    j=bisect.bisect_right(c1h_ts, ts)-1
    # use chop at j-1 to guarantee before signal bar
    if j-1>=0 and j-1 < len(chop1h):
        return chop1h[j-1]
    elif j>=0:
        return chop1h[j]
    return 50.0

# Build HTF intervals for both modes
from src.btc.engines.v7_timecap import simulate_btc_trades_v7

def intervals_for(htf_break):
    trades=simulate_btc_trades_v7(c1h, sw1h, entry_break=htf_break, sl_mode="swing", rr_target=3.0, trailing="off", breakeven_r=0.0, skip_first=True, fine=fine, cap_days=16)
    iv=[]
    for t in trades:
        if t["outcome"]=="open": continue
        iv.append((int(t["entry_ts"]), int(t["exit_ts"]), 1 if t["dir"]=="long" else -1, float(t["entry_price"]), float(t["sl"])))
    iv.sort(key=lambda x: x[0])
    return iv, trades

intervals_flip,_ = intervals_for("flip")
intervals_b2,_ = intervals_for("b2")
starts_flip=[s for s,_,_,_,_ in intervals_flip]
starts_b2=[s for s,_,_,_,_ in intervals_b2]

# Collect LTF decisive signals
from src.btc.btc_engine import _collect_signals
ltf_sigs=_collect_signals(sw15, "decisive", skip_first=True, selection="stream", candles=c15)
print(f"LTF decisive signals: {len(ltf_sigs)}")

# For each signal, compute chop bucket and test both HTF modes hypothetical R
# Instead of full trade simulation, we can approximate by checking if signal would be inside each HTF mode's window
# But to get actual R, we need to run LTF trade to completion and see R under each HTF filter.
# Simpler: run full v5 twice (HTF flip vs HTF b2) and then for each LTF trade, attribute its R to chop bucket of its entry bar (chop before).
# Then we can compute per bucket: Flip R total vs B2 R total on same bucket, but not same interval.

# First get full runs for both HTF modes
nested_flip=simulate_htf_ltf_15m(c1h, sw1h, c15, sw15, fine, htf_entry_break="flip", ltf_entry_break="decisive", sl_mode="swing", rr_target=3.0, ltf_trailing="swing", htf_breakeven=0, ltf_breakeven=0, htf_cap_days=16, ext_stop_r=1.5, sl_buf_atr=0.25)
nested_b2=simulate_htf_ltf_15m(c1h, sw1h, c15, sw15, fine, htf_entry_break="b2", ltf_entry_break="decisive", sl_mode="swing", rr_target=3.0, ltf_trailing="swing", htf_breakeven=0, ltf_breakeven=0, htf_cap_days=16, ext_stop_r=1.5, sl_buf_atr=0.25)
ltf_flip=nested_flip["ltf_trades"]
ltf_b2=nested_b2["ltf_trades"]
for lst in [ltf_flip, ltf_b2]:
    _trade_costs(lst, FEE, SLIP)

# Bucket by chop before entry
def bucket_chop(ch):
    if ch <38.2: return "LOW <38.2"
    if ch <61.8: return "MED 38.2-61.8"
    if ch <75: return "HIGH 61.8-75"
    return "EXTREME >75"

buckets_flip=defaultdict(list)
buckets_b2=defaultdict(list)
for tr in ltf_flip:
    if tr["outcome"]=="open": continue
    idx=tr["entry_idx"]
    ch=chop_before_ltf_bar(idx)
    b=bucket_chop(ch)
    r=float(tr["r_multiple"])-float(tr.get("cost_r",0))
    buckets_flip[b].append(r)
for tr in ltf_b2:
    if tr["outcome"]=="open": continue
    idx=tr["entry_idx"]
    ch=chop_before_ltf_bar(idx)
    b=bucket_chop(ch)
    r=float(tr["r_multiple"])-float(tr.get("cost_r",0))
    buckets_b2[b].append(r)

print("\n=== B2 vs Flip per chop bucket (both modes on same 1h window logic, chop BEFORE signal, no lookahead) ===")
print("Bucket            | Flip tr | Flip net | B2 tr | B2 net | B2-Flip | Flip win% | B2 win%")
for b in ["LOW <38.2","MED 38.2-61.8","HIGH 61.8-75","EXTREME >75"]:
    rf=buckets_flip[b]; rb=buckets_b2[b]
    net_f=sum(rf) if rf else 0
    net_b=sum(rb) if rb else 0
    wr_f=sum(1 for x in rf if x>0)/len(rf)*100 if rf else 0
    wr_b=sum(1 for x in rb if x>0)/len(rb)*100 if rb else 0
    diff=net_b - net_f
    print(f"{b:17s} | {len(rf):7d} | {net_f:8.1f} | {len(rb):5d} | {net_b:6.1f} | {diff:+7.1f} | {wr_f:6.1f}% | {wr_b:6.1f}%")

# Also per year walk-forward: train 2023 test 2024 etc with fixed threshold 61.8
print("\n=== Walk-forward: fixed chop 61.8 rule (HIGH->B2 else Flip) vs pure ===")
# Our conditional v11 b2_vs_flip_chop is exactly that rule, already tested: 446 +197 net vs 442 +168 vs 558 +122
# Let's compute walk-forward splits: train on prior years, test on next year with same rule
# We can compute per year net for each mode from earlier runs
from collections import defaultdict
def per_year(trades):
    y=defaultdict(float)
    for t in trades:
        if t["outcome"]=="open": continue
        y[t["exit_date"][:4]] += float(t["r_multiple"])-float(t.get("cost_r",0))
    return y
y_flip=per_year(ltf_flip)
y_b2=per_year(ltf_b2)
# Conditional b2_vs_flip_chop per year from earlier test (we can recompute via v11)
from src.btc.engines.htf_ltf.v11_conditional_htf import simulate_htf_ltf_conditional
nested_cond=simulate_htf_ltf_conditional(c1h,sw1h,c15,sw15,fine, sl_buf_atr=0.25, ext_stop_r=1.5, chop_thresh=61.8, mode="b2_vs_flip_chop")
ltf_cond=nested_cond["ltf_trades"]
_trade_costs(ltf_cond, FEE, SLIP)
y_cond=per_year(ltf_cond)
print(f"Year | Flip | B2 | Cond b2_vs_flip | Decisive | Best")
for y in ["2023","2024","2025","2026"]:
    print(f"{y} | {y_flip.get(y,0):5.1f} | {y_b2.get(y,0):5.1f} | {y_cond.get(y,0):5.1f} |")

# Verify no lookahead: show 20 boundary cases where chop 60-63 around threshold
print("\n=== 20 boundary cases chop 60-63 around 61.8 (signal_time, chop_before, mode_selected, Flip R if any, B2 R if any) ===")
# For each LTF signal near threshold, show both modes hypothetical
# Find signals where chop 60-63
filtered=[]
for sig in ltf_sigs:
    idx=sig["bar"]
    ch=chop_before_ltf_bar(idx)
    if 60 <= ch <= 63:
        bar_ts=c15[idx]["ts"]
        # check if signal would be taken in Flip vs B2
        # Find interval containing bar_ts for each mode
        def in_interval(intervals, starts, bar_ts, sig_dir):
            j=bisect.bisect_right(starts, bar_ts)-1
            if j<0: return False, None
            s,e,d,pe,psl=intervals[j]
            if not (s < bar_ts <= e): return False, None
            if sig["dir"] != d: return False, None
            # ext_stop check
            hrisk=abs(pe-psl)
            if hrisk>0:
                ext=(float(c15[idx]["close"])-pe)*d/hrisk
                if ext > 1.5: return False, None
            return True, (s,e,d)
        in_flip,_ = in_interval(intervals_flip, starts_flip, bar_ts, sig["dir"])
        in_b2,_ = in_interval(intervals_b2, starts_b2, bar_ts, sig["dir"])
        # Also get eventual R if trade taken (find matching trade by entry_idx)
        r_flip=next((float(t["r_multiple"])-float(t.get("cost_r",0)) for t in ltf_flip if t["entry_idx"]==idx), None)
        r_b2=next((float(t["r_multiple"])-float(t.get("cost_r",0)) for t in ltf_b2 if t["entry_idx"]==idx), None)
        filtered.append((bar_ts, ch, sig["dir"], in_flip, in_b2, r_flip, r_b2, c15[idx]["date"]))
        if len(filtered)>=20:
            break
for ts,ch,dir_,in_f,in_b,rf,rb,date in filtered:
    print(f"{date} chop {ch:.1f} dir {'long' if dir_==1 else 'short'} in_flip {in_f} in_b2 {in_b} R_flip {rf} R_b2 {rb}")

print("\nDone B2 vs Flip conditionality — check if HIGH chop B2 genuinely better than Flip per bucket, not just total.")
