"""G3 - no look-ahead: does a truncated chain match the full chain's prefix?

WHAT IS BEING MEASURED
----------------------
A mark is only meaningful if it was knowable on its own bar. The engine guards
that with `_seal_h_idx < g_idx` (firstswing.py:356, 360) - the seal must belong to
an EARLIER candle than the break. If any path let a future candle reach that
comparison, the chain would still print plausible numbers, they would just not
have been available yet.

The test: run the chain over a prefix of the candles, then over all of them, and
require that every swing and every mark in the short run is identical - same
index, same time, same price, same kind - to its counterpart in the long run. The
short run must also be a strict PREFIX of the long run: it must stop early, never
skip, never reorder.

This was passed before the per-kind guard landed. That guard added _seal_h_idx
and _seal_l_idx, which are new fields written during the walk and read during
arming, so the earlier pass says nothing about the current wiring. It has to be
re-run against the engine that is actually shipping.

TRUNCATION POINTS
-----------------
Several, not one. A single cut can miss a leak that only shows up at a different
alignment - a leak on the 60,000th candle is invisible if the only cut is at
60,000 and the chain happens to be re-armed by then. 12%, 35%, 58% and 82% of the
window, plus an exact-prefix check at each one.

Note the limit is applied to the CANDLE COUNT, not a date, so the same data the
chart uses is what gets truncated.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from src.btc.btc_routes import _load_window
from src.btc.btc_swing import compute_btc_swings

TF, MIN_BARS, SYMBOL, LIMIT = "15m", 50, "BTCUSDT_BYBIT", 200000
FRACTIONS = (0.12, 0.35, 0.58, 0.82)


def chain(flow):
    swings = compute_btc_swings(flow, opts={"minBars": MIN_BARS},
                                max_swings=max(1, len(flow) // 2))
    out = []
    for s in swings:
        for b in s["breaks"]:
            out.append((b["idx"], b["time"], b["kind"], b["dir"], b["px"]))
    return out


def compare(full, cut, cut_n):
    """cut must be a strict prefix of full: same values, same order, only shorter."""
    if len(cut) > len(full):
        return ("LONG", "short run has %d marks, full has %d" % (len(cut), len(full)))
    first_diff = None
    for i, (a, b) in enumerate(zip(cut, full)):
        if a != b:
            first_diff = (i, a, b)
            break
    if first_diff:
        i, a, b = first_diff
        return ("DIFF", "mark %d: short %s vs full %s" % (i, a, b))
    if len(cut) == len(full):
        # Removing the final bar produced the same marks. That is only sound if the
        # last mark sits strictly before the cut, i.e. the dropped bar genuinely
        # marked nothing. If a mark were AT the cut, dropping the bar would have
        # had to remove it, so equality at the boundary is what must fail.
        if full and full[-1][0] < cut_n:
            return ("EQUAL", "same %d marks; the dropped final bar produced none" % len(cut))
        return ("SUSPECT", "same length but the last mark sits at the cut")
    return ("PREFIX", "identical for all %d marks, then stops early" % len(cut))


def main():
    candles, flow = _load_window(TF, LIMIT, SYMBOL)[0]
    flow = list(flow)
    n = len(flow)
    full = chain(flow)

    print("=" * 78)
    print("G3  no look-ahead - truncated chain must be a strict PREFIX of the full chain")
    print("=" * 78)
    print("candles %d    full chain: %d marks" % (n, len(full)))
    print("")

    results = []
    ok_all = True
    for f in FRACTIONS + (None,):
        if f is None:
            cut_n = n - 1
            label = "n-1 (last bar removed)"
        else:
            cut_n = int(n * f)
            label = "%d%% = %d candles" % (int(f * 100), cut_n)
        cut = chain(flow[:cut_n])
        verdict, detail = compare(full, cut, cut_n)
        ok = verdict in ("PREFIX", "EQUAL")
        ok_all &= ok
        results.append({"label": label, "cut": cut_n, "marks": len(cut),
                        "verdict": verdict, "detail": detail, "pass": ok})
        print("  %-26s short=%-6d  %-7s %s" % (label, len(cut), verdict, detail))
        print("  %-26s %s" % ("", "" if ok else "<-- FAIL"))

    print("")
    # the strong form: every mark before the cut must equal the full chain's mark
    # at the same index, checked by direct lookup rather than zip-order
    cut_n = int(n * 0.58)
    cut = chain(flow[:cut_n])
    by_idx = {}
    for m in full:
        by_idx.setdefault(m[0], []).append(m)
    mism = 0
    for m in cut:
        if by_idx.get(m[0], [None])[0] != m:
            mism += 1
    print("  cross-check by index (58%% cut): %d marks compared, %d mismatched" % (len(cut), mism))
    ok_all &= (mism == 0)

    print("")
    print("  VERDICT: %s" % ("NO LOOK-AHEAD. Every truncated run reproduced the full"
                            "\n           chain's marks exactly and stopped early."
                            if ok_all else
                            "LOOK-AHEAD DETECTED - see the FAIL lines above."))

    Path(ROOT / "backtest/tests/_g3.json").write_text(json.dumps({
        "candles": n, "full_marks": len(full), "cuts": results,
        "index_mismatches": mism, "pass": bool(ok_all)}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
