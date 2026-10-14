"""
A - FS-TERMINAL CAUSALITY GATE

THE INVARIANT

For every swing, no break may fall at or after the swing's FS. The entry is
triggered by FS, so any break at or after the FS bar carries information the
trader did not have when they entered.

Empirically this holds absolutely, which is what makes it worth asserting:

    15m  2840 / 2840 swings - FS is the final event
    1h   1540 / 1540 swings - FS is the final event

WHY THIS GATE DID NOT EXIST BEFORE

The correction mislabelled 43 B2s as FLIP and 35 FLIPs as B2. A swing whose true
last mark is a FLIP, but which was labelled B2, would still satisfy "no break
after FS" - the break is still before FS, only mislabelled. So this invariant
cannot catch the bug that was actually fixed. It catches a different and more
fundamental failure: a break that is genuinely located after the FS bar, i.e. a
break whose information only exists at or after entry.

That failure mode is exactly what closed three graveyard families (see
CLOSED_DO_NOT_REPEAT: the M2/end_px family, prevpos, and the directional-FS
books). All three shipped large numbers by reading a field that settles later.
This gate is the cheap standing check for that class, and it had no automated
cover at all.

WHAT IT CHECKS, on every chain and both eras

  1. No break with idx >= fs_at_idx on any swing that has an FS.
  2. FS is present on swings that have any break (an FS-less swing with emitted
     marks would be a different kind of inconsistency).
  3. Terminal-kind census, reported as a fingerprint so a change is visible.

Failure here is NOT a thing to patch. It means the chain is reading the future
and every downstream number produced from it is void until it is fixed.

Usage:
    $env:PYTHONIOENCODING='utf-8'
    ..\\..\\backend\\venv\\Scripts\\python.exe -u exp_fs_terminal_gate.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]   # experiments/<name>/ -> repo root
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

HERE = Path(__file__).resolve().parent

CHAINS = [
    ("15m mb50", "15m", "min_bars_15m"),
    ("1h  mb10", "1h", "min_bars_1h"),
    ("1h  mb15", "1h", 15),
]


def main() -> int:
    from engine.v18_params import SWING
    from test_4_new_concepts import load_unseen
    from run_experiment import get_data
    from src.btc.btc_swing import compute_btc_swings

    print("=" * 92)
    print("A - FS-TERMINAL CAUSALITY GATE")
    print("=" * 92)
    print("  Rule: no emitted break may fall at or after the swing's FS bar.")
    print("  A violation means the entry used information that had not happened.")
    print()

    sets = {"is": None, "oos": None}
    d_is = get_data()
    sets["is"] = (d_is["c15"], d_is["f15"])
    (c15o, f15o), (c1ho, f1ho) = load_unseen("15m"), load_unseen("1h")
    sets["oos"] = (c15o, f15o, c1ho, f1ho)

    out = {"stage": "fs_terminal_gate", "chains": {}}
    bad = []

    for label, tf, mb in CHAINS:
        for era in ("is", "oos"):
            if era == "is":
                flow = d_is["f15"] if tf == "15m" else d_is["f1h"]
            else:
                if tf == "15m":
                    flow = f15o
                else:
                    flow = f1ho
            minb = SWING[mb] if isinstance(mb, str) else mb
            sw = compute_btc_swings(flow, opts={"minBars": max(2, int(minb)),
                                                "b2GapBars": 1},
                                    max_swings=max(1, len(flow) // 2))

            viol = 0
            fs_less_with_breaks = 0
            checked = 0
            worst = None
            term = {}
            for s in sw:
                fs = s.get("fs_at_idx")
                if fs is None:
                    if s["breaks"]:
                        fs_less_with_breaks += 1
                    continue
                checked += 1
                after = [b for b in s["breaks"] if b["idx"] >= fs]
                if after:
                    viol += 1
                    if worst is None:
                        worst = {"swing": s["swing_index"], "fs_idx": fs,
                                 "n_after": len(after),
                                 "kinds": sorted({b["kind"] for b in after})}
                tk = s["breaks"][-1]["kind"] if s["breaks"] else "none"
                term[tk] = term.get(tk, 0) + 1

            key = "%s|%s" % (label, era)
            out["chains"][key] = {"swings": len(sw), "checked": checked,
                                  "violations": viol, "terminal": term}
            status = "ok  " if viol == 0 and fs_less_with_breaks == 0 else "FAIL"
            print("  [%s] %-9s %-4s swings=%-5d fs-checked=%-5d violations=%-4d fs-less-with-breaks=%d"
                  % (status, label, era.upper(), len(sw), checked, viol,
                     fs_less_with_breaks))
            print("         terminal kinds: %s"
                  % ", ".join("%s=%d" % (k, term[k]) for k in sorted(term)))
            if viol or fs_less_with_breaks:
                bad.append(key)
                if worst:
                    print("         FIRST VIOLATION: %r" % worst)

    print()
    (HERE / "fs_terminal_results.json").write_text(json.dumps(out, indent=2),
                                                   encoding="utf-8")
    print("  wrote %s" % (HERE / "fs_terminal_results.json"))
    if bad:
        print()
        print("  RESULT: FAIL on %s" % ", ".join(bad))
        print()
        print("  DO NOT PATCH THIS. A violation means the chain reads a field that")
        print("  settles at or after the entry bar, which is the same failure that")
        print("  closed the M2, prevpos and directional-FS families. Every number")
        print("  derived from this chain is void until the engine is fixed.")
        return 1

    print()
    print("  RESULT: pass - on every chain, in both eras, FS is the final event.")
    print("  No emitted break sits at or after the FS bar, so no entry in this")
    print("  sweep can have read a mark that had not printed yet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())