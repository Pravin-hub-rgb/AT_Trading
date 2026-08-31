"""Check ts alignment between 5-min and 1-min bars."""
import sys
sys.path.insert(0, ".")
from src.config import DATA_DIR
import pandas as pd

df5 = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df5["ts_str"] = df5["timestamp"].astype(str).str[:10]
day_5m = df5[df5["ts_str"] == "2026-08-28"].reset_index(drop=True)
day_5m["timestamp"] = pd.to_datetime(day_5m["timestamp"])
day_5m["ts"] = day_5m["timestamp"].astype("int64") // 10**9

df1 = pd.read_csv(DATA_DIR / "nifty_1min.csv")
df1["ts_str"] = df1["timestamp"].astype(str).str[:10]
day_1m = df1[df1["ts_str"] == "2026-08-28"].reset_index(drop=True)
day_1m["timestamp"] = pd.to_datetime(day_1m["timestamp"])
day_1m["ts"] = day_1m["timestamp"].astype("int64") // 10**9

print("=== 5-min bars ===")
for i, row in day_5m.iterrows():
    if i <= 8:
        print(f"Bar {i}: timestamp={row['timestamp']} ts={row['ts']}")

print("\n=== 1-min bars 09:30-10:00 ===")
for i, row in day_1m.iterrows():
    bar_time = str(row["timestamp"])[11:16]
    if "09:30" <= bar_time <= "10:00":
        print(f"  {bar_time}: timestamp={row['timestamp']} ts={row['ts']}")