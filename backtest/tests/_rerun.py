"""Bulk rerun of every pinned book against unified.py.

Compares n and net against the recorded pin. This is the rerun - it does not
change any book, it tells us which pins still hold and which were measured on
an engine that no longer exists.
"""
import sys, pathlib, json, time
R=pathlib.Path(__file__).resolve().parents[2]
for s in ("backtest/tests","backtest","backend"): sys.path.insert(0,str((R/s).resolve()))
sys.path.insert(0,str(R.resolve()))
import run_experiment as re_
from src.btc.btc_routes import _trade_costs,_net_stats
from src.btc.btc_engine import trade_stats
d=re_.get_data(); sim=re_.build_module()
E=re_.EXPERIMENTS
rows=[]
for k,cfg in E.items():
    pins=cfg.get("pins")
    if not pins or "n" not in pins: continue
    sw=re_.get_swings(d,cfg["swing"])
    P={**dict(re_.BP),**cfg["params"]}
    fine=d["fine"] if cfg.get("basis","fine")=="fine" else []
    try:
        tr=sim(d["c1h"],sw,d["c15"],d["sw15"],fine_ltf=fine,**P)["ltf_trades"]
        _trade_costs(tr,0.055,2,0.005,0.01,0.01)
        net=_net_stats(trade_stats(tr),tr)["net_total_r"]
    except Exception as e:
        rows.append((k,pins.get("n"),pins.get("net"),None,None,"ERROR %s"%type(e).__name__))
        continue
    rows.append((k,pins.get("n"),pins.get("net"),len(tr),net,""))
    print(".",end="",flush=True)
print()
ok=bad=err=0
print("%-42s %6s %6s %9s %9s %s"%("book","pinN","gotN","pinNet","gotNet",""))
for k,pn,pnet,gn,gnet,note in rows:
    good = gn is not None and pn==gn and (pnet is None or abs(gnet-pnet)<0.5)
    if note: err+=1
    elif good: ok+=1
    else: bad+=1
    print("%-42s %6s %6s %9s %9s %s"%(k,pn,gn,pnet,gnet,"OK" if good else ("FAIL" if not note else note)),flush=True)
print()
print("reproduce: %d   mismatch: %d   error: %d   (of %d)"%(ok,bad,err,len(rows)))
pathlib.Path("_rerun_report.json").write_text(json.dumps(
    [{"key":k,"pin_n":pn,"pin_net":pnet,"got_n":gn,"got_net":g,"status":note or ("OK" if gn is not None and pn==gn and (pnet is None or abs(g-pnet)<0.5) else "FAIL")} for k,pn,pnet,gn,g,note in rows],indent=1),encoding="utf-8")
