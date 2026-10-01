import sys, os, pickle, types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for p in ("backtest","backtest/tests","backtest/sweeps","backend"):
    sys.path.insert(0,str(ROOT/p))
sys.path.append(str(ROOT/"backend"/"src"))
import test_experiments_craze as tc
from exp_concurrency_guard import load_unseen
from test_4_new_concepts import load_fine_1m as lfo
from run_experiment import net_r
from experiment_registry import BP,EXPERIMENTS
from exp_concurrency_guard import concurrency, pf
(oc15,of15),(oc1h,of1h)=load_unseen("15m"),load_unseen("1h")
of= lfo(oc15[0]["ts"],oc15[-1]["ts"])
src=(ROOT/"backend/src/btc/engines/htf_ltf/v19_champion.py").read_text(encoding="utf-8")
mod=types.ModuleType("v19o"); mod.__file__="v19o.py"
exec(compile(src,"v19o.py","exec"),mod.__dict__)
fn=mod.simulate_htf_ltf_streak_halt
pr={**BP,**EXPERIMENTS["champion_multi_sw10"]["params"]}
p={k:v for k,v in pr.items() if k not in {"exp_mltf","exp_persist","exp_partial_r"}}
r=fn(oc1h,tc._compute_swings(of1h,"continuous",min_bars=10),oc15,tc._compute_swings(of15,"continuous",min_bars=50),fine_ltf=of,**p)
tr=[t for t in r["ltf_trades"] if t.get("outcome")!="open"]
rs=[float(t["r_multiple"]) for t in tr]
print("V19 OOS: n=%d net=%+.2fR PF=%.3f maxconc=%d"%(len(rs),net_r(tr),pf(rs),concurrency(tr)))
print("PIN:     n=279 net=+70.1R maxconc=5")
print("MATCH:",len(rs)==279 and abs(net_r(tr)-70.15)<0.5)
