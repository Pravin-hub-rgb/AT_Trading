"""
C - SUPPRESSION ACCOUNTING: what is thrown away, and by which rule.

THE BLACK BOX

The invariant harness counts 20,460 ARMED breaks that never became an emitted
mark, against 7,734 marks that did. That is 73% of everything the engine
detected. The dir_confirmed gate accounts for 6,668 of them. Roughly 13,800
suppressed breaks have never been attributed to any rule - they are 1.8x the
emitted mark count, and the whole sweep has been run without anyone asking where
they went.

WHY THIS FILE IS PART INVENTORY, PART MEASUREMENT

The suppression stack is decided by engine state that is not visible from the
finished swing record - `self.armed`, `self._pending_arm`, `self.dir_confirmed`,
`self._b2_done_in_dir`, `self._last_mark_kind`. Splitting the 20,460 by reason
therefore needs engine instrumentation inside the walk, not a post-hoc read of
the chain. That instrumentation is a separate, riskier change and is NOT done
here.

What IS done, without editing the engine:

  1. The gap rule is isolated by toggling b2GapBars, which is a chain option and
     needs no patch. That measures exactly one suppression path precisely.
  2. The remaining suppression paths are inventoried from the shipping source
     with file and line, so the black box has a known shape even where it does
     not yet have a number.
  3. The unattributed residual is stated as a number rather than left implied.

WHAT THIS DOES NOT CLAIM

No path is guessed at. The source comment at firstswing.py:391 already records
4,102 breaks dropped while NOT armed - which is a separate bucket from the 20,460
armed ones, and is called out so the two are not conflated.

Usage:
    $env:PYTHONIOENCODING='utf-8'
    ..\\..\\..\\backend\\venv\\Scripts\\python.exe -u exp_suppressed_accounting.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

HERE = Path(__file__).resolve().parent

# Recorded by exp_swing_invariants.py on the current chain.
ARMED_SUPPRESSED = 20460
DIR_CONFIRMED_SUPPRESSED = 6668

PATHS = [
    ("not armed", "firstswing.py:428", 4102,
     "self.armed false - the minBars / pending-arm gate. 3,941 of 4,102 (96%) "
     "broke a pivot sealed on an EARLIER bar, per the source comment. Separate "
     "bucket from the armed ones."),
    ("dir_confirmed", "firstswing.py:472", DIR_CONFIRMED_SUPPRESSED,
     "B2 requires a confirmed direction. Forcing it False released this many B2s "
     "(measured by exp_dir_confirmed_b2_path.py)."),
    ("volatile sustains a flipped leg", "firstswing.py:528-534", None,
     "NO MARK AT ALL. Owner 2023-06-10 22:30: 'we cannot mark it anything here "
     "... so we have to wait.' Silent - produces no row in the swing record."),
    ("B2 already done in this direction", "firstswing.py:535", None,
     "_b2_done_in_dir - one B2 per direction per swing."),
    ("gap rule", "firstswing.py:_b2_if_gap_allows", None,
     "Extreme did not survive one candle. ISOLATED BELOW by toggle."),
]


def main() -> int:
    from engine.v18_params import SWING
    from test_4_new_concepts import load_unseen
    from run_experiment import get_data
    from src.btc.btc_swing import compute_btc_swings

    print("=" * 104)
    print("C - SUPPRESSION ACCOUNTING")
    print("=" * 104)

    d = get_data()
    counts = {}
    for gap in (1, 0, 2):
        sw = compute_btc_swings(
            d["f15"], opts={"minBars": SWING["min_bars_15m"], "b2GapBars": gap},
            max_swings=max(1, len(d["f15"]) // 2))
        kinds = {}
        for s in sw:
            for b in s["breaks"]:
                kinds[b["kind"]] = kinds.get(b["kind"], 0) + 1
        counts[gap] = (sum(kinds.values()), kinds, len(sw))

    base_marks, base_kinds, base_sw = counts[1]
    gap0_marks, gap0_kinds, _ = counts[0]
    print()
    print("  THE GAP RULE, isolated by toggle (15m IS, chain option, no engine patch)")
    print("    %-24s %8s %8s %8s %8s" % ("b2GapBars", "swings", "marks", "B2", "FLIP"))
    for gap in (1, 0, 2):
        m, k, s = counts[gap]
        print("    %-24s %8d %8d %8d %8d" % ("gap=%d%s" % (gap, "  <- pinned" if gap == 1 else ""),
                                            s, m, k.get("B2", 0), k.get("FLIP", 0)))
    gap_rule = gap0_marks - base_marks
    print()
    print("    the gap rule removes %d marks in total (%d B2, %d FLIP). It is the ONLY"
          % (gap_rule, gap0_kinds.get("B2", 0) - base_kinds.get("B2", 0),
             gap0_kinds.get("FLIP", 0) - base_kinds.get("FLIP", 0)))
    print("    suppression path that can be measured exactly from the chain alone.")
    print()

    print("  THE SUPPRESSION STACK, from the shipping source")
    print("    %-36s %-26s %8s" % ("path", "site", "count"))
    print("    " + "-" * 76)
    for name, site, n, _ in PATHS:
        print("    %-36s %-26s %8s" % (name, site, n if n is not None else "unmeasured"))
    print()
    for name, site, n, note in PATHS:
        print("    %s" % name)
        print("      %s" % note)
        print()

    attributed = gap_rule + DIR_CONFIRMED_SUPPRESSED
    residual = ARMED_SUPPRESSED - attributed
    print("  ACCOUNTING for the %d ARMED suppressed breaks" % ARMED_SUPPRESSED)
    print("    %-40s %8d" % ("gap rule (measured by toggle)", gap_rule))
    print("    %-40s %8d" % ("dir_confirmed (measured)", DIR_CONFIRMED_SUPPRESSED))
    print("    %-40s %8d" % ("RESIDUAL - not yet attributed", residual))
    print()
    print("    The residual is %.1f%% of the armed suppressions and %.2fx the emitted"
          % (100.0 * residual / ARMED_SUPPRESSED, residual / base_marks))
    print("    mark count. Closing it needs counters inside the walk, not a read of")
    print("    the finished chain. NOT DONE HERE.")
    print()
    print("    The 4,102 not-armed drops are a SEPARATE bucket and are not part of")
    print("    the %d above; mixing them would make the residual look smaller than it is."
          % ARMED_SUPPRESSED)

    out = {"stage": "suppressed_accounting", "armed_suppressed": ARMED_SUPPRESSED,
           "emitted_marks_is": base_marks,
           "gap_rule_marks": gap_rule,
           "dir_confirmed": DIR_CONFIRMED_SUPPRESSED,
           "residual_unattributed": residual,
           "not_armed_separate_bucket": 4102,
           "paths": [{"name": n, "site": s, "count": c, "note": t}
                     for n, s, c, t in PATHS]}
    (HERE / "suppressed_results.json").write_text(json.dumps(out, indent=2),
                                                  encoding="utf-8")
    print()
    print("  wrote %s" % (HERE / "suppressed_results.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())