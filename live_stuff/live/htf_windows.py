"""HTF window (interval) construction for book 107 (and shared with unified).

Mirrors the `to_intervals` closure that used to live inside
`simulate_htf_ltf_streak_halt` in `_vendored/unified.py`. Extracted so it can
be unit-tested and reused by the incremental HTF tracker.
"""
import bisect
from typing import Any, List, Optional


def _r_touch_end(trade, fine_ltf, fine_ts, ext_r):
    """HTF window end = first ts price touches ext_r (1.5R) from HTF entry."""
    d = 1 if trade["dir"] == "long" else -1
    pe = float(trade["entry_price"])
    psl = float(trade["sl"])
    hrisk = abs(pe - psl)
    if hrisk <= 0 or ext_r <= 0 or not fine_ltf:
        return int(trade["exit_ts"])
    level = pe + ext_r * hrisk * d
    e_ts = int(trade["exit_ts"])
    k = bisect.bisect_right(fine_ts, int(trade["entry_ts"]))
    while k < len(fine_ltf):
        ts = int(fine_ltf[k]["ts"])
        if ts > e_ts:
            break
        hi = float(fine_ltf[k]["high"])
        lo = float(fine_ltf[k]["low"])
        if (d == 1 and hi >= level) or (d == -1 and lo <= level):
            return ts
        k += 1
    return e_ts


def to_intervals(trades, candles_htf=None, fine_ltf=None, fine_ts=None,
                 ext_stop_r=1.5, window_end="exit"):
    """Convert HTF trades into (start, end, dir, entry, sl) interval tuples.

    window_end:
      "exit"      -> HTF trade exit + settle (default, shipped)
      "r_touch"   -> first touch of ext_stop_r R
      "bias_flip" -> next opposite-direction HTF entry
    """
    fine_ltf = fine_ltf or []
    fine_ts = fine_ts or []
    candles_htf = candles_htf or []
    _wend_settle = 60 if fine_ltf else 3600
    last_htf_ts = int(candles_htf[-1]["ts"]) if candles_htf else 0

    iv = []
    for t in trades:
        if t.get("outcome") == "open":
            iv.append([int(t["entry_ts"]), last_htf_ts + 3600,
                       1 if t["dir"] == "long" else -1,
                       float(t["entry_price"]), float(t["sl"])])
            continue
        if window_end == "r_touch":
            wend = _r_touch_end(t, fine_ltf, fine_ts, ext_stop_r)
        else:
            wend = int(t["exit_ts"]) + _wend_settle
        iv.append([int(t["entry_ts"]), wend,
                   1 if t["dir"] == "long" else -1,
                   float(t["entry_price"]), float(t["sl"])])
    iv.sort(key=lambda x: x[0])
    if window_end == "bias_flip":
        last_ts = int(candles_htf[-1]["ts"]) if candles_htf else 0
        for i, w in enumerate(iv):
            nxt = None
            for j in range(i + 1, len(iv)):
                if iv[j][2] != w[2]:
                    nxt = iv[j][0]
                    break
            w[1] = (nxt - 1) if nxt is not None else max(w[1], last_ts)
    return [tuple(w) for w in iv]