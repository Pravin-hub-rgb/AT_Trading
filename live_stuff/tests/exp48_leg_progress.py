"""Exp 48 - price-space autopsy + leg-progress gate (the "relative to price" family).

Origin: user observation - 2023 BTC ~20k vs 2024 ~100k; R-multiples are already
risk-relative, but our gates so far measure TIME from window start (wage/
curfew/defer). The untested axis is PRICE-space: how far has the whole
same-direction LEG already moved, in units of the current window's risk.

  leg anchor = first window of the current same-dir streak (causal - all
               past, closed windows)
  progress R = (signal_close - leg_anchor)*d / |pe-psl|   (window risk units)

  RQ1 (autopsy): bucket w0 trades by leg-progress (and pullback off the leg
      extreme) - where in price-space do winners/losers live?
  RQ2 (gate): skip signals whose leg progress > X, X in {4,6,8,10,12}, on
      lb30 + A4 at ext1.5 - does cutting late-leg entries help like the
      time-space curfew did?
  RQ3: canary (no kept trade above its threshold) + WF of the cells.
Gates first: identity + user coarse matrix + 4 fine pins. Nothing deleted.
NOTE: v2 of this harness - v1 had a nested-loop bug (documented in §18).
"""
import sys,time,json,bisect
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"live_stuff/tests"))
sys.path.insert(0,str(ROOT/"live_stuff"))
sys.path.insert(0,str(ROOT/"backend"))
from exp40c_wage_gate import BP,fund,run_coarse
from test_experiments_craze import build_module,load_candles,_compute_swings,SWING,MB15,INSTRUMENT,stats
from engine.v18_params import get_v18_params as _gvp
from src.btc.btc_routes import _load_fine_1m,_trade_costs
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod
A4=dict(exp31_lb=30,chop_thresh=55.0,exp_persist=2)
LB30=dict(exp31_lb=30)
GATES=[4.0,6.0,8.0,10.0,12.0]
# POST trail-fix ee574f9: fine nets ~-26R vs pre-fix exp40c pins; n unchanged.
PINS={("lb30","w0"):(349,170.5),("lb30","w24"):(265,159.1),
      ("A4","w0"):(359,177.5),("A4","w24"):(261,197.3)}
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
 # ---------- PHASE 0: gates ----------
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
 # ---------- PHASE 1: w0 ledgers + leg-info helper ----------
 fine=_load_fine_1m(min(c1h[0]["ts"],c15[0]["ts"]),max(c1h[-1]["ts"],c15[-1]["ts"]),symbol=INSTRUMENT)
 hts=[int(c["ts"]) for c in c1h]
 hhi=[float(c["high"]) for c in c1h];hlo=[float(c["low"]) for c in c1h]
 LANEDEF=[("lb30",sw20,LB30),("A4",sw10,A4)]
 led={}
 def _ivs(htf):
  iv=[(int(t["entry_ts"]),int(t["exit_ts"]),1 if t["dir"]=="long" else -1,
       float(t["entry_price"]),float(t["sl"])) for t in htf if t.get("outcome")!="open"]
  iv.sort();return iv,[w[0] for w in iv]
 JOIN={}
 for tag,swh,kw in LANEDEF:
  r=sim(c1h,swh,c15,sw15,fine_ltf=fine,**{**BP,**kw,"ext_stop_r":1.5})
  led[(tag,"w0")]=r
  trf=r["ltf_trades"];net=_net(trf);mark=""
  if (tag,"w0") in PINS:
   en,eg=PINS[(tag,"w0")];m=(len(trf)==en and abs(net-eg)<=0.15);ok=ok and m
   mark="   %s (pin %dt %+.1f)"%(("OK" if m else "MISMATCH"),en,eg)
  print("  %-5s w0 %3dt NET %+8.1f DD%5.1f%s"%(tag,len(trf),net,stats(trf)["dd"],mark),flush=True)
  ivf,sf=_ivs(r["htf_trades"]);ivb,sb=_ivs(r["htf_trades_b2"])
  JOIN[tag]=(ivf,sf,ivb,sb)
 if not ok:raise SystemExit("FINE PIN MISMATCH - abort")
 def _leginfo(t,tag):
  """(progress_R, pullback_R) via same-lane window + same-dir leg anchor."""
  ts=int(t["entry_ts"]);td=1 if t["dir"]=="long" else -1
  ivf,sf,ivb,sb=JOIN[tag]
  iv,st=(ivf,sf) if t.get("htf_regime","flip")=="flip" else (ivb,sb)
  j=bisect.bisect_right(st,ts)-1
  if j<0 or iv[j][2]!=td or not (iv[j][0]<ts<=iv[j][1]):return None
  _j=j
  while _j>0 and iv[_j-1][2]==td:_j-=1
  anc=iv[_j][0];hr=abs(iv[j][3]-iv[j][4])
  if hr<=0:return None
  li=bisect.bisect_right(hts,anc);hi=bisect.bisect_right(hts,ts)
  if hi<=li:return None
  seg_h=max(hhi[li:hi]);seg_l=min(hlo[li:hi])
  prog=(float(t["entry_price"])-anc)*td/hr
  pull=((seg_h-float(t["entry_price"]))*td/hr if td==1 else (float(t["entry_price"])-seg_l)*td/hr)
  return prog,pull
 # ---------- PHASE 2 (RQ1): price-space autopsy on w0 ledgers ----------
 print("PHASE A - price-space autopsy: avgR by leg-progress bucket (w0 ledgers)",flush=True)
 outA=[]
 for tag,swh,kw in LANEDEF:
  tr0=led[(tag,"w0")]["ltf_trades"]
  bins={};pbins={};n_info=0
  for t in tr0:
   li=_leginfo(t,tag)
   if li is None:n_info+=1;continue
   prog,pull=li
   if prog>=20:pl=">=20R"
   elif prog>=10:pl="[10,20)"
   elif prog>=6:pl="[6,10)"
   elif prog>=4:pl="[4,6)"
   elif prog>=2:pl="[2,4)"
   elif prog>=0:pl="[0,2)"
   elif prog>=-1:pl="[-1,0)"
   else:pl="<-1R"
   bins.setdefault(pl,[]).append(float(t["r_multiple"]))
   if pull<0.5:k2="off<0.5R"
   elif pull<1.5:k2="off0.5-1.5R"
   elif pull<3.0:k2="off1.5-3R"
   else:k2="off>=3R"
   pbins.setdefault(k2,[]).append(float(t["r_multiple"]))
  print("  %-5s (%d unjoinable)"%(tag,n_info),flush=True)
  for k in ("<-1R","[-1,0)","[0,2)","[2,4)","[4,6)","[6,10)","[10,20)",">=20R"):
   if k not in bins:continue
   v=bins[k]
   print("    prog %-9s %3dt avgR%+5.2f sum%+8.1f WR%4.1f%%"%(k,len(v),sum(v)/max(len(v),1),sum(v),100.0*sum(1 for r in v if r>0)/max(len(v),1)),flush=True)
  for k in ("off<0.5R","off0.5-1.5R","off1.5-3R","off>=3R"):
   if k not in pbins:continue
   v=pbins[k]
   print("    pull %-9s %3dt avgR%+5.2f sum%+8.1f WR%4.1f%%"%(k,len(v),sum(v)/max(len(v),1),sum(v),100.0*sum(1 for r in v if r>0)/max(len(v),1)),flush=True)
  outA.append(dict(lane=tag,prog={k:dict(n=len(v),avgR=round(sum(v)/max(len(v),1),2),sum=round(sum(v),1)) for k,v in bins.items()},
                   pull={k:dict(n=len(v),avgR=round(sum(v)/max(len(v),1),2),sum=round(sum(v),1)) for k,v in pbins.items()}))
 print(flush=True)
 # ---------- PHASE 3 (RQ2): legskip gate cells ----------
 print("PHASE B - legskip gate cells (skip if leg progress > X), ext1.5",flush=True)
 for tag,swh,kw in LANEDEF:
  for X in GATES:
   r=sim(c1h,swh,c15,sw15,fine_ltf=fine,**{**BP,**kw,"exp_legskip_r":X,"ext_stop_r":1.5})
   led[(tag,"g%g"%X)]=r
   trf=r["ltf_trades"];net=_net(trf)
   viol=0
   for t in trf:
    li=_leginfo(t,tag)
    if li is not None and li[0]>X:viol+=1
   print("  %-5s legskip>%-4.0f %3dt NET %+8.1f npt%+.3f DD%5.1f | in-band violations: %d"%(tag,X,len(trf),net,net/max(len(trf),1),stats(trf)["dd"],viol),flush=True)
  r=sim(c1h,swh,c15,sw15,fine_ltf=fine,**{**BP,**kw,"exp_wage_h":24.0,"ext_stop_r":1.5})
  led[(tag,"w24")]=r
  print("  %-5s w24(ref)   %3dt NET %+8.1f npt%+.3f DD%5.1f"%(tag,len(r["ltf_trades"]),_net(r["ltf_trades"]),_net(r["ltf_trades"])/max(len(r["ltf_trades"]),1),stats(r["ltf_trades"])["dd"]),flush=True)
 print(flush=True)
 # ---------- PHASE 4: WF on gate cells ----------
 K=6
 ts0=min(c1h[0]["ts"],c15[0]["ts"]);ts1=max(c1h[-1]["ts"],c15[-1]["ts"])
 step=(ts1-ts0)/float(K)
 print("PHASE C - walk-forward (6 segs ~%.0fd, fixed configs, fine NET)"%((ts1-ts0)/86400.0/K),flush=True)
 for tag,swh,kw in LANEDEF:
  for X in GATES:
   trf=led[(tag,"g%g"%X)]["ltf_trades"]
   segs=[[]for _ in range(K)]
   for t in trf:
    i=min(int((int(t["entry_ts"])-ts0)/step),K-1)
    if i<0:i=0
    segs[i].append(t)
   nets=[_net(sg) if sg else 0.0 for sg in segs]
   half=len(trf)//2
   print("  %-5s legskip>%-4.0f %3dt NET %+8.1f | segs "%(tag,X,len(trf),_net(trf))+" ".join("%+6.1f"%x for x in nets)+" | worst %+6.1f"%(min(nets)),flush=True)
 (ROOT/"live_stuff/tests/_exp48_results.json").write_text(json.dumps({"autopsy":outA},indent=1))
 print(flush=True)
 print("(exp48 done %.0fs)"%(time.time()-t0),flush=True)
if __name__=="__main__":main()


