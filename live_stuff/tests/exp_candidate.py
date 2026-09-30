"""BACKTESTING ONLY. Is the champion a final candidate?
Subperiod robustness + multiple-comparison threshold M."""
import sys, os, pickle
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[2]
for p in ("live_stuff","live_stuff/tests","backend"):
    sys.path.insert(0,str(ROOT/p))
sys.path.append(str(ROOT/"backend"/"src"))
with open(Path(os.environ["TEMP"])/"at_datacache.pkl","rb") as f: d=pickle.load(f)
from src.btc.engines.htf_ltf.v19_champion import simulate_htf_ltf_streak_halt as V19
from run_experiment import net_r
from experiment_registry import BP,EXPERIMENTS
pr={**BP,**EXPERIMENTS["champion_multi_sw10"]["params"]}
p={k:v for k,v in pr.items() if k not in {"exp_mltf","exp_persist","exp_partial_r"}}
r=V19(d["c1h"],d["sw10"],d["c15"],d["sw15"],fine_ltf=d["fine"],**p)
tr=[t for t in r["ltf_trades"] if t.get("outcome")!="open"]
M=193.4
print("CHAMPION SUBPERIOD ROBUSTNESS (IS)")
print("="*62)
yr=defaultdict(list)
for t in tr:
    yr[str((t.get("exit_date") or "")[:4])].append(t)
tot=0.0
print("  %-6s %6s %10s %8s"%("year","n","net","PF"))
for y in sorted(yr):
    g=net_r(yr[y]); tot+=g
    rs=[float(t["r_multiple"]) for t in yr[y]]
    w=sum(x for x in rs if x>0); l=abs(sum(x for x in rs if x<0))
    print("  %-6s %6d %+9.1fR %8.2f"%(y,len(yr[y]),g,(w/l if l else 9.0)))
print("  "+"-"*34)
print("  %-6s %6d %+9.1fR"%("ALL",len(tr),net_r(tr)))
print()
halves=defaultdict(list)
allts=sorted(tr,key=lambda t:int(t["entry_ts"]))
mid=len(allts)//2
for i,t in enumerate(allts):
    halves["H1 (first half)" if i<mid else "H2 (second half)"].append(t)
print("  HALVES (guards against one-lucky-period):")
for h in ("H1 (first half)","H2 (second half)"):
    print("    %-20s n=%3d net=%+8.1fR"%(h,len(halves[h]),net_r(halves[h])))
print()
print("MULTIPLE-COMPARISON CHECK")
print("  M = %.1fR (threshold from the experiment count)"%M)
g=net_r(tr)
print("  champion IS net = %+.1fR"%g)
print("  vs M: %s (%.2fx M)"%("EXCEEDS" if abs(g)>M else "below",abs(g)/M))