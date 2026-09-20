"""Exp 41 — missing ext2.0 cells + segmented walk-forward on the leaders.

Follows exp40c (validated: identity gate OK, user lb30 matrix 4/4 exact, fine
NET 4/4 exact). Two questions left open by exp40c's verdict:
  1. The one cheap missing cell: OPT-cd10 x ext2.0 (w0, w24) — ext sweeps on
     the other lanes showed 2.5 as the ceiling, but OPT-cd10 only got 1.5/2.5.
  2. Segmented walk-forward on the leader set: exp40c's per-lane winners are
     in-sample (OPT stacks 4-5 knobs). Six equal segments by entry_ts of the
     causal full-history sim — per-segment NET/DD shows whether the leaders
     earn consistently or are one-lucky-stretch configs. Configs are FIXED
     (no per-fold re-fit); the sim itself is causal, so segment buckets are
     honest per-segment ledgers of a fixed rule (selection bias is the known
     in-sample caveat, stated, not hidden).
Same engine + conventions as exp40c: craze module, coarse gross + fine
(1m fills, fee+slip+funding) NET, BP base (chop 58) + per-lane knob dicts.
"""
import sys,time,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"live_stuff/tests"))
sys.path.insert(0,str(ROOT/"live_stuff"))
sys.path.insert(0,str(ROOT/"backend"))
from exp40c_wage_gate import BP,fund,run_coarse
from test_experiments_craze import build_module,load_candles,_compute_swings,SWING,MB15,INSTRUMENT,stats
from engine.v18_params import get_v18_params as _gvp
from src.btc.btc_routes import _load_fine_1m,_trade_costs
OPT0=dict(exp_mltf=True,exp_persist=2,chop_thresh=55.0,cooldown_bars=0)
OPT10=dict(exp_mltf=True,exp_persist=2,chop_thresh=55.0,cooldown_bars=10)
A4=dict(exp31_lb=30,chop_thresh=55.0,exp_persist=2)
LB30=dict(exp31_lb=30)
CELLS=[("OPT-cd10",OPT10,(0,24),(1.5,2.0,2.5))]
LEADERS=[("lb30 w0 e1.5",LB30,0,1.5),
         ("lb30 w0 e2.5",LB30,0,2.5),
         ("lb30 w24 e2.5",LB30,24,2.5),
         ("A4 w24 e1.5",A4,24,1.5),
         ("OPTcd0 w0 e1.5",OPT0,0,1.5),
         ("OPTcd0 w24 e1.5",OPT0,24,1.5),
         ("OPTcd10 w24 e1.5",OPT10,24,1.5),
         ("OPTcd10 w24 e2.0",OPT10,24,2.0)]
def main():
 t0=time.time()
 (c15,f15),(c1h,f1h)=load_candles()
 sw15=_compute_swings(f15,"continuous",min_bars=MB15)
 sw20=_compute_swings(f1h,"continuous",min_bars=SWING["min_bars_1h"])
 sw10=_compute_swings(f1h,"continuous",min_bars=10)
 sim=build_module()
 fine=_load_fine_1m(min(c1h[0]["ts"],c15[0]["ts"]),max(c1h[-1]["ts"],c15[-1]["ts"]),symbol=INSTRUMENT)
 _g=_gvp(INSTRUMENT)
 def _net(tr):
  rs=[float(t["r_multiple"])for t in tr]
  c2,_=_trade_costs(tr,_g["fee_pct"],0.0,_g["entry_slip_pct"],_g["exit_slip_pct"])
  return sum(rs)-c2-fund(tr)
 def _fine(swh,kw,w,ext):
  wage={"exp_wage_h":w} if w else {}
  r=sim(c1h,swh,c15,sw15,fine_ltf=fine,**{**BP,**kw,**wage,"ext_stop_r":ext})
  return r["ltf_trades"]
 # ---------- PHASE 1: missing OPT-cd10 x ext2.0 cells ----------
 print("PHASE 1 - OPT-cd10 ext sweep incl missing 2.0 (coarse + fine)",flush=True)
 out1=[]
 for w in (0,24):
  for ext in (1.5,2.0,2.5):
   tr,g=run_coarse(sim,c1h,sw20,c15,sw15,sw10,OPT10,w,ext)
   trf=_fine(sw10,OPT10,w,ext)
   s=stats(trf);net=_net(trf)
   print("  OPT-cd10 w%-2d ext%.1f coarse %3dt g%+7.1f | fine %3dt NET %+8.1f npt%+.3f DD%5.1f"%(w,ext,len(tr),g,len(trf),net,net/max(len(trf),1),s["dd"]),flush=True)
   out1.append(dict(wage_h=w,ext=ext,n_coarse=len(tr),n=len(trf),net=round(net,1),dd=round(s["dd"],1)))
 print(flush=True)
 # ---------- PHASE 2: segmented walk-forward on the leader set ----------
 K=6
 ts0=min(c1h[0]["ts"],c15[0]["ts"]);ts1=max(c1h[-1]["ts"],c15[-1]["ts"])
 step=(ts1-ts0)/float(K)
 bounds=[ts0+step*i for i in range(K+1)]
 print("PHASE 2 - walk-forward: %d equal segments, fixed configs (fine NET)"%K,flush=True)
 print("  seg span ~%.0f days"%((ts1-ts0)/86400.0/K),flush=True)
 out2=[]
 for tag,kw,w,ext in LEADERS:
  swh=sw20 if tag.startswith("lb30") else sw10
  trf=_fine(swh,kw,w,ext)
  segs=[[]for _ in range(K)]
  for t in trf:
   ts=int(t["entry_ts"]);i=min(int((ts-ts0)/step),K-1)
   if i<0:i=0
   segs[i].append(t)
  nets=[_net(sg)for sg in segs]
  dds=[stats(sg)["dd"] for sg in segs]
  ns=[len(sg)for sg in segs]
  tot=_net(trf);worst=min(nets)
  half=len(trf)//2
  h1,h2=_net(trf[:half]),_net(trf[half:])
  tail=" | worst %+6.1f | DDs "%worst+" ".join("%4.1f"%x for x in dds)+" | H1/H2 %+7.1f/%+7.1f"%(h1,h2)
  print("  %-17s %3dt NET %+8.1f | segs "%(tag,len(trf),tot)+" ".join("%+6.1f"%x for x in nets)+tail,flush=True)
  out2.append(dict(tag=tag,wage_h=w,ext=ext,n=len(trf),net=round(tot,1),
                   segs=[round(x,1)for x in nets],ns=ns,dds=[round(x,1)for x in dds],
                   worst_seg=round(worst,1),h1=round(h1,1),h2=round(h2,1)))
 print(flush=True)
 (ROOT/"live_stuff/tests/_exp41_results.json").write_text(json.dumps({"cells":out1,"wf":out2},indent=1))
 print("(exp41 done %.0fs)"%(time.time()-t0),flush=True)
if __name__=="__main__":main()
