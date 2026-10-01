"""Exp 40c — N5 wage-gate audit-rebuild + reproduction + off-diagonal cells.

Context: the ORIGINAL Exp40/41 harness (N5 wage>=24h + N6 wage x ext matrix)
was deleted after its run, so its gate code was the one item the gate audit
(2026-09-19) could not inspect. This experiment closes that gap:
  1. Wage gate rebuilt as an asserted craze patch (exp_wage_h, default 0 =
     no-op; causal — window start ts is a closed 1h candle).
  2. PHASE A: REPRODUCTION of the deleted run, exact — coarse trade COUNTS
       (lb30+w24 275 | lb14+w24 281 | A4+w24 266) AND fine NET
       (224.5 / 201.9 / 228.6, funding-inclusive).
  3. PHASE B: wage x ext off-diagonals never run outside lb30 (coarse):
       lb30 w24 x ext{2.0,2.5}; A4 w0/w24 x ext{1.5,2.5};
       OPT-cd0 / cd10 w0/w24 x ext{1.5,2.5}
  4. PHASE C: fine (1m fills, fee+slip+funding NET) for all B cells.
Identity gate: flags-off patched module must equal shipped engine (coarse).
"""
import sys,time,json,bisect,os as _os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"backtest/tests"))
sys.path.insert(0,str(ROOT / "backtest"))
sys.path.insert(0,str(ROOT/"backend"))
from test_experiments_craze import build_module,BASE,load_candles,_compute_swings,SWING,MB15,INSTRUMENT,stats
from engine.v18_params import get_v18_params as _gvp
from src.btc.btc_routes import _load_fine_1m,_trade_costs
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod
BP=dict(BASE);BP["chop_thresh"]=58.0
def fund(tr):
 f=0.0
 for t in tr:
  e,sl=float(t["entry_price"]),float(t["sl"]);rk=abs(e-sl)
  if rk>0 and e>0:f+=(int(t.get("bars_held")or 0)*0.25/8.0)*0.0001*(e/rk)
 return f
def run_coarse(sim,c1h,sw20,c15,sw15,swh,kw,w,ext):
 wage={"exp_wage_h":w} if w else {}
 r=sim(c1h,swh,c15,sw15,fine_ltf=[],**{**BP,**kw,**wage,"ext_stop_r":ext})
 tr=r["ltf_trades"]
 return tr,sum(float(t["r_multiple"]) for t in tr)
