"""Trace the simulate_day entry loop for 28-Aug to find why bar 4 doesn't enter."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime, timezone, timedelta
from src.config import DATA_DIR
from src.intraday import simulate_day

IST = timezone(timedelta(hours=5, minutes=30))

def load_5min_candles():
    df = pd.read_csv(DATA_DIR / "nifty_5min.csv")
    df["ts_str"] = df["timestamp"].astype(str).str[:10]
    df = df[df["ts_str"] == "2026-08-28"].copy().reset_index(drop=True)
    candles = []
    for i, row in df.iterrows():
        ts_str = str(row["timestamp"])
        if " " in ts_str:
            dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            ts = int(dt.timestamp())
            time_str = dt.strftime("%H:%M")
        else:
            ts = int(row.get("ts", 0))
            time_str = ts_str[11:16] if len(ts_str) > 16 else ts_str
        candles.append({
            "index": i,
            "time": time_str,
            "ts": ts,
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
        })
    return candles

def load_1min_candles():
    df = pd.read_csv(DATA_DIR / "nifty_1min.csv")
    df["ts_str"] = df["timestamp"].astype(str).str[:10]
    df = df[df["ts_str"] == "2026-08-28"].copy().reset_index(drop=True)
    candles = []
    for i, row in df.iterrows():
        ts_str = str(row["timestamp"])
        if " " in ts_str:
            dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            ts = int(dt.timestamp())
            time_str = dt.strftime("%H:%M")
        else:
            ts = int(row.get("ts", 0))
            time_str = ts_str[11:16] if len(ts_str) > 16 else ts_str
        candles.append({
            "index": i,
            "time": time_str,
            "ts": ts,
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
        })
    return candles

def load_daily():
    df = pd.read_csv(DATA_DIR / "nifty_daily.csv")
    df["ts_str"] = df["timestamp"].astype(str).str[:10]
    df = df[df["ts_str"] == "2026-08-28"].copy().reset_index(drop=True)
    if len(df) == 0:
        return None
    row = df.iloc[0]
    ts_str = str(row["timestamp"])
    dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
    return {
        "date": "2026-08-28",
        "open": float(row["open"]),
        "high": float(row["high"]),
        "low": float(row["low"]),
        "close": float(row["close"]),
        "prev_close": float(row.get("prev_close", 24100.0)),
        "ts": int(dt.timestamp()),
    }

candles5 = load_5min_candles()
m1_candles = load_1min_candles()
daily = load_daily()

print(f"5-min candles: {len(candles5)}")
print(f"1-min candles: {len(m1_candles)}")
print(f"Daily: {daily}")
print()

# Config matching what the UI sends
cfg = {
    "sl_mode": "avg",
    "execution": "1min",
    "trailing": "off",
    "trail_distance_r": 1.0,
    "gap_pct": 0.0027,
    "sl_pivot_buffer": 1.0,
    "ft_fail_enabled": True,
    "entry_method": "pivot_break",
    "swing_mode": "opposite_swing_needed",
}

print(f"Config: entry_method={cfg['entry_method']}, execution={cfg['execution']}, swing_mode={cfg['swing_mode']}")
print()

# Run simulate_day with correct signature
result = simulate_day(candles5, daily["raw_bias"], cfg, m1_day=m1_candles, ctx={"gap": "flat", "extreme": None})

# Print events for bars 0-15
print("\n=== KEY EVENTS ===")
for ev in result.get("events", []):
    t = ev.get("type", "")
    bar = ev.get("bar", -1)
    time = ev.get("time", "")
    if t in ("pace_break", "trade_opened", "first_swing_confirmed", "first_swing_sustained", "swing_declared", "fs_gate_opened", "entry_gate", "swing_voided", "setup_armed", "setup_disarmed"):
        print(f"  [{bar}] {time} | {t} | {ev}")

print("\n=== TRADES ===")
for t in result.get("trades", []):
    print(f"  {t.get('entry_time', 'N/A')} | {t.get('dir')} | outcome={t.get('outcome')} | entry_bar={t.get('entry_bar')}")

print(f"\nFirst swing confirmed idx: {result.get('first_swing_confirmed_idx')}")
print(f"First swing end time: {result.get('first_swing_end_time')}")
print(f"1-min FS gate: {result.get('fs1_1min_confirmed_idx_5min')}")
print(f"Case: {result.get('case')}")
print(f"Effective bias: {result.get('effective_bias')}")
print(f"Swing direction: {result.get('swing_direction')}")
