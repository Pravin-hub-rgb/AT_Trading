"""B1->B2 age decomposition on literal-default v18."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/"live_stuff/tests"),str(ROOT/"live_stuff"),str(ROOT/"backend")]
from exp_geom_pure_v18_sweep import load_data,params_for,stats
from test_experiments_craze import build_module
from run_experiment import identity_gate
OUT={"is":ROOT/"live_stuff/tests/_geom_b1_b2_age_decomp_is.json","oos":ROOT/"live_stuff/tests/_geom_b1_b2_age_decomp_oos.json"}
CONTROLS=("literal_v18_single","literal_v18_multi")
POLICIES=("block_age0","block_age1","block_age2","block_0_1","block_immediate")
def run_scope(scope):
 d=load_data(scope); sim=build_module()
 if scope=="is": identity_gate({"c1h":d[0],"sw20":d[1],"c15":d[2],"sw15":d[3]},sim)
 result={"instrument":"BTCUSDT_BYBIT","scope":scope,"variants":{}}
 for c in CONTROLS:
  base=params_for(c); o=sim(*d,**base); tr=o["ltf_trades"] if isinstance(o,dict) else o; b=stats(tr)
  result["variants"][c]={"baseline":b}
  for p in POLICIES:
   rows=[]; o=sim(*d,**base,exp_b1_b2_mode=p,exp_b1_b2_stats=rows); tr=o["ltf_trades"] if isinstance(o,dict) else o; m=stats(tr)
   result["variants"][c][p]={"metrics":m,"blocked":sum(not int(r["allowed"]) for r in rows),"activation_n":len(rows)}
   print(f" {scope.upper()} {c:19} {p:18} blocked={result['variants'][c][p]['blocked']:3d} n={m['n']:3d} G={m['gross_r']:+8.1f} N={m['net_r']:+8.1f} dN={m['net_r']-b['net_r']:+7.1f} DD={m['max_net_dd']:5.1f}",flush=True)
 return result
def main():
 p=argparse.ArgumentParser();p.add_argument("--scope",choices=("is","oos","both"),default="both");a=p.parse_args()
 for s in (("is","oos") if a.scope=="both" else (a.scope,)):
  r=run_scope(s);OUT[s].write_text(json.dumps(r,indent=2));print("wrote",OUT[s])
if __name__=="__main__":main()
