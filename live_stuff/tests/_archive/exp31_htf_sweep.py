"""Exp 31 — HTF-SIDE LEVER SWEEP (first HTF-side experiments of the program).

Everything so far touched the LTF entry/trail. These levers live on the 1h side:
  lb        : chop-series lookback (shipped 14) — regime responsiveness
  htf_rr    : 1h R-target that closes the HTF window (shipped 3.0)
  ext_stop_r: entry extension filter (shipped 1.5) — skips over-extended signals
Each lever swept at TWO bases: v18 anchor (production) and B3-OPT+halt6 cd10.
Identity gate enforced; fine pass for winners afterwards.
"""
import sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import build_module, stats, show, BASE, \
    load_candles, _compute_swings, SWING, MB15
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod

BP = dict(BASE)
BP["chop_thresh"] = 58.0
B3OPT = dict(b3_k=8, b3_mode="close", exp_persist=2,
             max_consecutive_losses=6)
OPT_P = dict(chop_thresh=55.0)  # + mb1h10 chain, cd10 production kept

RUNS = []
for base_tag, hflags, pover, mb in [
        ("anchor", {}, {}, 20),
        ("B3-OPT+halt6", B3OPT, OPT_P, 10)]:
    for lb in (10, 20, 30):
        RUNS.append(("%s lb=%d" % (base_tag, lb), hflags, pover, mb,
                     dict(exp31_lb=lb)))
    for rr in (2.0, 2.5, 3.5, 4.0):
        RUNS.append(("%s htf_rr=%.1f" % (base_tag, rr), hflags, pover, mb,
                     dict(htf_rr=rr)))
    for esr in (1.0, 1.25, 2.0):
        RUNS.append(("%s ext=%.2f" % (base_tag, esr), hflags, pover, mb,
                     dict(ext_stop_r=esr)))


def main():
    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    chains = {20: _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"]),
              10: _compute_swings(f1h, "continuous", min_bars=10)}
    sim = build_module()

    r_ship = shipped_mod.simulate_htf_ltf_streak_halt(c1h, chains[20], c15, sw15, fine_ltf=[], **BP)
    s_ship = stats(r_ship["ltf_trades"])
    assert s_ship["n"] == 351, "ANCHOR MISMATCH"
    r0 = sim(c1h, chains[20], c15, sw15, fine_ltf=[], **BP)
    s0 = stats(r0["ltf_trades"])
    assert s0["n"] == 351 and s0["rs"] == s_ship["rs"], "IDENTITY GATE FAILED"
    print("IDENTITY GATE OK (351t exact)\n")

    print("=== bases (coarse) ===")
    show("anchor (base)", s_ship)
    r = sim(c1h, chains[10], c15, sw15, fine_ltf=[], **{**BP, **OPT_P, **B3OPT})
    show("B3-OPT+halt6 (base)", stats(r["ltf_trades"]))

    print("\n=== HTF lever sweep (coarse) ===")
    for tag, hflags, pover, mb, extra in RUNS:
        r = sim(c1h, chains[mb], c15, sw15, fine_ltf=[],
                **{**BP, **pover, **hflags, **extra})
        show(tag, stats(r["ltf_trades"]))

    print("\n(exp31 HTF sweep done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()
