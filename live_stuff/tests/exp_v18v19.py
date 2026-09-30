import sys, os, pickle, inspect
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for p in ("live_stuff","live_stuff/tests","backend"):
    sys.path.insert(0,str(ROOT/p))
sys.path.append(str(ROOT/"backend"/"src"))
with open(Path(os.environ["TEMP"])/"at_datacache.pkl","rb") as f: d=pickle.load(f)
import src.btc.engines.htf_ltf.v18_streak_halt as M18
from src.btc.engines.htf_ltf.v19_champion import simulate_htf_ltf_streak_halt as M19
from run_experiment import net_r
from experiment_registry import BP,EXPERIMENTS
from exp_concurrency_guard import pf
pr={**BP,**EXPERIMENTS["champion_multi_sw10"]["params"]}
q={k:v for k,v in pr.items() if k not in {"exp_mltf","exp_persist","exp_partial_r"}}
sig=set(inspect.signature(M18.simulate_htf_ltf_streak_halt).parameters)
p={k:v for k,v in q.items() if k in sig}
print("IDENTICAL params for both engines. Only the code differs.")
print()
for name,fn in (("v18 original",M18.simulate_htf_ltf_streak_halt),("v19 champion",M19)):
    r=fn(d["c1h"],d["sw10"],d["c15"],d["sw15"],fine_ltf=d["fine"],**p)
    tr=[t for t in r["ltf_trades"] if t.get("outcome")!="open"]
    rs=[float(t["r_multiple"]) for t in tr]
    ev=[]
    for t in tr:
        ev.append((int(t["entry_ts"]),1)); ev.append((int(t["exit_ts"]),-1))
    ev.sort()
    cur=mx=0
    for _,x in ev:
        cur+=x
        if cur>mx: mx=cur
    print("  %-14s n=%4d  net=%+8.2fR  PF=%.3f  maxconc=%d"%(name,len(rs),net_r(tr),pf(rs),mx))