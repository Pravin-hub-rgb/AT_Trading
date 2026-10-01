"""Exp 31b — lb extension: monotone finding at lb=30, push to 40/50/60.
Both bases, coarse. Identity gate enforced.
"""
import sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import build_module, stats, show, BASE, \
    load_candles, _compute_swings, SWING, MB15
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod

BP = dict(BASE)
BP["chop_thresh"] = 58.0
B3OPT = dict(b3_k=8, b3_mode="close", exp_persist=2,
             max_consecutive_losses=6)
OPT_P = dict(chop_thresh=55.0)


def main():
    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    chains = {20: _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"]),
              10: _compute_swings(f1h, "continuous", min_bars=10)}
    sim = build_module()
    r_ship = shipped_mod.simulate_htf_ltf_streak_halt(c1h, chains[20], c15, sw15, fine_ltf=[], **BP)
    s_ship = stats(r_ship["ltf_trades"])
    r0 = sim(c1h, chains[20], c15, sw15, fine_ltf=[], **BP)
    s0 = stats(r0["ltf_trades"])
    assert s0["n"] == 351 and s0["rs"] == s_ship["rs"], "IDENTITY GATE FAILED"
    print("IDENTITY GATE OK\n")
    for base_tag, hflags, pover, mb in [
            ("anchor", {}, {}, 20), ("B3-OPT+halt6", B3OPT, OPT_P, 10)]:
        for lb in (14, 30, 40, 50, 60, 80):
            r = sim(c1h, chains[mb], c15, sw15, fine_ltf=[],
                    **{**BP, **pover, **hflags, "exp31_lb": lb})
            show("%s lb=%d" % (base_tag, lb), stats(r["ltf_trades"]))
    print("\n(exp31b done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()
