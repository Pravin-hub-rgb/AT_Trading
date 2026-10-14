"""E3 - B2 vs FLIP on the HTF plane: does the break KIND matter where it has never been tested?

WHY THIS EXPERIMENT EXISTS
--------------------------
The owner has been explicit about the semantics:

    "B1 and B2 are of the same direction. If B1 is upside direction, the B2 also
     have to break the extreme on the up direction. [...] Now flip is opposite
     to B1 or B2."

and

    "we might be having B1, then B2, then a flip, then again a B2. B2 would be
     again on the same direction of B1 and B2 [...] This can also happen. I have
     seen it multiple times."

That distinction - B2 and FLIP are different KINDS of break, not two names for
the same one - has never been tested on the HTF plane. `unified.py` chooses
between them per mode:

    elif mode=="atr_high":
        use="decisive" if atrp > atr_high_thresh else "flip"     # shipped: 86/93 books
    elif mode=="b2_vs_flip_chop":
        use="b2" if ch > chop_thresh else "flip"                 # B2 explicitly

"decisive" is `("B2", "FLIP")` - it takes EITHER. So the shipped family has
never asked which of the two it actually wants, and `b2_vs_flip_chop` - the one
branch that names B2 specifically - appears in no active book.

The LTF plane WAS tested today (docs/method/ENTRY_BREAK_AND_PLATEAU_TIER4.md):
decisive and b2 came out byte-identical on every cell, flip-only took 716 trades
against decisive's 419, and FS-print entry reached 0.691R expectancy out of
sample against 0.008R for break entry. That was the 15m plane. This is the 1h
plane, where the window-opening decision is actually made.

THE THREE ARMS
--------------
    atr_high        SHIPPED. "decisive" = B2 or FLIP, whichever comes first.
    b2_vs_flip_chop B2 when 1h chop is high, FLIP when it is low.
    htf_mag         magnitude-based, no chop at all.

Arm 3 exists because arm 2 routes on chop, and chop was measured DEAD under
`atr_high` (exp_knob_liveness.py, 2026-10-14). If the B2-vs-FLIP distinction is
real, it should not depend on a signal that does nothing - arm 3 is the control
for that.

WHAT THIS IS NOT
----------------
Not a promotion. It prints three numbers per book. A mode that wins needs its own
registry entry and its own OOS reveal.

PIPELINE DISCIPLINE (backtest/docs/pipeline/README.md)
-----------------------------------------------------
Identity gate first. Both eras. Nothing promoted. Nothing retired.

Output: b2_vs_flip_htf_results.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "b2_vs_flip_htf_results.json"

import exp_repin_stale as repin                                  # noqa: E402
import test_experiments_craze as craze                           # noqa: E402
from experiment_registry import EXPERIMENTS                      # noqa: E402

ARMS = [
    ("atr_high", "SHIPPED - decisive (B2 or FLIP)"),
    ("b2_vs_flip_chop", "B2 when chop high, FLIP when low"),
    ("htf_mag", "magnitude - no chop, control for the dead-knob finding"),
]

BOOKS = [
    "fsent_champ_long_htf15",
    "fsent_champ_long_htffs",
    "fsent_champ_long_mcloff",
    "fsent_champ_long",
    "fsent_champ_short",
]

TOTAL = len(BOOKS) * (len(ARMS) + 1) * 2
_DONE = 0
_T0 = time.time()


def progress(label: str) -> None:
    global _DONE
    _DONE += 1
    pct = 100.0 * _DONE / TOTAL
    el = time.time() - _T0
    eta = (el / _DONE) * (TOTAL - _DONE) if _DONE else 0.0
    print("\r  [%3d%%] %-42s %-38s %5.1fs elapsed, ~%4.0fs left   "
          % (pct, "#" * int(pct / 2.5), label[:38], el, eta),
          end="", flush=True)


def sweep_key(book: str) -> str:
    return "htf15" if book.endswith("htf15") else "sw10"


def main() -> int:
    print("E3 - B2 vs FLIP on the HTF plane")
    print("3 arms x 5 books x 2 eras + identity gate")
    print("estimated ~%d min\n" % (TOTAL * 11 // 60))
    t0 = time.time()

    sim = craze.build_module()
    print("loading eras ...", flush=True)
    from exp_signal_metrics import load_era
    eras = {"is": load_era("is"), "oos": load_era("oos")}
    print("loaded (%.0fs)\n" % (time.time() - t0), flush=True)

    out = {"arms": [a for a, _ in ARMS], "books": BOOKS,
           "identity": {}, "rows": {}}

    print("=" * 100)
    print("IDENTITY GATE")
    print("=" * 100)
    gate_ok = True
    for book in BOOKS:
        cfg = dict(EXPERIMENTS[book])
        cfg["swing"] = sweep_key(book)
        cfg["basis"] = "fine"
        pin = cfg.get("pins") or {}
        for era in ("is", "oos"):
            m = repin.measure(sim, eras[era], cfg)
            progress("%s | OWN | %s" % (book, era))
            wn = pin.get("n") if era == "is" else pin.get("oos_n")
            wt = pin.get("net") if era == "is" else pin.get("oos_net")
            ok = m["n"] == wn and abs(m["net"] - wt) < 0.01
            gate_ok = gate_ok and ok
            print("  %-30s %-4s n=%-5d net=%9.2f pin %9.2f  %s"
                  % (book, era, m["n"], m["net"], wt,
                     "OK" if ok else "*** MISMATCH ***"))
            out["identity"]["%s|%s" % (book, era)] = {"ok": ok}
    print()
    if not gate_ok:
        print("!! GATE FAILED - stopping.")
        RESULTS.write_text(json.dumps(out, indent=1), encoding="utf-8")
        return 1
    print("gate passed.\n")

    for book in BOOKS:
        base = dict(EXPERIMENTS[book])
        base["swing"] = sweep_key(book)
        base["basis"] = "fine"
        rows = {}
        print("=" * 106)
        print("%s" % book)
        print("=" * 106)
        print("  %-22s %6s %10s %8s %6s %10s  %s"
              % ("arm", "n", "IS net", "PF", "n", "OOS net", "note"))
        print("  " + "-" * 80)
        for arm, note in ARMS:
            cfg = dict(base)
            cfg["params"] = dict(base["params"], mode=arm)
            r = {}
            for era in ("is", "oos"):
                r[era] = repin.measure(sim, eras[era], cfg)
                progress("%s | %s | %s" % (book, arm, era))
            rows[arm] = r
            tag = "SHIPPED" if arm == "atr_high" else ""
            if arm != "atr_high" and r["is"]["net"] > 0 and r["oos"]["net"] > 0:
                tag = "both +"
            print("  %-22s %6d %10.2f %8.2f %6d %10.2f  %s"
                  % (arm, r["is"]["n"], r["is"]["net"], r["is"].get("pf") or 0,
                     r["oos"]["n"], r["oos"]["net"], tag))
            if arm == "atr_high":
                print("  %-22s %s" % ("", note))
        out["rows"][book] = rows
        ship = rows["atr_high"]["oos"]["net"]
        for arm, _ in ARMS:
            if arm == "atr_high":
                continue
            d = rows[arm]["oos"]["net"] - ship
            if abs(d) > 0.5:
                print("    %-20s OOS delta vs shipped: %+.2fR" % (arm, d))
        print()

    RESULTS.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("wrote %s  (%.0fs)" % (RESULTS.name, time.time() - t0))
    print("\nNOTHING PROMOTED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())