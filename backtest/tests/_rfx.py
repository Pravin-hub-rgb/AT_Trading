import sys, json, pathlib
R=pathlib.Path(r"c:\Users\Pravin\Desktop\main\AT_Trading")
for s in ("backtest/tests","backtest","backend"): sys.path.insert(0,str(R/s))
sys.path.insert(0,str(R))
import exp_equity_quality as E, run_experiment as re_
from src.btc.btc_routes import _trade_costs,_net_stats
from src.btc.btc_engine import trade_stats
import experiment_registry as reg
OUT=R/"_refix.json"; res={}
def flush(): OUT.write_text(json.dumps(res,indent=1),encoding="utf-8")
sim=re_.build_module()
def measure(data,cfg):
    tr=sim(data["c1h"],data[cfg["swing"]],data["c15"],data["sw15"],fine_ltf=data["fine"],
           **{**dict(re_.BP),**cfg["params"]})["ltf_trades"]
    _trade_costs(tr,0.055,2,0.005,0.01,0.01)
    return {"n":len(tr),"net":round(_net_stats(trade_stats(tr),tr)["net_total_r"],2),"dd":round(re_._net_dd(tr),2)}
KEYS=[k for k in reg.EXPERIMENTS if isinstance(reg.EXPERIMENTS[k],dict)
      and reg.EXPERIMENTS[k].get("params",{}).get("cooldown_bars")==8
      and k.startswith("gap_")]
print("re-measuring",len(KEYS),"books",flush=True)
for scope in ("is","oos"):
    data=E.load_scope(scope)
    for k in KEYS:
        if "%s|%s"%(scope,k) in res: continue
        try: res["%s|%s"%(scope,k)]=measure(data,reg.EXPERIMENTS[k])
        except Exception as e: res["%s|%s"%(scope,k)]={"err":repr(e)[:100]}
        flush()
        r=res["%s|%s"%(scope,k)]
        print("  %-3s %-24s %s"%(scope,k,("ERR") if "err" in r else "n=%4d net=%+9.2f dd=%6.2f"%(r["n"],r["net"],r["dd"])),flush=True)
print("DONE")
