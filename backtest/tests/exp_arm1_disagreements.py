"""Every candle where unpatched and patched DISAGREE, for the owner to adjudicate.

THE LOOP THIS EXISTS TO FEED
----------------------------
The owner cannot adjudicate unpatched against patched by eyeballing a summary -
some marks are right in one, some in the other, so "which is better" has no answer.
What he asked for instead, and what this produces, is the disagreement list itself:
a short, dated, ordered list of the candles where the two chains mark something
differently, each with what it looks like, so he can walk them one at a time and
say which side is right. Then the engine is adjusted, and the list is regenerated
until it is empty.

That is the same shape as the retro/causal reconciliation he already did once:
reconcile until the two agree, then retire one.

THE OWNER'S RULE, AS HE STATED IT
---------------------------------
Two things are legitimate B1 marks and BOTH count:

  1. PIVOT BREAK - the bar broke a pivot that was sealed on an EARLIER bar. This is
     the white flow line on the chart. (2026-08-14 22:45, B1 up at 63191.3.)

  2. FIRST-CANDLE EXTREME BREAK - at the very start of a leg the flow line has not
     been drawn yet and no pivot can exist, so the extreme of the FIRST candle of
     the leg substitutes for the missing pivot. His own words: "the extreme point
     here is 7:15's high ... the pivot is at 8:30 ... if the high of this 7:15
     candle was broken, then it can be considered as a broken pivot, because it is
     an extreme." And for a leg whose first candle starts at 22:15 with the pivot
     at 22:30: a later candle breaking the 22:15 high, on a red candle, is a valid
     B1 in the opposite direction.

So a mark is NOT wrong merely because it broke an extreme rather than a pivot. It
is wrong only when it broke neither a prior-bar pivot NOR the leg's own first
candle. That distinction is the whole point and it is why a plain
pivot-only rule (which is what was tried and is recorded as ZERO flagged) discards
legitimate marks - it counts them as errors when they are not.

WHAT IS FLAGGED
---------------
  pivot-break        broke a pivot sealed on an earlier bar            -> legitimate
  first-candle-ext   broke the extreme of the leg's first candle       -> legitimate
  same-bar           the "pivot" it sits on was sealed on this bar     -> wrong
  neither            broke no prior pivot and no leg-start extreme   -> wrong

Only the last two are "wrong" by the owner's own rule, and this script prints
those separately from the ones that merely need a yes/no from him.

Usage:  $env:PYTHONIOENCODING='utf-8'; python -u exp_arm1_disagreements.py [limit]
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import exp_phantom_marks as PM          # noqa: E402

OUT = ROOT / "backtest/tests/_arm1_disagreements.json"
TF, MIN_BARS, SYMBOL = "15m", 50, "BTCUSDT_BYBIT"


def verdict(r: dict) -> str:
    """Apply the owner's rule to one mark."""
    up = r["dir"] == "up"
    piv_idx = r["piv_idx"]
    crossed = (r["bar_hi"] > r["piv_px"]) if up else (r["bar_lo"] < r["piv_px"]) \
        if r["piv_px"] is not None else False
    # the level that was actually broken == the leg's first candle?
    first_candle = r["lvl_idx"] == r["seed_idx"] and r["lvl_idx"] >= 0
    if piv_idx < 0:
        return "first-candle-ext" if first_candle else "no-pivot"
    if piv_idx == r["idx"]:
        return "same-bar"
    if crossed:
        return "pivot-break"
    if first_candle:
        return "first-candle-ext"
    return "neither"


def classify(recs):
    out = []
    for r in recs:
        r = dict(r)
        r["verdict"] = verdict(r)
        r["leg_first_bar"] = r["idx"] - r["bars_seen"] + 1
        out.append(r)
    return out


def main() -> int:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 200000
    t0 = time.time()
    PM.LIMIT = limit
    print("running both chains ...", flush=True)
    ship = classify(PM.run(False))
    pat = classify(PM.run(True))

    def key(recs):
        return {(r["time"], r["kind"], r["dir"]): r for r in recs}
    S, P = key(ship), key(pat)
    only_p = sorted(set(P) - set(S))
    only_s = sorted(set(S) - set(P))
    both = sorted(set(S) & set(P))

    print("\n  marks in BOTH chains (identical) : %d" % len(both))
    print("  marks ONLY in patched             : %d" % len(only_p))
    print("  marks ONLY in unpatched           : %d" % len(only_s))

    wrong_p = [P[k] for k in only_p if P[k]["verdict"] in ("same-bar", "neither")]
    wrong_s = [S[k] for k in only_s if S[k]["verdict"] in ("same-bar", "neither")]
    legit_p = [P[k] for k in only_p if P[k]["verdict"] not in ("same-bar", "neither")]
    legit_s = [S[k] for k in only_s if S[k]["verdict"] not in ("same-bar", "neither")]

    print("\n=== by the owner's rule (pivot-break OR first-candle-ext = legitimate) ===")
    print("  patched adds   legitimate %-6d  wrong %d" % (len(legit_p), len(wrong_p)))
    print("  unpatched-only legitimate %-6d  wrong %d" % (len(legit_s), len(wrong_s)))

    # The walk list. Chronological, wrong-first, so the owner starts at the top of
    # the chart and works down. Capped so it stays something a person will do.
    CAP = 40
    print("\n" + "=" * 78)
    print("DISAGREEMENTS THE OWNER SHOULD LOOK AT  (earliest first, wrong first)")
    print("=" * 78)
    walk = ([("patched adds it", r) for r in wrong_p] +
            [("unpatched only", r) for r in wrong_s])
    walk.sort(key=lambda x: x[1]["idx"])
    for i, (side, r) in enumerate(walk[:CAP], 1):
        print("%3d  %s  %-4s %-4s   %-16s  leg_first_bar=%d  piv=%s@%s  bar=%s"
              % (i, r["time"], r["kind"], r["dir"], side, r["leg_first_bar"],
                 r["piv_px"], r["piv_idx"], r["bars_seen"]))
    if len(walk) > CAP:
        print("     ... and %d more in the JSON" % (len(walk) - CAP))

    print("\n--- first 12 LEGITIMATE disagreements (patched adds; likely correct) ---")
    for r in sorted(legit_p, key=lambda x: x["idx"])[:12]:
        print("  %s  %-4s %-4s  %-16s  piv=%s@%s  leg_first=%s"
              % (r["time"], r["kind"], r["dir"], r["verdict"], r["piv_px"],
                 r["piv_idx"], r["lvl_idx"] == r["seed_idx"]))

    print("\n--- first 12 LEGITIMATE disagreements (unpatched only; patch may have lost a good mark) ---")
    for r in sorted(legit_s, key=lambda x: x["idx"])[:12]:
        print("  %s  %-4s %-4s  %-16s  piv=%s@%s  leg_first=%s"
              % (r["time"], r["kind"], r["dir"], r["verdict"], r["piv_px"],
                 r["piv_idx"], r["lvl_idx"] == r["seed_idx"]))

    OUT.write_text(json.dumps(
        {"walk": [{"side": s, **r} for s, r in walk],
         "patched_only": [P[k] for k in only_p],
         "unpatched_only": [S[k] for k in only_s]},
        indent=1, default=str) + "\n", encoding="utf-8")
    print("\nwrote %s  (%.0fs)" % (OUT, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
