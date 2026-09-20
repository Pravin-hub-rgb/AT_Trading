"""Exp 47 - stats board: gross/net/avgR/DD/WR + per-year NET + delta vs anchor.

Purpose: the experiment records so far published NET/DD/WF-segments; this
harness produces the FULL stats sheet for the current single-position board
(+ the multi champion as reference) in one table:
  n, gross R, costs (fee+slip), funding, NET, avg NET/trade, DD, WR,
  NET by calendar year (2023-2026, by entry), delta NET vs anchor lb30.
Gates first (identity + user coarse matrix + 5 fine pins); nothing deleted.
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
A4=dict(exp31_lb=30,chop_thresh=55.0,exp_persist=2)
LB30=dict(exp31_lb=30)
LB14=dict()
OPT10=dict(exp_mltf=True,exp_persist=2,chop_thresh=55.0,cooldown_bars=10)
# (lane-swh, knob-dict, label, curfew_a, curfew_b, defer_h, wage_h, ext)
BOARD=[
 ("lb30","ANCHOR lb30 w0 e1.5",0,0,0,0,1.5),
 ("lb30","lb30 curf6-24 e1.5",6,24,0,0,1.5),
 ("lb30","lb30 defer24 e1.5",0,0,24,0,1.5),
 ("lb30","lb30 w0 ext2.5",0,0,0,0,2.5),
 ("A4","A4 w24 e1.5",0,0,0,24,1.5),
 ("A4","A4 curf6-30 e1.5",6,30,0,0,1.5),
 ("A4","A4 defer6 e1.5",0,0,6,0,1.5),
 ("lb14","lb14 w24 e1.5",0,0,0,24,1.5),
 ("OPT-cd10","OPTcd10 w24 e1.5 (multi)",0,0,0,24,1.5),
]
PINS={("ANCHOR lb30 w0 e1.5",1.5):(349,196.3),("lb30 w0 ext2.5",2.5):(377,231.1),
      ("A4 w24 e1.5",1.5):(261,223.1),("lb14 w24 e1.5",1.5):(272,193.7),
      ("OPTcd10 w24 e1.5 (multi)",1.5):(326,337.7)}
def main():
 t0=time.time()
 (c15,f15),(c1h,f1h)=load_candles()
 sw15=_compute_swings(f15,"continuous",min_bars=MB15)
 sw20=_compute_swings(f1h,"continuous",min_bars=SWING["min_bars_1h"])
 sw10=_compute_swings(f1h,"continuous",min_bars=10)
 sim=build_module()
 _g=_gvp(INSTRUMENT)
 SWH={"lb30":sw20,"A4":sw10,"lb14":sw20,"OPT-cd10":sw10}
 KD={"lb30":LB30,"A4":A4,"lb14":LB14,"OPT-cd10":OPT10}
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
 # ---------- PHASE 1: fine stats board ----------
 fine=_load_fine_1m(min(c1h[0]["ts"],c15[0]["ts"]),max(c1h[-1]["ts"],c15[-1]["ts"]),symbol=INSTRUMENT)
 anchor_net=None;rows=[]
 for swh,lab,ca,cb,dh,wg,ext in BOARD:
  tag,_,swh2=swh,swh,SWH[swh] if isinstance(swh,str) else swh
  kw2={}
  if wg:kw2["exp_wage_h"]=float(wg)
  if ca or cb:kw2["exp_curfew_a"]=float(ca);kw2["exp_curfew_b"]=float(cb)
  if dh:kw2["exp_defer_h"]=float(dh)
  r=sim(c1h,SWH[swh],c15,sw15,fine_ltf=fine,**{**BP,**KD[swh],**kw2,"ext_stop_r":ext})
  trf=r["ltf_trades"]
  rs=[float(t["r_multiple"])for t in trf]
  c2,_=_trade_costs(trf,_g["fee_pct"],0.0,_g["entry_slip_pct"],_g["exit_slip_pct"])
  fr=fund(trf);net=sum(rs)-c2-fr
  gross=sum(rs);n=len(trf)
  dd=stats(trf)["dd"];wr=100.0*sum(1 for x in rs if x>0)/max(n,1)
  yr={}
  for t in trf:
   y=datetime.datetime.utcfromtimestamp(int(t["entry_ts"])).year
   yr[y]=round(yr.get(y,0.0)+float(t["r_multiple"]),1)
  mark=""
  if (lab,ext) in PINS:
   en,eg=PINS[(lab,ext)];m=(n==en and abs(net-eg)<=0.15);ok=ok and m
   mark="   %s (pin %dt %+.1f)"%(("OK" if m else "MISMATCH"),en,eg)
  if lab.startswith("ANCHOR"):anchor_net=net
  rows.append((lab,n,gross,c2+fr,net,net/max(n,1),dd,wr,yr,ext,mark))
 for lab,n,gross,costs,net,npt,dd,wr,yr,ext,mark in rows:
  dl=""
  if anchor_net is not None and not lab.startswith("ANCHOR"):
   dl=" | d(anchor) %+6.1f"%(net-anchor_net)
  ys="  ".join("%d:%+7.1f"%(k,v) for k,v in sorted(yr.items()))
  print("  %-26s %3dt gross%+8.1f cost%6.1f NET%+8.1f npt%+.3f DD%5.1f WR%4.1f%%%s"%(
   lab,n,gross,costs,net,npt,dd,wr,mark),flush=True)
  print("      ext%.1f  years: %s%s"%(ext,ys,dl),flush=True)
 if not ok:raise SystemExit("FINE PIN MISMATCH - abort")
 (ROOT/"live_stuff/tests/_exp47_results.json").write_text(json.dumps(
   [{"label":lab,"n":n,"gross":round(gross,1),"costs":round(costs,1),"net":round(net,1),
     "npt":round(npt,3),"dd":round(dd,1),"wr":round(wr,1),
     "years":{str(k):v for k,v in sorted(yr.items())},"ext":ext} for lab,n,gross,costs,net,npt,dd,wr,yr,ext,mark in rows],indent=1))
 print(flush=True)
 print("(exp47 done %.0fs)"%(time.time()-t0),flush=True)
if __name__=="__main__":main()

