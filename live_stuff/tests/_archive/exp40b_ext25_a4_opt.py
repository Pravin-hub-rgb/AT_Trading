"""Exp 40b — ext_stop_r 1.5 -> 2.5 on A4 / OPTIMAL (fine, funding-inclusive NET).

Follows N6 (wage x ext matrix, lb30 w0): ext2.5 adopted as single-best on lb30.
Here: propagate the ONE stock kwarg (no patcher code — audited 2026-09-19,
gate is pre-fill, signal-bar-close, causal) to the two fine leaders:
  A4      = lb30 + chop55 + mb1h10 + persist2
  OPTIMAL = mltf + persist2 + chop55 (cd0 / cd10)
Paired run (ext1.5 vs ext2.5, same flags) so the delta is per-config exact.
Identity gate: flags-off patched module must equal shipped engine (coarse).
"""
import sys,time,json
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"live_stuff/tests"))
sys.path.insert(0,str(ROOT/"live_stuff"))
sys.path.insert(0,str(ROOT/"backend"))
from test_experiments_craze import build_module,BASE,load_candles,_compute_swings,SWING,MB15,INSTRUMENT,stats
from engine.v18_params import get_v18_params as _gvp
from src.btc.btc_routes import _load_fine_1m,_trade_costs
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod
BP=dict(BASE);BP["chop_thresh"]=58.0;_g=_gvp(INSTRUMENT)
def fund(tr):
 f=0.0
 for t in tr:
  e,sl=float(t["entry_price"]),float(t["sl"]);rk=abs(e-sl)
  if rk>0 and e>0:f+=(int(t.get("bars_held")or 0)*0.25/8.0)*0.0001*(e/rk)
 return f
def main():
 t0=time.time()
 (c15,f15),(c1h,f1h)=load_candles()
 sw15=_compute_swings(f15,"continuous",min_bars=MB15)
 sw20=_compute_swings(f1h,"continuous",min_bars=SWING["min_bars_1h"])
 sw10=_compute_swings(f1h,"continuous",min_bars=10)
 sim=build_module()
 fine=_load_fine_1m(min(c1h[0]["ts"],c15[0]["ts"]),max(c1h[-1]["ts"],c15[-1]["ts"]),symbol=INSTRUMENT)
 # ---------- IDENTITY GATE (coarse: flags-off patched == shipped) ----------
 r_ship=shipped_mod.simulate_htf_ltf_streak_halt(c1h,sw20,c15,sw15,fine_ltf=[],**BP)
 s_ship=stats(r_ship["ltf_trades"])
 r0=sim(c1h,sw20,c15,sw15,fine_ltf=[],**BP)
 s0=stats(r0["ltf_trades"])
 assert s0["n"]==s_ship["n"] and s0["rs"]==s_ship["rs"], "IDENTITY GATE FAILED"
 print("IDENTITY GATE OK (flags-off == shipped, n=%d)\n"%s0["n"],flush=True)
 cfgs=[("A4-lb30chop55mb10p2",sw10,dict(exp31_lb=30,chop_thresh=55.0,exp_persist=2)),
       ("OPT-mltf-cd0",sw10,dict(exp_mltf=True,exp_persist=2,chop_thresh=55.0,cooldown_bars=0)),
       ("OPT-mltf-cd10",sw10,dict(exp_mltf=True,exp_persist=2,chop_thresh=55.0,cooldown_bars=10))]
 out=[]
 for tag,swh,kw in cfgs:
  for ext in (1.5,2.5):
   r=sim(c1h,swh,c15,sw15,fine_ltf=fine,**{**BP,**kw,"ext_stop_r":ext})
   tr=r["ltf_trades"];s=stats(tr)
   rs=[float(t["r_multiple"])for t in tr];g=sum(rs)
   c2,_=_trade_costs(tr,_g["fee_pct"],0.0,_g["entry_slip_pct"],_g["exit_slip_pct"]);fr=fund(tr);net=g-c2-fr
   print("  %-24s ext%.1f %4dt NET %+8.1f (g%+7.1f f%5.1f fd%4.1f) npt%+.3f WR%4.1f%% DD%5.1f H1%+7.1f H2%+7.1f %s"%(tag,ext,len(tr),net,g,c2,fr,net/max(len(tr),1),s["wr"],s["dd"],s["h1"],s["h2"],{k:round(v,1)for k,v in sorted(s["py"].items())}),flush=True)
   out.append(dict(tag=tag,ext=ext,n=len(tr),net=round(net,1),dd=round(s["dd"],1)))
  print(flush=True)
 (ROOT/"live_stuff/tests/_exp40b_results.json").write_text(json.dumps(out,indent=1))
 print("(exp40b done %.0fs)"%(time.time()-t0),flush=True)
if __name__=="__main__":main()
