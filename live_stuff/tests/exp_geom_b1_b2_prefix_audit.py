"""Prefix-invariance audit for literal-v18 B1->B2 immediate block."""
from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/"live_stuff/tests"),str(ROOT/"live_stuff"),str(ROOT/"backend")]
from exp_geom_pure_v18_sweep import load_data,params_for
from test_experiments_craze import build_module
from src.btc.btc_routes import _compute_swings
from src.walker import FlowCandle
OUT={"is":ROOT/"live_stuff/tests/_geom_b1_b2_prefix_audit_is.json","oos":ROOT/"live_stuff/tests/_geom_b1_b2_prefix_audit_oos.json"}
CONTROLS=("literal_v18_single","literal_v18_multi"); FRACTIONS=(0.70,0.85)
def flow(cs): return [FlowCandle(date=c["date"],open=float(c["open"]),high=float(c["high"]),low=float(c["low"]),close=float(c["close"])) for c in cs]
def prefix_data(d,cut):
 c1h=[c for c in d[0] if int(c["ts"])<=cut]; c15=[c for c in d[2] if int(c["ts"])<=cut]; fine=[c for c in d[4] if int(c["ts"])<=cut]
 return c1h,_compute_swings(flow(c1h),"continuous",min_bars=10),c15,_compute_swings(flow(c15),"continuous",min_bars=50),fine
def key(t): return (int(t["entry_ts"]),1 if t.get("dir")=="long" else -1,int(t.get("exit_ts") or 0),round(float(t.get("r_multiple") or 0),6))
def run_scope(scope,sim):
 d=load_data(scope); result={"scope":scope,"fractions":FRACTIONS,"variants":{}}
 for c in CONTROLS:
  base=params_for(c); result["variants"][c]={}
  for frac in FRACTIONS:
   cut=int(d[2][int((len(d[2])-1)*frac)]["ts"]); pd=prefix_data(d,cut); row={}
   for arm,flags in (("baseline",{}),("block_immediate",{"exp_b1_b2_mode":"block_immediate"})):
    fo=sim(*d,**{**base,**flags}); ft=fo["ltf_trades"] if isinstance(fo,dict) else fo
    po=sim(*pd,**{**base,**flags}); pt=po["ltf_trades"] if isinstance(po,dict) else po
    fd=[t for t in ft if int(t.get("exit_ts") or 0)<=cut]; pdone=[t for t in pt if int(t.get("exit_ts") or 0)<=cut]
    fk={key(t) for t in fd}; pk={key(t) for t in pdone}
    row[arm]={"cutoff":cut,"full_n":len(fd),"prefix_n":len(pdone),"full_only":len(fk-pk),"prefix_only":len(pk-fk),"full_r":round(sum(float(t.get("r_multiple") or 0) for t in fd),6),"prefix_r":round(sum(float(t.get("r_multiple") or 0) for t in pdone),6),"passed":fk==pk}
   result["variants"][c][str(frac)]=row; print(scope.upper(),c,frac,row,flush=True)
 return result
def main():
 sim=build_module()
 for s in ("is","oos"):
  r=run_scope(s,sim);OUT[s].write_text(json.dumps(r,indent=2));print("wrote",OUT[s])
if __name__=="__main__":main()
