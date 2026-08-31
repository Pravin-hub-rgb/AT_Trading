"""Debug: trace pending_direct creation at bars 6-14."""
import sys
sys.path.insert(0, ".")
from src.intraday import simulate_day, resolve_cfg
from src.config import DATA_DIR
import pandas as pd

# Load data
df5 = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df5["ts_str"] = df5["timestamp"].astype(str).str[:10]
day_5m = df5[df5["ts_str"] == "2026-08-28"].reset_index(drop=True)
day_5m["timestamp"] = pd.to_datetime(day_5m["timestamp"])

df1 = pd.read_csv(DATA_DIR / "nifty_1min.csv")
df1["ts_str"] = df1["timestamp"].astype(str).str[:10]
day_1m = df1[df1["ts_str"] == "2026-08-28"].reset_index(drop=True)
day_1m["timestamp"] = pd.to_datetime(day_1m["timestamp"])

cfg = resolve_cfg({
    "swing_mode": "opposite_swing_needed",
    "entry_method": "pivot_break",
    "execution": "1min",
    "sl_mode": "prev_pivot",
    "sl_pivot_buffer": 1.0,
})

# Monkey-patch the pending_direct creation to add debug
original_code = """
        # Check if this is a direct break (domination, candle-size, or 1min pivot_break)
        if brk["type"] in ("domination", "candle-size", "pivot_break"):
            # Direct flow-favor entry ON the aggressive break candle
            brk_q = (
                (cur["close"] - cur["low"]) / cur["range"]
                if trade_dir == 1
                else (cur["high"] - cur["close"]) / cur["range"]
            ) if cur["range"] > 0 else 0.0
            if use_1m:
                pending_direct = {
                    "bar_idx": i,
                    "trade_dir": trade_dir,
                    "level": brk["level"],
                    "break_type": brk["type"],
                    "armed_ts": armed_ts,
                }
                result["events"].append({
                    "type": "pending_direct_1m",
                    "bar": i, "time": cur["time"],
                    "ts": int(cur["ts"]),
                    "level": round(brk["level"], 2),
                    "break_type": brk["type"],
                })
                entered = False
            else:
                entered = brk_q >= DOM_CLOSE_Q and _open_trade(
                    i, trade_dir, brk["level"], cur, brk["type"]
                )
            if not entered:
                armed = {
                    "level": brk["level"],
                    "trade_dir": trade_dir,
                    "break_type": brk["type"],
                    "armed_at": i,
                    "age": 0,
                }
"""

result = simulate_day(
    day_5m, "bearish", cfg, m1_day=day_1m, ctx={"gap": "flat", "extreme": None}
)

# Manually trace bars 6-14
print("=== 5-min bars 6-14 pivot_break analysis ===")
for i, row in day_5m.iterrows():
    if 6 <= i <= 14:
        bar_time = str(row["timestamp"])[11:16]
        print(f"Bar {i} ({bar_time}): O={row['open']:.2f} H={row['high']:.2f} L={row['low']:.2f} C={row['close']:.2f}")
        
        # Check for breaks using 5-min data (simplified)
        prev_row = day_5m.iloc[i-1] if i > 0 else None
        if prev_row is not None:
            prev_low = prev_row["low"]
            prev_high = prev_row["high"]
            cur_low = row["low"]
            cur_high = row["high"]
            cur_close = row["close"]
            
            # Short break: close < prev_low
            if cur_close < prev_low:
                print(f"  SHORT break: close {cur_close:.2f} < prev_low {prev_low:.2f}")
            # Long break: close > prev_high
            if cur_close > prev_high:
                print(f"  LONG break: close {cur_close:.2f} > prev_high {prev_high:.2f}")

print("\n=== All events between bars 6-14 ===")
for ev in result.get("events", []):
    bar = ev.get("bar", -1)
    if 6 <= bar <= 14 or (ev.get("type") in ["entry", "exit"] and bar <= 20):
        print(f"  [{ev.get('type')}] bar={bar} time={ev.get('time')} level={ev.get('level')} aligned={ev.get('aligned_with_bias') if 'bias' in str(ev) else '?'}")