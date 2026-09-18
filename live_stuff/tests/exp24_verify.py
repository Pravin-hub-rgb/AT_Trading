"""AUDIT: their OPTIMAL combo pieces, re-run on the SHIPPED engine (identity-gated).

Their claims (their harness): SAFE (mb1h10+chop55+persist2) 368t/+267.3;
OPTIMAL (SAFE + cd=0 + multi-LTF) 515t/+456.2. Their baseline: 351t/+238.0
(diverges from shipped 340t/+225.3 — signal selection differs from Jan 2023).
This runs each piece on the REAL engine to see what survives.
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import (build_module, stats, show, BASE,
                                    load_candles, _compute_swings, SWING, MB15)
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod


def main():
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    sw1h10 = _compute_swings(f1h, "continuous", min_bars=10)
    sim = build_module()

    # identity gate
    r_ship = shipped_mod.simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15,
                                                      fine_ltf=[], **BASE)
    t_ship = r_ship["ltf_trades"] if isinstance(r_ship, dict) else r_ship
    s_ship = stats(t_ship)
    r0 = sim(c1h, sw1h, c15, sw15, fine_ltf=[], **BASE)
    s0 = stats(r0["ltf_trades"] if isinstance(r0, dict) else r0)
    assert s0["n"] == 340 and s0["rs"] == s_ship["rs"], "IDENTITY GATE FAILED"
    print("IDENTITY GATE OK (340t exact)\n")

    print("=== THEIR PIECES ON THE SHIPPED ENGINE (coarse) ===")
    show("v18 anchor (their base ref: 351t/+238.0)", s_ship)
    cfgs = [
        ("chop=55 only", dict(), dict(chop_thresh=55.0), sw1h),
        ("cd=0 only", dict(), dict(cooldown_bars=0), sw1h),
        ("mb1h=10 only", dict(), dict(), sw1h10),
        ("persist=2 only", dict(exp_persist=2), dict(), sw1h),
        ("multi-LTF only", dict(exp_mltf=True), dict(), sw1h),
        ("SAFE: mb1h10+chop55+persist2", dict(exp_persist=2),
         dict(chop_thresh=55.0), sw1h10),
        ("OPTIMAL: SAFE + cd0 + mltf", dict(exp_persist=2, exp_mltf=True),
         dict(chop_thresh=55.0, cooldown_bars=0), sw1h10),
    ]
    for tag, hflags, pover, s1h_use in cfgs:
        r = sim(c1h, s1h_use, c15, sw15, fine_ltf=[],
                **{**BASE, **pover, **hflags})
        show(tag, stats(r["ltf_trades"] if isinstance(r, dict) else r))


if __name__ == "__main__":
    main()