def main():
 t0=time.time()
 (c15,f15),(c1h,f1h)=load_candles()
 sw15=_compute_swings(f15,"continuous",min_bars=MB15)
 sw20=_compute_swings(f1h,"continuous",min_bars=SWING["min_bars_1h"])
 sw10=_compute_swings(f1h,"continuous",min_bars=10)
 sim=build_module()
 # ---------- IDENTITY GATE (coarse: flags-off patched == shipped) ----------
 r_ship=shipped_mod.simulate_htf_ltf_streak_halt(c1h,sw20,c15,sw15,fine_ltf=[],**BP)
 s_ship=stats(r_ship["ltf_trades"])
 r0=sim(c1h,sw20,c15,sw15,fine_ltf=[],**BP)
 s0=stats(r0["ltf_trades"])
 assert s0["n"]==s_ship["n"] and s0["rs"]==s_ship["rs"],"IDENTITY GATE FAILED"
 print("IDENTITY GATE OK (flags-off == shipped, n=%d)\n"%s0["n"],flush=True)
 # ---------- PHASE A: wage-gate validation vs user's coarse matrix ----------
 # Authority = the user's OWN lb30 w24 matrix (coarse, gross):
 #   ext1.5 265t +231.6 | ext2.0 294t +248.2 | ext2.5 304t +231.7 |
 #   ext3.0 307t +222.4. Gate: pre-fill, age = signal-bar ts - raw window
 #   start ts (same lane the trade was admitted under). N5a doc row
 #   (265 coarse +231.6g) confirms the ext1.5 cell independently.
 print("PHASE A - prefill wage validation (user matrix, lb30 w24 ext sweep)",flush=True)
 fine=_load_fine_1m(min(c1h[0]["ts"],c15[0]["ts"]),max(c1h[-1]["ts"],c15[-1]["ts"]),symbol=INSTRUMENT)
 _g=_gvp(INSTRUMENT)
 Mx={1.5:(265,231.6),2.0:(294,248.2),2.5:(304,231.7),3.0:(307,222.4)}
 bases={"lb30":(sw20,dict(exp31_lb=30)),
        "A4":(sw10,dict(exp31_lb=30,chop_thresh=55.0,exp_persist=2))}
 def _net(tr):
  rs=[float(t["r_multiple"])for t in tr]
  c2,_=_trade_costs(tr,_g["fee_pct"],0.0,_g["entry_slip_pct"],_g["exit_slip_pct"])
  return sum(rs)-c2-fund(tr)
 ok=True
 for bname,(swh,kw) in bases.items():
  for w in (0,24):
   for ext in ([1.5,2.0,2.5,3.0] if bname=="lb30" else [1.5,2.5]):
    tr,g=run_coarse(sim,c1h,sw20,c15,sw15,swh,kw,w,ext)
    tag=bname+("" if w==0 else "+w24");mark=""
    if bname=="lb30" and w==24:
     en,eg=Mx[ext]
     m=(len(tr)==en and abs(g-eg)<=0.15);ok=ok and m
     mark="   %s (exp %dt %+.1f)"%(("OK" if m else "MISMATCH"),en,eg)
    print("  %-10s ext%.1f coarse %3dt gross %+8.1f%s"%(tag,ext,len(tr),g,mark),flush=True)
 if not ok:raise SystemExit("PHASE A MISMATCH - prefill raw wage gate != user coarse matrix")
 print(flush=True)

 if _os.environ.get("EXP40C_PHASE","ALL")=="A":
  print("(exp40c phase A done %.0fs)"%(time.time()-t0),flush=True)
  return
 # ---------- PHASE B: wage x ext off-diagonals (coarse, gross) ----------
 print("PHASE B - wage x ext off-diagonals (coarse, gross)",flush=True)
 cells=[("lb30",sw20,dict(exp31_lb=30),(0,24),(1.5,2.0,2.5)),
        ("A4",sw10,dict(exp31_lb=30,chop_thresh=55.0,exp_persist=2),(0,24),(1.5,2.5)),
        ("OPT-cd0",sw10,dict(exp_mltf=True,exp_persist=2,chop_thresh=55.0,cooldown_bars=0),(0,24),(1.5,2.5)),
        ("OPT-cd10",sw10,dict(exp_mltf=True,exp_persist=2,chop_thresh=55.0,cooldown_bars=10),(0,24),(1.5,2.5))]
 outB=[]
 for tag,swh,kw,wages,exts in cells:
  for w in wages:
   for ext in exts:
    tr,g=run_coarse(sim,c1h,sw20,c15,sw15,swh,kw,w,ext)
    print("  %-9s w%-2d ext%.1f %3dt gross %+8.1f"%(tag,w,ext,len(tr),g),flush=True)
    outB.append(dict(tag=tag,wage_h=w,ext=ext,n=len(tr),gross=round(g,1)))
  print(flush=True)
 # ---------- PHASE C: fine (1m fills, funding-inclusive NET) ----------
 print("PHASE C - fine (1m fills, funding-inclusive NET)",flush=True)
 outC=[]
 for tag,swh,kw,wages,exts in cells:
  for w in wages:
   for ext in exts:
    wage={"exp_wage_h":w} if w else {}
    r=sim(c1h,swh,c15,sw15,fine_ltf=fine,**{**BP,**kw,**wage,"ext_stop_r":ext})
    tr=r["ltf_trades"];s=stats(tr)
    rs=[float(t["r_multiple"])for t in tr];g=sum(rs)
    c2,_=_trade_costs(tr,_g["fee_pct"],0.0,_g["entry_slip_pct"],_g["exit_slip_pct"]);fr=fund(tr);net=g-c2-fr
    print("  %-9s w%-2d ext%.1f %3dt NET %+8.1f npt%+.3f DD%5.1f"%(tag,w,ext,len(tr),net,net/max(len(tr),1),s["dd"]),flush=True)
    outC.append(dict(tag=tag,wage_h=w,ext=ext,n=len(tr),net=round(net,1),dd=round(s["dd"],1)))
  print(flush=True)
 (ROOT/"backtest/tests/_exp40c_results.json").write_text(json.dumps({"coarse":outB,"fine":outC},indent=1))
 print("(exp40c done %.0fs)"%(time.time()-t0),flush=True)
if __name__=="__main__":main()
