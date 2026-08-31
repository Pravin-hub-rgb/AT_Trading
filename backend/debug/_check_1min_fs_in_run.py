"""Debug: check 1-min FS computation inside run_backtest for 28-Aug.

Uses the same code path as the API.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Patch simulate_day to intercept the 1-min FS computation
import src.intraday as intraday

_patched = False
_patch_result = {}

_orig_simulate_day = intraday.simulate_day

def patched_simulate_day(candles, bias, day_date, day_df, m1_day, m5_day, cfg):
    """Wrapper that captures the 1-min FS state after computation."""
    # Let the original run, but we'll monkey-patch the _classify_first_swing_v2 result
    return _orig_simulate_day(candles, bias, day_date, day_df, m1_day, m5_day, cfg)

# Monkey-patch: intercept the _classify_first_swing_v2 call inside simulate_day
_original_classify = intraday._classify_first_swing_v2

_captured = {}

def patched_classify(candles, day_date):
    result = _original_classify(candles, day_date)
    direction, seed, events, confirmed_idx, end_idx, end_px, end_time = result
    _captured[day_date] = {
        "direction": direction,
        "seed": seed,
        "confirmed_idx": confirmed_idx,
        "end_idx": end_idx,
        "end_px": end_px,
        "end_time": end_time,
        "num_candles": len(candles),
        "first_candle": candles[0] if candles else None,
        "last_candle": candles[-1] if candles else None,
    }
    print(f"\n  [_classify_first_swing_v2] day={day_date} confirmed_idx={confirmed_idx} end_idx={end_idx} end_time={end_time}")
    return result

intraday._classify_first_swing_v2 = patched_classify

# Now run the backtest via the server's helper (same path as API)
from server import _intraday_backtest, _bias_labels_cached
from src.intraday import resolve_cfg

cfg = resolve_cfg({
    "swing_mode": "opposite_swing_needed",
    "entry_method": "pivot_break",
    "execution": "1min",
})

print("=== Config ===")
for k, v in cfg.items():
    print(f"  {k}: {v}")

print("\n=== Running backtest ===")
result = _intraday_backtest(cfg)

days = result.get("days_summary", [])
print(f"\nDays in summary: {len(days)}")

# Find 28-Aug
for day in days:
    if day.get("date") == "2026-08-28":
        print("\n=== 28-Aug day result ===")
        for k, v in day.items():
            if k in ("trades", "candles", "events"):
                continue
            print(f"  {k}: {v}")
        print(f"  trades: {len(day.get('trades', []))}")
        for t in day.get("trades", []):
            print(f"    -> {t.get('entry_time', '?')} | dir={t.get('dir', '?')} | {t.get('pnl_r', 0):.2f}R")

print("\n=== _captured for 28-Aug ===")
if "2026-08-28" in _captured:
    for k, v in _captured["2026-08-28"].items():
        print(f"  {k}: {v}")
else:
    print("  NOT CAPTURED!")
    print(f"  Available dates: {list(_captured.keys())}")
