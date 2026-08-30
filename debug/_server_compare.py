"""Compare server-style bias filtering vs direct."""
import sys
sys.path.insert(0, "backend")
import pandas as pd
from src.intraday import run_backtest, DEFAULT_CFG
from src.bias import compute_bias
from src.config import DATA_DIR

df = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])

# Server-style: compute bias then filter to dates in the 5min data
all_labels = compute_bias(df)
date_set = set(df["timestamp"].astype(str).str[:10])
labels = [lb for lb in all_labels if lb["date"] in date_set]
print(f"Server-style: {len(labels)} labels, dates in 5min data: {len(date_set)}")

cfg = dict(DEFAULT_CFG)
r = run_backtest(df, labels, cfg)
s = r["stats"]
n_traded = sum(1 for d in r["days"] if d.get("trades"))
print(f"avg mode (server-style filter): trades={s['trades']}  win_rate={s['win_rate']}%  total_r={s['total_r']}  longs={s.get('longs', 0)} shorts={s.get('shorts', 0)}")

# Also show direct (no filter)
labels2 = compute_bias(df)
r2 = run_backtest(df, labels2, cfg)
s2 = r2["stats"]
n_traded2 = sum(1 for d in r2["days"] if d.get("trades"))
print(f"avg mode (direct, no filter):   trades={s2['trades']}  win_rate={s2['win_rate']}%  total_r={s2['total_r']}  longs={s2.get('longs', 0)} shorts={s2.get('shorts', 0)}")
