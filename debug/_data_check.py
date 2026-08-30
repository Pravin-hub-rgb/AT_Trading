"""Check data range and full backtest trade count for prev_pivot mode."""
import sys
sys.path.insert(0, "backend")
import pandas as pd
import collections
from src.config import DATA_DIR
from src.intraday import simulate_day, _prep_day, _classify_first_swing_v2, DEFAULT_CFG, FALLBACK_AVG_RANGE, MIN_CANDLES

df = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["date"] = df["timestamp"].dt.date

print("Date range:", df["date"].min(), "to", df["date"].max())
print("Total rows:", len(df))
print("Unique dates:", df["date"].nunique())

dates = sorted(df["date"].unique())

cfg = dict(DEFAULT_CFG)
cfg["sl_mode"] = "prev_pivot"
cfg["sl_pivot_buffer"] = 1.0

print("\n--- prev_pivot, buffer=1.0 (last 15 days) ---")
for d in dates[-15:]:
    sub = df[df["date"] == d]
    if len(sub) < MIN_CANDLES:
        continue
    total = 0
    for bias in ("bullish", "bearish"):
        r = simulate_day(sub, bias=bias, cfg=cfg, ctx={"gap": "flat", "extreme": None, "avg_range": FALLBACK_AVG_RANGE})
        total += len(r["trades"])
    print(f"  {d}: {total} trades")

# Compare with avg mode
print("\n--- avg mode (last 15 days) ---")
cfg2 = dict(DEFAULT_CFG)
cfg2["sl_mode"] = "avg"
for d in dates[-15:]:
    sub = df[df["date"] == d]
    if len(sub) < MIN_CANDLES:
        continue
    total = 0
    for bias in ("bullish", "bearish"):
        r = simulate_day(sub, bias=bias, cfg=cfg2, ctx={"gap": "flat", "extreme": None, "avg_range": FALLBACK_AVG_RANGE})
        total += len(r["trades"])
    print(f"  {d}: {total} trades")
