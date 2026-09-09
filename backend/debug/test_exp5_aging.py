"""Exp5 — 16-day time-stop aging (time-held vs outcome).
Buckets: 0-2d / 3-5 / 6-12 / 13-16 / >16 (but >16 not possible due to cap, but we check).
Uses v5 FULL 442tr, 15m bars held."""
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
from src.btc.btc_routes import _compute_swings, _load_fine_1m, _trade_costs
from src.btc.btc_config import load_btc_df
from src.btc.engines.htf_ltf.v1_15m import simulate_htf_ltf_15m
from src.walker import FlowCandle
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
from src.btc.btc_routes import _compute_swings
sw1h = _compute_swings(f1h,"continuous",min_bars=20)
sw15 = _compute_swings(f15,"continuous",min_bars=50)
t0=min(c1h[0]["ts"],c15[0]["ts"]); t1=max(c1h[-1]["ts"],c15[-1]["ts"])
fine=_load_fine_1m(t0,t1)
nested = simulate_htf_ltf_15m(c1h,sw1h,c15,sw15,fine, htf_entry_break="flip", ltf_entry_break="decisive", sl_mode="swing", rr_target=3.0, ltf_trailing="swing", htf_breakeven=0, ltf_breakeven=0, htf_cap_days=16, ext_stop_r=1.5, sl_buf_atr=0.25)
ltf=nested["ltf_trades"]
_trade_costs(ltf,FEE,SLIP)

# Buckets by bars_held: 15m bars: 96 per day
def bucket_days(bars):
    days=bars/96
    if days <=2: return "0-2d"
    if days <=5: return "3-5d"
    if days <=8: return "6-8d"
    if days <=12: return "9-12d"
    if days <=16: return "13-16d"
    return ">16d"
buckets=defaultdict(list)
for tr in ltf:
    if tr["outcome"]=="open": continue
    b=bucket_days(tr["bars_held"])
    buckets[b].append(tr)

# also check bars_held stats for runners
runners=[t for t in ltf if float(t["r_multiple"])-float(t.get("cost_r",0)) >=3 and t["outcome"]!="open"]

print(f"Exp5 — Time-stop aging v5 FULL 442tr 16d cap (96 bars/day)")
print(f"Overall: {len([t for t in ltf if t['outcome']!='open'])} closed, runners>=3R {len(runners)}")
if runners:
    avg_bars=sum(t["bars_held"] for t in runners)/len(runners)
    print(f"Runners avg held {avg_bars:.1f} bars ({avg_bars/96:.1f}d)  min {min(t['bars_held'] for t in runners)} max {max(t['bars_held'] for t in runners)}")
    # what % runners need >10d?
    cnt10=sum(1 for t in runners if t["bars_held"]/96 >10)
    print(f"Runners >10d: {cnt10}/{len(runners)} ({cnt10/len(runners)*100:.1f}%)  >12d: {sum(1 for t in runners if t['bars_held']/96>12)}/{len(runners)}")

for k in ["0-2d","3-5d","6-8d","9-12d","13-16d",">16d"]:
    lst=buckets[k]
    if not lst: continue
    nets=[float(t["r_multiple"])-float(t.get("cost_r",0)) for t in lst]
    net=sum(nets)
    win=sum(1 for x in nets if x>0)/len(nets)*100
    runners_b=sum(1 for x in nets if x>=3)
    avg=net/len(nets)
    print(f"{k:8s} | tr {len(lst):3d} | net {net:+7.1f} | avg {avg:+5.2f} | win {win:4.1f}% | runners {runners_b:2d} ({runners_b/len(lst)*100:4.1f}%) | PF { (sum(x for x in nets if x>0)/abs(sum(x for x in nets if x<0)) if sum(x for x in nets if x<0)!=0 else 0):4.2f}")

# R at 16d? We can approximate: for trades that lasted >13-16d, what was their eventual R vs time
# Also check max runner at 16d boundary
print("\nTop held trades (bars -> days):")
for tr in sorted(ltf, key=lambda x: x["bars_held"], reverse=True)[:10]:
    if tr["outcome"]=="open": continue
    print(f"  {tr['bars_held']:4d} bars {tr['bars_held']/96:4.1f}d  net {float(tr['r_multiple'])-float(tr.get('cost_r',0)):+5.2f} {tr['outcome']:5s} {tr['exit_date'][:10]}")

# Conditional cap test: reuse v9 logic? We can test what if cap 12d vs 16d vs 20d by filtering trades that exceed cap
# Quick estimate: trades with bars_held > 12d (1152 bars) — how many would be cut at 12d?
print("\nIf cap 12d instead of 16d (1152 bars):")
cut12=[t for t in ltf if t["bars_held"]>1152 and t["outcome"]!="open"]
print(f"  Trades that held >12d: {len(cut12)}  their net sum {sum(float(t['r_multiple'])-float(t.get('cost_r',0)) for t in cut12):+.1f}  avg {sum(float(t['r_multiple'])-float(t.get('cost_r',0)) for t in cut12)/max(1,len(cut12)):+.2f}")
print(f"  Among them runners>=3R: {sum(1 for t in cut12 if float(t['r_multiple'])-float(t.get('cost_r',0))>=3)}")

print("\nIf extend to 30d for 2R at 16d (v9): check how many 16d trades were >=2R at 16d bar (approx via mfe not available) — skip, need v9 engine run for true test.")
# For now run v9 engine direct if available
try:
    from src.btc.engines.v9_conditional_cap import simulate_btc_trades_v9
    # v9 is single TF 1h, not LTF, so not comparable for Exp5 LTF; we test 1h aging instead
    from src.btc.engines.htf_ltf.v1_15m import simulate_htf_ltf_15m
    # No LTF conditional yet, so just note
    print("LTF conditional cap not wired (v1_15m has fixed HTF 16d only). 1h conditional v9 exists but LTF Let run vs Strict window not tested.")
except Exception as e:
    print(f"v9 check skip: {e}")
