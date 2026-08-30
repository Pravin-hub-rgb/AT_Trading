"""Compare bias labels between approaches."""
import sys
sys.path.insert(0, "backend")
import pandas as pd
from src.bias import compute_bias
from src.config import DATA_DIR

# Direct approach
df = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])
bl_direct = compute_bias(df)

# Server approach
df5 = pd.read_csv(DATA_DIR / "nifty_5min.csv")
daily_df = pd.read_csv(DATA_DIR / "nifty_daily.csv")
bl_server = compute_bias(df5, daily_df)
dates_in_5min = set(df5["timestamp"].astype(str).str[:10])
bl_server_filtered = [lb for lb in bl_server if lb["date"] in dates_in_5min]

# Compare
print(f"Direct bl count: {len(bl_direct)}")
print(f"Server bl count (raw): {len(bl_server)}")
print(f"Server bl count (filtered): {len(bl_server_filtered)}")

# Find differences
direct_dates = {lb["date"]: lb for lb in bl_direct}
server_dates = {lb["date"]: lb for lb in bl_server_filtered}

all_dates = set(direct_dates.keys()) | set(server_dates.keys())
print(f"Total unique dates: {len(all_dates)}")

diff_dates = []
for d in sorted(all_dates):
    d1 = direct_dates.get(d)
    d2 = server_dates.get(d)
    if d1 is None:
        print(f"Only in server: {d}")
    elif d2 is None:
        print(f"Only in direct: {d}")
    elif d1["bias"] != d2["bias"] or d1.get("effective_bias") != d2.get("effective_bias"):
        diff_dates.append(d)
        print(f"DIFF: {d} direct={d1['bias']}/{d1.get('effective_bias')} server={d2['bias']}/{d2.get('effective_bias')}")

print(f"\nTotal differences: {len(diff_dates)}")
