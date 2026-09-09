"""Exp1 Continuous crossover: B2 R - Flip R vs continuous chop
Don't bucket 38.2/61.8 only, use 10 buckets 0-20,20-30,... to see systematic relationship.
Also continuous per signal: chop_before, ATR%, B2 R, Flip R, delta.
"""
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
from src.btc.btc_routes import _compute_swings, _load_fine_1m, _trade_costs
from src.btc.btc_config import load_btc_df
from src.btc.engines.htf_ltf.v1_15m import simulate_htf_ltf_15m
from src.walker import FlowCandle
import bisect, math
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
    return c,f

c1h,f1h = load_window("1h")
c15,f15 = load_window("15m")
sw1h = _compute_swings(f1h,"continuous",min_bars=20)
sw15 = _compute_swings(f15,"continuous",min_bars=50)
t0=min(c1h[0]["ts"],c15[0]["ts"]); t1=max(c1h[-1]["ts"],c15[-1]["ts"])
fine=_load_fine_1m(t0,t1)
print(f"ready 1h {len(c1h)} 15m {len(c15)} fine {len(fine)}")

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
c15_ts=[c["ts"] for c in c15]
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
atr_pct=[atr15[i]/float(c15[i]["close"])*100 for i in range(len(c15))]

# Run both modes full
nested_flip=simulate_htf_ltf_15m(c1h, sw1h, c15, sw15, fine, htf_entry_break="flip", ltf_entry_break="decisive", sl_mode="swing", rr_target=3.0, ltf_trailing="swing", htf_breakeven=0, ltf_breakeven=0, htf_cap_days=16, ext_stop_r=1.5, sl_buf_atr=0.25)
nested_b2=simulate_htf_ltf_15m(c1h, sw1h, c15, sw15, fine, htf_entry_break="b2", ltf_entry_break="decisive", sl_mode="swing", rr_target=3.0, ltf_trailing="swing", htf_breakeven=0, ltf_breakeven=0, htf_cap_days=16, ext_stop_r=1.5, sl_buf_atr=0.25)
ltf_flip=nested_flip["ltf_trades"]
ltf_b2=nested_b2["ltf_trades"]
for lst in [ltf_flip, ltf_b2]:
    _trade_costs(lst, FEE, SLIP)

# Map entry_idx -> trade net for each mode
map_flip={t["entry_idx"]: float(t["r_multiple"])-float(t.get("cost_r",0)) for t in ltf_flip if t["outcome"]!="open"}
map_b2={t["entry_idx"]: float(t["r_multiple"])-float(t.get("cost_r",0)) for t in ltf_b2 if t["outcome"]!="open"}
# Also need chop before per signal: use LTF decisive signals list to get all signals
from src.btc.btc_engine import _collect_signals
ltf_sigs=_collect_signals(sw15, "decisive", skip_first=True, selection="stream", candles=c15)
print(f"LTF decisive signals {len(ltf_sigs)} flip trades {len(ltf_flip)} b2 trades {len(ltf_b2)}")

# For each signal, get chop_before (at bar-1) and atr
import csv, pathlib
out_path=Path(r"C:\Users\Pravin\AppData\Local\Temp\opencode\continuous_crossover.csv")
with open(out_path, "w", newline="", encoding="utf-8") as f:
    w=csv.writer(f)
    w.writerow(["signal_time","chop_before","atr_pct","flip_R","b2_R","delta_B2_Flip","in_flip","in_b2"])
    for sig in ltf_sigs:
        idx=sig["bar"]
        # chop before at bar-1
        ts=c15[idx]["ts"]
        j=bisect.bisect_right(c1h_ts, ts)-1
        chop_before=chop1h[j-1] if j-1>=0 else 50.0
        atrp=atr_pct[idx] if idx < len(atr_pct) else 0
        flip_r=map_flip.get(idx)
        b2_r=map_b2.get(idx)
        in_flip=idx in map_flip
        in_b2=idx in map_b2
        # delta only where both have trades? but also where one has and other not, delta is not defined
        # For continuous analysis, we want per signal delta where both modes have comparable signal (same interval)
        # If signal not traded in one mode due to HTF window filter, then that mode's R is None
        delta=None
        if flip_r is not None and b2_r is not None:
            delta=b2_r - flip_r
        elif flip_r is not None and b2_r is None:
            # B2 would have skipped due to HTF window, treat as 0? But better to mark as not comparable
            delta=None
        elif flip_r is None and b2_r is not None:
            delta=None
        w.writerow([c15[idx]["date"], f"{chop_before:.2f}", f"{atrp:.3f}", flip_r if flip_r is not None else "", b2_r if b2_r is not None else "", delta if delta is not None else "", in_flip, in_b2])

