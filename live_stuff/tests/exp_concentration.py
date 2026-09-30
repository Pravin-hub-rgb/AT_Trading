import sys, os, pickle
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[2]
for p in ("live_stuff","live_stuff/tests","backend"):
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
print("CONCENTRATION: how clustered are the concurrent positions?")
print()
# cluster = overlapping in time
iv=sorted([(int(t["entry_ts"]),int(t["exit_ts"]),t) for t in tr],key=lambda x:(x[0],x[1]))
ev=[]
for a,b,t in iv: ev.append((a,1,t)); ev.append((b,-1,t))
ev.sort(key=lambda x:(x[0],x[1]))
cur=[]; clusters=[]
for ts,d,t in ev:
    if d==1:
        cur.append(t)
        if len(cur)>=2: pass
    else:
        if cur:
            clusters.append(list(cur)); cur=[]
if cur: clusters.append(list(cur))
multi=[c for c in clusters if len(c)>=2]
print("  trades total          :",len(tr))
print("  overlap clusters      :",len(multi))
print("  trades in a cluster   : %d (%.1f%%)"%(sum(len(c) for c in multi),100.0*sum(len(c) for c in multi)/len(tr)))
print()
sizes=defaultdict(int)
for c in multi: sizes[len(c)]+=1
print("  cluster size distribution:")
for k in sorted(sizes): print("     %d concurrent: %d clusters"%(k,sizes[k]))
print()
# same-direction?
sameside=sum(1 for c in multi if len(set(str(t["dir"]) for t in c))==1)
print("  clusters entirely ONE direction: %d of %d (%.0f%%)"%(sameside,len(multi),100.0*sameside/max(1,len(multi))))
mixed=sum(1 for c in multi if len(set(str(t["dir"]) for t in c))>1)
print("  clusters with BOTH directions  : %d"%mixed)
print()
# net R of multi clusters vs singles
inC=set()
for c in multi:
    for t in c: inC.add(id(t))
multiR=sum(float(t["r_multiple"]) for t in tr if id(t) in inC)
singR=sum(float(t["r_multiple"]) for t in tr if id(t) not in inC)
nsing=len(tr)-len(inC)
print("  clustered trades: n=%d  gross %+.1fR"%(len(inC),multiR))
print("  single trades   : n=%d  gross %+.1fR"%(nsing,singR))