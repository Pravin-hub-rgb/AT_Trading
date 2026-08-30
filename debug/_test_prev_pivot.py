"""Quick test for prev_pivot SL mode vs avg mode."""
import sys
sys.path.insert(0, "src")
from intraday import simulate_day, run_backtest, DEFAULT_CFG
from bias import compute_bias
from config import DATA_DIR
import pandas as pd
import json

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

# Sample trade
for dy in r_pp["days"]:
    for t in dy["trades"]:
        if t.get("pivot_ref"):
            print("\n=== Sample prev_pivot trade ===", flush=True)
            print(json.dumps(t, indent=2, default=str), flush=True)
            break
    else:
        continue
    break
else:
    # Show any trade
    for dy in r_pp["days"]:
        for t in dy["trades"]:
            print("\n=== Sample trade (any) ===", flush=True)
            print(json.dumps(t, indent=2, default=str), flush=True)
            break
        else:
            continue
        break