print(f"CSV written {out_path}")

# Now bucket analysis continuous
# Read back and bucket by chop
import csv as csv2
buckets=defaultdict(list)
buckets_counts=defaultdict(lambda: {"flip_trades":0,"b2_trades":0,"flip_net":0,"b2_net":0})
with open(out_path, encoding="utf-8") as f:
    rdr=csv2.DictReader(f)
    for row in rdr:
        try:
            ch=float(row["chop_before"])
        except: continue
        # bucket 10
        if ch <20: b="0-20"
        elif ch <30: b="20-30"
        elif ch <40: b="30-40"
        elif ch <50: b="40-50"
        elif ch <55: b="50-55"
        elif ch <60: b="55-60"
        elif ch <62: b="60-62"
        elif ch <65: b="62-65"
        elif ch <70: b="65-70"
        elif ch <75: b="70-75"
        else: b="75+"
        # get Rs
        flip_r=row["flip_R"]
        b2_r=row["b2_R"]
        if flip_r != "":
            try:
                rf=float(flip_r)
                buckets[b].append(("flip", rf))
                buckets_counts[b]["flip_trades"]+=1
                buckets_counts[b]["flip_net"]+=rf
            except: pass
        if b2_r != "":
            try:
                rb=float(b2_r)
                buckets[b].append(("b2", rb))
                buckets_counts[b]["b2_trades"]+=1
                buckets_counts[b]["b2_net"]+=rb
            except: pass

print("\n=== Continuous crossover — 10 chop buckets (per signal, where trade occurred) ===")
print("Bucket | Flip tr | Flip net | B2 tr | B2 net | B2-Flip net | Flip PF | B2 PF | Flip avg | B2 avg")
for b in ["0-20","20-30","30-40","40-50","50-55","55-60","60-62","62-65","65-70","70-75","75+"]:
    cnt=buckets_counts[b]
    flip_tr=cnt["flip_trades"]
    b2_tr=cnt["b2_trades"]
    flip_net=cnt["flip_net"]
    b2_net=cnt["b2_net"]
    diff=b2_net - flip_net
    # compute PF and avg per bucket
    # need to collect per bucket flip/b2 separately
    flip_rs=[v for k,v in buckets[b] if k=="flip"]
    b2_rs=[v for k,v in buckets[b] if k=="b2"]
    def pf(lst):
        pos=sum(x for x in lst if x>0)
        neg=abs(sum(x for x in lst if x<0))
        return pos/neg if neg else 0
    flip_pf=pf(flip_rs)
    b2_pf=pf(b2_rs)
    flip_avg=sum(flip_rs)/len(flip_rs) if flip_rs else 0
    b2_avg=sum(b2_rs)/len(b2_rs) if b2_rs else 0
    print(f"{b:7s} | {flip_tr:7d} | {flip_net:8.1f} | {b2_tr:5d} | {b2_net:6.1f} | {diff:+8.1f} | {flip_pf:5.2f} | {b2_pf:5.2f} | {flip_avg:5.2f} | {b2_avg:5.2f}")

# Also per signal delta where both have trades (paired)
paired=[]
with open(out_path, encoding="utf-8") as f:
    rdr=csv2.DictReader(f)
    for row in rdr:
        if row["flip_R"] != "" and row["b2_R"] != "":
            try:
                ch=float(row["chop_before"])
                delta=float(row["delta_B2_Flip"])
                paired.append((ch, delta))
            except: pass
print(f"\nPaired signals where both Flip and B2 traded same LTF signal: {len(paired)} of {len(ltf_sigs)}")
if paired:
    # bucket paired delta by chop
    from collections import defaultdict as dd
    pbuckets=dd(list)
    for ch,d in paired:
        if ch <30: b="20-30"
        elif ch <40: b="30-40"
        elif ch <50: b="40-50"
        elif ch <60: b="55-60"
        elif ch <65: b="62-65"
        else: b="65+"
        pbuckets[b].append(d)
    print("Paired delta (B2-Flip) per chop where both traded same signal:")
    for b in ["20-30","30-40","40-50","55-60","62-65","65+"]:
        lst=pbuckets[b]
        if lst:
            avg=sum(lst)/len(lst)
            med=sorted(lst)[len(lst)//2]
            print(f" {b:7s} n={len(lst):3d} avg delta {avg:+5.2f} med {med:+5.2f} B2 wins {sum(1 for x in lst if x>0)}/{len(lst)}")

print("\nDone continuous crossover")
