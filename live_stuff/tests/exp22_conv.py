"""Exp 22 — Second-Swing Conviction Trail (coarse, vs v18 base).

Trail ratchets activate at each same-dir swing's B2 MARK (break) instead of
its confirmation (which lags ~mb bars). Same pivot, earlier activation.
Ratchet conditions (sl_cur < cand < low) still gate every move — causal.
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

    print("=== EXP 22 conviction trail (coarse, base = v18) ===")
    show("v18 anchor", s_ship)
    r = sim(c1h, sw1h, c15, sw15, fine_ltf=[], exp22_conv=True, **BASE)
    tr = r["ltf_trades"] if isinstance(r, dict) else r
    s = stats(tr)
    show("conviction trail", s)
    print("      exits: %s" % dict(Counter(x["outcome"] for x in tr)))
    oc_ship = dict(Counter(x["outcome"] for x in t_ship))
    print("      anchor exits: %s" % oc_ship)


if __name__ == "__main__":
    main()
