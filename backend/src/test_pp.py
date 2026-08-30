"""Test prev_pivot SL mode vs avg mode. Run: python -m src.test_pp from backend/ dir."""
import pandas as pd
import json
from .intraday import simulate_day, run_backtest, DEFAULT_CFG
from .bias import compute_bias
from .config import DATA_DIR

print("loading data", flush=True)
df = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])
dates = df["timestamp"].dt.strftime("%Y-%m-%d").unique()
print(f"Loaded {len(df)} rows across {len(dates)} dates", flush=True)

bias_labels = compute_bias(df)
print(f"Bias labels: {len(bias_labels)}", flush=True)

print("\n=== AVG MODE ===", flush=True)
r_avg = run_backtest(df, bias_labels, cfg={"sl_mode": "avg"})
print(json.dumps(r_avg["stats"], indent=2), flush=True)

print("\n=== PREV_PIVOT MODE (buffer=1.0) ===", flush=True)
r_pp = run_backtest(df, bias_labels, cfg={"sl_mode": "prev_pivot", "sl_pivot_buffer": 1.0})
print(json.dumps(r_pp["stats"], indent=2), flush=True)

for dy in r_pp["days"]:
    for t in dy["trades"]:
        if t.get("pivot_ref"):
            print("\n=== Sample prev_pivot trade ===", flush=True)
            print(json.dumps(t, indent=2, default=str), flush=True)
            print("\nDONE", flush=True)
            exit(0)
print("\nNo pivot_ref trade found (may need longer history)", flush=True)
print("DONE", flush=True)
