"""Exp 46 — deferred entry: requeue young signals instead of dropping them.

Origin: exp43's mechanism split - the w24 gate works partly by chain re-timing
(+52.7 of the champion's +78.3), i.e. TIMING matters more than removal. So
test the structural version of that insight: a too-young signal (age <
exp_defer_h) is NOT dropped - it is requeued to the first 15m bar at/after
s+defer_h*3600, provided (all known at the defer bar - causal):
  - the SAME window is still open (candle_ts <= e+2700, live-observable),
  - the original SL pivot was never touched between signal and defer bar
    (setup survived = "HTF proved itself" without killing the trigger),
  - ext at the defer bar still passes.
Entry at the defer bar close; busy/cooldown/halt apply there (entry-time
data only). filtered is re-sorted by final bar so the ledger stays causal.

RQ1: does deferral beat BOTH w0 and w24 on lb30 (capturing the good 0-6h
     triggers late) and compete on A4/lb14?
RQ2: defer horizon {6,12,24}h - and how does defer24 ("wait a day, enter if
     the setup is still alive") compare to w24 ("drop everything <24h")?
RQ3: WF stability of the defer configs.
Canary: no trade in a defer ledger may recompute age < defer_h.

Process rules (EXP40C doc §12): identity gate + user coarse matrix + 6 fine
pins before any defer number is read; harness kept on disk; fine NET.
"""
import sys,time,json,bisect
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
A4=dict(exp31_lb=30,chop_thresh=55.0,exp_persist=2)
LB30=dict(exp31_lb=30)
LB14=dict()
VARIANTS=[("w0",0.0),("w24",0.0),("d6",6.0),("d12",12.0),("d24",24.0)]
PINS={("lb30","w0"):(349,196.3),("lb30","w24"):(265,185.0),
      ("A4","w0"):(359,203.3),("A4","w24"):(261,223.1),
      ("lb14","w0"):(351,148.0),("lb14","w24"):(272,193.7)}
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
 # ---------- PHASE 0: gates (identity + user matrix) ----------
 r_ship=shipped_mod.simulate_htf_ltf_streak_halt(c1h,sw20,c15,sw15,fine_ltf=[],**BP)
 s_ship=stats(r_ship["ltf_trades"])
 r0=sim(c1h,sw20,c15,sw15,fine_ltf=[],**BP)
 s0=stats(r0["ltf_trades"])
 assert s0["n"]==s_ship["n"] and s0["rs"]==s_ship["rs"],"IDENTITY GATE FAILED"
 print("IDENTITY GATE OK (flags-off == shipped, n=%d)"%s0["n"],flush=True)
 Mx={1.5:(265,231.6),2.0:(294,248.2),2.5:(304,231.7),3.0:(307,222.4)}
 ok=True
 for ext in (1.5,2.0,2.5,3.0):
  tr,g=run_coarse(sim,c1h,sw20,c15,sw15,sw20,LB30,24,ext)
  en,eg=Mx[ext];m=(len(tr)==en and abs(g-eg)<=0.15);ok=ok and m
  print("  MATRIX w24 ext%.1f coarse %3dt g%+7.1f   %s"%(ext,len(tr),g,("OK" if m else "MISMATCH")),flush=True)
 if not ok:raise SystemExit("MATRIX GATE FAILED - abort")
 # ---------- PHASE 1: fine ledgers (3 lanes x 5 variants, ext1.5) ----------
 fine=_load_fine_1m(min(c1h[0]["ts"],c15[0]["ts"]),max(c1h[-1]["ts"],c15[-1]["ts"]),symbol=INSTRUMENT)
 LANEDEF=[("lb30",sw20,LB30),("A4",sw10,A4),("lb14",sw20,LB14)]
 led={}
 for tag,swh,kw in LANEDEF:
  for vn,dh in VARIANTS:
   kw2={}
   if vn=="w24":kw2["exp_wage_h"]=24.0
   if vn.startswith("d"):kw2["exp_defer_h"]=dh
   r=sim(c1h,swh,c15,sw15,fine_ltf=fine,**{**BP,**kw,**kw2,"ext_stop_r":1.5})
   led[(tag,vn)]=r
   trf=r["ltf_trades"];net=_net(trf);mark=""
   if (tag,vn) in PINS:
    en,eg=PINS[(tag,vn)];m=(len(trf)==en and abs(net-eg)<=0.15);ok=ok and m
    mark="   %s (pin %dt %+.1f)"%(("OK" if m else "MISMATCH"),en,eg)
   print("  %-5s %-4s %3dt NET %+8.1f npt%+.3f DD%5.1f%s"%(tag,vn,len(trf),net,net/max(len(trf),1),stats(trf)["dd"],mark),flush=True)
 if not ok:raise SystemExit("FINE PIN MISMATCH - abort before defer analysis")
 print(flush=True)
 # ---------- join helpers (age recompute, same convention as exp43/44/45) ----------
 def _ivs(htf):
  iv=[(int(t["entry_ts"]),int(t["exit_ts"]),1 if t["dir"]=="long" else -1)
      for t in htf if t.get("outcome")!="open"]
  iv.sort();return iv,[w[0] for w in iv]
 JOIN={}
 for tag,swh,kw in LANEDEF:
  rf=led[(tag,"w0")]
  ivf,sf=_ivs(rf["htf_trades"]);ivb,sb=_ivs(rf["htf_trades_b2"])
  JOIN[tag]=(ivf,sf,ivb,sb)
 def _age_of(t,tag):
  ts=int(t["entry_ts"]);td=1 if t["dir"]=="long" else -1
  ivf,sf,ivb,sb=JOIN[tag]
  reg=t.get("htf_regime")
  if reg in ("flip","b2"):
   iv,st=(ivf,sf) if reg=="flip" else (ivb,sb)
   j=bisect.bisect_right(st,ts)-1
   if j>=0 and iv[j][0]<ts<=iv[j][1] and iv[j][2]==td:return (ts-iv[j][0])/3600.0
  for iv,st in ((ivf,sf),(ivb,sb)):
   j=bisect.bisect_right(st,ts)-1
   if j>=0 and iv[j][0]<ts<=iv[j][1] and iv[j][2]==td:return (ts-iv[j][0])/3600.0
  return None
 # ---------- PHASE 2: defer canary (no kept trade younger than the defer horizon) ----------
 print("PHASE A - defer canary: recomputed age of every defer-run trade (must be >= defer_h)",flush=True)
 for tag,swh,kw in LANEDEF:
  for vn,dh in VARIANTS:
   if not vn.startswith("d"):continue
   trf=led[(tag,vn)]["ltf_trades"]
   viol=0
   for t in trf:
    ag=_age_of(t,tag)
    if ag is not None and ag<dh:viol+=1
   print("  %-5s %-4s %3dt | age<%dh violations: %d"%(tag,vn,len(trf),int(dh),viol),flush=True)
 print(flush=True)
 # ---------- PHASE 3: segmented WF (6 segs) on all cells ----------
 K=6
 ts0=min(c1h[0]["ts"],c15[0]["ts"]);ts1=max(c1h[-1]["ts"],c15[-1]["ts"])
 step=(ts1-ts0)/float(K)
 print("PHASE B - walk-forward (6 segs ~%.0fd, fixed configs, fine NET)"%((ts1-ts0)/86400.0/K),flush=True)
 out2=[]
 for tag,swh,kw in LANEDEF:
  for vn,dh in VARIANTS:
   trf=led[(tag,vn)]["ltf_trades"]
   if not trf:continue
   segs=[[]for _ in range(K)]
   for t in trf:
    i=min(int((int(t["entry_ts"])-ts0)/step),K-1)
    if i<0:i=0
    segs[i].append(t)
   nets=[_net(sg) if sg else 0.0 for sg in segs]
   half=len(trf)//2
   h1,h2=_net(trf[:half]),_net(trf[half:])
   worst=min(nets)
   print("  %-5s %-4s %3dt NET %+8.1f | segs "%(tag,vn,len(trf),_net(trf))+" ".join("%+6.1f"%x for x in nets)+" | worst %+6.1f | H1/H2 %+7.1f/%+7.1f"%(worst,h1,h2),flush=True)
   out2.append(dict(lane=tag,variant=vn,defer_h=dh,n=len(trf),net=round(_net(trf),1),segs=[round(x,1)for x in nets],worst_seg=round(worst,1),h1=round(h1,1),h2=round(h2,1)))
 (ROOT/"backtest/tests/_exp46_results.json").write_text(json.dumps({"wf":out2},indent=1))
 print(flush=True)
 print("(exp46 done %.0fs)"%(time.time()-t0),flush=True)
if __name__=="__main__":main()


