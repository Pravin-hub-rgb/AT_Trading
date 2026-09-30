import sys, os, pickle, types, bisect
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for p in ("live_stuff","live_stuff/tests","backend"):
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
iv=r.get("intervals") or []
print("windows available:",len(iv))
starts=[x[0] for x in iv]
def auc(scores,labels):
    pairs=sorted(zip(scores,labels))
    npos=sum(1 for _,l in pairs if l==1); nneg=len(pairs)-npos
    if npos==0 or nneg==0: return 0.5
    rank=0.0; i=0; ties=0.0; prev=None; cnt=0
    ssum=0.0
    ranks={}
    for idx,(s,l) in enumerate(pairs): ranks[idx]=idx+1
    sr=0.0
    for idx,(s,l) in enumerate(pairs):
        if l==1: sr+=ranks[idx]
    return (sr-npos*(npos+1)/2.0)/(npos*nneg)
rows=[]
for t in tr:
    e=int(t["entry_ts"]); j=bisect.bisect_right(starts,e)-1
    if j<0: continue
    _s,_e2,_dir,_pe,_psl=iv[j]
    if not (_s<=e<=_e2): continue
    held=int(t["bars_held"])
    bte=(_e2-e)//900+1
    outlive=1 if bte>held else 0
    since_open=(e-_s)//900
    rows.append((bte,held,outlive,since_open,int(t["r_multiple"])))
print("matched trades:",len(rows))
lab=[x[2] for x in rows]
a_post=auc([x[0] for x in rows],lab)
a_caus=auc([x[3] for x in rows],lab)
print()
print("NON-CIRCULAR CHECK")
print("  label = outlived its HTF window (post-outcome)")
print()
print("  AUC bars_to_window_end (POST-OUTCOME, circular): %.3f"%a_post)
print("  AUC bars_since_window_open (CAUSAL, knowable) : %.3f"%a_caus)
print()
print("  0.500 = no signal at all")
print()
out=[x for x in rows if x[2]==1]; inn=[x for x in rows if x[2]==0]
print("  outlived : n=%3d  net=%+8.1fR"%(len(out),sum(x[4] for x in out)))
print("  inside   : n=%3d  net=%+8.1fR"%(len(inn),sum(x[4] for x in inn)))