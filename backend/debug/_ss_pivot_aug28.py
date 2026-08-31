"""Check why pivot_break didn't fire a trade on 2026-08-28.

User says: for selling, it enters on pivot low break.

Settings:
  - entry_method = pivot_break
  - swing_mode = opposite_swing_needed
  - execution = 1min
  - sl = avg x 1

This script:
  1. Runs backtest with pivot_break
  2. Filters to 28 Aug
  3. Prints all pivot_break events (attempts)
  4. Prints gate state and why each attempt was rejected (if any)
  5. Prints final trade result
"""
from __future__ import annotations
import sys
sys.path.insert(0, '.')

import pandas as pd
from src.config import DATA_DIR
from src.intraday import run_backtest, DEFAULT_CFG
from src.bias import compute_bias

df5 = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df5["timestamp"] = pd.to_datetime(df5["timestamp"])
df1 = pd.read_csv(DATA_DIR / "nifty_1min.csv") if (DATA_DIR / "nifty_1min.csv").exists() else None
if df1 is not None:
    df1["timestamp"] = pd.to_datetime(df1["timestamp"])

daily_df = pd.read_csv(DATA_DIR / "nifty_daily.csv") if (DATA_DIR / "nifty_daily.csv").exists() else None
labels = compute_bias(df5, daily_df)
labels = [lb for lb in labels if lb["date"] in set(df5["timestamp"].astype(str).str[:10])]

DATE = "2026-08-28"

cfg = dict(DEFAULT_CFG)
cfg["execution"] = "1min"
cfg["swing_mode"] = "opposite_swing_needed"
cfg["entry_method"] = "pivot_break"   # <-- changed
cfg["sl_mode"] = "avg"
cfg["sl_mult"] = 1.0

print("=" * 78)
print("USER SETTINGS: 1min + pivot_break + opposite_swing_needed + sl=avg x 1")
print("=" * 78)

r = run_backtest(df5, labels, cfg, df_1min=df1)
day = next((d for d in r["days"] if d.get("date") == DATE), None)
if day is None:
    print(f"[!] {DATE} not found")
    for d in r["days"][-5:]:
        print(f"    {d.get('date')}: trades={len(d.get('trades', []))}")
    sys.exit(1)

# Day 5-min + 1-min
day5 = df5[df5["timestamp"].dt.strftime("%Y-%m-%d") == DATE].reset_index(drop=True)

print(f"\nDATE: {DATE}")
print(f"Bias: {day.get('bias')}")
print(f"swing_direction: {day.get('swing_direction')}")
print(f"swing2_direction: {day.get('swing2_direction')}")
print(f"first_swing_confirmed_idx: {day.get('first_swing_confirmed_idx')}")
print(f"swing2_confirmed_idx: {day.get('swing2_confirmed_idx')}")
print(f"\nTrades: {len(day.get('trades', []))}")
for t in day.get("trades", []):
    print(f"  {t}")

# ── All pivot_break events ────────────────────────────────────────────────
print("\n" + "=" * 78)
print("ALL PIVOT_BREAK EVENTS")
print("=" * 78)
pivot_events = [e for e in day.get("events", []) if "pivot" in e.get("type", "").lower()]
if not pivot_events:
    print("  (no pivot_break events at all)")
for e in pivot_events:
    b = e.get("bar", e.get("bar_idx"))
    bar_t = day5.iloc[b]["timestamp"] if isinstance(b, int) and b < len(day5) else "?"
    print(f"  bar={b} @ {bar_t}  {e}")

# ── All entry-related events ─────────────────────────────────────────────
print("\n" + "=" * 78)
print("ALL ENTRY-RELATED EVENTS")
print("=" * 78)
for e in day.get("events", []):
    t = e.get("type", "")
    if any(k in t for k in ("entry", "pivot", "pending", "disarm", "armed", "gate")):
        b = e.get("bar", e.get("bar_idx"))
        bar_t = day5.iloc[b]["timestamp"] if isinstance(b, int) and b < len(day5) else "?"
        print(f"  bar={b} @ {bar_t}  {e}")

# ── First swing events ───────────────────────────────────────────────────
print("\n" + "=" * 78)
print("FIRST SWING EVENTS")
print("=" * 78)
for e in day.get("events", []):
    t = e.get("type", "")
    if "fsv2" in t or "first_swing" in t:
        b = e.get("bar", e.get("bar_idx"))
        print(f"  bar={b}  {e}")

# ── Second swing events ──────────────────────────────────────────────────
print("\n" + "=" * 78)
print("SECOND SWING EVENTS")
print("=" * 78)
for e in day.get("events", []):
    t = e.get("type", "")
    if "second" in t or "fs2" in t or "swing2" in t:
        b = e.get("bar", e.get("bar_idx"))
        bar_t = day5.iloc[b]["timestamp"] if isinstance(b, int) and b < len(day5) else "?"
        print(f"  bar={b} @ {bar_t}  {e}")

# ── Looking for the L-pivot break that should have fired (selling) ───────
print("\n" + "=" * 78)
print("CHECKING: For selling, did price break below an L-pivot after gate open?")
print("=" * 78)
fs1_idx = day.get("first_swing_confirmed_idx", -1)
print(f"  Gate opened at bar {fs1_idx} ({day5.iloc[fs1_idx]['timestamp']} if valid)")

# Find micro-pivot break attempts
pivot_low_break_attempts = []
for e in day.get("events", []):
    t = e.get("type", "")
    if "pivot_low" in t or "pivot" in t.lower():
        b = e.get("bar", e.get("bar_idx"))
        if isinstance(b, int) and b > fs1_idx:
            bar_t = day5.iloc[b]["timestamp"] if b < len(day5) else "?"
            pivot_low_break_attempts.append((b, bar_t, e))

if pivot_low_break_attempts:
    for b, bt, e in pivot_low_break_attempts:
        print(f"  bar={b} @ {bt}  {e}")
else:
    print("  (no pivot_low break attempts after gate open)")
    print()
    # Check if there were any break attempts at all after gate
    print("  Checking raw break events after gate...")
    for e in day.get("events", []):
        b = e.get("bar", e.get("bar_idx"))
        t = e.get("type", "")
        if isinstance(b, int) and b > fs1_idx and any(k in t for k in ("break", "domination", "candle")):
            bar_t = day5.iloc[b]["timestamp"] if b < len(day5) else "?"
            print(f"    bar={b} @ {bar_t}  {e}")
