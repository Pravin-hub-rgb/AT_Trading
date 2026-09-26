"""Exp 43 — loss autopsy + runner preservation + parent-window diagnostics.

Origin: research-methods review + the structural fact that this strategy is
TAIL-DEPENDENT: many small losses paid for by rare big runners (>=4R). Before
inventing another filter, MEASURE the structure. Research questions:

  RQ1 (wage-gate bug canary): recompute every trade's window age with the same
      join the gate uses; EVERY trade in a real w24 ledger must recompute
      age >= 24h. Any miss = join drift (bug alarm).
  RQ2 (decomposition): per lane, what exactly does the w24 gate remove —
      n / gross / net / WR / median / tail counts / R by year? Systematic
      early-window-failure removal, or one lucky cluster?
  RQ3 (runner preservation): how many >=3R/>=4R/>=5R/>=10R runners sit in the
      removed young bucket? (the "amputating the tail" check)
  RQ4 (mechanism split): actual w24 NET delta vs post-hoc removal delta.
      The pre-fill gate ALSO shifts busy/cooldown chains — how much of the
      effect is removal vs re-timing?
  RQ5 (HTF side): do LTF trades inherit the parent window's fate? LTF avg R
      by parent-HTF outcome x window-age bucket — is there causal HTF-side
      structure LEFT after wage+ext, or is the window set already squeezed?

Process rules (EXP40C doc §12): gates before results (identity gate + user
coarse matrix + 8 fine pins to exp40c/exp42 Phase C), harness kept on disk,
separate doc (EXP43_LOSS_AUTOPSY.md), fine NET everywhere, nothing deleted.
"""
import sys,time,json,bisect
from pathlib import Path
from collections import Counter
import datetime
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"live_stuff/tests"))
sys.path.insert(0,str(ROOT/"live_stuff"))
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
WAGE=24.0
TAILS=(2.0,3.0,4.0,5.0,10.0)
# fine pins: exp40c Phase C + exp42 Phase 1 (all ext1.5)
# POST trail-fix ee574f9 (2026-09-21): fine nets shifted ~-26R vs pre-fix
# exp40c/exp42 values; n and DD unchanged. Re-baselined from exp43 re-run.
PINS={("lb30",0):(349,170.5),("lb30",24):(265,159.1),
      ("A4",0):(359,177.5),("A4",24):(261,197.3),
      ("OPT-cd10",0):(453,233.5),("OPT-cd10",24):(326,311.8),
      ("lb14",0):(351,122.1),("lb14",24):(272,167.8)}
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
 # ---------- PHASE 0: gates (identity + user matrix; abort on fail) ----------
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
 # ---------- PHASE 1: fine ledgers (4 lanes x w0/w24) ----------
 fine=_load_fine_1m(min(c1h[0]["ts"],c15[0]["ts"]),max(c1h[-1]["ts"],c15[-1]["ts"]),symbol=INSTRUMENT)
 LANEDEF=[("lb30",sw20,LB30),("A4",sw10,A4),("lb14",sw20,LB14),("OPT-cd10",sw10,OPT10)]
 led={}
 for tag,swh,kw in LANEDEF:
  for w in (0,WAGE):
   wage={"exp_wage_h":w} if w else {}
   r=sim(c1h,swh,c15,sw15,fine_ltf=fine,**{**BP,**kw,**wage,"ext_stop_r":1.5})
   led[(tag,w)]=r
   trf=r["ltf_trades"];net=_net(trf);mark=""
   if (tag,int(w)) in PINS:
    en,eg=PINS[(tag,int(w))];m=(len(trf)==en and abs(net-eg)<=0.15);ok=ok and m
    mark="   %s (pin %dt %+.1f)"%(("OK" if m else "MISMATCH"),en,eg)
   print("  %-9s w%-4.0f %3dt NET %+8.1f DD%5.1f%s"%(tag,w,len(trf),net,stats(trf)["dd"],mark),flush=True)
 if not ok:raise SystemExit("FINE PIN MISMATCH - abort before autopsy")
 print(flush=True)
 # ---------- window joins per lane (from the w0 run; HTF side is wage-independent) ----------
 def _ivs(htf):
  iv=[(int(t["entry_ts"]),int(t["exit_ts"]),1 if t["dir"]=="long" else -1,float(t.get("r_multiple") or 0.0))
      for t in htf if t.get("outcome")!="open"]
  iv.sort();return iv,[w[0] for w in iv]
 JOIN={}
 for tag,swh,kw in LANEDEF:
  rf=led[(tag,0)]
  ivf,sf=_ivs(rf["htf_trades"]);ivb,sb=_ivs(rf["htf_trades_b2"])
  JOIN[tag]=(ivf,sf,ivb,sb)
 def _find(iv,st,ts,td):
  j=bisect.bisect_right(st,ts)-1
  if j>=0 and iv[j][0]<ts<=iv[j][1] and iv[j][2]==td:return iv[j]
  return None
 def _age_of(t,tag):
  """same-lane if the trade carries the regime tag, else canonical
  (dir-matched flip, then dir-matched b2). Returns (age_h, parent_r|None)."""
  ts=int(t["entry_ts"]);td=1 if t["dir"]=="long" else -1
  ivf,sf,ivb,sb=JOIN[tag]
  reg=t.get("htf_regime")
  if reg in ("flip","b2"):
   iv,st=(ivf,sf) if reg=="flip" else (ivb,sb)
   w=_find(iv,st,ts,td)
   if w is not None:return (ts-w[0])/3600.0,w[3]
  w=_find(ivf,sf,ts,td)
  if w is not None:return (ts-w[0])/3600.0,w[3]
  w=_find(ivb,sb,ts,td)
  if w is not None:return (ts-w[0])/3600.0,w[3]
  return None,None
 def _bucket(tr):
  rs=[float(t["r_multiple"])for t in tr]
  c2,_=_trade_costs(tr,_g["fee_pct"],0.0,_g["entry_slip_pct"],_g["exit_slip_pct"])
  return dict(n=len(tr),gross=round(sum(rs),1),net=round(sum(rs)-c2-fund(tr),1),
              wr=round(100.0*sum(1 for r in rs if r>0)/max(len(rs),1),1),
              med=round(sorted(rs)[len(rs)//2],2) if rs else 0.0,
              tails={">=%.0fR"%th:(sum(1 for r in rs if r>=th),round(sum(r for r in rs if r>=th),1)) for th in TAILS})
 # ---------- PHASE 2 (RQ1): wage-join bug canary ----------
 print("PHASE A - RQ1 join canary: recomputed age of every w24-ledger trade (must all be >=24h)",flush=True)
 for tag,swh,kw in LANEDEF:
  tr24=led[(tag,WAGE)]["ltf_trades"]
  aged=[_age_of(t,tag)[0] for t in tr24]
  known=sum(1 for a in aged if a is not None);miss=sum(1 for a in aged if a is not None and a<WAGE)
  tagged=sum(1 for t in tr24 if t.get("htf_regime") in ("flip","b2"))
  print("  %-9s w24 ledger %3dt | aged %3d (tagged-in-trade %3d) | age<24h violations: %d"%(tag,len(tr24),known,tagged,miss),flush=True)
 print(flush=True)
 # ---------- PHASE 3 (RQ2+RQ3): decompose what w24 removes, per lane ----------
 print("PHASE B - RQ2/RQ3: w24 decomposition (post-hoc partition of the w0 ledger)",flush=True)
 outB=[]
 for tag,swh,kw in LANEDEF:
  tr0=led[(tag,0)]["ltf_trades"]
  young=[];old=[];none_=0
  for t in tr0:
   a,_=_age_of(t,tag)
   if a is None:none_+=1
   elif a<WAGE:young.append(t)
   else:old.append(t)
  yb=_bucket(young);base=_bucket(tr0)
  actual24=_net(led[(tag,WAGE)]["ltf_trades"])
  d_actual=round(actual24-base["net"],1);d_removal=round(-yb["net"],1)
  chain=round(d_actual-d_removal,1)
  yr={}
  for t in young:
   y=datetime.datetime.utcfromtimestamp(int(t["entry_ts"])).year
   yr[y]=round(yr.get(y,0.0)+float(t["r_multiple"]),1)
  print("  %-9s w0 %3dt net%+7.1f | w24-run net%+7.1f (d_act %+6.1f) | removed<24h: %3dt g%+7.1f net%+7.1f WR%4.1f%% med%+5.2f | d_removal %+6.1f -> chain-shift %+6.1f"%(tag,base["n"],base["net"],actual24,d_actual,yb["n"],yb["gross"],yb["net"],yb["wr"],yb["med"],d_removal,chain),flush=True)
  print("            removed tails: "+"  ".join("%s:%d(%+.1f)"%(k,v[0],v[1]) for k,v in yb["tails"].items()),flush=True)
  print("            removed R by year: "+"  ".join("%d:%+7.1f"%(k,v) for k,v in sorted(yr.items())),flush=True)
  outB.append(dict(lane=tag,base=base,actual24=round(actual24,1),d_actual=d_actual,young=yb,
                   d_removal=d_removal,chain_shift=chain,removed_by_year={str(k):v for k,v in sorted(yr.items())}))
 print(flush=True)
 # ---------- PHASE 4 (RQ5): parent-window inheritance (w0 ledgers) ----------
 print("PHASE C - RQ5: parent-window inheritance on w0 ledgers (lb30 + champion OPT-cd10)",flush=True)
 outC=[]
 for tag in ("lb30","OPT-cd10"):
  tr0=led[(tag,0)]["ltf_trades"]
  pb={"htf_win":[],"htf_loss":[],"htf_other":[]}
  ag={};AGEB=(0,6,12,24,48,10**9)
  for t in tr0:
   a,pr=_age_of(t,tag);rs=float(t["r_multiple"])
   k="htf_win" if (pr is not None and pr>=2.0) else ("htf_loss" if (pr is not None and pr<=-0.5) else "htf_other")
   pb[k].append(rs)
   if a is not None:
    for i in range(len(AGEB)-1):
     if AGEB[i]<=a<AGEB[i+1]:
      ag.setdefault("%d-%dh"%(AGEB[i],AGEB[i+1]) if AGEB[i+1]<10**8 else ">=48h",[]).append(rs);break
  print("  %-9s parent HTF won (r>=2): %3dt avgR%+5.2f sum%+8.1f | parent HTF lost: %3dt avgR%+5.2f sum%+8.1f | other: %3dt"%(tag,len(pb["htf_win"]),sum(pb["htf_win"])/max(len(pb["htf_win"]),1),sum(pb["htf_win"]),len(pb["htf_loss"]),sum(pb["htf_loss"])/max(len(pb["htf_loss"]),1),sum(pb["htf_loss"]),len(pb["htf_other"])),flush=True)
  for k in sorted(ag,key=lambda s:int(s.split("-")[0]) if s[0].isdigit() else 999):
   v=ag[k]
   print("    age %-8s %3dt sumR%+8.1f avgR%+5.2f WR%4.1f%%"%(k,len(v),sum(v),sum(v)/max(len(v),1),100.0*sum(1 for r in v if r>0)/max(len(v),1)),flush=True)
  outC.append(dict(lane=tag,parent_groups={k:dict(n=len(v),sumR=round(sum(v),1)) for k,v in pb.items()},
                   age_buckets={k:dict(n=len(v),sumR=round(sum(v),1),avgR=round(sum(v)/max(len(v),1),2)) for k,v in ag.items()}))
 print(flush=True)
 (ROOT/"live_stuff/tests/_exp43_results.json").write_text(json.dumps({"decomp":outB,"parent":outC},indent=1))
 print("(exp43 done %.0fs)"%(time.time()-t0),flush=True)
if __name__=="__main__":main()




