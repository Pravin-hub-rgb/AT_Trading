"""Check 5-min bars 5-10 and what's happening with pending_direct."""
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

print("=== 5-min bars 5-12 ===")
for i, row in day_5m.iterrows():
    if 5 <= i <= 12:
        bar_time = str(row["timestamp"])[11:16]
        print(f"Bar {i} ({bar_time}): O={row['open']:.2f} H={row['high']:.2f} L={row['low']:.2f} C={row['close']:.2f}")
        # Show 1-min bars in this 5-min window
        ts_start = row["timestamp"].value // 10**9
        end_ts = (row["timestamp"] + pd.Timedelta(minutes=5)).value // 10**9
        m1_in_window = day_1m[(day_1m["timestamp"] >= row["timestamp"]) & (day_1m["timestamp"] < row["timestamp"] + pd.Timedelta(minutes=5))]
        print(f"  1-min bars in window:")
        for _, m1row in m1_in_window.iterrows():
            print(f"    {str(m1row['timestamp'])[11:16]}: L={m1row['low']:.2f} H={m1row['high']:.2f}")