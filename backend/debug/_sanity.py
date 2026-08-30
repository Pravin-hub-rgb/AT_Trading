"""Sanity check after gate removal."""
import sys
sys.path.insert(0, '.')
import pandas as pd
from src.intraday import run_backtest, DEFAULT_CFG
from src.bias import compute_bias
from src.config import DATA_DIR
df = pd.read_csv(DATA_DIR / 'nifty_5min.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
daily_df = pd.read_csv(DATA_DIR / 'nifty_daily.csv') if (DATA_DIR / 'nifty_daily.csv').exists() else None
bl = [lb for lb in compute_bias(df, daily_df) if lb['date'] in set(df['timestamp'].astype(str).str[:10])]
res = run_backtest(df, bl, cfg=dict(DEFAULT_CFG))
total_r = sum(t['r_multiple'] for d in res['days'] for t in d['trades'])
total = sum(len(d['trades']) for d in res['days'])
print(f"Total trades: {total}, Total R: {total_r:.2f}")
print("require_fs_confirmation present in cfg?", 'require_fs_confirmation' in DEFAULT_CFG)
