"""CRAZE Exp 14 — B3: entry AFTER structural confirmation of the B2/flip break.

User's concept: a swing entry needs b1+b2 (both BEFORE, already known) and the
judgment happens on B3 — the confirmation event AFTER the break. Entry moves
from the B2 bar to the B3 trigger bar.

Trigger (per variant):
  close mode: first bar whose CLOSE goes beyond the B2 signal bar's extreme
  wick  mode: first bar whose HIGH/LOW touches beyond it
Invalidation: SL pivot touched before trigger -> signal dies (no trade).
Timeout: b3_k bars; if no trigger -> signal dies.
Causality: scan reads only bars AFTER the signal bar; decision at trigger close;
busy_until + cooldown re-checked at the trigger bar; trail events must confirm
at/after the entry bar. ATR/SL from the trigger bar (past data only).

Arms:
  A. anchor mb50 + B3 (k=2/4/8, close/wick)
  B. low-mb arm: entry chain mb30/40 (faster swings) + B3 — structure
     confirmation replaces time confirmation ("might not need minbar")
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import (build_module, stats, show, BASE, SRC,
                                    load_candles, _compute_swings, SWING,
                                    MB15)
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod


def main():
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    chains = {mb: _compute_swings(f15, "continuous", min_bars=mb)
              for mb in (30, 40, 50)}
    sim = build_module()

    # ---- identity gate: all-off == shipped ----
    r_ship = shipped_mod.simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15,
                                                      fine_ltf=[], **BASE)
    t_ship = r_ship["ltf_trades"] if isinstance(r_ship, dict) else r_ship
    s_ship = stats(t_ship)
    r0 = sim(c1h, sw1h, c15, sw15, fine_ltf=[], **BASE)
    s0 = stats(r0["ltf_trades"] if isinstance(r0, dict) else r0)
    ok = (s0["n"] == s_ship["n"] and s0["rs"] == s_ship["rs"])
    assert ok and s_ship["n"] == 340, "IDENTITY/ANCHOR GATE FAILED"
    print("IDENTITY GATE OK: 340t / %+.2fR exact match\n" % s0["gross"])

    print("=== ARM A: mb50 + B3 (coarse) ===")
    show("anchor (b3 off)", s_ship)
    for k in (2, 4, 8):
        for mode in ("close", "wick"):
            r = sim(c1h, sw1h, c15, sw15, fine_ltf=[],
                    b3_k=k, b3_mode=mode, **BASE)
            show("k=%d %s" % (k, mode),
                 stats(r["ltf_trades"] if isinstance(r, dict) else r))

    print("\n=== ARM B: low-mb entry chain + B3 (trail stays mb50) ===")
    show("anchor mb30 (no b3)", stats(
        (sim(c1h, sw1h, c15, chains[30], swings_trail=sw15, **BASE)
         ["ltf_trades"])))
    show("anchor mb40 (no b3)", stats(
        (sim(c1h, sw1h, c15, chains[40], swings_trail=sw15, **BASE)
         ["ltf_trades"])))
    for mb in (30, 40):
        for k in (4, 8):
            r = sim(c1h, sw1h, c15, chains[mb], swings_trail=sw15,
                    b3_k=k, b3_mode="close", **BASE)
            show("mb%d + k%d close" % (mb, k),
                 stats(r["ltf_trades"] if isinstance(r, dict) else r))


if __name__ == "__main__":
    main()
