"""Interval-level B2 vs Flip CSV: chop, ATR, Δchop, B2 R, Flip R, B2-Flip, MFE, MAE, exit, runner
For each HTF interval (1h Flip cap16 vs B2 cap16), compute chop_before (at interval start-1, no lookahead), ATR% before, then aggregate LTF decisive trades inside interval.
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

# chop series 1h lb14
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
            try: chop[i]=100*math.log10(tr_sum/rang)/math.log10(lb)
            except: chop[i]=50.0
    return chop

chop1h=chop_series(c1h, lb=14)
c1h_ts=[c["ts"] for c in c1h]
# ATR% 15m
tr15=[0.0]*len(c15)
for i in range(len(c15)):
    hi=float(c15[i]["high"]); lo=float(c15[i]["low"])
    if i==0: tr15[i]=hi-lo
    else:
        pc=float(c15[i-1]["close"])
        tr15[i]=max(hi-lo, abs(hi-pc), abs(lo-pc))
atr15=[0.0]*len(c15)
for i in range(len(c15)):
    lo_i=max(0,i-13)
    atr15[i]=sum(tr15[lo_i:i+1])/(i-lo_i+1)
atr_pct=[atr15[i]/float(c15[i]["close"])*100 if float(c15[i]["close"])!=0 else 0 for i in range(len(c15))]
c15_ts=[c["ts"] for c in c15]

# Run both HTF modes full
nested_flip=simulate_htf_ltf_15m(c1h, sw1h, c15, sw15, fine, htf_entry_break="flip", ltf_entry_break="decisive", sl_mode="swing", rr_target=3.0, ltf_trailing="swing", htf_breakeven=0, ltf_breakeven=0, htf_cap_days=16, ext_stop_r=1.5, sl_buf_atr=0.25)
nested_b2=simulate_htf_ltf_15m(c1h, sw1h, c15, sw15, fine, htf_entry_break="b2", ltf_entry_break="decisive", sl_mode="swing", rr_target=3.0, ltf_trailing="swing", htf_breakeven=0, ltf_breakeven=0, htf_cap_days=16, ext_stop_r=1.5, sl_buf_atr=0.25)
ltf_flip=nested_flip["ltf_trades"]
ltf_b2=nested_b2["ltf_trades"]
for lst in [ltf_flip, ltf_b2]:
    _trade_costs(lst, FEE, SLIP)
# Build HTF intervals for both
from src.btc.engines.v7_timecap import simulate_btc_trades_v7
def intervals_for(br):
    tr=simulate_btc_trades_v7(c1h, sw1h, entry_break=br, sl_mode="swing", rr_target=3.0, trailing="off", breakeven_r=0.0, skip_first=True, fine=fine, cap_days=16)
    iv=[]
    for t in tr:
        if t["outcome"]=="open": continue
        iv.append((int(t["entry_ts"]), int(t["exit_ts"]), 1 if t["dir"]=="long" else -1, float(t["entry_price"]), float(t["sl"]), t["trade_no"]))
    iv.sort(key=lambda x: x[0])
    return iv
iv_flip=intervals_for("flip")
iv_b2=intervals_for("b2")
print(f"HTF intervals flip {len(iv_flip)} b2 {len(iv_b2)}")

# For each LTF trade, we have entry_idx, need MFE/MAE via fine as in Exp1 (quick approx via trade's r vs mfe not available, compute via fine)
fine_ts=[c["ts"] for c in fine] if fine else []
def compute_mfe_mae(tr):
    idx=tr["entry_idx"]
    entry=tr["entry_price"]
    risk=abs(entry - tr["sl"])
    if risk<=0: return 0,0
    dir_ = 1 if tr["dir"]=="long" else -1
    entry_ts=tr["entry_ts"]; exit_ts=tr["exit_ts"]
    f_start=bisect.bisect_left(fine_ts, entry_ts+1)
    f_end=bisect.bisect_right(fine_ts, exit_ts)
    window=fine[f_start:f_end] if fine else []
    highs=[x["high"] for x in window] if window else []
    lows=[x["low"] for x in window] if window else []
    if not highs:
        # fallback to 15m
        highs=[c15[i]["high"] for i in range(idx+1, tr["exit_idx"]+1)]
        lows=[c15[i]["low"] for i in range(idx+1, tr["exit_idx"]+1)]
    if not highs:
        return 0,0
    if dir_==1:
        mfe_px=max(highs)
        mae_px=min(lows)
        mfe=(mfe_px-entry)/risk
        mae=(entry-mae_px)/risk
    else:
        mfe_px=min(lows)
        mae_px=max(highs)
        mfe=(entry-mfe_px)/risk
        mae=(mae_px-entry)/risk
    return mfe, mae

# Build per HTF interval aggregation
# For FLIP intervals
import csv
out_path=Path(r"C:\Users\Pravin\AppData\Local\Temp\opencode\b2_flip_interval.csv")
with open(out_path, "w", newline="", encoding="utf-8") as f:
    w=csv.writer(f)
    w.writerow(["htf_interval_idx","htf_mode","start_time","end_time","chop_before","atr_pct_before","chop_change","chop_slope3","chop_slope5","htf_trades_in_interval","ltf_trades","ltf_R","ltf_MFE","ltf_MAE","winner","delta_R"])
    # For this CSV we will do per HTF interval for FLIP mode, with B2 counterpart R on same calendar interval
    # For each FLIP interval, find overlapping B2 interval(s) that cover same time? Instead do per FLIP interval, compute B2 R in same calendar window (start to end)
    # Build maps for quick lookup of LTF trades per interval
    # For FLIP: bucket LTF trades by which FLIP interval they fall into
    # For B2: similarly bucket
    # To compare same interval, we need to define HTF interval as time window, not trade-based
    # Simpler: For each FLIP interval, compute B2 R as sum of B2 LTF trades whose entry_ts inside same FLIP interval window
    # This gives direct comparison per FLIP window
    for idx_iv, (s,e,d,pe,psl,tn) in enumerate(iv_flip):
        # chop before at s (HTF interval start)
        j=bisect.bisect_right(c1h_ts, s)-1
        # chop at j-1 for no lookahead
        if j-1>=0:
            chop_before=chop1h[j-1]
            chop_prev2=chop1h[max(0,j-3)] if j-3>=0 else chop_before
            chop_prev5=chop1h[max(0,j-6)] if j-6>=0 else chop_before
        else:
            chop_before=50.0
            chop_prev2=50.0
            chop_prev5=50.0
        chop_change=chop_before - chop1h[max(0,j-2)] if j-2>=0 else 0
        chop_slope3=chop_before - chop_prev2
        chop_slope5=chop_before - chop_prev5
        # ATR% at LTF time near s (find 15m bar containing s)
        k15=bisect.bisect_right(c15_ts, s)-1
        atrp=atr_pct[max(0,k15)] if k15>=0 else 0
        # LTF trades inside this FLIP interval
        ltf_in_flip=[t for t in ltf_flip if s < int(t["entry_ts"]) <= e]
        # B2 trades inside same calendar window (s to e) even though B2 HTF window may differ
        ltf_in_b2_same_window=[t for t in ltf_b2 if s < int(t["entry_ts"]) <= e]
        # compute R, MFE, MAE
        def agg(trades):
            if not trades:
                return 0,0,0,0,0
            rs=[float(t["r_multiple"])-float(t.get("cost_r",0)) for t in trades]
            net=sum(rs)
            # MFE/MAE avg for those trades
            mfes=[]
            maes=[]
            for t in trades:
                mfe,mae=compute_mfe_mae(t)
                mfes.append(mfe)
                maes.append(mae)
            avg_mfe=sum(mfes)/len(mfes) if mfes else 0
            avg_mae=sum(maes)/len(maes) if maes else 0
            wins=sum(1 for x in rs if x>0)
            runners=sum(1 for x in rs if x>=3)
            return net, sum(mfes)/len(mfes) if mfes else 0, sum(maes)/len(maes) if maes else 0, wins, runners
        net_f, mfe_f, mae_f, wins_f, run_f = agg(ltf_in_flip)
        net_b, mfe_b, mae_b, wins_b, run_b = agg(ltf_in_b2_same_window)
        delta=net_b - net_f
        winner="B2" if delta>0 else "Flip" if delta<0 else "Tie"
        w.writerow([idx_iv, "Flip", c1h[bisect.bisect_right(c1h_ts, s)-1]["date"] if bisect.bisect_right(c1h_ts, s)-1 >=0 else "", c1h[bisect.bisect_right(c1h_ts, e)-1]["date"] if bisect.bisect_right(c1h_ts, e)-1>=0 else "", f"{chop_before:.1f}", f"{atrp:.3f}", f"{chop_change:.1f}", f"{chop_slope3:.1f}", f"{chop_slope5:.1f}", len(ltf_in_flip), len(ltf_in_b2_same_window), f"{net_f:.2f}", f"{net_b:.2f}", f"{delta:.2f}", winner])
print(f"CSV written to {out_path} with {len(iv_flip)} FLIP intervals")

# Also bucket analysis like before but per HTF interval, not per LTF trade
# Quick bucket summary for interval-level delta
from collections import defaultdict
buckets=defaultdict(list)
for row in open(out_path, encoding="utf-8").read().splitlines()[1:]:
    parts=row.split(",")
    # chop_before is 4th column?
    # Re-read via csv
    pass
# Instead compute bucket stats directly
bucket_stats=defaultdict(list)
for idx_iv, (s,e,d,pe,psl,tn) in enumerate(iv_flip):
    j=bisect.bisect_right(c1h_ts, s)-1
    chop_before=chop1h[j-1] if j-1>=0 else 50.0
    # bucket
    if chop_before <38.2: b="LOW <38.2"
    elif chop_before <61.8: b="MED 38.2-61.8"
    elif chop_before <75: b="HIGH 61.8-75"
    else: b="EXTREME >75"
    # compute net_f and net_b for this interval as above (reuse)
    ltf_in_flip=[t for t in ltf_flip if s < int(t["entry_ts"]) <= e]
    ltf_in_b2=[t for t in ltf_b2 if s < int(t["entry_ts"]) <= e]
    net_f=sum(float(t["r_multiple"])-float(t.get("cost_r",0)) for t in ltf_in_flip)
    net_b=sum(float(t["r_multiple"])-float(t.get("cost_r",0)) for t in ltf_in_b2)
    bucket_stats[b].append((net_f, net_b, net_b-net_f))

print("\n=== Interval-level B2-Flip per HTF interval (FLIP intervals as base calendar) ===")
for b in ["LOW <38.2","MED 38.2-61.8","HIGH 61.8-75","EXTREME >75"]:
    lst=bucket_stats[b]
    if not lst: continue
    avg_f=sum(x[0] for x in lst)/len(lst)
    avg_b=sum(x[1] for x in lst)/len(lst)
    avg_delta=sum(x[2] for x in lst)/len(lst)
    win_b=sum(1 for x in lst if x[1]>x[0])
    print(f"{b:15s} | intervals {len(lst):3d} | avg Flip {avg_f:6.2f} | avg B2 {avg_b:6.2f} | avg delta {avg_delta:+6.2f} | B2 wins {win_b}/{len(lst)} ({win_b/len(lst)*100:.1f}%)")

# Same-interval paired where both have trades
paired=[]
for s,e,d,pe,psl,tn in iv_flip:
    # find overlapping B2 interval that contains s? Instead find B2 interval that overlaps time window
    # For paired, require both modes have at least 1 LTF trade in same FLIP window
    ltf_f=[t for t in ltf_flip if s < int(t["entry_ts"]) <= e]
    ltf_b=[t for t in ltf_b2 if s < int(t["entry_ts"]) <= e]
    if ltf_f and ltf_b:
        net_f=sum(float(t["r_multiple"])-float(t.get("cost_r",0)) for t in ltf_f)
        net_b=sum(float(t["r_multiple"])-float(t.get("cost_r",0)) for t in ltf_b)
        j=bisect.bisect_right(c1h_ts, s)-1
        chop_before=chop1h[j-1] if j-1>=0 else 50.0
        paired.append((chop_before, net_f, net_b, net_b-net_f))
print(f"\nPaired intervals where both Flip and B2 have trades in same FLIP window: {len(paired)}/{len(iv_flip)}")
if paired:
    # bucket paired delta
    from collections import defaultdict as dd2
    b2_dd=dd2(list)
    for ch,nf,nb,d in paired:
        b="LOW <38.2" if ch<38.2 else "MED 38.2-61.8" if ch<61.8 else "HIGH 61.8-75" if ch<75 else "EXTREME >75"
        b2_dd[b].append(d)
    for b in ["LOW <38.2","MED 38.2-61.8","HIGH 61.8-75"]:
        lst=b2_dd[b]
        if lst:
            print(f" Paired {b}: n={len(lst)} avg delta {sum(lst)/len(lst):+.2f} B2 wins {sum(1 for x in lst if x>0)}/{len(lst)}")

print("\nDone interval CSV")
