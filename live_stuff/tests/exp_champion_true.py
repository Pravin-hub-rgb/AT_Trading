"""STEP 0 - HARD GATE. Reproduce the champion pin or abort everything."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for p in ("live_stuff/tests","live_stuff","backend"):
    sys.path.insert(0,str(ROOT/p))
sys.path.append(str(ROOT/"backend"/"src"))
import test_experiments_craze as tc
from run_experiment import get_data, net_r
from experiment_registry import BP,EXPERIMENTS

d=get_data()
def run(name):
    p={**BP,**EXPERIMENTS[name]["params"]}
    res=tc.build_module()(d["c1h"],d["sw10"],d["c15"],d["sw15"],fine_ltf=d["fine"],**p)
    tr=[t for t in res["ltf_trades"] if t.get("outcome")!="open"]
    return tr, net_r(tr)

tr,net=run("champion_multi_sw10")
print("="*60)
print("STEP 0 - PIN REPRODUCTION (hard gate)")
print("="*60)
print("  champion_multi_sw10 IS : n=%d  net=%+.1fR"%(len(tr),net))
print("  EXPECTED              : n=500  net=+325.8R")
ok = (len(tr)==500) and abs(net-325.8)<0.5
print()
print("  RESULT: %s"%("PIN OK -- safe to continue" if ok else "*** PIN MISMATCH -- ABORT ***"))
print("="*60)
raise SystemExit(0 if ok else 1)