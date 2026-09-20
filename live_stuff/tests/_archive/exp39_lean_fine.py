"""Exp39 lean fine: 7 survivors, funding-inclusive NET."""
import sys,time,json
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"live_stuff/tests"))
sys.path.insert(0,str(ROOT/"live_stuff"))
sys.path.insert(0,str(ROOT/"backend"))
from test_experiments_craze import build_module,BASE,load_candles,_compute_swings,SWING,MB15,INSTRUMENT
from engine.v18_params import get_v18_params as _gvp
from src.btc.btc_routes import _load_fine_1m,_trade_costs
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
 cfgs=[("F-anchor-lb14",sw20,dict()),("F-anchor-lb30",sw20,dict(exp31_lb=30)),("F-A4-lb30chop55mb10p2",sw10,dict(exp31_lb=30,chop_thresh=55.0,exp_persist=2)),("F-B0-lb30-halt0",sw20,dict(exp31_lb=30,max_consecutive_losses=0)),("F-B2-lb30-halt6",sw20,dict(exp31_lb=30,max_consecutive_losses=6)),("F-C1-OPT-mltf-cd0",sw10,dict(exp_mltf=True,exp_persist=2,chop_thresh=55.0,cooldown_bars=0)),("F-C2-OPT-mltf-cd10",sw10,dict(exp_mltf=True,exp_persist=2,chop_thresh=55.0,cooldown_bars=10))]
 out=[]
 for tag,swh,kw in cfgs:
  r=sim(c1h,swh,c15,sw15,fine_ltf=fine,**{**BP,**kw});tr=r["ltf_trades"]
  rs=[float(t["r_multiple"])for t in tr];g=sum(rs)
  c2,_=_trade_costs(tr,_g["fee_pct"],0.0,_g["entry_slip_pct"],_g["exit_slip_pct"]);fr=fund(tr);net=g-c2-fr
  pk=cum=dd=0.0
  for x in rs:
   cum+=x;pk=max(pk,cum);dd=max(dd,pk-cum)
  py=defaultdict(float)
  for t,x in zip(tr,rs):py[(t.get("exit_date")or t.get("entry_date")or"")[:4]]+=x
  wr=100.0*len([x for x in rs if x>0])/max(len(rs),1)
  print("  %-24s %4dt NET %+8.1f (g%+7.1f f%5.1f fd%4.1f) npt%+.3f WR%4.1f%% DD%5.1f H1%+7.1f H2%+7.1f %s"%(tag,len(tr),net,g,c2,fr,net/max(len(tr),1),wr,dd,py.get("2023",0)+py.get("2024",0),py.get("2025",0)+py.get("2026",0),{k:round(v,1)for k,v in sorted(py.items())}),flush=True)
  out.append(dict(tag=tag,n=len(tr),net=round(net,1),dd=round(dd,1)))
 (ROOT/"live_stuff/tests/_exp39_results.json").write_text(json.dumps(out,indent=1))
 print("(exp39 done %.0fs)"%(time.time()-t0),flush=True)
if __name__=="__main__":main()
