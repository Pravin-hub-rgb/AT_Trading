"""CHECK: do low min_bars values really produce IDENTICAL swing counts?

The grid printed:
    -- min_bars=3: 91,559 1m swings
    -- min_bars=5: 91,559 1m swings

Identical to the unit, on 1.95M bars. Either `min_bars` below some floor has
no effect on the chain, or the sweep is not actually varying it. This has to
be settled before any low-min_bars cell is believed, because a "min_bars
ladder" that silently collapses is not a ladder - it is one cell repeated,
and it would understate the search while looking thorough.

Settles it by comparing the actual swing OBJECTS (not just counts) at
several values, and by checking whether the engine's own `max(2, min_bars)`
clamp is the cause.

Run:  $env:PYTHONIOENCODING='utf-8'; python -u scalp_1m_minbars_check.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("live_stuff/tests", "live_stuff", "backend"):
    sys.path.insert(0, str(ROOT / p))

OUT = ROOT / "live_stuff/tests/_1m_minbars_check.json"
VALUES = (2, 3, 4, 5, 6, 8, 10, 15, 20)


def _flow(candles):
    from src.walker import FlowCandle
    return [FlowCandle(date=c["date"], open=float(c["open"]),
                       high=float(c["high"]), low=float(c["low"]),
                       close=float(c["close"])) for c in candles]


def main():
    from src.btc.btc_routes import _compute_swings
    from exp_5m_confirm import load_book

    data, _ = load_book("is")
    c1m = data["fine"]
    flow = _flow(c1m)
    out = {"values": list(VALUES), "counts": {}, "identical_to_prev": {}}

    prev = None
    prev_v = None
    for mb in VALUES:
        sw = _compute_swings(flow, "continuous", min_bars=mb)
        # A cheap but decisive fingerprint: the first and last swing's
        # (index, px) plus the count. Counts alone can coincide.
        fp = None
        if sw:
            fp = [
                (s.get("swing_index"), s.get("dir"),
                 s.get("seg", {}).get("start_idx"),
                 s.get("seg", {}).get("end_idx"),
                 round(float(s.get("seg", {}).get("end_px", 0)), 2))
                for s in (sw[0], sw[len(sw) // 2], sw[-1])
            ]
        out["counts"][str(mb)] = len(sw)
        if prev is not None:
            same = (len(sw) == len(prev)) and (fp == out.get("_fp_prev"))
            out["identical_to_prev"][str(mb)] = bool(same)
            print(f"  min_bars={mb:<3} swings={len(sw):>7,}  "
                  f"same_as_{prev_v}={same}")
        else:
            print(f"  min_bars={mb:<3} swings={len(sw):>7,}")
        out["_fp_prev"] = fp
        prev, prev_v = sw, mb
    out.pop("_fp_prev", None)
    OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
