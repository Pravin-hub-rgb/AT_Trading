"""Step-by-step walkthrough of the 10:55 1-min precision entry on 2026-08-28.

User's settings:
  - sl_mode = avg (sl = avg x 1)
  - execution = precise_1min (1-min precision entry hunt)
  - entry_method = pace_break
  - swing_mode = opposite_swing_needed
"""
from __future__ import annotations
import sys
sys.path.insert(0, '.')

import pandas as pd
from src.config import DATA_DIR
from src.intraday import run_backtest, DEFAULT_CFG
from src.bias import compute_bias

# ── 1) Load data ──────────────────────────────────────────────────────────
df5 = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df5["timestamp"] = pd.to_datetime(df5["timestamp"])
df1_path = DATA_DIR / "nifty_1min.csv"
df1 = pd.read_csv(df1_path) if df1_path.exists() else None
if df1 is not None:
    df1["timestamp"] = pd.to_datetime(df1["timestamp"])

daily_df = pd.read_csv(DATA_DIR / "nifty_daily.csv") if (DATA_DIR / "nifty_daily.csv").exists() else None
labels = compute_bias(df5, daily_df)
labels = [lb for lb in labels if lb["date"] in set(df5["timestamp"].astype(str).str[:10])]

DATE = "2026-08-28"

# ── 2) Run user's exact config ────────────────────────────────────────────
cfg = dict(DEFAULT_CFG)
cfg["execution"] = "1min"
cfg["swing_mode"] = "opposite_swing_needed"
cfg["entry_method"] = "pace_break"
cfg["sl_mode"] = "avg"
cfg["sl_mult"] = 1.0

print("=" * 78)
print("USER SETTINGS: 1min + pace_break + opposite_swing_needed + sl=avg x 1")
print("=" * 78)

r = run_backtest(df5, labels, cfg, df_1min=df1)

# ── 3) Filter to 28 Aug ───────────────────────────────────────────────────
day = next((d for d in r["days"] if d.get("date") == DATE), None)
if day is None:
    print(f"[!] {DATE} not found")
    for d in r["days"][-5:]:
        print(f"    {d.get('date')}: trades={len(d.get('trades', []))}, "
              f"fs1={d.get('first_swing_confirmed_idx')}")
    sys.exit(1)

# Build the day's 5-min + 1-min candles for context
day5 = df5[df5["timestamp"].dt.strftime("%Y-%m-%d") == DATE].reset_index(drop=True)
if df1 is not None:
    day1 = df1[df1["timestamp"].dt.strftime("%Y-%m-%d") == DATE].reset_index(drop=True)
else:
    day1 = None

print(f"\nDATE: {DATE}")
print(f"Bias: {day.get('bias')}, swing_direction: {day.get('swing_direction')}, "
      f"swing2_direction: {day.get('swing2_direction')}")
print(f"5-min bars for the day: {len(day5)}, 1-min bars: {len(day1) if day1 is not None else 0}")

# ── [1] First swing (cyan line — entry gate) ──────────────────────────────
print("\n" + "=" * 78)
print("[1] FIRST SWING (cyan line — ENTRY GATE)")
print("=" * 78)
fs1_idx = day.get("first_swing_confirmed_idx", -1)
fs1_time = day.get("first_swing_end_time")
print(f"  first_swing_confirmed_idx = {fs1_idx}")
print(f"  first_swing_end_time      = {fs1_time}")
print(f"  swing_direction           = {day.get('swing_direction')}")
if fs1_idx is not None and fs1_idx >= 0 and fs1_idx < len(day5):
    bar = day5.iloc[fs1_idx]
    print(f"  Day 5-min bar #{fs1_idx} = {bar['timestamp']}  "
          f"O={bar['open']:.2f} H={bar['high']:.2f} L={bar['low']:.2f} C={bar['close']:.2f}")
    print(f"  >> This is when the cyan line locks its FS direction 'buying' (UP)")

# ── [2] Second swing (yellow line — direction filter only) ────────────────
print("\n" + "=" * 78)
print("[2] SECOND SWING (yellow line — DIRECTION FILTER only)")
print("=" * 78)
fs2_idx = day.get("swing2_confirmed_idx", -1)
fs2_dir = day.get("swing2_direction")
print(f"  swing2_direction     = {fs2_dir}")
print(f"  swing2_confirmed_idx = {fs2_idx}")
if fs2_idx is not None and fs2_idx >= 0 and fs2_idx < len(day5):
    bar = day5.iloc[fs2_idx]
    print(f"  Day 5-min bar #{fs2_idx} = {bar['timestamp']}  "
          f"O={bar['open']:.2f} H={bar['high']:.2f} L={bar['low']:.2f} C={bar['close']:.2f}")
    if fs2_dir != day.get("swing_direction"):
        print(f"  >> Yellow line is OPPOSITE direction to cyan line")
        print(f"  >> So entry GATE = bar {fs1_idx} (FS1, cyan), and trade direction = buying")
    else:
        print(f"  >> Yellow line matches cyan line direction — entry DISABLED for the day")

