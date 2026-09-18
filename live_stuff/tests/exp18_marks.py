"""Exp 18 — 3-Mark Judgment System: ALL arms, coarse, vs v18 base.

Mark stream (verified): B1 = first extreme break (anchors a sequence),
B2 = same-dir re-break, FLIP = opposite break. Sequences anchored on B1
resolve at the 3rd mark (arm D: at the 2nd when it's a flip). SL pivots via
_collect_signals attribution; B1 decision marks resolve silently. All v18
gates (chop routing, C14/C15 windows, ext_stop, busy/cooldown/halt) apply.

Arms:
  P1   : trade only all-three-same (B1↑B2↑B3↑ -> dir 3)
  full : every resolved 3-mark sequence trades its 3rd mark's direction
         (P1 + P2 flip-after-two + P3 reclaim + P4 double-flip)
  P2b  : full minus P2 (pure reversal after two same skipped)
  D    : flip exception — 2-mark flip trades immediately; + P1; P2 flips trade
Compare base: v18 (340t / +225.3R coarse) — per user instruction.
"""
import sys
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import (build_module, stats, show, BASE,
                                    load_candles, _compute_swings, SWING, MB15)
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod


def kinds(tr):
    return dict(Counter(x["break_kind"] for x in tr))


def main():
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    sim = build_module()

    r_ship = shipped_mod.simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15,
                                                      fine_ltf=[], **BASE)
    t_ship = r_ship["ltf_trades"] if isinstance(r_ship, dict) else r_ship
    s_ship = stats(t_ship)
    r0 = sim(c1h, sw1h, c15, sw15, fine_ltf=[], **BASE)
    s0 = stats(r0["ltf_trades"] if isinstance(r0, dict) else r0)
    assert s0["n"] == 340 and s0["rs"] == s_ship["rs"], "IDENTITY GATE FAILED"
    print("IDENTITY GATE OK (340t exact)\n")

    print("=== EXP 18 arms (coarse, base = v18) ===")
    show("v18 anchor", s_ship)
    for arm in ("P1", "full", "P2b", "D"):
        r = sim(c1h, sw1h, c15, sw15, fine_ltf=[], exp18_arm=arm, **BASE)
        tr = r["ltf_trades"] if isinstance(r, dict) else r
        s = stats(tr)
        show("arm %s" % arm, s)
        print("      marks traded: %s" % kinds(tr))


if __name__ == "__main__":
    main()
