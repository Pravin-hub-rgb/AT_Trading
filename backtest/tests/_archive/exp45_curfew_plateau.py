"""Exp 45 - curfew edge-plateau map + the curf x ext combo (lb30 singles).

Origin: exp44 won lb30 with curf6-24 (+217.4), but (6,24) are exp43's bucket
EDGES, not tuned values - and lb30's two wins (curfew +21.1, ext2.5 +34.8)
were never combined. Two questions:

  RQ1 (plateau): does (6,24) sit on a stable region? Grid lower {4,6,8} x
      upper {24,30,36} on lb30 at ext1.5. Plateau => robust; spike => kill.
  RQ2 (combo): lb30 + curf6-24 + ext2.5 - do the two lb30 edges stack?
  RQ3 (A4 edges): A4 curf6-24/6-30 already ~tie w36h; check (4,24)/(8,24)
      neighbors for the same plateau behavior.
  RQ4: WF stability of the survivors (6 segs, fixed configs).
  Canary: 0 in-band violations for every curfew cell.

Process rules (EXP40C doc §12): identity gate + user coarse matrix + 6 fine
pins (incl. lb30 w0/w24 at BOTH ext values) before any new cell is read;
harness kept on disk; fine NET everywhere; nothing deleted.
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
# (lane, variant-name, a, b, ext) ; a=b=0 -> no curfew ; w24 uses wage knob
CELLS=[("lb30","w0",0,0,1.5),("lb30","w24",0,24,1.5),
       ("lb30","c4-24",4,24,1.5),("lb30","c6-24",6,24,1.5),("lb30","c8-24",8,24,1.5),
       ("lb30","c6-30",6,30,1.5),("lb30","c6-36",6,36,1.5),
       ("lb30","w0+e25",0,0,2.5),("lb30","w24+e25",0,24,2.5),("lb30","c6-24+e25",6,24,2.5),
       ("A4","w0",0,0,1.5),("A4","w24",0,24,1.5),
       ("A4","c4-24",4,24,1.5),("A4","c6-24",6,24,1.5),("A4","c6-30",6,30,1.5)]
PINS={("lb30","w0",1.5):(349,196.3),("lb30","w24",1.5):(265,185.0),
      ("lb30","w0+e25",2.5):(377,231.1),("lb30","w24+e25",2.5):(303,179.1),
      ("A4","w0",1.5):(359,203.3),("A4","w24",1.5):(261,223.1)}
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
 # ---------- PHASE 1: fine ledgers ----------
 fine=_load_fine_1m(min(c1h[0]["ts"],c15[0]["ts"]),max(c1h[-1]["ts"],c15[-1]["ts"]),symbol=INSTRUMENT)
 LANEDEF={"lb30":sw20,"A4":sw10}
 KW={"lb30":LB30,"A4":A4}
 led={}
 for tag,vn,a,b,ext in CELLS:
  swh=LANEDEF[tag];kw2={}
  if vn.startswith("w24"):kw2["exp_wage_h"]=float(b)
  if vn.startswith("c"):kw2["exp_curfew_a"]=float(a);kw2["exp_curfew_b"]=float(b)
  r=sim(c1h,swh,c15,sw15,fine_ltf=fine,**{**BP,**KW[tag],**kw2,"ext_stop_r":ext})
  led[(tag,vn)]=r
  trf=r["ltf_trades"];net=_net(trf);mark=""
  if (tag,vn,ext) in PINS:
   en,eg=PINS[(tag,vn,ext)];m=(len(trf)==en and abs(net-eg)<=0.15);ok=ok and m
   mark="   %s (pin %dt %+.1f)"%(("OK" if m else "MISMATCH"),en,eg)
  print("  %-5s %-10s ext%.1f %3dt NET %+8.1f npt%+.3f DD%5.1f%s"%(tag,vn,ext,len(trf),net,net/max(len(trf),1),stats(trf)["dd"],mark),flush=True)
 if not ok:raise SystemExit("FINE PIN MISMATCH - abort")
 print(flush=True)
 # ---------- join helpers (age recompute, same convention as exp43/44) ----------
 def _ivs(htf):
  iv=[(int(t["entry_ts"]),int(t["exit_ts"]),1 if t["dir"]=="long" else -1)
      for t in htf if t.get("outcome")!="open"]
  iv.sort();return iv,[w[0] for w in iv]
 JOIN={}
 for tag in LANEDEF:
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
 # ---------- PHASE 2: curfew canary (no kept trade inside its skipped band) ----------
 print("PHASE A - curfew canary",flush=True)
 for tag,vn,a,b,ext in CELLS:
  if not vn.startswith("c"):continue
  inband=0
  for t in led[(tag,vn)]["ltf_trades"]:
   ag=_age_of(t,tag)
   if ag is not None and a<=ag<b:inband+=1
  print("  %-5s %-10s %3dt | in-band violations: %d"%(tag,vn,len(led[(tag,vn)]["ltf_trades"]),inband),flush=True)
 print(flush=True)
 # ---------- PHASE 3: segmented WF (6 segs) on all cells ----------
 K=6
 ts0=min(c1h[0]["ts"],c15[0]["ts"]);ts1=max(c1h[-1]["ts"],c15[-1]["ts"])
 step=(ts1-ts0)/float(K)
 print("PHASE B - walk-forward (6 segs ~%.0fd, fixed configs, fine NET)"%((ts1-ts0)/86400.0/K),flush=True)
 out2=[]
 for tag,vn,a,b,ext in CELLS:
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
  print("  %-5s %-10s ext%.1f %3dt NET %+8.1f | segs "%(tag,vn,ext,len(trf),_net(trf))+" ".join("%+6.1f"%x for x in nets)+" | worst %+6.1f | H1/H2 %+7.1f/%+7.1f"%(worst,h1,h2),flush=True)
  out2.append(dict(lane=tag,variant=vn,ext=ext,n=len(trf),net=round(_net(trf),1),segs=[round(x,1)for x in nets],worst_seg=round(worst,1),h1=round(h1,1),h2=round(h2,1)))
 (ROOT/"backtest/tests/_exp45_results.json").write_text(json.dumps({"wf":out2},indent=1))
 print(flush=True)
 print("(exp45 done %.0fs)"%(time.time()-t0),flush=True)
if __name__=="__main__":main()