for ev in day.get("events", []):
    if ev.get("type") in ("second_swing_armed", "skipped_same_direction_swing2"):
        print(f"  event: {ev}")

# ── [3] TRADES ────────────────────────────────────────────────────────────
print("\n" + "=" * 78)
print("[3] TRADES")
print("=" * 78)
trades = day.get("trades", [])
if not trades:
    print("  (no trades)")
for i, t in enumerate(trades):
    b = t.get("bar_idx")
    b_str = f"{b:>3}" if b is not None else "  ?"
    et = t.get("entry_time", t.get("time"))
    et_str = str(et) if et is not None else "?"
    px = t.get("entry_price", 0)
    px_str = f"{px:>7.2f}" if px is not None else "    ?  "
    direction = t.get("dir", "?")
    ttype = t.get("type", "?")
    sl = t.get("sl", 0)
    sl_str = f"{sl:.2f}" if sl is not None else "?"
    print(f"  [{i}] bar={b_str}  time={et_str}  dir={direction:>5}  px={px_str}  type={ttype:<8}  sl={sl_str}")
    if b == 19:
        print(f"      >> THIS is the 10:55 entry. bar 19 > gate bar {fs1_idx} -> gate is OPEN")

# ── [4] Entry-related events on 5-min bars 14..22 ─────────────────────────
print("\n" + "=" * 78)
print("[4] ALL ENTRY EVENTS, DAY-BARS 14..22 (the run-up to 10:55)")
print("=" * 78)
events = day.get("events", [])
for ev in events:
    b = ev.get("bar", ev.get("bar_idx"))
    if isinstance(b, int) and 14 <= b <= 22:
        bar_t = day5.iloc[b]["timestamp"] if b < len(day5) else "?"
        print(f"  bar={b:>3} @ {bar_t}  {ev}")

# Also any 1-min events that mention 10:5x
for ev in events:
    t = ev.get("type", "")
    if t in ("pending_direct_1m", "setup_disarmed_pre_gate"):
        ev_time = ev.get("time", "")
        if ev_time and ("10:5" in str(ev_time) or "11:0" in str(ev_time)):
            print(f"  {ev}")

# ── [5] 1-minute candles 10:30..11:00 ─────────────────────────────────────
print("\n" + "=" * 78)
print("[5] 1-MIN CANDLES 10:30..11:00 — what the precision hunt saw")
print("=" * 78)
if day1 is not None and len(day1) > 0:
    sub = day1[(day1["timestamp"] >= f"{DATE} 10:30") & (day1["timestamp"] <= f"{DATE} 11:00")]
    if len(sub) == 0:
        print("  (no 1-min data in window)")
    else:
        for _, row in sub.iterrows():
            ts = row["timestamp"]
            o, h, l, c = row["open"], row["high"], row["low"], row["close"]
            print(f"  {ts}  O={o:>7.2f}  H={h:>7.2f}  L={l:>7.2f}  C={c:>7.2f}")
else:
    print("  (no 1-min data file found)")

# ── [6] All pending_direct + disarm events ────────────────────────────────
print("\n" + "=" * 78)
print("[6] ALL PENDING_DIRECT / SETUP_DISARMED EVENTS")
print("=" * 78)
for ev in events:
    t = ev.get("type", "")
    if t in ("pending_direct_1m", "setup_disarmed_pre_gate", "second_swing_armed"):
        print(f"  {ev}")

# ── [7] Gate check ────────────────────────────────────────────────────────
print("\n" + "=" * 78)
print("[7] GATE CHECK")
print("=" * 78)
for t in trades:
    b = t.get("bar_idx", 0)
    if b is None:
        # try to recover from time
        et = t.get("entry_time", t.get("time"))
        print(f"  Entry at {et} (bar_idx not stored) — gate bar = {fs1_idx}, day bar lookup skipped")
    else:
        status = "PASS" if b > fs1_idx else "FAIL"
        print(f"  Entry bar {b} > gate bar {fs1_idx}?  ->  {status}")
