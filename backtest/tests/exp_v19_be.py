# P113 - break-even clamp on the swing ratchet, line-based patching.
# A: champion as-is. B: ratchet snaps to entry. C: breakeven at +1R MFE.
import sys, os, pickle, types, inspect
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for p in ("backtest","backtest/tests","backtest/sweeps","backend"):
    sys.path.insert(0,str(ROOT/p))
sys.path.append(str(ROOT/"backend"/"src"))
import test_experiments_craze as tc
from exp_concurrency_guard import load_unseen, pf
from test_4_new_concepts import load_fine_1m as lfo
from run_experiment import net_r
from experiment_registry import BP,EXPERIMENTS
SRC=(ROOT/"backend/src/btc/engines/htf_ltf/v19_champion.py").read_text(encoding="latin-1")

def ind(s): return s[:len(s)-len(s.lstrip())]

def patch_clamp(lines):
    # after each ratchet assignment, snap the stop to entry
    out=[]; hits=0
    for i,ln in enumerate(lines):
        s=ln.strip()
        prev=lines[i-1].strip() if i else ""
        if s=="sl_cur=cand" and prev=="if sl_cur < cand:":
            out.append(ln); out.append(ind(ln)+"if sl_cur < entry: sl_cur = entry"); hits+=1
        elif s=="sl_cur=cand" and prev=="if cand < sl_cur:":
            out.append(ln); out.append(ind(ln)+"if sl_cur > entry: sl_cur = entry"); hits+=1
        elif s=="sl_cur_f=cand" and prev=="if sl_cur_f < cand:":
            out.append(ln); out.append(ind(ln)+"if sl_cur_f < entry: sl_cur_f = entry"); hits+=1
        elif s=="sl_cur_f=cand" and prev=="if cand < sl_cur_f:":
            out.append(ln); out.append(ind(ln)+"if sl_cur_f > entry: sl_cur_f = entry"); hits+=1
        else:
            out.append(ln)
    assert hits==4, "clamp anchors hit %d"%hits
    return out

def patch_be1r(lines):
    # once favourable excursion reaches 1R, move the stop to entry
    out=[]; hits=0
    for ln in lines:
        s=ln.strip()
        out.append(ln)
        if s=="if hi>best: best=hi":
            out.append(ind(ln)+"if best >= entry + 1.0*risk and sl_cur < entry: sl_cur = entry"); hits+=1
        elif s=="if lo<best: best=lo":
            out.append(ind(ln)+"if best <= entry - 1.0*risk and sl_cur > entry: sl_cur = entry"); hits+=1
        elif s=="if hi>best_f: best_f=hi":
            out.append(ind(ln)+"if best_f >= entry + 1.0*risk and sl_cur_f < entry: sl_cur_f = entry"); hits+=1
        elif s=="if lo<best_f: best_f=lo":
            out.append(ind(ln)+"if best_f <= entry - 1.0*risk and sl_cur_f > entry: sl_cur_f = entry"); hits+=1
    assert hits==4, "1R anchors hit %d"%hits
    return out

def build(name,patcher):
    s=SRC
    if patcher: s="\n".join(patcher(s.split("\n")))
    m=types.ModuleType(name); m.__file__=name+".py"
    exec(compile(s,name+".py","exec"),m.__dict__)
    return m.simulate_htf_ltf_streak_halt

PR={**BP,**EXPERIMENTS["champion_multi_sw10"]["params"]}
ARMS=(("A champion as-is",None),("B ratchet snaps to entry",patch_clamp),("C breakeven at +1R MFE",patch_be1r))

with open(Path(os.environ["TEMP"])/"at_datacache.pkl","rb") as f: d=pickle.load(f)
(oc15,of15),(oc1h,of1h)=load_unseen("15m"),load_unseen("1h")
of=lfo(oc15[0]["ts"],oc15[-1]["ts"])
SW15=tc._compute_swings(of15,"continuous",min_bars=50)
SW1H=tc._compute_swings(of1h,"continuous",min_bars=10)

def show(tag,fn,a1h,sw1h,c15,sw15,fin):
    sig=set(inspect.signature(fn).parameters)
    p={k:v for k,v in PR.items() if k in sig}
    r=fn(a1h,sw1h,c15,sw15,fine_ltf=fin,**p)
    tr=[t for t in r["ltf_trades"] if t.get("outcome")!="open"]
    rs=[float(t["r_multiple"]) for t in tr]
    neg=len([t for t in tr if t["outcome"]=="trail" and float(t["r_multiple"])<0])
    wr=100.0*len([x for x in rs if x>0])/max(1,len(rs))
    print("%-24s %5d %+9.2f %7.3f  wr=%4.1f%%  negtrail=%d"%(tag,len(rs),net_r(tr),pf(rs),wr,neg))

print("="*72); print("IS 2023-2026"); print("="*72)
for nm,pa in ARMS: show(nm,build("is"+nm[0],pa),d["c1h"],d["sw10"],d["c15"],d["sw15"],d["fine"])
print(); print("="*72); print("OOS unseen"); print("="*72)
for nm,pa in ARMS: show(nm,build("oos"+nm[0],pa),oc1h,SW1H,oc15,SW15,of)