"""FS-EXIT experiment (direction-matched): enter exactly as the book does,
exit when THIS trade's own swing confirms. Sweeps the gap gate on IS and OOS, plus the 1h/4h/15m leg counts.
The knob now lives in the production engine (unified.py), default -1 = off."""
import sys, pathlib, json
R=pathlib.Path(r"c:\Users\Pravin\Desktop\main\AT_Trading")
for s in ("backtest/tests","backtest","backend"): sys.path.insert(0,str(R/s))
sys.path.insert(0,str(R))
import exp_equity_quality as E, run_experiment as re_
from src.btc.btc_routes import _trade_costs
BASE=dict(re_.BP); BASE.update(mode="atr_high",atr_high_thresh=0.65,atr_low_thresh=0.35,
 sl_buf_atr=0.01,chop_thresh=58.0,cooldown_bars=8,max_consecutive_losses=3,
 ext_stop_r=3.0,exp_partial_r=0.0,exp_persist=7,window_end="exit",pivot_rule="leg",exp_mltf=True)
sim=re_.build_module()
def run(scope,knobs):
    d=E.load_scope(scope); o=dict(BASE); o.update(knobs)
    out=sim(d["c1h"],d["sw10"],d["c15"],d["sw15"],fine_ltf=d["fine"],**o)
    tr=out["ltf_trades"]; _trade_costs(tr,0.055,2,0.005,0.01,0.01)
    eq=0.0; pk=0.0; dd=0.0; n=0; nf=0
    for t in tr:
        if t.get("outcome")=="open": continue
        n+=1
        if t.get("fk")=="fs_exit" or t.get("outcome")=="fs_exit": nf+=1
        eq+=float(t.get("r_multiple",0.0))-float(t.get("cost_r",0.0))
        pk=max(pk,eq); dd=max(dd,pk-eq)
    st={}
    return {"n":n,"net":eq,"dd":dd,"per":eq/max(n,1),"fs_exits":nf}
ARMS=[("control (no FS exit)",-1.0),
      ("exit on ANY FS",0.0),
      ("exit if gap <= 2h",2.0),
      ("exit if gap <= 4h",4.0),
      ("exit if gap <= 6h",6.0),
      ("exit if gap <= 8h",8.0),
      ("exit if gap <= 12h",12.0),
      ("exit if gap <= 24h",24.0)]
print("%-24s %-26s %-26s"%("arm","IS  (n / net R / DD / per)","OOS (n / net R / DD / per)"))
print("-"*80)
res={}
for name,g in ARMS:
    a=run("is",{"exit_fs_max_gap_h":g}); b=run("oos",{"exit_fs_max_gap_h":g})
    res[name]={"is":a,"oos":b}
    print("%-24s %4d /%+8.2f /%6.1f /%+.3f      %4d /%+8.2f /%6.1f /%+.3f   (fs_exits %d/%d)"
          %(name,a["n"],a["net"],a["dd"],a["per"],b["n"],b["net"],b["dd"],b["per"],a["fs_exits"],b["fs_exits"]))
(R/"backtest"/"tests"/"_fs_exit_results.json").write_text(json.dumps(res,indent=1),encoding="utf-8")
print()
print("=== 15m / 1h / 4h leg volume, champion multi ===")
d=E.load_scope("is")
for tag,key in (("HTF 1h book","sw10"),):
    print("  %s swings: %d"%(tag,len(d[key])))
print("  LTF 15m swings: %d"%len(d["sw15"]))
print("  IS trades      : %d"%res["control (no FS exit)"]["is"]["n"])
