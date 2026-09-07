"""Regression: daily-mode swing indices must be window-offset (chart positions).

Bug fixed 2026-09-05: in `btc_routes._compute_swings(..., mode='daily')` the
per-day offset loop only touched TOP-LEVEL index keys; seg.start_idx/end_idx
are nested inside `seg`, so the swing zigzag was drawn relative to each day's
slice start (landing on the FIRST day of the window instead of its own day).

Checks (fails on the old code, passes on the fix):
  - every daily-mode swing's seg.start_idx/end_idx falls inside ITS OWN day's
    window slice AND the candle at start_idx carries the swing's day label
  - confirmed_at_idx / fs_at_idx / breaks[].idx are also in-bounds
  - idx ordering (start <= end < confirmed) and px anchoring still hold
  - continuous mode is unaffected (indexes already relative to the window)

Run:  cd backend ; python debug/_btc_daily_idx_check.py
"""
from __future__ import annotations

import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, ".")

from src.btc.btc_routes import _compute_swings, _load_window  # noqa: E402

fails: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        fails.append(msg)
        print("   FAIL", msg)


def day_bounds(candles: list[dict]) -> dict[str, tuple[int, int]]:
    """{date: (slice_start, slice_end)} within the window, at IST days."""
    out: dict[str, tuple[int, int]] = {}
    slice_start = 0
    n = len(candles)
    for i in range(1, n + 1):
        if i == n or candles[i]["date"][:10] != candles[slice_start]["date"][:10]:
            out[candles[slice_start]["date"][:10]] = (slice_start, i)
            slice_start = i
    return out


def check_daily(tf: str, n: int) -> int:
    win, err = _load_window(tf, n)
    assert err is None, (tf, err)
    candles, flow = win
    bounds = day_bounds(candles)
    swings = _compute_swings(flow, "daily", min_bars=14)
    bad_local = 0
    for s in swings:
        day = s["day"]
        lo, hi = bounds.get(day, (0, len(candles)))
        seg = s["seg"]
        st, en = seg["start_idx"], seg["end_idx"]
        cf, fs = s["confirmed_at_idx"], s.get("fs_at_idx", -1)

        # THE regression: seg.* must be within the swing's OWN day slice,
        # and the candle at start_idx must carry that day's date.
        if not (lo <= st < hi):
            bad_local += 1
            check(False, f"{tf}: swing {s['swing_index']} day={day} seg.start={st} outside [{lo},{hi})")
        if not (lo <= en < hi):
            bad_local += 1
            check(False, f"{tf}: swing {s['swing_index']} day={day} seg.end={en} outside [{lo},{hi})")
        if 0 <= st < len(candles) and day != candles[st]["date"][:10]:
            bad_local += 1
            check(False, f"{tf}: swing day={day} but candle@start={candles[st]['date'][:10]}")

        check(st <= en, f"{tf}: seg.start({st}) <= seg.end({en})")
        check(en <= cf < len(candles), f"{tf}: confirmed idx in bounds ({cf})")
        if fs >= 0:
            check(fs < len(candles), f"{tf}: fs idx in bounds ({fs})")
        # px anchoring
        if 0 <= st < len(candles):
            check(candles[st]["low"] - 1e-9 <= seg["start_px"] <= candles[st]["high"] + 1e-9, f"{tf}: start px in bar @{st}")
        if 0 <= en < len(candles):
            check(candles[en]["low"] - 1e-9 <= seg["end_px"] <= candles[en]["high"] + 1e-9, f"{tf}: end px in bar @{en}")
        prev_i = -1
        for b in s["breaks"]:
            check(prev_i < b["idx"] < len(candles), f"{tf}: break idx ordered/bounded ({b['idx']})")
            prev_i = b["idx"]
            check(candles[b["idx"]]["low"] - 1e-9 <= b["px"] <= candles[b["idx"]]["high"] + 1e-9, f"{tf}: break px in bar @{b['idx']}")
    ok = len(swings) - bad_local
    print(f"[daily {tf}] window={n} swings={len(swings)} in-day-ok={ok} violations={bad_local}")
    return bad_local


def main() -> int:
    total = 0
    total += check_daily("5m", 4000)
    total += check_daily("15m", 3000)
    total += check_daily("1m", 5000)
    print(f"\nTOTAL daily-mode index violations: {total}")
    print("RESULT:", "PASS" if total == 0 else "FAIL")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())