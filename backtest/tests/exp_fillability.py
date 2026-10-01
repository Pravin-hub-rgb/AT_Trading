import sys, os, pickle, types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for p in ("backtest","backtest/tests","backtest/sweeps","backend"):
    sys.path.insert(0,str(ROOT/p))
sys.path.append(str(ROOT/"backend"/"src"))
with open(Path(os.environ["TEMP"])/"at_datacache.pkl","rb") as f: d=pickle.load(f)
from run_experiment import net_r
from experiment_registry import BP,EXPERIMENTS
src=(ROOT/"backend/src/btc/engines/htf_ltf/v19_champion.py").read_text(encoding="utf-8")
m=types.ModuleType("v"); m.__file__="v.py"
exec(compile(src,"v.py","exec"),m.__dict__)
pr={**BP,**EXPERIMENTS["champion_multi_sw10"]["params"]}
p={k:v for k,v in pr.items() if k not in {"exp_mltf","exp_persist","exp_partial_r"}}
r=m.simulate_htf_ltf_streak_halt(d["c1h"],d["sw10"],d["c15"],d["sw15"],fine_ltf=d["fine"],**p)
tr=[t for t in r["ltf_trades"] if t.get("outcome")!="open"]
c15=d["c15"]
idx={int(c["ts"]):i for i,c in enumerate(c15)}
n_same=0; n_diff=0; fav_r=0.0; unfav_r=0.0; tot_r=0.0; miss=0
for t in tr:
    e=int(t["entry_ts"]); i=idx.get(e)
    if i is None or i+1>=len(c15):
        miss+=1; continue
    close_i=float(c15[i]["close"]); open_next=float(c15[i+1]["open"])
    ep=float(t["entry_price"]); sl=float(t["sl"]); rk=abs(ep-sl)
    if rk<=0:
        miss+=1; continue
    _dv=t.get("dir"); dirn=1 if str(_dv).lower().startswith("l") or _dv==1 else -1
    diff=close_i-open_next
    edge=-dirn*diff/rk
    tot_r+=edge
    if abs(diff)<1e-9: n_same+=1
    else:
        n_diff+=1
        if edge>0: fav_r+=edge
        else: unfav_r+=edge
print("FILLABILITY: is bar.close a price we could actually get?")
print()
print("  trades checked        :",len(tr))
print("  no next bar (skipped) :",miss)
print("  close[i] == open[i+1] : %d  (%.1f%%)"%(n_same,100.0*n_same/max(1,len(tr))))
print("  close[i] != open[i+1] : %d  (%.1f%%)"%(n_diff,100.0*n_diff/max(1,len(tr))))
print()
print("  FAVOURABLE gaps (close was better for us): %+.2fR"%fav_r)
print("  ADVERSE   gaps (close was worse for us) : %+.2fR"%unfav_r)
print("  NET EDGE from close-fill                : %+.2fR"%tot_r)
print()
print("  champion reported                        : %+.2fR"%net_r(tr))
print("  if next-open fill were used             : %+.2fR"%(net_r(tr)-tot_r))
