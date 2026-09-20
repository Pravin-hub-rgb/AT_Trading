"""Exp 32 — FINAL INTERACTION SWEEPS before freezing the config.

A: chop_thresh x lb 2D interaction (chop was picked pre-lb; they couple)
B: persist {0,2,5} re-check at the winning (chop, lb)
C: LTF trail-mb re-check on the new stack (swings_trail machinery, Exp 11)
Base: B3-OPT+halt6 cd10 (b3_k8 close, chop55, mb1h10, persist2, halt6).
Identity gate enforced. Fine pass for anything that beats lb=50 base.
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

BP = dict(BASE)              # production params
BP["chop_thresh"] = 58.0     # <- the reconciliation fix; BASE carries 61.8!
BP55 = dict(BP)
BP55["chop_thresh"] = 55.0   # B3-OPT family threshold — used by the sweeps
H = dict(b3_k=8, b3_mode="close", exp_persist=2, max_consecutive_losses=6)


def main():
    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h10 = _compute_swings(f1h, "continuous", min_bars=10)
    sw1h20 = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    tchains = {mb: _compute_swings(f15, "continuous", min_bars=mb)
               for mb in (SWING["min_bars_15m"], 35, 65)}
    sim = build_module()
    r_ship = shipped_mod.simulate_htf_ltf_streak_halt(c1h, sw1h20, c15, sw15, fine_ltf=[], **BP)
    s_ship = stats(r_ship["ltf_trades"])
    r0 = sim(c1h, sw1h20, c15, sw15, fine_ltf=[], **BP)
    s0 = stats(r0["ltf_trades"])
    print("gate: ship %dt/%+.2f | sim %dt/%+.2f | identical=%s"
          % (s_ship["n"], s_ship["gross"], s0["n"], s0["gross"],
             s0["rs"] == s_ship["rs"]))
    if s0["n"] != 351 or s0["rs"] != s_ship["rs"]:
        for i, (a, b) in enumerate(zip(s_ship["rs"], s0["rs"])):
            if a != b:
                print("first diff trade %d: ship %+.3f sim %+.3f" % (i, a, b))
                break
        print("lens:", len(s_ship["rs"]), len(s0["rs"]))
        raise SystemExit("IDENTITY GATE FAILED")
    print("IDENTITY GATE OK\n")

    print("=== A: chop x lb 2D (B3-OPT+halt6 cd10, coarse) ===")
    best = (None, -1e9)
    for chop in (50.0, 52.0, 55.0, 58.0):
        row = []
        for lb in (30, 40, 50, 60):
            r = sim(c1h, sw1h10, c15, sw15, fine_ltf=[],
                    **{**BP, **H, "chop_thresh": chop, "exp31_lb": lb})
            s = stats(r["ltf_trades"])
            row.append("%+7.1f" % s["gross"])
            if s["gross"] > best[1]:
                best = ((chop, lb), s["gross"])
        print("  chop=%.0f  lb30 %s | lb40 %s | lb50 %s | lb60 %s" % (chop, row[0], row[1], row[2], row[3]))
    print("  2D best: chop/lb=%s gross %+.1f (base lb50/chop55 = +427.8)" % (str(best[0]), best[1]))

    print("\n=== B: persist re-check at best (chop, lb) ===")
    cb, lb = best[0]
    for pers in (0, 2, 5):
        r = sim(c1h, sw1h10, c15, sw15, fine_ltf=[],
                **{**BP, **H, "exp_persist": pers, "chop_thresh": cb, "exp31_lb": lb})
        show("persist=%d" % pers, stats(r["ltf_trades"]))

    print("\n=== C: LTF trail-mb re-check (base trail mb=%d) ===" % SWING["min_bars_15m"])
    for mb, ch in tchains.items():
        r = sim(c1h, sw1h10, c15, sw15, fine_ltf=[],
                **{**BP, **H, "chop_thresh": cb, "exp31_lb": lb, "swings_trail": ch})
        show("trail-mb=%d" % mb, stats(r["ltf_trades"]))

    print("\n(exp32 interaction sweeps done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()
