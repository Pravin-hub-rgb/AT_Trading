"""Exp 44 — curfew gate: skip only the 6-24h window-age band (keep 0-6h + >=24h).

Origin: exp43's age profile showed the LTF loss pocket is the 6-24h band
(lb30 U-curve: 0-6h +0.10 avgR, 6-12h -0.61, 12-24h -0.11, >=24h +1.2;
OPT-cd10 monotonic after a bad 0-12h) while w24 is a blunt tool that also
cuts lb30's good 0-6h pocket. New knob exp_curfew_a/b skips only a<=age<b
(no-op when b=0; identity-gated).

RQ1: does keeping 0-6h + skipping 6-24h beat BOTH w0 and w24 on lb30 (the
     U-curve lane) and at least match w24 on the others?
RQ2: band edge - is (6,30) better than (6,24) on the >=48h-strong lanes?
RQ3: walk-forward stability of the curfew configs (6 segs, fixed configs).
RQ4: canary - no curfew-run trade may recompute into the skipped band.

Process rules (EXP40C doc §12): identity gate + user coarse matrix + 8 fine
pins before any new-cell number is read; harness kept on disk; fine NET
(1m fills + fee + slip + funding) everywhere; nothing deleted.
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
OPT10=dict(exp_mltf=True,exp_persist=2,chop_thresh=55.0,cooldown_bars=10)
A4=dict(exp31_lb=30,chop_thresh=55.0,exp_persist=2)
LB30=dict(exp31_lb=30)
LB14=dict()
VARIANTS=[("w0",0.0,0.0),("w24",0.0,24.0),("curf6-24",6.0,24.0),("curf6-30",6.0,30.0)]
PINS={("lb30","w0"):(349,196.3),("lb30","w24"):(265,185.0),
      ("A4","w0"):(359,203.3),("A4","w24"):(261,223.1),
      ("lb14","w0"):(351,148.0),("lb14","w24"):(272,193.7),
      ("OPT-cd10","w0"):(453,259.4),("OPT-cd10","w24"):(326,337.7)}
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
 # ---------- PHASE 1: fine ledgers (4 lanes x 4 variants, ext1.5) ----------
 fine=_load_fine_1m(min(c1h[0]["ts"],c15[0]["ts"]),max(c1h[-1]["ts"],c15[-1]["ts"]),symbol=INSTRUMENT)
 LANEDEF=[("lb30",sw20,LB30),("A4",sw10,A4),("lb14",sw20,LB14),("OPT-cd10",sw10,OPT10)]
 led={}
 for tag,swh,kw in LANEDEF:
  for vn,a,b in VARIANTS:
   kw2={}
   if vn=="w24":kw2["exp_wage_h"]=b
   if vn.startswith("curf"):kw2["exp_curfew_a"]=a;kw2["exp_curfew_b"]=b
   r=sim(c1h,swh,c15,sw15,fine_ltf=fine,**{**BP,**kw,**kw2,"ext_stop_r":1.5})
   led[(tag,vn)]=r
   trf=r["ltf_trades"];net=_net(trf);mark=""
   if (tag,vn) in PINS:
    en,eg=PINS[(tag,vn)];m=(len(trf)==en and abs(net-eg)<=0.15);ok=ok and m
    mark="   %s (pin %dt %+.1f)"%(("OK" if m else "MISMATCH"),en,eg)
   print("  %-9s %-9s %3dt NET %+8.1f npt%+.3f DD%5.1f%s"%(tag,vn,len(trf),net,net/max(len(trf),1),stats(trf)["dd"],mark),flush=True)
 if not ok:raise SystemExit("FINE PIN MISMATCH - abort before curfew analysis")
 print(flush=True)
 # ---------- join helpers (same convention as exp43; HTF side is variant-independent) ----------
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
 # ---------- PHASE 2 (RQ4): curfew canary - no trade may sit in the skipped band ----------
 print("PHASE A - curfew canary: recomputed age of every curfew-run trade (must be <a or >=b)",flush=True)
 for tag,swh,kw in LANEDEF:
  for vn,a,b in VARIANTS:
   if not vn.startswith("curf"):continue
   trf=led[(tag,vn)]["ltf_trades"]
   inband=0
   for t in trf:
    ag=_age_of(t,tag)
    if ag is not None and a<=ag<b:inband+=1
   print("  %-9s %-9s %3dt | in-band violations: %d"%(tag,vn,len(trf),inband),flush=True)
 print(flush=True)
 # ---------- PHASE 3 (RQ3): segmented walk-forward on all ledgers ----------
 K=6
 ts0=min(c1h[0]["ts"],c15[0]["ts"]);ts1=max(c1h[-1]["ts"],c15[-1]["ts"])
 step=(ts1-ts0)/float(K)
 print("PHASE B - walk-forward (6 segs ~%.0fd, fixed configs, fine NET)"%((ts1-ts0)/86400.0/K),flush=True)
 out2=[]
 for tag,swh,kw in LANEDEF:
  for vn,a,b in VARIANTS:
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
   print("  %-9s %-9s %3dt NET %+8.1f | segs "%(tag,vn,len(trf),_net(trf))+" ".join("%+6.1f"%x for x in nets)+" | worst %+6.1f | H1/H2 %+7.1f/%+7.1f"%(worst,h1,h2),flush=True)
   out2.append(dict(lane=tag,variant=vn,n=len(trf),net=round(_net(trf),1),segs=[round(x,1)for x in nets],worst_seg=round(worst,1),h1=round(h1,1),h2=round(h2,1)))
 (ROOT/"backtest/tests/_exp44_results.json").write_text(json.dumps({"wf":out2},indent=1))
 print(flush=True)
 print("(exp44 done %.0fs)"%(time.time()-t0),flush=True)
if __name__=="__main__":main()


