"""V5.4 Partial exit — post-hoc via Exp1 MFE.
For each V5 trade, if MFE >=2R, close p% at +2R, rest trails to eventual net.
p=0,20,30. Uses same v5 442tr FULL, net after costs, MFE from 1m fine."""
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
from src.btc.btc_routes import _compute_swings, _load_fine_1m, _trade_costs
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
c15,f15,_ = load_window("15m")
sw1h = _compute_swings(f1h,"continuous",min_bars=20)
sw15 = _compute_swings(f15,"continuous",min_bars=50)
t0=min(c1h[0]["ts"],c15[0]["ts"]); t1=max(c1h[-1]["ts"],c15[-1]["ts"])
fine=_load_fine_1m(t0,t1)
fine_ts=[x["ts"] for x in fine] if fine else []
candle_ts=[c["ts"] for c in c15]
n=len(c15)

nested = simulate_htf_ltf_15m(c1h,sw1h,c15,sw15,fine, htf_entry_break="flip", ltf_entry_break="decisive", sl_mode="swing", rr_target=3.0, ltf_trailing="swing", htf_breakeven=0, ltf_breakeven=0, htf_cap_days=16, ext_stop_r=1.5, sl_buf_atr=0.25)
ltf=nested["ltf_trades"]
_trade_costs(ltf,FEE,SLIP)

# compute MFE per trade as in Exp1 (fine 1m)
results=[]
for tr in ltf:
    if tr["outcome"]=="open": continue
    idx=tr["entry_idx"]
    entry=tr["entry_price"]
    risk=abs(entry - tr["sl"])
    if risk<=0: continue
    dir_ = 1 if tr["dir"]=="long" else -1
    entry_ts=tr["entry_ts"]; exit_ts=tr["exit_ts"]
    f_start=bisect.bisect_left(fine_ts, entry_ts+1)
    f_end=bisect.bisect_right(fine_ts, exit_ts)
    window=fine[f_start:f_end]
    highs=[x["high"] for x in window] if window else []
    lows=[x["low"] for x in window] if window else []
    if not highs:
        highs=[c15[i]["high"] for i in range(idx+1, tr["exit_idx"]+1)]
        lows=[c15[i]["low"] for i in range(idx+1, tr["exit_idx"]+1)]
    if not highs:
        mfe_r=0
    else:
        if dir_==1:
            mfe_px=max(highs)
            mfe_r=(mfe_px - entry)/risk
        else:
            mfe_px=min(lows)
            mfe_r=(entry - mfe_px)/risk
    r_net=float(tr["r_multiple"])-float(tr.get("cost_r",0))
    results.append({"r_net":r_net, "mfe_r":mfe_r, "exit_date":tr["exit_date"], "bars_held":tr["bars_held"], "dir":tr["dir"]})

def eval_partial(p):
    nets=[]
    yearly=defaultdict(float)
    for r in results:
        base=r["r_net"]
        mfe=r["mfe_r"]
        if mfe >=2.0:
            # partial p at +2R
            nets.append(p*2.0 + (1-p)*base)
            # for yearly, need to assign to same year as original
            # we will sum per original exit_date
        else:
            nets.append(base)
    # yearly with partial
    yearly=defaultdict(float)
    for r in results:
        y=r["exit_date"][:4]
        base=r["r_net"]; mfe=r["mfe_r"]
        val=(p*2.0 + (1-p)*base) if mfe>=2.0 else base
        yearly[y]+=val
    total=sum(nets)
    wins=sum(1 for x in nets if x>0)
    pos=sum(x for x in nets if x>0); neg=abs(sum(x for x in nets if x<0))
    pf=pos/neg if neg else 0
    # DD approx same as baseline? compute via sorted by exit_date order (not precise but estimate)
    # For DD we reuse baseline DD scaling: partial reduces DD proportionally to net reduction? We'll recompute via trade order sorted by exit_date (approx)
    # Sort results by exit_date (string)
    sorted_r=sorted(results, key=lambda x: x["exit_date"])
    nets_sorted=[]
    for r in sorted_r:
        base=r["r_net"]; mfe=r["mfe_r"]
        nets_sorted.append((p*2.0 + (1-p)*base) if mfe>=2.0 else base)
    # compute DD on cumulative
    cum=0; peak=0; dd=0
    for x in nets_sorted:
        cum+=x
        if cum>peak: peak=cum
        dd=max(dd, peak-cum)
    runners=sum(1 for x in nets if x>=3)
    avg_runner=sum(x for x in nets if x>=3)/max(1,runners)
    # mfe capture: avg realized / avg mfe for winners
    winners=[ ( (p*2.0 + (1-p)*r["r_net"]) if r["mfe_r"]>=2.0 else r["r_net"], r["mfe_r"]) for r in results if r["r_net"]>0 or ((p*2.0 + (1-p)*r["r_net"]) if r["mfe_r"]>=2.0 else r["r_net"])>0 ]
    # Actually recompute winners based on partial net
    partial_nets=[ (p*2.0 + (1-p)*r["r_net"]) if r["mfe_r"]>=2.0 else r["r_net"] for r in results ]
    # mfe capture for partial winners: realized / mfe
    caps=[]
    for orig, pn in zip(results, partial_nets):
        if pn>0:
            caps.append(pn / max(0.1, orig["mfe_r"]))
    avg_cap=sum(caps)/len(caps) if caps else 0
    return {"tr":len(results),"net":total,"pf":pf,"dd":dd,"runners":runners,"avg_runner":avg_runner,"yearly":dict(yearly),"avg_cap":avg_cap,"win":wins/len(nets)*100 if nets else 0}

print(f"V5.0 baseline (p=0): 442tr net {sum(r['r_net'] for r in results):.1f}  PF baseline 1.86 DD 23.3")
for p in [0.0, 0.2, 0.3]:
    r=eval_partial(p)
    print(f"V5.4 Partial p={int(p*100)}% at +2R | tr {r['tr']:3d} | net {r['net']:6.1f} | PF {r['pf']:4.2f} | DD {r['dd']:5.1f} | win {r['win']:4.1f}% | runners {r['runners']:2d} avg {r['avg_runner']:4.1f} | cap {r['avg_cap']*100:4.1f}% | 2023 {r['yearly'].get('2023',0):6.1f} 2024 {r['yearly'].get('2024',0):6.1f} 2025 {r['yearly'].get('2025',0):6.1f} 2026 {r['yearly'].get('2026',0):6.1f}")

# Also test p=0.5 for curiosity
for p in [0.5]:
    r=eval_partial(p)
    print(f"V5.4 Partial p={int(p*100)}% at +2R | tr {r['tr']:3d} | net {r['net']:6.1f} | PF {r['pf']:4.2f} | DD {r['dd']:5.1f}")

# Show how many trades hit +2R MFE
hit2=sum(1 for r in results if r["mfe_r"]>=2)
print(f"\nTrades with MFE>=2R: {hit2}/{len(results)} ({hit2/len(results)*100:.1f}%)  MFE>=5R: {sum(1 for r in results if r['mfe_r']>=5)}/{len(results)}")
print(f"Of 50 runners >=3R, MFE>=2R: {sum(1 for r in results if r['r_net']>=3 and r['mfe_r']>=2)}/50")
