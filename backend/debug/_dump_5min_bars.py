"""Dump 5-min bars to verify timestamps and OHLC."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import datetime
from src.config import DATA_DIR

df = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["ts"] = df["ts"].astype("int64")
df = df[df["timestamp"].dt.strftime("%Y-%m-%d") == "2026-08-28"].copy().reset_index(drop=True)
print(f"5-min bars: {len(df)}")
for i, row in df.iterrows():
    if i >= 0 and i <= 15:
        ts = int(row["ts"])
        # Convert ts to IST
        ist_dt = datetime.datetime.utcfromtimestamp(ts) + datetime.timedelta(hours=5, minutes=30)
        print(f"  [{i}] ts={ts} IST={ist_dt.strftime('%H:%M')} | O={row['open']:.2f} H={row['high']:.2f} L={row['low']:.2f} C={row['close']:.2f}")