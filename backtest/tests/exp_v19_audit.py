import sys, os, pickle, inspect
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for p in ("backtest","backtest/tests","backtest/sweeps","backend"):
    sys.path.insert(0,str(ROOT/p))
sys.path.append(str(ROOT/"backend"/"src"))
with open(Path(os.environ["TEMP"])/"at_datacache.pkl","rb") as f: d=pickle.load(f)
from src.btc.engines.htf_ltf.v19_champion import simulate_htf_ltf_streak_halt as S
from run_experiment import net_r
from experiment_registry import BP,EXPERIMENTS
q={**BP,**EXPERIMENTS["champion_multi_sw10"]["params"]}
sig=set(inspect.signature(S).parameters)
p={k:v for k,v in q.items() if k in sig}
r=S(d["c1h"],d["sw10"],d["c15"],d["sw15"],fine_ltf=d["fine"],**p)
tr=r["ltf_trades"]; c=d["c15"]
FAIL=[]
def ck(cond,msg):
    print(("  PASS  " if cond else "  FAIL  ")+msg)
    if not cond: FAIL.append(msg)
print("=== A. structural integrity, all %d trades ==="%len(tr))
ck(all(t["exit_idx"]>t["entry_idx"] for t in tr),"exit_idx after entry_idx")
ck(all(float(t["r_multiple"])==float(t["r_multiple"]) for t in tr),"no NaN in r_multiple")
ck(all(t["exit_ts"]<=c[-1]["ts"] for t in tr),"no exit past final candle")
ck(all(t["r_multiple"] is not None for t in tr),"every trade has r_multiple")
print()
print("=== B. THE causal fill rule: entry = close[i], and close[i]==open[i+1] ===")
m1=sum(1 for t in tr if abs(float(t["entry_price"])-float(c[t["entry_idx"]]["close"]))>1e-9)
ck(m1==0,"entry_price == close of signal bar (%d off)"%m1)
m2=sum(1 for t in tr if t["entry_idx"]+1<len(c) and abs(float(c[t["entry_idx"]]["close"])-float(c[t["entry_idx"]+1]["open"]))>1e-9)
ck(m2==0,"close[i]==open[i+1] at every entry (%d off)"%m2)
print()
print("=== C. R accounting, recomputed independently ===")
dr=0.0
for t in tr:
    sgn=1.0 if t["dir"]=="long" else -1.0
    risk=abs(float(t["entry_price"])-float(t["sl"]))
    v=sgn*(float(t["exit_price"])-float(t["entry_price"]))/risk
    dr=max(dr,abs(v-float(t["r_multiple"])))
ck(dr<1e-6,"recomputed R == reported R (max drift %.2e)"%dr)
sl=[t for t in tr if t["outcome"]=="sl"]
ck(all(abs(float(t["r_multiple"])+1.0)<1e-9 for t in sl),"all %d SL exits == exactly -1.0R"%len(sl))
print()
print("=== D. trail exits that still lost money (expected: stop moved to breakeven+) ===")
trl=[t for t in tr if t["outcome"]=="trail"]
neg=[t for t in trl if float(t["r_multiple"])<0]
print("   trail exits: %d, of which negative R: %d (%.1f%%)"%(len(trl),len(neg),100.0*len(neg)/len(trl)))
ck(all(float(t["r_multiple"])>=-1.0 for t in neg),"no trail exit worse than -1R (a stop cannot lose more than 1R)")
print()
print("=== E. duplicates + concurrency ===")
dp=len(tr)-len({(t["entry_ts"],t["exit_ts"],t["dir"]) for t in tr})
ck(dp==0,"no duplicated trades (%d)"%dp)
ev=[]
for t in tr:
    ev.append((t["entry_ts"],1)); ev.append((t["exit_ts"],-1))
ev.sort(key=lambda z:(z[0],z[1]))
cur=mx=0
for _,x in ev:
    cur+=x; mx=max(mx,cur)
ck(mx==6,"max concurrent = %d (multi is real)"%mx)
print()
print("n=%d  net=%+.2fR   FAILURES=%d"%(len(tr),net_r(tr),len(FAIL)))