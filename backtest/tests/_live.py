"""THE TEST: for each pivot_rule, would a live trader have been able to compute
the same stop at the entry bar?

Live-recompute: rebuild the swing chain on candles cut AT the entry bar, then
recompute the stop. Compare with what the full-data chain produces.

This is the test I should have run the first time. The earlier one truncated at
swing CONFIRMATION, which proves nothing - after confirmation the chain is
frozen by definition.
"""
import sys, pathlib, datetime
R=pathlib.Path(__file__).resolve().parents[2]
for s in ("backtest/tests","backtest","backend"): sys.path.insert(0,str((R/s).resolve()))
sys.path.insert(0,str(R.resolve()))
import run_experiment as re_
from src.btc.btc_routes import _compute_swings
from src.btc.btc_engine import _collect_signals
from src.walker import FlowCandle
d=re_.get_data()
c1h=d["c1h"]; c15=d["c15"]
sw10=re_.get_swings(d,"sw10")
ts=lambda x:int(datetime.datetime.strptime(str(x)[:19],"%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc).timestamp())
def chain_at(cut_ts):
    cut=[c for c in c1h if int(c["ts"])<=cut_ts]
    f=[FlowCandle(date=c["date"],open=float(c["open"]),high=float(c["high"]),
                  low=float(c["low"]),close=float(c["close"])) for c in cut]
    return _compute_swings(f,"continuous",min_bars=10)
RULES=("origin","leg","leg_no_entry")
print("%-14s %8s %8s %8s %s"%("rule","stop@live","stop@full","match","verdict"))
print("-"*62)
tally={r:[0,0,0] for r in RULES}   # same, differ, swing-missing
sigs=_collect_signals(sw10,"decisive",skip_first=True,selection="stream",candles=c15,pivot_rule="origin")
done=0
for s in sigs[::150]:
    bt=ts(s["bar"])
    try: live_sw=chain_at(bt)
    except Exception: break
    if not live_sw: break
    for rule in RULES:
        full=_collect_signals(sw10,"decisive",skip_first=True,selection="stream",candles=c15,pivot_rule=rule)
        got=[x for x in full if ts(x["bar"])==bt]
        lv =_collect_signals(live_sw,"decisive",skip_first=True,selection="stream",candles=[c for c in c15 if int(c["ts"])<=bt],pivot_rule=rule)
        gotl=[x for x in lv if ts(x["bar"])==bt]
        if not got or not gotl:
            tally[rule][2]+=1     # the signal does not even exist live
            continue
        a=float(got[0]["swing_start_px"]); b=float(gotl[0]["swing_start_px"])
        ok=abs(a-b)<1e-9
        tally[rule][0 if ok else 1]+=1
        if done<4:
            print("%-14s %8.2f %8.2f %8s %s"%(rule,b,a,"yes" if ok else "NO",
                  "live could compute it" if ok else "LOOKAHEAD: live cannot"))
            done+=1
print()
print("%-14s %10s %10s %s"%("rule","same","differs","not-live"))
for r in RULES:
    s,df,nm=tally[r]
    print("%-14s %10d %10d %d"%(r,s,df,nm))
