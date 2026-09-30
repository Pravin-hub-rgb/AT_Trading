import sys, os, pickle
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for p in ("live_stuff","live_stuff/tests","backend"):
    sys.path.insert(0,str(ROOT/p))
sys.path.append(str(ROOT/"backend"/"src"))
# REAL IMPORT - not exec, not compile, not read_text
from src.btc.engines.htf_ltf.v19_champion import simulate_htf_ltf_streak_halt as V19
import inspect
print("imported OK from:",inspect.getfile(V19))
print("is it the committed file?", "v19_champion" in inspect.getfile(V19))
with open(Path(os.environ["TEMP"])/"at_datacache.pkl","rb") as f: d=pickle.load(f)
from run_experiment import net_r
from experiment_registry import BP,EXPERIMENTS
from exp_concurrency_guard import pf
pr={**BP,**EXPERIMENTS["champion_multi_sw10"]["params"]}
p={k:v for k,v in pr.items() if k not in {"exp_mltf","exp_persist","exp_partial_r"}}
r=V19(d["c1h"],d["sw10"],d["c15"],d["sw15"],fine_ltf=d["fine"],**p)
tr=[t for t in r["ltf_trades"] if t.get("outcome")!="open"]
rs=[float(t["r_multiple"]) for t in tr]
print()
print("REAL IMPORT, v19_champion.py from disk:")
print("  IS  n=%d  net=%+.2fR  PF=%.3f"%(len(rs),net_r(tr),pf(rs)))
print("  PIN  n=500  net=+325.8R")
print("  MATCH:",len(rs)==500 and abs(net_r(tr)-325.78)<0.5)