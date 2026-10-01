"""Exp 42 - wage-threshold sweep (is 24h physics or a lucky point?) + lb14 recheck.

Follows exp40c/exp41 (both validated). Open questions:
  1. The w24 gate threshold was never swept - only 0 vs 24. If NET rises
     smoothly into 24h and falls after, 24h is a curve-fit point; if it
     plateaus across ~18-36h, the "window physics" claim is robust.
     Sweep wage in {0,12,18,24,36,48} x lanes {lb30, A4, OPT-cd10} at ext1.5
     (fine NET: 1m fills + fee + slip + funding).
  2. lb14+w24 (the old "DD-king" lane, doc DD 15.8) was never re-run under
     the validated gate - 2 extra cells (w0/w24, ext1.5, no external pin).
  3. Segmented WF (6 segs, fixed configs, exp41 design) on the SAME sweep
     ledgers - the wage threshold must be stable across regimes, not just
     in-sample. WF here is ledger bucketing by entry_ts, no re-sims.
Gates before results (doc section 12 rules): identity gate + user lb30 w24
coarse matrix + 6 fine pins to _exp40c_out.txt Phase C; abort on any mismatch.
"""
import sys,time,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"backtest/tests"))
sys.path.insert(0,str(ROOT/"backtest"))
sys.path.insert(0,str(ROOT/"backend"))
from exp40c_wage_gate import BP,fund,run_coarse
from test_experiments_craze import build_module,load_candles,_compute_swings,SWING,MB15,INSTRUMENT,stats
from engine.v18_params import get_v18_params as _gvp
from src.btc.btc_routes import _load_fine_1m,_trade_costs
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod
OPT10=dict(exp_mltf=True,exp_persist=2,chop_thresh=55.0,cooldown_bars=10)
A4=dict(exp31_lb=30,chop_thresh=55.0,exp_persist=2)
LB30=dict(exp31_lb=30)
LB14=dict()
WAGES=(0,12,18,24,36,48)
# fine pins from exp40c Phase C (_exp40c_out.txt), all at ext1.5
PINS={("lb30",0):(349,196.3),("lb30",24):(265,185.0),
      ("A4",0):(359,203.3),("A4",24):(261,223.1),
      ("OPT-cd10",0):(453,259.4),("OPT-cd10",24):(326,337.7)}

