"""Was P90 next-open arm anti-causal? And what is the TRUE next-open cost?"""
import sys, os, pickle, bisect
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for p in ("backtest", "backtest/tests", "backtest/sweeps", "backend"):
    sys.path.insert(0,str(ROOT/p))
sys.path.append(str(ROOT/"backend"/"src"))
with open(Path(os.environ["TEMP"])/"at_datacache.pkl","rb") as f: d=pickle.load(f)
from src.btc.engines.htf_ltf.v19_champion import simulate_htf_ltf_streak_halt as V19
from run_experiment import net_r
from experiment_registry import BP,EXPERIMENTS
pr={**BP,**EXPERIMENTS["champion_multi_sw10"]["params"]}
p={k:v for k,v in pr.items() if k not in {"exp_mltf","exp_persist","exp_partial_r"}}
r=V19(d["c1h"],d["sw10"],d["c15"],d["sw15"],fine_ltf=d["fine"],**p)
tr=[t for t in r["ltf_trades"] if t.get("outcome")!="open"]
c15=d["c15"]; ts=[int(c["ts"]) for c in c15]
op=[float(c["open"]) for c in c15]; cl=[float(c["close"]) for c in c15]
idx={int(c["ts"]):i for i,c in enumerate(c15)}
print("P90/P91 FILL ARMS vs SHIPPED")
print("="*64)
print("  shipped entry      = close[i]      (signal bar close)")
print("  P90 arm called it   = open[i]       (signal bar OPEN)")
print("  TRUE next-open      = open[i+1]     (next bar open)")
print()
a_anti=0.0; a_true=0.0; n_diff=0; n_true_diff=0
for t in tr:
    e=int(t["entry_ts"]); i=idx.get(e)
    if i is None or i+1>=len(c15): continue
    ep=float(t["entry_price"]); sl=float(t["sl"]); rk=abs(ep-sl)
    if rk<=0: continue
    dr=1.0 if str(t["dir"]).lower().startswith("l") else -1.0
    g=float(t["r_multiple"])
    # re-R if filled at open[i]  (the ANTI-CAUSAL arm)
    def rereturn(px):
        ex=float(t["exit_price"])
        newgain=(ex-px)*dr
        nr=abs(px-sl)
        if nr<=0: return None
        return newgain/nr
    xa=rereturn(op[i]); xt=rereturn(op[i+1])
    if xa is not None:
        a_anti+=xa-g
        if abs(op[i]-ep)>1e-9: n_diff+=1
    if xt is not None:
        a_true+=xt-g
        if abs(op[i+1]-ep)>1e-9: n_true_diff+=1
print("  P90 anti-causal arm (open[i]):")
print("     trades where fill differed : %d / %d"%(n_diff,len(tr)))
print("     total R delta              : %+.1fR"%a_anti)
print()
print("  TRUE next-open arm (open[i+1]):")
print("     trades where fill differed : %d / %d"%(n_true_diff,len(tr)))
print("     total R delta              : %+.1fR"%a_true)
print()
print("  champion net = %+.2fR"%net_r(tr))