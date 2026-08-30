"""Test if the server gives the same result as direct call."""
import sys
sys.path.insert(0, "backend")
import requests
import pandas as pd
from src.intraday import run_backtest, DEFAULT_CFG
from src.bias import compute_bias
from src.config import DATA_DIR

# Direct call
df = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])
bl = compute_bias(df)
print(f"Direct: bl count = {len(bl)}")

cfg = dict(DEFAULT_CFG)
cfg["sl_mode"] = "avg"
r = run_backtest(df, bl, cfg)
s = r["stats"]
print(f"DIRECT  avg: trades={s['trades']} wins={s['wins']} wr={s['win_rate']}% total_r={s['total_r']}")

# Server call (mimics what server does)
df5 = pd.read_csv(DATA_DIR / "nifty_5min.csv")
labels = [lb for lb in bl if lb["date"] in set(df5["timestamp"].astype(str).str[:10])]
print(f"Server filter: labels count = {len(labels)} (after date filter)")

daily_df = pd.read_csv(DATA_DIR / "nifty_daily.csv")
# server's compute_bias call:
# labels = bias_svc.compute_bias(df5, daily_df) - both with and without daily
# but bl is from compute_bias(df) - no daily_df

# Call server's bias function exactly
from src.bias import compute_bias as cb
labels2 = cb(df5, daily_df)
print(f"compute_bias with daily: count = {len(labels2)}")
labels3 = [lb for lb in labels2 if lb["date"] in set(df5["timestamp"].astype(str).str[:10])]
print(f"After date filter: count = {len(labels3)}")
r2 = run_backtest(df5, labels3, cfg=cfg, df_1min=None)
s2 = r2["stats"]
print(f"SERVER-SIM  avg: trades={s2['trades']} wins={s2['wins']} wr={s2['win_rate']}% total_r={s2['total_r']}")
