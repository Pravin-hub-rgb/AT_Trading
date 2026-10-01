"""STEP 1 - ABLATION, one arm per invocation (tools timeout at 30s).

Arms (same data, same params, only the flag changes):
  A  production-as-is  exp_mltf OFF, persist OFF  -> what SHIPPED code does
  B  persist only      exp_mltf OFF, persist=7    -> regime hysteresis alone
  C  champion control  exp_mltf ON,  persist=7    -> must equal the PIN

Results append to _ablation.jsonl so runs are independent and resumable.
"""
import sys, json, os, pickle
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for p in ("backtest/tests","backtest","backend"):
    sys.path.insert(0,str(ROOT/p))
sys.path.append(str(ROOT/"backend"/"src"))
TMP=Path(os.environ.get("TEMP","."))
CACHE=TMP/"at_datacache.pkl"

def data():
    if CACHE.exists():
        with open(CACHE,"rb") as f: return pickle.load(f)
    from run_experiment import get_data
    d=get_data()
    with open(CACHE,"wb") as f: pickle.dump(d,f)
    return d

def cells(d):
    import test_experiments_craze as tc
    from exp_concurrency_guard import load_unseen
    from test_4_new_concepts import load_fine_1m as load_fine_oos
    (oc15,of15),(oc1h,of1h)=load_unseen("15m"),load_unseen("1h")
    oos_fine=load_fine_oos(oc15[0]["ts"],oc15[-1]["ts"])
    return {"is":(d["c1h"],d["sw10"],d["c15"],d["sw15"],d["fine"]),
            "oos":(oc1h,tc._compute_swings(of1h,"continuous",min_bars=10),
                   oc15,tc._compute_swings(of15,"continuous",min_bars=50),oos_fine)}

def main():
    arm=sys.argv[1]; scope=sys.argv[2]; lane=sys.argv[3]
    import test_experiments_craze as tc
    from run_experiment import net_r
    from experiment_registry import BP,EXPERIMENTS
    from exp_concurrency_guard import concurrency, pf
    d=data(); params={**BP,**EXPERIMENTS[lane]["params"]}
    p=dict(params)
    if arm=="A":
        for k in ("exp_mltf","exp_persist","exp_partial_r","exp_max_concurrent"):
            p.pop(k,None)
    elif arm=="B":
        p["exp_persist"]=7; p["exp_mltf"]=False
    else:
        p["exp_persist"]=7; p["exp_mltf"]=True
    tr=[t for t in tc.build_module()(*cells(d)[scope],**p)["ltf_trades"] if t.get("outcome")!="open"]
    rs=[float(t["r_multiple"]) for t in tr]
    rec={"arm":arm,"scope":scope,"lane":lane,"n":len(rs),"net":round(net_r(tr),2),
         "pf":round(pf(rs),3),"maxconc":concurrency(tr)}
    with open(ROOT/"_ablation.jsonl","a",encoding="utf-8") as f: f.write(json.dumps(rec)+"\n")
    print(json.dumps(rec))

main()