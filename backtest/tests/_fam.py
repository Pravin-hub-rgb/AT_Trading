import sys, pathlib, collections
R=pathlib.Path(__file__).resolve().parents[2]
for s in ("backtest/tests","backtest","backend"): sys.path.insert(0,str((R/s).resolve()))
sys.path.insert(0,str(R.resolve()))
sys.path.insert(0,str(R/"backtest/tests"))
import experiment_registry as reg
E=reg.EXPERIMENTS
BASE_KEYS={"mode","atr_high_thresh","atr_low_thresh","sl_buf_atr","chop_thresh",
           "cooldown_bars","max_consecutive_losses","ext_stop_r","window_end",
           "exp_partial_r","exp_mltf","exp_persist"}
fam=collections.defaultdict(list)
for k,cfg in E.items():
    if not cfg.get("pins") or "n" not in cfg["pins"]: continue
    diff=[kk for kk in cfg.get("params",{}) if kk not in BASE_KEYS]
    tag=",".join(sorted(diff)) if diff else "(baseline only)"
    fam[tag].append((k,cfg["pins"]["n"],cfg["pins"].get("net")))
print("PINNED BOOKS BY EXPERIMENT FAMILY")
print("="*76)
n=0
for tag in sorted(fam, key=lambda t:-len(fam[t])):
    ks=sorted(fam[tag])
    print()
    print("### %s   (%d books)"%(tag,len(ks)))
    for k,pn,pg in ks:
        n+=1
        print("   %2d. %-40s pin %4s / %s"%(n,k,pn,pg))
print()
print("total pinned:",n)
