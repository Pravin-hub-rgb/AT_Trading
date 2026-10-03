"""Inventory: which books have pins, which reproduce on the current engine.
The 40 knob-ing experiments all sit on the champion base. Rerunning means
running each one against unified.py and checking whether its pin still holds."""
import sys, pathlib, re, collections
R=pathlib.Path(__file__).resolve().parents[2]
for s in ("backtest/tests","backtest","backend"): sys.path.insert(0,str((R/s).resolve()))
sys.path.insert(0,str(R.resolve()))
sys.path.insert(0,str(R/"backtest/tests"))
import experiment_registry as reg
E=reg.EXPERIMENTS
print("total books in registry :",len(E))
have=[k for k,v in E.items() if v.get("pins")]
print("books carrying a pin    :",len(have))
print()
knobs=collections.Counter()
for k,v in E.items():
    for kk in v.get("params",{}):
        if kk.startswith("exp_"): knobs[kk]+=1
print("most-used experiment knobs (top 15):")
for kk,c in knobs.most_common(15):
    print("   %-24s %d books"%(kk,c))
