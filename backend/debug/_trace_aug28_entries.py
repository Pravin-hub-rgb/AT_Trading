"""Trace each 5-min bar after gate to find which bar gets the pivot break entry."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime, timezone, timedelta
from src.config import DATA_DIR
from src.walker import WalkerEngine, FlowCandle

IST = timezone(timedelta(hours=5, minutes=30))

def load_1min_candles():
    """Load 1-min data and parse timestamps."""
    df = pd.read_csv(DATA_DIR / "nifty_1min.csv")
    df["ts_str"] = df["timestamp"].astype(str).str[:10]
    df = df[df["ts_str"] == "2026-08-28"].copy().reset_index(drop=True)
    candles = []
    for i, row in df.iterrows():
        ts_str = str(row["timestamp"])
        # Parse timestamp
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

def load_5min_candles():
    """Load 5-min data and parse timestamps."""
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

def detect_pivot_break_1m(candles_5m, i, trade_dir, normal_highs_1m, normal_lows_1m, m1_candles):
    """Detect pivot break using 1-min pivots."""
    cur_5_ts = candles_5m[i].get("ts", 0)
    m1_end_idx = -1
    for k in range(len(m1_candles) - 1, -1, -1):
        if m1_candles[k].get("ts", 0) <= cur_5_ts:
            m1_end_idx = k
            break
    if m1_end_idx < 0:
        return None
    if trade_dir == -1 and normal_lows_1m:  # short
        for piv in reversed(normal_lows_1m):
            if piv.idx <= m1_end_idx:
                if candles_5m[i]["low"] < piv.px:
                    return {"type": "pivot_break", "level": piv.px, "bar": i, "pivot_idx": piv.idx, "pivot_time": m1_candles[piv.idx]["time"]}
                break
    elif trade_dir == 1 and normal_highs_1m:  # long
        for piv in reversed(normal_highs_1m):
            if piv.idx <= m1_end_idx:
                if candles_5m[i]["high"] > piv.px:
                    return {"type": "pivot_break", "level": piv.px, "bar": i, "pivot_idx": piv.idx, "pivot_time": m1_candles[piv.idx]["time"]}
                break
    return None

m1_candles = load_1min_candles()
m5_candles = load_5min_candles()

print(f"5-min bars: {len(m5_candles)}")
print(f"1-min bars: {len(m1_candles)}")

# Gate: 1-min FS at 09:30 = 5-min bar 3
gate_bar = 3
print(f"\nGate opens at bar {gate_bar} (09:30)")

# Initialize 1-min Walker
walker_1m = WalkerEngine()
normal_highs_1m = []
normal_lows_1m = []
for idx, mc in enumerate(m1_candles):
    mc_dt = f"2026-08-28T{mc['time']}:00"
    fc = FlowCandle(date=mc_dt, open=mc["open"], high=mc["high"], low=mc["low"], close=mc["close"])
    new_p = walker_1m.process_bar(fc, idx)
    for p in new_p:
        if p.kind == "H":
            normal_highs_1m.append(p)
        else:
            normal_lows_1m.append(p)

print(f"\nTracing pivot_break entries from bar {gate_bar+1} onwards:")
print(f"Swing direction: buying (short trades)\n")

for i in range(gate_bar + 1, min(gate_bar + 12, len(m5_candles))):
    c = m5_candles[i]
    t = c["time"]
    trade_dir = -1  # short
    
    brk_1m = detect_pivot_break_1m(m5_candles, i, trade_dir, normal_highs_1m, normal_lows_1m, m1_candles)
    
    if brk_1m:
        print(f"[{i}] {t}: LOW={c['low']:.2f}")
        print(f"     *** PIVOT BREAK at {t} ***")
        print(f"     1m pivot: idx={brk_1m['pivot_idx']} time={brk_1m['pivot_time']} level={brk_1m['level']}")
        print(f"     -> Should trigger entry at {t}")
    else:
        print(f"[{i}] {t}: LOW={c['low']:.2f} — no pivot break")
