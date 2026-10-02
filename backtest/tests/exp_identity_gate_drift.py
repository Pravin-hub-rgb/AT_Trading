"""Is the identity-gate drift caused by C16, or is it something else?

The gate at run_experiment.py:88 warns whenever the shipped engine on the coarse
basis (sw20, chop 61.8, fine_ltf=[]) misses the 340t / +225.3R anchor. It is
currently warning: 339t / +237.5R, one trade short and 12.2R high, 5.4% off.

That anchor was measured before C16 flipped the pivot default, so the obvious
explanation is that C16 moved it. The obvious explanation is not a diagnosis. This
runs the same basis under both rules:

  pivot_rule="origin"  -> if 340t / +225.3R, C16 caused the drift, re-anchor
  pivot_rule="leg"     -> if 339t / +237.5R, something else did

The shipped engine is called directly, not the patched module, so this isolates
the pivot rule from every other patch in the craze harness.

Run: python -u exp_identity_gate_drift.py     (about 2 min)
"""
import sys
from pathlib import Path

ROOT = Path(r"C:/Users/Pravin/Desktop/main/AT_Trading")
for p in ("backtest", "backtest/tests", "backtest/sweeps", "backtest/engine", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from run_experiment import BASE, get_data
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod

ANCHOR_N, ANCHOR_R = 340, 225.3

d = get_data()
rows = []
for rule in ("origin", "leg"):
    r = shipped_mod.simulate_htf_ltf_streak_halt(
        d["c1h"], d["sw20"], d["c15"], d["sw15"], fine_ltf=[],
        pivot_rule=rule, **dict(BASE))
    tr = [t for t in r["ltf_trades"] if t.get("outcome") != "open"]
    n = len(tr)
    g = sum(float(t["r_multiple"]) for t in tr)
    rows.append((rule, n, g))
    hit = "MATCHES ANCHOR" if abs(n - ANCHOR_N) <= 1 and abs(g - ANCHOR_R) <= 0.5 else "misses"
    print(f"  pivot_rule={rule:7s} n={n:<5d} grossR={g:+8.1f}   {hit}")

o, l = rows
print()
print(f"  anchor            n={ANCHOR_N:<5d} grossR={ANCHOR_R:+8.1f}")
print(f"  rule delta        n={l[1]-o[1]:+d}  grossR={l[2]-o[2]:+.1f}")
print()
if abs(o[1] - ANCHOR_N) <= 1 and abs(o[2] - ANCHOR_R) <= 0.5:
    print("  DIAGNOSIS: the anchor is an origin-era figure. C16 moved the coarse")
    print("  basis exactly as it moved the champion book, and the gate is")
    print(f"  mis-warning because it still compares against origin. Re-anchor to")
    print(f"  {l[1]}t / {l[2]:+.1f}R and the gate is honest again.")
elif abs(l[1] - ANCHOR_N) <= 1 and abs(l[2] - ANCHOR_R) <= 0.5:
    print("  DIAGNOSIS: origin and leg BOTH miss the anchor, so C16 did not cause")
    print("  this. The coarse basis drifted for another reason and the gate needs")
    print("  a real diagnosis before anyone trusts it.")
else:
    print("  DIAGNOSIS: neither rule reproduces the anchor. The coarse basis moved")
    print("  for a reason other than the pivot rule. Investigate before re-anchoring")
    print("  - re-anchoring now would bless whatever is currently happening.")