"""Direct: does each rule read candles AT OR AFTER the entry bar?
Read the source, then check numerically with a handful of signals."""
import sys, pathlib, datetime
R=pathlib.Path(__file__).resolve().parents[2]
for s in ("backtest/tests","backtest","backend"): sys.path.insert(0,str((R/s).resolve()))
sys.path.insert(0,str(R.resolve()))
import run_experiment as re_
from src.btc.btc_routes import _compute_swings
from src.btc.btc_engine import _collect_signals
from src.walker import FlowCandle
d=re_.get_data()
c1h=d["c1h"]; c15=d["c15"]; sw10=re_.get_swings(d,"sw10")
ts=lambda x:int(datetime.datetime.strptime(str(x)[:19],"%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc).timestamp())
def chain_at(t):
    cut=[c for c in c1h if int(c["ts"])<=t]
    f=[FlowCandle(date=c["date"],open=float(c["open"]),high=float(c["high"]),
                  low=float(c["low"]),close=float(c["close"])) for c in cut]
    return _compute_swings(f,"continuous",min_bars=10)
sigs=_collect_signals(sw10,"decisive",skip_first=True,selection="stream",candles=c15,pivot_rule="origin")
tally={r:{"same":0,"diff":0,"nolive":0} for r in ("origin","leg","leg_no_entry")}
shown=0
for s in sigs[::400]:
    bt=ts(s["bar"])
    try: live=chain_at(bt)
    except Exception: break
    c15c=[c for c in c15 if int(c["ts"])<=bt]
    for r in tally:
        got=[x for x in _collect_signals(sw10,"decisive",skip_first=True,selection="stream",candles=c15,pivot_rule=r) if ts(x["bar"])==bt]
        gl =[x for x in _collect_signals(live,"decisive",skip_first=True,selection="stream",candles=c15c,pivot_rule=r) if ts(x["bar"])==bt]
        if not got or not gl:
            tally[r]["nolive"]+=1
        elif abs(float(got[0]["swing_start_px"])-float(gl[0]["swing_start_px"]))<1e-9:
            tally[r]["same"]+=1
            if shown<3: print("   %-13s live px = %.2f  = full px  (causal)"%(r,float(gl[0]["swing_start_px"]))); shown+=1
        else:
            tally[r]["diff"]+=1
            print("   %-13s live px = %.2f  vs full px = %.2f   <-- LOOKAHEAD"%(r,float(gl[0]["swing_start_px"]),float(got[0]["swing_start_px"])))
print()
print("%-14s %8s %9s %9s"%("rule","same","differs","not-live"))
for r,v in tally.items():
    print("%-14s %8d %9d %9d"%(r,v["same"],v["diff"],v["nolive"]))
