import sys, os, pickle, inspect, types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for p in ("live_stuff","live_stuff/tests","backend"):
    sys.path.insert(0,str(ROOT/p))
sys.path.append(str(ROOT/"backend"/"src"))
with open(Path(os.environ["TEMP"])/"at_datacache.pkl","rb") as f: d=pickle.load(f)
from run_experiment import net_r
from experiment_registry import BP,EXPERIMENTS
from exp_concurrency_guard import concurrency, pf
src=(ROOT/"backend/src/btc/engines/htf_ltf/v19_champion.py").read_text(encoding="utf-8")
mod=types.ModuleType("v19_champion")
mod.__file__="backend/src/btc/engines/htf_ltf/v19_champion.py"
exec(compile(src,"v19_champion.py","exec"),mod.__dict__)
fn=mod.simulate_htf_ltf_streak_halt
params={**BP,**EXPERIMENTS["champion_multi_sw10"]["params"]}
drop={"exp_mltf","exp_persist","exp_partial_r"}
p={k:v for k,v in params.items() if k not in drop}
print("V19 is REAL CODE, harness flags dropped: %s"%sorted(drop))
res=fn(d["c1h"],d["sw10"],d["c15"],d["sw15"],fine_ltf=d["fine"],**p)
tr=[t for t in res["ltf_trades"] if t.get("outcome")!="open"]
rs=[float(t["r_multiple"]) for t in tr]
print()
print("V19 PRODUCTION-STYLE CHAMPION (IS)")
print("  n=%d  net=%+.2fR  PF=%.3f  maxconc=%d"%(len(rs),net_r(tr),pf(rs),concurrency(tr)))
print("  PIN was:  n=500  net=+325.8R  maxconc=6")
print("  MATCH: %s"%(len(rs)==500 and abs(net_r(tr)-325.78)<0.5))

