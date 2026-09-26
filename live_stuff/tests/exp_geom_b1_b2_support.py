"""Support matrix: immediate B1->B2 block on current v18 references."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/"live_stuff/tests"),str(ROOT/"live_stuff"),str(ROOT/"backend")]
from experiment_registry import BP,EXPERIMENTS
from exp_thesis_structure_volume import load_scope
from test_experiments_craze import build_module
from exp_geom_pure_v18_sweep import stats
from run_experiment import identity_gate
OUT={"is":ROOT/"live_stuff/tests/_geom_b1_b2_support_results_is.json",
     "oos":ROOT/"live_stuff/tests/_geom_b1_b2_support_results_oos.json"}
CONFIGS=("fullstack_wage10_cd0_single_sw10","champion_multi_sw10","utcsat_multi_sw10")

def run_scope(scope):
 d=load_scope(scope); sim=build_module()
 if scope=="is": identity_gate(d,sim)
 result={"instrument":"BTCUSDT_BYBIT","scope":scope,"policy":"block_immediate_b1_b2","variants":{}}
 for key in CONFIGS:
  base={**BP,**EXPERIMENTS[key]["params"]}; base.setdefault("exp_partial_r",0.0)
  out=sim(d["c1h"],d["sw10"],d["c15"],d["sw15"],fine_ltf=d["fine"],**base)
  tr=out["ltf_trades"] if isinstance(out,dict) else out
  rows=[]; out2=sim(d["c1h"],d["sw10"],d["c15"],d["sw15"],fine_ltf=d["fine"],**base,
                   exp_b1_b2_mode="block_immediate",exp_b1_b2_stats=rows)
  tr2=out2["ltf_trades"] if isinstance(out2,dict) else out2
  b=stats(tr); m=stats(tr2)
  result["variants"][key]={"baseline":b,"block_immediate":{"metrics":m,
      "activation":{"b2_candidates":len(rows),"blocked":sum(not int(r["allowed"]) for r in rows)}}}
  print(f"  {scope.upper():3} {key:38} blocked={result['variants'][key]['block_immediate']['activation']['blocked']:3d} n={m['n']:3d} G={m['gross_r']:+8.1f} N={m['net_r']:+8.1f} dN={m['net_r']-b['net_r']:+7.1f} DD={m['max_net_dd']:5.1f}",flush=True)
 return result

def main():
 p=argparse.ArgumentParser(); p.add_argument("--scope",choices=("is","oos","both"),default="both"); a=p.parse_args()
 for scope in (("is","oos") if a.scope=="both" else (a.scope,)):
  result=run_scope(scope); OUT[scope].write_text(json.dumps(result,indent=2),encoding="utf-8"); print("wrote",OUT[scope])
if __name__=="__main__": main()
