"""Count the strategy's real degrees of freedom, and separate the two kinds.

THE ARGUMENT BEING TESTED
-------------------------
The deflated-statistics study (`exp_thesis_deflated_stats.py`) estimated 464
trials from `logged_experiments x 8 documented arms per experiment` and found
the out-of-sample result indistinguishable from the best of 464 lucky searches
(p = 0.9975). That number decides the verdict, so it deserves to be earned
rather than assumed.

The argument against 464: most of those trials were numeric knob sweeps -
atr_low_thresh 0.30 or 0.35, chop_thresh 54 or 58, cooldown_bars 6 or 8. Tuning
a threshold that lands nowhere meaningful is not a distinct strategy, it is the
same strategy measured twice. The structural choices - B1 or B2 entry, whether
to wait for the swing to complete, which HTF leg, serial or multi - are a small
handful of genuinely different books.

So this splits the parameter space in two and reports, for each:

  CATEGORICAL  a switch between different books. Each distinct combination is a
               real trial and must be counted.
  NUMERIC      a threshold moved along a line. These should NOT each count as a
               trial, because whether they deserve to depends on something
               measurable: does moving the knob leave the book intact (a plateau)
               or destroy it (a spike fitted to the sweep point)?

The plateau question is answered by `exp_dof_plateau.py`. This file only does
the accounting.

Output: dof_inventory.json
"""
from __future__ import annotations

import io
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tests"))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / "backend"))

from experiment_registry import EXPERIMENTS, BP, ENGINE_DEFAULTS  # noqa: E402

OUT = HERE / "dof_inventory.json"

# Why each knob is in the bucket it is in. Not a guess - each line records what
# the knob actually changes in the engine, because the same knob name can be
# structural in one family and a threshold in another.
STRUCTURAL = {
    "mode":            "which regime branch in unified.py runs - a different book",
    "pivot_rule":      "how the HTF leg is cut",
    "exp_fs_entry_side": "long / short / off - a different book",
    "exp_mltf":        "multi-timeframe filter on/off",
    "exp_mltf_side":   "multi-timeframe filter on/off",
    "window_end":      "entry or exit window end",
    "swing":           "which swing series the book is built on (registry field)",
    "use_bp":          "baseline params or engine defaults",
    "exp_htf_es_only": "HTF exit source",
    "exp_mcloff":      "max consecutive losses gate on/off",
    "max_positions":   "SERIAL (1) vs MULTI (0) - the largest structural choice there is",
    "exp_htf_fs_entry": "all vs flip entry gate",
    "exp_decay_mode":  "decay gate mode 3/4/5",
    "exp_event_mode":  "event gate mode",
    "exp_loss_streak_mode": "loss streak behaviour",
    "exp_window_win_kill_action": "what the kill gate does",
}
NUMERIC = {
    "atr_high_thresh": "ATR high threshold",
    "atr_low_thresh":  "ATR low threshold",
    "chop_thresh":     "chop threshold",
    "cooldown_bars":   "bars between entries",
    "max_consecutive_losses": "loss streak gate length",
    "sl_buf_atr":      "stop buffer as a fraction of ATR",
    "ext_stop_r":      "extension stop in R",
    "exp_partial_r":   "partial take-profit level in R",
    "exp_persist":     "bars a signal persists",
    "exit_fs_max_gap_h": "max hours to wait for the swing confirmation",
    "exp_pause_bars":  "bars to pause after a signal",
    "atr_high":        "ATR multiple",
    "atr_low":         "ATR multiple",
    "exp_trail_skip_n": "trailing events to drop",
    "exp_skip_n":      "trailing events to drop",
    "exp_htf_leg":     "HTF leg length in bars",
}


def main() -> int:
    vals = defaultdict(set)
    books = 0
    for k, e in EXPERIMENTS.items():
        if not isinstance(e, dict):
            continue
        books += 1
        p = dict(e.get("params") or {})
        if e.get("swing"):
            p["swing"] = e["swing"]
        if e.get("use_bp") is not None:
            p["use_bp"] = e["use_bp"]
        for kk, vv in p.items():
            try:
                vals[kk].add(json.dumps(vv, sort_keys=True))
            except TypeError:
                vals[kk].add(str(vv))

    s_vals, n_vals, unk = {}, {}, {}
    for k, v in vals.items():
        d = sorted(v)
        if k in STRUCTURAL:
            s_vals[k] = {"values": d, "n": len(d), "why": STRUCTURAL[k]}
        elif k in NUMERIC:
            try:
                nums = sorted(float(json.loads(x)) for x in d)
            except (ValueError, TypeError):
                nums = []
            n_vals[k] = {"values": nums, "n": len(nums), "why": NUMERIC[k]}
        else:
            unk[k] = {"values": d, "n": len(d)}

    # Effective structural space: the product of the categorical switches that
    # actually vary. Not all switches vary, and a switch pinned to one value
    # across every book contributes nothing.
    vary_struct = {k: v for k, v in s_vals.items() if v["n"] > 1}
    vary_num = {k: v for k, v in n_vals.items() if v["n"] > 1}
    struct_combos = 1
    for v in vary_struct.values():
        struct_combos *= v["n"]

    print("=" * 76)
    print("DEGREES OF FREEDOM INVENTORY")
    print("=" * 76)
    print("books with params : %d" % books)
    print()
    print("STRUCTURAL - each distinct combination is a genuinely different book")
    print("-" * 76)
    for k, v in sorted(s_vals.items(), key=lambda x: -x[1]["n"]):
        mark = "*" if v["n"] > 1 else " "
        print(" %s %-20s %d distinct   %s" % (mark, k, v["n"], ",".join(v["values"])[:44]))
    print()
    print("NUMERIC - a threshold moved along a line, NOT automatically a trial")
    print("-" * 76)
    for k, v in sorted(n_vals.items(), key=lambda x: -x[1]["n"]):
        mark = "*" if v["n"] > 1 else " "
        print(" %s %-20s %2d distinct  %s" % (mark, k, v["n"], str(v["values"])[:44]))
    print()
    print("UNCLASSIFIED - needs a home before the count can be trusted")
    print("-" * 76)
    for k, v in sorted(unk.items(), key=lambda x: -x[1]["n"]):
        print("   %-20s %d distinct  %s" % (k, v["n"], ",".join(v["values"])[:44]))
    print()
    print("=" * 76)
    print("structural combinations actually varied : 2^%d = %d"
          % (len(vary_struct), struct_combos))
    print("  from %d varying switches: %s"
          % (len(vary_struct), ", ".join("%s(%d)" % (k, v["n"]) for k, v in vary_struct.items())))
    print("numeric knobs that varied                : %d" % len(vary_num))
    print()
    print("The 464 in exp_thesis_deflated_stats.py is an estimate from a")
    print("documented log, not an enumeration. The enumeration the registry")
    print("supports is above. Which numeric knobs deserve trial status depends")
    print("on plateau width, which is measured separately.")
    print()
    res = {"books": books,
           "structural": s_vals, "numeric": n_vals, "unclassified": unk,
           "structural_combinations": struct_combos,
           "varying_structural_switches": {k: v["n"] for k, v in vary_struct.items()},
           "varying_numeric_knobs": {k: v["n"] for k, v in vary_num.items()}}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(res, indent=1, sort_keys=True))
    print("wrote %s" % OUT.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())