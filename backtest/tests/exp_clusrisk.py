import sys, os, pickle
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for p in ("backtest","backtest/tests","backtest/sweeps","backend"):
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
iv=sorted([(int(t["entry_ts"]),int(t["exit_ts"]),t) for t in tr],key=lambda x:(x[0],x[1]))
ev=[]
for a,b,t in iv: ev.append((a,1,t)); ev.append((b,-1,t))
ev.sort(key=lambda x:(x[0],x[1]))
clusters=[]; cur=[]
for ts,dl,t in ev:
    if dl==1: cur.append(t)
    else:
        if cur: clusters.append(cur); cur=[]
if cur: clusters.append(cur)
multi=[c for c in clusters if len(c)>=2]
print("WORST-CASE: all trades in a same-direction cluster hit SL together")
print("="*70)
def clusstats(sig_name,size_thresh):
    sel=[c for c in multi if len(c)>=size_thresh]
    if not sel: return
    n=sum(len(c) for c in sel)
    tot=0.0
    for c in sel:
        # simultaneous loss = all in cluster lose together
        worst=sum(float(t["r_multiple"]) for t in c)
        tot+=worst
    print("  %s:"%sig_name)
    print("     clusters=%d  trades=%d"%(len(sel),n))
    print("     if ALL hit SL same bar: %+.1fR"%(tot))
    print("     mean R per cluster    : %+.2fR"%(tot/len(sel)))
    print("     worst single cluster  : %+.2fR"%(min(sum(float(t["r_multiple"]) for t in c) for c in sel)))
    print()
clusstats("ALL overlapping clusters",2)
clusstats("clusters of 3+ only",3)
clusstats("clusters of 4+ only",4)
print("="*70)
print("PER-CLUSTER R DISTRIBUTION (all overlapping):")
vals=sorted(sum(float(t["r_multiple"]) for t in c) for c in multi)
print("  n=%d  min=%+.2f  p25=%+.2f  median=%+.2f  p75=%+.2f  max=%+.2f"%(len(vals),vals[0],vals[len(vals)//4],vals[len(vals)//2],vals[3*len(vals)//4],vals[-1]))
loss=[v for v in vals if v<0]
print()
print("  LOSING clusters: %d of %d (%.0f%%)"%(len(loss),len(vals),100.0*len(loss)/len(vals)))
print("  total R in losing clusters: %+.1fR"%sum(loss))