"""
SHOW ME THE SUPPRESSED BREAKS - the candles, with the reason, for the chart.

WHY THIS FILE WAS REWRITTEN TWICE

Attempt 1 diffed the b2GapBars=0 chain against the shipped chain and reported
8,305 removed. Wrong: swing_index was in the signature, and gap=0 yields 2,979
swings against 2,840, so nearly every row "differed". B1=2878 removed gave it
away - the B1 count is identical in both chains.

Attempt 2 dropped swing_index and reported 1,907. Still wrong, and the reason is
worth writing down: changing the gap changes the CHAIN, not just which marks
survive. 2,979 swings against 2,840 means segmentation itself moves, so a set
difference over two structurally different chains cannot attribute a candle to a
rule. The aggregate (8,545 vs 7,734 = 811) was always right; the per-candle
attribution from a chain diff was never available.

SO THIS READS THE LEDGER INSTEAD. firstswing.py now carries a debug-only
suppression list, off by default, recording time, side, the level that was
rejected and why. That is the only sound source. exp_baseline_freeze.py --compare
reports IDENTICAL with the flag off, so the instrumentation changes nothing.

Usage:
    $env:PYTHONIOENCODING='utf-8'
    ..\\..\\..\\backend\\venv\\Scripts\\python.exe -u exp_show_suppressed.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

HERE = Path(__file__).resolve().parent
SHOW = 20


def main() -> int:
    from run_experiment import get_data
    from engine.v18_params import SWING
    from src.btc.btc_swing import compute_btc_swings

    d = get_data()
    c15 = d["c15"]
    ts_idx = {c["date"][:16]: i for i, c in enumerate(c15)}
    mb = SWING["min_bars_15m"]

    plain = compute_btc_swings(d["f15"], opts={"minBars": mb, "b2GapBars": 1},
                               max_swings=max(1, len(d["f15"]) // 2))
    dbg = compute_btc_swings(d["f15"],
                             opts={"minBars": mb, "b2GapBars": 1,
                                   "debugSuppressed": True},
                             max_swings=max(1, len(d["f15"]) // 2))

    # identity: the flag must not move a single mark
    def sig(sws):
        return sorted((b["time"][:16], b["kind"], b["dir"], round(float(b["px"]), 1))
                      for s in sws for b in s["breaks"])
    same = sig(plain) == sig(dbg)
    print("=" * 108)
    print("SUPPRESSED BREAKS - 15m IS, minBars=%d, gap=%d" % (mb, 1))
    print("=" * 108)
    print("  flag-off vs flag-on mark sets identical: %s  (%d marks either way)"
          % (same, len(sig(plain))))
    if not same:
        print("  ABORT: the debug flag changed the chain.")
        return 2
    print()

    recs = []
    for s in dbg:
        for r in s.get("suppressed", []):
            recs.append((r, s["swing_index"]))

    counts = Counter(r["reason"] for r, _ in recs)
    print("  %d suppressions recorded, by reason:" % len(recs))
    for k, v in counts.most_common():
        print("    %-34s %7d" % (k, v))
    print()
    total_marks = sum(len(s["breaks"]) for s in dbg)
    print("  for scale: %d marks were emitted, %d detections were suppressed."
          % (total_marks, len(recs)))
    print()

    LBL = {
        "gap_contaminated": ("The candle after the extreme ALSO breached it, so the",
                             "level was contaminated - no B2. Never fires on 15m IS:",
                             "the target is the running extreme, which by definition",
                             "nothing has breached. Vestigial path."),
        "gap_too_fresh": ("The extreme was only 1 bar old. It must survive a whole",
                          "candle before a break counts. NO WHITE PIVOT IS INVOLVED",
                          "- owner verified 2023-01-01 swing 1, where 18:30 / 18:45",
                          "/ 19:00 are lower-high AND lower-low with no reversal bar,",
                          "so there is no pivot at any of those candles to name."),
        "not_armed": ("self.armed is false - the minBars / pending-arm window.",
                      "_step never ran, so no mark of any kind was possible."),
        "volatile_sustains_flipped_leg": ("Volatile candle sustained a direction that",
                                           "had ALREADY flipped since B1, so a second",
                                           "mark in that direction is impossible: it",
                                           "cannot be B2 (B2 belongs to B1's side) and",
                                           "cannot be a FLIP (already that direction).",
                                           "NO MARK is the correct outcome here."),
    }

    for reason in ("gap_contaminated", "gap_too_fresh",
                   "volatile_sustains_flipped_leg", "not_armed"):
        rows = [(r, swi) for r, swi in recs if r["reason"] == reason]
        if not rows:
            continue
        print("  " + "=" * 104)
        print("  REASON: %s   (%d)" % (reason, len(rows)))
        print("  %s" % LBL.get(reason, ("", ""))[0])
        print("  %s" % LBL.get(reason, ("", ""))[1])
        print()
        print("    %-17s %-9s %-6s %10s %10s %s"
              % ("time", "side", "swing", "lvl_px", "this_px", "context"))
        print("    " + "-" * 96)
        for r, swi in rows[:SHOW]:
            tm = r["time"][:16]
            i = ts_idx.get(tm)
            ctx = ""
            if i is not None:
                c = c15[i]
                ctx = "H=%.1f L=%.1f C=%.1f" % (c["high"], c["low"], c["close"])
            extra = ""
            if r.get("lvl_time"):
                extra = "lvl@%s" % r["lvl_time"][11:16]
            if r.get("gap_px") is not None:
                extra += " nextbar=%s" % r["gap_px"]
            if r.get("bars_since") is not None:
                extra += " bars_since=%s" % r["bars_since"]
            print("    %-17s %-9s %-6s %10s %10s %s  %s"
                  % (tm, r.get("side", ""), swi, r.get("lvl_px", ""),
                     r.get("close") or r.get("high") or "", ctx, extra))
        if len(rows) > SHOW:
            print("    ... and %d more" % (len(rows) - SHOW))
        print()

    out = {"stage": "show_suppressed", "identity_ok": same,
           "emitted_marks": total_marks,
           "total_suppressed": len(recs),
           "by_reason": dict(counts),
           "samples": {k: [r for r, _ in recs if r["reason"] == k][:300]
                       for k in counts}}
    (HERE / "show_suppressed_results.json").write_text(json.dumps(out, indent=2),
                                                       encoding="utf-8")
    print("  wrote %s  (300 samples of each reason kept)" % (HERE / "show_suppressed_results.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())