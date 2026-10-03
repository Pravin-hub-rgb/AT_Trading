"""Independent: re-derive every pin FROM THE ENGINE, not from any stored JSON."""
import sys, json, pathlib
R=pathlib.Path(r"c:\Users\Pravin\Desktop\main\AT_Trading")
for s in ("backtest/tests","backtest","backend"): sys.path.insert(0,str(R/s))
sys.path.insert(0,str(R))
import run_experiment as re_
from src.btc.btc_routes import _trade_costs,_net_stats
from src.btc.btc_engine import trade_stats
import experiment_registry as reg
d=re_.get_data(); sim=re_.build_module()
OUT=R/"_final.json"; res={}
def flush(): OUT.write_text(json.dumps(res,indent=1),encoding="utf-8")
for i,k in enumerate([k for k in reg.EXPERIMENTS if isinstance(reg.EXPERIMENTS[k],dict)],1):
    cfg=reg.EXPERIMENTS[k]
    try:
        sw=re_.get_swings(d,cfg["swing"])
        fine=d["fine"] if cfg.get("basis","fine")=="fine" else []
        tr=sim(d["c1h"],sw,d["c15"],d["sw15"],fine_ltf=fine,**{**dict(re_.BP),**cfg["params"]})["ltf_trades"]
        _trade_costs(tr,0.055,2,0.005,0.01,0.01)
        nt=_net_stats(trade_stats(tr),tr)["net_total_r"]; dd=re_._net_dd(tr)
        p=cfg.get("pins",{})
        ok=(p.get("n")==len(tr) and abs((p.get("net") or 0)-nt)<0.5 and abs((p.get("dd_net") or 0)-dd)<0.5)
        res[k]={"n":len(tr),"net":round(nt,2),"dd":round(dd,2),"OK":ok}
        if not ok: print("  MISMATCH %-28s engine %d/%.2f/%.2f  pin %s/%.2f/%.2f"%(k,len(tr),nt,dd,p.get("n"),p.get("net") or 0,p.get("dd_net") or 0),flush=True)
    except Exception as e:
        res[k]={"err":repr(e)[:100],"OK":False}
    flush()
print("checked %d books; mismatches: %d"%(len(res),sum(1 for v in res.values() if not v.get("OK"))))
