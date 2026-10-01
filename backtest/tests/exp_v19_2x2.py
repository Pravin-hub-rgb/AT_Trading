# P114 - the 2x2 that L75/L76 of reality of champion.md asked for.
# Which of exp_mltf / exp_persist actually carries the R?
import sys, os, pickle, types, inspect
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for p in ("backtest", "backtest/tests", "backtest/sweeps", "backend"):
    sys.path.insert(0,str(ROOT/p))
sys.path.append(str(ROOT/"backend"/"src"))
import test_experiments_craze as tc
from exp_concurrency_guard import load_unseen, pf
from test_4_new_concepts import load_fine_1m as lfo
from run_experiment import net_r
from experiment_registry import BP,EXPERIMENTS
V18=(ROOT/"backend/src/btc/engines/htf_ltf/v18_streak_halt.py").read_text(encoding="latin-1")
V19=(ROOT/"backend/src/btc/engines/htf_ltf/v19_champion.py").read_text(encoding="latin-1")
def ind(s): return s[:len(s)-len(s.lstrip())]
def add_persist(lines):
    out=[]; state=0; hits=0
    for i,ln in enumerate(lines):
        out.append(ln)
        s=ln.strip()
        if s=="chop_per_ltf=[50.0]*len(candles_ltf)":
            out.append(ind(ln)+"# persist state"); out.append(ind(ln)+"_rg_s=None; _rg_c=0; PERSIST=7"); hits+=1
        if s=="# pick intervals":
            b=ind(ln)
            out.append(b+"if PERSIST>0:")
            out.append(b+"    if _rg_s is None: _rg_s=use")
            out.append(b+"    if use!=_rg_s:")
            out.append(b+"        _rg_c+=1")
            out.append(b+"        if _rg_c>=PERSIST: _rg_s=use; _rg_c=0")
            out.append(b+"    else: _rg_c=0")
            out.append(b+"    use=_rg_s")
            hits+=1
    assert hits==2, "persist anchors %d"%hits
    return out
def build(src,persist):
    s="\n".join(add_persist(src.split("\n"))) if persist else src
    m=types.ModuleType("m%d"%int(persist)); m.__file__="m.py"
    exec(compile(s,"m.py","exec"),m.__dict__)
    return m.simulate_htf_ltf_streak_halt
PR={**BP,**EXPERIMENTS["champion_multi_sw10"]["params"]}
with open(Path(os.environ["TEMP"])/"at_datacache.pkl","rb") as f: d=pickle.load(f)
(oc15,of15),(oc1h,of1h)=load_unseen("15m"),load_unseen("1h")
of=lfo(oc15[0]["ts"],oc15[-1]["ts"])
SW15=tc._compute_swings(of15,"continuous",min_bars=50)
SW1H=tc._compute_swings(of1h,"continuous",min_bars=10)
ARMS=(("gate ON,  persist OFF",V18,False),("gate ON,  persist ON ",V18,True),("gate OFF, persist OFF",V19,False),("gate OFF, persist ON ",V19,True))
def run(fn,a1h,sw1h,c15,sw15,fin):
    sig=set(inspect.signature(fn).parameters)
    p={k:v for k,v in PR.items() if k in sig}
    r=fn(a1h,sw1h,c15,sw15,fine_ltf=fin,**p)
    tr=[t for t in r["ltf_trades"] if t.get("outcome")!="open"]
    rs=[float(t["r_multiple"]) for t in tr]
    ev=[]
    for t in tr:
        ev.append((t["entry_ts"],1)); ev.append((t["exit_ts"],-1))
    ev.sort(key=lambda z:(z[0],z[1]))
    cur=mx=0
    for _,x in ev:
        cur+=x; mx=max(mx,cur)
    return len(rs),net_r(tr),pf(rs),mx
print("%-22s | %5s %10s %7s %4s | %5s %10s"%("arm","ISn","ISnet","ISPF","conc","OOSn","OOSnet"))
print("-"*76)
for nm,src,ps in ARMS:
    fn=build(src,ps)
    a=run(fn,d["c1h"],d["sw10"],d["c15"],d["sw15"],d["fine"])
    b=run(fn,oc1h,SW1H,oc15,SW15,of)
    print("%-22s | %5d %+10.2f %7.3f %4d | %5d %+10.2f"%(nm,a[0],a[1],a[2],a[3],b[0],b[1]))