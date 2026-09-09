"""Exp4 — Volatility-state diagnostic (diagnose only, no gate).
Buckets trades by ATR% and Chop on entry bar.
Uses v5 FULL 442tr, 15m entry bar's ATR14/close and 1h Chop(14) at entry."""
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
from src.btc.btc_routes import _compute_swings, _load_fine_1m, _trade_costs
from src.btc.btc_engine import trade_stats
from src.btc.btc_config import load_btc_df
from src.btc.engines.htf_ltf.v1_15m import simulate_htf_ltf_15m
from src.walker import FlowCandle
from collections import defaultdict
import bisect

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

c1h,f1h,_ = load_window("1h")
c15,f15,df15 = load_window("15m")
sw1h = _compute_swings(f1h,"continuous",min_bars=20)
sw15 = _compute_swings(f15,"continuous",min_bars=50)
t0=min(c1h[0]["ts"],c15[0]["ts"]); t1=max(c1h[-1]["ts"],c15[-1]["ts"])
fine=_load_fine_1m(t0,t1)

nested = simulate_htf_ltf_15m(c1h,sw1h,c15,sw15,fine, htf_entry_break="flip", ltf_entry_break="decisive", sl_mode="swing", rr_target=3.0, ltf_trailing="swing", htf_breakeven=0, ltf_breakeven=0, htf_cap_days=16, ext_stop_r=1.5, sl_buf_atr=0.25)
ltf=nested["ltf_trades"]
_trade_costs(ltf,FEE,SLIP)

# Build ATR14 per bar on 15m
n=len(c15)
tr_l=[0.0]*n
for i in range(n):
    hi=c15[i]["high"]; lo=c15[i]["low"]
    if i==0:
        tr_l[i]=hi-lo
    else:
        pc=c15[i-1]["close"]
        tr_l[i]=max(hi-lo, abs(hi-pc), abs(lo-pc))
atr=[0.0]*n
for i in range(n):
    lo_i=max(0,i-13)
    atr[i]=sum(tr_l[lo_i:i+1])/(i-lo_i+1)
atr_pct=[atr[i]/c15[i]["close"]*100 if c15[i]["close"] else 0 for i in range(n)]

# Chop on 1h and map to 15m entry via ts
# Compute chop similarly to v4_chop.py
def chop_series(candles, lb=14):
    n=len(candles)
    chop=[50.0]*n
    for i in range(lb, n):
        tr_sum=sum(tr_l[i-lb+1:i+1]) if 'tr_l' in locals() else 0
        # recompute TR for 1h separately
        # simpler: compute 1h TR
        pass
    return chop

# Instead compute 1h chop correctly
# Build 1h TR
tr1h=[0.0]*len(c1h)
for i in range(len(c1h)):
    hi=c1h[i]["high"]; lo=c1h[i]["low"]
    if i==0:
        tr1h[i]=hi-lo
    else:
        pc=c1h[i-1]["close"]
        tr1h[i]=max(hi-lo, abs(hi-pc), abs(lo-pc))
chop1h=[50.0]*len(c1h)
lb=14
for i in range(lb, len(c1h)):
    tr_sum=sum(tr1h[i-lb+1:i+1])
    hi_max=max(c1h[j]["high"] for j in range(i-lb+1, i+1))
    lo_min=min(c1h[j]["low"] for j in range(i-lb+1, i+1))
    rang=hi_max - lo_min
    if rang>0 and tr_sum>0:
        import math
        chop1h[i]=100*math.log10(tr_sum/rang)/math.log10(lb)
    else:
        chop1h[i]=50.0
c1h_ts=[c["ts"] for c in c1h]
# For each LTF trade, find 1h chop at entry bar (bisect)
def atr_bucket(p):
    if p < 0.35: return "LOW vol (<0.35% ATR)"
    if p < 0.65: return "MED vol (0.35-0.65%)"
    return "HIGH vol (>0.65%)"
def chop_bucket(ch):
    if ch < 38.2: return "LOW chop (<38.2) trending"
    if ch < 61.8: return "MED chop (38.2-61.8)"
    return "HIGH chop (>61.8) choppy"

buckets_atr=defaultdict(list)
buckets_chop=defaultdict(list)

for tr in ltf:
    if tr["outcome"]=="open": continue
    idx=tr["entry_idx"]
    # ATR bucket
    p=atr_pct[idx]
    b=atr_bucket(p)
    buckets_atr[b].append(tr)
    # Chop bucket: find 1h bar containing entry_ts
    ets=tr["entry_ts"]
    j=bisect.bisect_right(c1h_ts, ets)-1
    ch=chop1h[max(0,j)]
    cb=chop_bucket(ch)
    buckets_chop[cb].append(tr)

def stats_for(bucket_trades):
    if not bucket_trades:
        return {"tr":0,"win":0,"net":0,"avg":0,"pf":0,"runner":0}
    nets=[float(t["r_multiple"])-float(t.get("cost_r",0)) for t in bucket_trades]
    wins=sum(1 for x in nets if x>0)
    net=sum(nets)
    # pf
    pos=sum(x for x in nets if x>0); neg=abs(sum(x for x in nets if x<0))
    pf=pos/neg if neg else 0
    runners=sum(1 for x in nets if x>=3)
    return {"tr":len(bucket_trades),"win":wins/len(bucket_trades)*100,"net":net,"avg":net/len(bucket_trades),"pf":pf,"runner":runners/len(bucket_trades)*100}

print(f"Exp4 — Volatility diagnostic on v5 FULL 442tr")
print(f"ATR% (15m) at entry: LOW <0.35% / MED 0.35-0.65% / HIGH >0.65%")
for k in ["LOW vol (<0.35% ATR)","MED vol (0.35-0.65%)","HIGH vol (>0.65%)"]:
    s=stats_for(buckets_atr[k])
    print(f"  {k:22s} | tr {s['tr']:3d} | win {s['win']:4.1f}% | net {s['net']:+6.1f} | avg {s['avg']:+5.2f} | PF {s['pf']:4.2f} | runner {s['runner']:4.1f}%")

print(f"\nChop(14) 1h at entry: LOW <38.2 trending / MED / HIGH >61.8 choppy")
for k in ["LOW chop (<38.2) trending","MED chop (38.2-61.8)","HIGH chop (>61.8) choppy"]:
    s=stats_for(buckets_chop[k])
    print(f"  {k:24s} | tr {s['tr']:3d} | win {s['win']:4.1f}% | net {s['net']:+6.1f} | avg {s['avg']:+5.2f} | PF {s['pf']:4.2f} | runner {s['runner']:4.1f}%")

# Also per-year x vol to see 2023 chop effect
print("\nPer-year x Chop HIGH (>61.8) — 2023 chop bleed check:")
for y in ["2023","2024","2025","2026"]:
    y_tr=[t for t in ltf if t["exit_date"][:4]==y and t["outcome"]!="open"]
    # high chop subset
    high=[t for t in y_tr if chop_bucket(chop1h[max(0,bisect.bisect_right(c1h_ts, t["entry_ts"])-1)])=="HIGH chop (>61.8) choppy"]
    s=stats_for(high)
    print(f"  {y} HIGH chop: {s['tr']:3d} tr net {s['net']:+6.1f} win {s['win']:4.1f}% runner {s['runner']:4.1f}%")

print("\nExp4 note: LOW vol <0.35% and HIGH chop >61.8 are opposite ends — expect LOW vol + HIGH chop = worst.")
