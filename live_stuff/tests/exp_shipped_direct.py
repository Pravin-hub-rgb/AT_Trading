"""DEFINITIVE: can the SHIPPED engine reproduce arm A with champion params?

Calls src.btc.engines.htf_ltf.v18_streak_halt.simulate_htf_ltf_streak_halt
DIRECTLY - no test_experiments_craze, no source patching, no harness.
This is the exact code path production would run.
"""
import sys, json, os, pickle
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for p in ("live_stuff/tests","live_stuff","backend"):
    sys.path.insert(0,str(ROOT/p))
sys.path.append(str(ROOT/"backend"/"src"))
CACHE=Path(os.environ["TEMP"])/"at_datacache.pkl"
with open(CACHE,"rb") as f: d=pickle.load(f)
import src.btc.engines.htf_ltf.v18_streak_halt as SHIPPED
from run_experiment import net_r
from experiment_registry import BP,EXPERIMENTS
from exp_concurrency_guard import concurrency, pf
import inspect

sig=set(inspect.signature(SHIPPED.simulate_htf_ltf_streak_halt).parameters)
params={**BP,**EXPERIMENTS["champion_multi_sw10"]["params"]}
dropped={k:params[k] for k in params if k not in sig}
p={k:v for k,v in params.items() if k in sig}
print("DROPPED (harness-only, engine never had them): %s"%json.dumps(dropped))
res=SHIPPED.simulate_htf_ltf_streak_halt(d["c1h"],d["sw10"],d["c15"],d["sw15"],fine_ltf=d["fine"],**p)
tr=[t for t in res["ltf_trades"] if t.get("outcome")!="open"]
rs=[float(t["r_multiple"]) for t in tr]
print()
print("SHIPPED ENGINE, champion params, zero harness:")
print("  n=%d  net=%+.2fR  PF=%.3f  maxconc=%d"%(len(rs),net_r(tr),pf(rs),concurrency(tr)))
print()
print("  harness arm A (same config) was: n=395  net=+137.72R  PF=1.859  maxconc=1")
print("  MATCHES: %s"%(len(rs)==395 and abs(net_r(tr)-137.72)<1.0))