def main():
 t0=time.time()
 (c15,f15),(c1h,f1h)=load_candles()
 sw15=_compute_swings(f15,"continuous",min_bars=MB15)
 sw20=_compute_swings(f1h,"continuous",min_bars=SWING["min_bars_1h"])
 sw10=_compute_swings(f1h,"continuous",min_bars=10)
 sim=build_module()
 _g=_gvp(INSTRUMENT)
 def _net(tr):
  rs=[float(t["r_multiple"])for t in tr]
  c2,_=_trade_costs(tr,_g["fee_pct"],0.0,_g["entry_slip_pct"],_g["exit_slip_pct"])
  return sum(rs)-c2-fund(tr)
 # ---------- PHASE 0: gates (identity + external matrix; abort on fail) ----------
 r_ship=shipped_mod.simulate_htf_ltf_streak_halt(c1h,sw20,c15,sw15,fine_ltf=[],**BP)
 s_ship=stats(r_ship["ltf_trades"])
 r0=sim(c1h,sw20,c15,sw15,fine_ltf=[],**BP)
 s0=stats(r0["ltf_trades"])
 assert s0["n"]==s_ship["n"] and s0["rs"]==s_ship["rs"],"IDENTITY GATE FAILED"
 print("IDENTITY GATE OK (flags-off == shipped, n=%d)"%s0["n"],flush=True)
 Mx={1.5:(265,231.6),2.0:(294,248.2),2.5:(304,231.7),3.0:(307,222.4)}
 print("MATRIX GATE - user lb30 w24 coarse matrix (ext sweep)",flush=True)
 ok=True
 for ext in (1.5,2.0,2.5,3.0):
  tr,g=run_coarse(sim,c1h,sw20,c15,sw15,sw20,LB30,24,ext)
  en,eg=Mx[ext];m=(len(tr)==en and abs(g-eg)<=0.15);ok=ok and m
  print("  w24 ext%.1f coarse %3dt g%+7.1f   %s (exp %dt %+.1f)"%(ext,len(tr),g,("OK" if m else "MISMATCH"),en,eg),flush=True)
 if not ok:raise SystemExit("MATRIX GATE FAILED - abort before any sweep output")
 print(flush=True)
 # ---------- PHASE 1: wage sweep (fine NET: 1m fills + fee + slip + funding) ----------
 fine=_load_fine_1m(min(c1h[0]["ts"],c15[0]["ts"]),max(c1h[-1]["ts"],c15[-1]["ts"]),symbol=INSTRUMENT)
 lanes=[("lb30",sw20,LB30),("A4",sw10,A4),("OPT-cd10",sw10,OPT10),("lb14",sw20,LB14)]
 def _fine(swh,kw,w):
  wage={"exp_wage_h":w} if w else {}
  r=sim(c1h,swh,c15,sw15,fine_ltf=fine,**{**BP,**kw,**wage,"ext_stop_r":1.5})
  return r["ltf_trades"]
 led={};out1=[]
 print("PHASE 1 - wage sweep ext1.5 (fine NET: 1m fills+fee+slip+funding)",flush=True)
 for tag,swh,kw in lanes:
  for w in WAGES:
   trf=_fine(swh,kw,w);led[(tag,w)]=trf
   net=_net(trf);s=stats(trf);mark=""
   if (tag,w) in PINS:
    en,eg=PINS[(tag,w)];m=(len(trf)==en and abs(net-eg)<=0.15);ok=ok and m
    mark="   %s (exp40c pin %dt %+.1f)"%(("OK" if m else "MISMATCH"),en,eg)
   print("  %-9s w%2dh %3dt NET %+8.1f npt%+.3f DD%5.1f%s"%(tag,w,len(trf),net,net/max(len(trf),1),s["dd"],mark),flush=True)
  best=max(WAGES,key=lambda w:_net(led[(tag,w)]))
  print("  -> %s argmax wage = %dh"%(tag,best),flush=True)
  out1.append(dict(tag=tag,rows=[dict(wage_h=w,n=len(led[(tag,w)]),net=round(_net(led[(tag,w)]),1),dd=round(stats(led[(tag,w)])["dd"],1)) for w in WAGES]))
 if not ok:raise SystemExit("FINE PIN MISMATCH - abort before WF")
 print(flush=True)
 # ---------- PHASE 2: segmented WF (6 segs, fixed configs) on the same ledgers ----------
 K=6
 ts0=min(c1h[0]["ts"],c15[0]["ts"]);ts1=max(c1h[-1]["ts"],c15[-1]["ts"])
 step=(ts1-ts0)/float(K)
 print("PHASE 2 - walk-forward on sweep ledgers (6 segs ~%.0fd, fixed configs, fine NET)"%((ts1-ts0)/86400.0/K),flush=True)
 out2=[]
 for tag,swh,kw in lanes:
  for w in WAGES:
   trf=led[(tag,w)]
   if not trf:continue
   segs=[[]for _ in range(K)]
   for t in trf:
    i=min(int((int(t["entry_ts"])-ts0)/step),K-1)
    if i<0:i=0
    segs[i].append(t)
   nets=[];dds=[]
   for sg in segs:
    if sg:nets.append(_net(sg));dds.append(stats(sg)["dd"])
    else:nets.append(0.0);dds.append(0.0)
   half=len(trf)//2
   h1,h2=_net(trf[:half]),_net(trf[half:])
   worst=min(nets)
   print("  %-9s w%2dh %3dt NET %+8.1f | segs "%(tag,w,len(trf),_net(trf))+" ".join("%+6.1f"%x for x in nets)+" | worst %+6.1f | H1/H2 %+7.1f/%+7.1f"%(worst,h1,h2),flush=True)
   out2.append(dict(tag=tag,wage_h=w,n=len(trf),net=round(_net(trf),1),segs=[round(x,1)for x in nets],worst_seg=round(worst,1),h1=round(h1,1),h2=round(h2,1)))
 (ROOT/"backtest/tests/_exp42_results.json").write_text(json.dumps({"sweep":out1,"wf":out2},indent=1))
 print(flush=True)
 print("(exp42 done %.0fs)"%(time.time()-t0),flush=True)
if __name__=="__main__":main()
