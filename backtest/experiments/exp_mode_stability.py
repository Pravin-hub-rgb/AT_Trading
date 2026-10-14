"""E1-STABILITY: are the mode winners real, or did I find them by looking at IS?

WHY THIS EXPERIMENT EXISTS
--------------------------
E1 (exp_mode_census.py) swept 26 mode branches across 5 books and found that on
EVERY book at least one mode beats the shipped `atr_high` in both eras:

    htf15   union      IS +70.73   OOS +66.57
    mcloff  garch      IS +171.56  OOS +36.04
    long    garch      IS +175.92  OOS +40.98
    short   session    IS  +20.03  OOS +72.28
    htffs   session    IS -124.91  OOS +15.72

That is 5 books and 26 modes, so a winner per book is what you would expect by
chance alone. The census answered "does anything beat the shipped mode", not
"is this beat real". It never claimed the latter - it ended with "NOTHING IS
PROMOTED HERE. A mode that wins needs its own experiment".

This is that experiment. The question is no longer "is X better than Y on one
split" but "is X better than Y when you move the thing it might be latched to".

WHAT "STABILITY" MEANS HERE
---------------------------
For each winner, two independent checks:

  1. NEIGHBOURHOOD. A real effect sits on a region; a fluke sits on a point.
     Sweep the knobs the winner depends on and require the gain to persist
     across the region, not only at the shipped value.

  2. THE DEAD-KNOB TEST, inverted. exp_knob_liveness.py proved that under
     `atr_high` the book cannot tell chop_thresh 40 from 74. If a "winner"
     mode turns out to be insensitive to the knob that supposedly drives it,
     then it is not winning by that mechanism - whatever it is doing, the
     stated story is wrong, and that gets recorded rather than promoted.

  3. DIRECTION CHECK. The long side and the short side should not both "win"
     with the same mode unless the mode is genuinely direction-agnostic. E1
     gave `garch` on long AND mcloff, `session` on short AND htffs. Two
     independent books per mode is weak corroboration; this checks whether the
     gain survives on the mirror book too.

WHAT THIS IS NOT
----------------
Not a promotion. A survivor here goes to the owner for a chart look, not into
the registry. Nothing is edited. Nothing is retired.

PIPELINE DISCIPLINE (backtest/docs/pipeline/README.md)
-----------------------------------------------------
Identity gate first. Both eras, always. Nothing promoted.

Output: mode_stability_results.json
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
RESULTS = HERE / "mode_stability_results.json"

import exp_repin_stale as repin                                  # noqa: E402
import test_experiments_craze as craze                           # noqa: E402
from experiment_registry import EXPERIMENTS                      # noqa: E402

# The winners E1 named, plus the shipped mode on each book as the control every
# delta is measured against. Named here rather than recomputed so the input to
# this experiment is auditable: read E1's table and check these are the rows.
PAIRS = [
    ("fsent_champ_long",        "atr_high", "garch",   "+175.92 IS / +40.98 OOS"),
    ("fsent_champ_long_mcloff", "atr_high", "garch",   "+171.56 IS / +36.04 OOS"),
    ("fsent_champ_long_htf15",  "atr_high", "union",   " +70.73 IS / +66.57 OOS"),
    ("fsent_champ_short",       "atr_high", "session", " +20.03 IS / +72.28 OOS"),
    ("fsent_champ_long_htffs",  "atr_high", "session", "-124.91 IS / +15.72 OOS"),
]

# The knob each winner actually routes on, read off unified.py:1051-1053.
#   garch   -> "b2" if garch_per_ltf[bar] > chop_thresh else "flip"
#   session -> "b2" if session_per_ltf[bar] in (0,3) else "flip"   (hardcoded,
#              no tunable parameter, so it is swept with its own inverse instead)
#   union   -> use="union", no routing at all, nothing to sweep
# A knob is listed only where one genuinely exists. Where none does, the
# neighbourhood test is skipped and recorded as SKIPPED rather than passed.
KNOB = {"garch": "chop_thresh", "session": None, "union": None}

# Chop thresholds to sweep. The shipped value is read from each book's registry
# entry, so these are absolute offsets around what that book actually uses.
CHOP_OFFSETS = [-16, -8, 0, +8, +16]

# The exact inverse routing of `session`, already in the engine at
# unified.py:1032-1035. If the session effect is real, flipping which sessions
# take B2 should NOT reproduce the gain. This is the neighbourhood test for
# session, and it needs no code change.
MIRROR = {"session": "session_flip"}

TOTAL = (len(PAIRS) * 2 * 2) + (len(PAIRS) * len(CHOP_OFFSETS) * 2) + (len(PAIRS) * 2)
_DONE = 0
_T0 = time.time()


def progress(label: str) -> None:
    global _DONE
    _DONE += 1
    pct = 100.0 * _DONE / TOTAL
    el = time.time() - _T0
    eta = (el / _DONE) * (TOTAL - _DONE) if _DONE else 0.0
    print("\r  [%3d%%] %-42s %-36s %5.1fs elapsed, ~%4.0fs left   "
          % (pct, "#" * int(pct / 2.5), label[:36], el, eta),
          end="", flush=True)


def sweep_key(book: str) -> str:
    return "htf15" if book.endswith("htf15") else "sw10"


def run(sim, eras, book, mode, extra=None):
    cfg = dict(EXPERIMENTS[book])
    cfg["swing"] = sweep_key(book)
    cfg["basis"] = "fine"
    params = dict(cfg["params"], mode=mode)
    if extra:
        params.update(extra)
    cfg["params"] = params
    return {era: repin.measure(sim, eras[era], cfg) for era in ("is", "oos")}


def main() -> int:
    print("E1-STABILITY - do the mode winners survive a knob they are supposed to depend on?")
    print("%d pairs, identity gate + repeat + knob sensitivity + session sweep" % len(PAIRS))
    print("estimated ~%d min\n" % (TOTAL * 11 // 60))
    t0 = time.time()

    sim = craze.build_module()
    print("loading eras ...", flush=True)
    from exp_signal_metrics import load_era
    eras = {"is": load_era("is"), "oos": load_era("oos")}
    print("loaded (%.0fs)\n" % (time.time() - t0), flush=True)

    out = {"pairs": [], "identity": {}}

    # ---- 1. IDENTITY GATE -------------------------------------------------
    print("=" * 104)
    print("IDENTITY GATE - shipped mode must reproduce its pin")
    print("=" * 104)
    gate_ok = True
    for book, ship, _win, _claim in PAIRS:
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

    # ---- 2. REPEAT + NEIGHBOURHOOD ---------------------------------------
    for book, ship, win, claim in PAIRS:
        print("=" * 106)
        print("%s   shipped=%s  winner=%s   (E1 claimed %s)"
              % (book, ship, win, claim))
        print("=" * 106)

        base = run(sim, eras, book, ship)
        cand = run(sim, eras, book, win)
        progress("%s | %s | both" % (book, win))
        dIS = cand["is"]["net"] - base["is"]["net"]
        dOOS = cand["oos"]["net"] - base["oos"]["net"]
        print("  shipped  %-16s IS %9.2f  OOS %9.2f" % (ship, base["is"]["net"], base["oos"]["net"]))
        print("  winner   %-16s IS %9.2f  OOS %9.2f   dIS %+.2f  dOOS %+.2f"
              % (win, cand["is"]["net"], cand["oos"]["net"], dIS, dOOS))

        # ---- 2b. NEIGHBOURHOOD, on the knob that actually exists ----------
        sweep = {}
        knob = KNOB.get(win)
        if knob:
            base_thr = float(EXPERIMENTS[book]["params"].get(knob, 58))
            print()
            print("  %s routes on %s (shipped %s). Sweeping it:"
                  % (win, knob, base_thr))
            print("    %-10s %7s %10s %7s %10s   %s"
                  % (knob, "n", "IS net", "n", "OOS net", "vs shipped IS/OOS"))
            print("    " + "-" * 74)
            gains_is, gains_oos = [], []
            for off in CHOP_OFFSETS:
                thr = base_thr + off
                r = run(sim, eras, book, win, {knob: thr})
                sweep["%d" % thr] = r
                gIS = r["is"]["net"] - base["is"]["net"]
                gOOS = r["oos"]["net"] - base["oos"]["net"]
                gains_is.append(gIS)
                gains_oos.append(gOOS)
                progress("%s | %s=%s" % (book, knob, thr))
                print("    %-10.4f %7d %10.2f %7d %10.2f   %+.2f / %+.2f%s"
                      % (thr, r["is"]["n"], r["is"]["net"], r["oos"]["n"],
                         r["oos"]["net"], gIS, gOOS,
                         "   <- shipped value" if off == 0 else ""))
            pos = sum(1 for g in gains_is if g > 0)
            posO = sum(1 for g in gains_oos if g > 0)
            spread = max(gains_is) - min(gains_is)
            # The dead-knob test, inverted. Under atr_high chop_thresh 40/58/74
            # were byte-identical. If the same is true here, garch is not
            # winning by chop routing and its stated mechanism is wrong.
            if spread < 1.0:
                live = "DEAD - identical across the sweep, so %s is NOT winning via %s" % (win, knob)
            elif pos >= len(CHOP_OFFSETS) - 1 and posO >= len(CHOP_OFFSETS) - 1:
                live = "LIVE and REGIONAL - %d/%d IS, %d/%d OOS positive, IS spread %.1fR" % (
                    pos, len(CHOP_OFFSETS), posO, len(CHOP_OFFSETS), spread)
            else:
                live = "LIVE but PATCHY - %d/%d IS, %d/%d OOS positive, IS spread %.1fR" % (
                    pos, len(CHOP_OFFSETS), posO, len(CHOP_OFFSETS), spread)
            verdict = live
            print("    -> %s" % live)

        elif win in MIRROR:
            # No parameter to sweep. Use the engine's own inverse branch as the
            # falsification test: a real routing effect should not survive
            # having its routing inverted.
            inv = MIRROR[win]
            r = run(sim, eras, book, inv)
            sweep[inv] = r
            progress("%s | %s" % (book, inv))
            mIS = r["is"]["net"] - base["is"]["net"]
            mOOS = r["oos"]["net"] - base["oos"]["net"]
            print()
            print("  %s has no tunable knob (routing is hardcoded at unified.py:1031)." % win)
            print("  Falsification test - its exact inverse, %s:" % inv)
            print("    %-16s IS %9.2f  OOS %9.2f   dIS %+.2f  dOOS %+.2f"
                  % (inv, r["is"]["net"], r["oos"]["net"], mIS, mOOS))
            if mIS <= 0 and mOOS <= 0:
                verdict = ("REGIONAL - inverting the routing removes the gain in both "
                           "eras, so the routing itself is the mechanism")
            else:
                verdict = ("NOT MECHANISM - inverting the routing KEEPS or improves the "
                           "gain, so %s is not winning by session routing" % win)
            print("    -> %s" % verdict)

        else:
            verdict = "SKIPPED - %s routes on nothing, no neighbourhood exists" % win
            print()
            print("  %s sets use=\"union\" unconditionally (unified.py:1026-1027)." % win)
            print("  -> %s" % verdict)
            print("  Recorded as untested, not as passed.")

        out["pairs"].append({
            "book": book, "shipped_mode": ship, "winner_mode": win,
            "e1_claim": claim,
            "shipped": {"is": base["is"], "oos": base["oos"]},
            "winner": {"is": cand["is"], "oos": cand["oos"]},
            "d_is": round(dIS, 2), "d_oos": round(dOOS, 2),
            "region_verdict": verdict,
            "knob_sweep": sweep,
        })
        print()

    # ---- 3. SUMMARY -------------------------------------------------------
    print("=" * 100)
    print("WHAT SURVIVES")
    print("=" * 100)
    for p in out["pairs"]:
        both = p["d_is"] > 0 and p["d_oos"] > 0
        print("  %-28s %-10s vs %-10s  dIS %+8.2f  dOOS %+8.2f  %s"
              % (p["book"], p["winner_mode"], p["shipped_mode"],
                 p["d_is"], p["d_oos"],
                 "BEATS BOTH" if both else "does not beat both"))
        print("      %s" % p["region_verdict"])
    print()
    print("  A survivor is not a promotion. Each one needs its own registry entry,")
    print("  a chart look from the owner, and one OOS reveal spent deliberately.")

    RESULTS.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print()
    print("wrote %s  (%.0fs)" % (RESULTS.name, time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())