"""Compare backtest with FsV2 gate ON vs OFF."""
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

# With the new FsV2 gate (require_fs_confirmation=True)
res = run_backtest(df, bl, cfg=dict(DEFAULT_CFG))
total_r = sum(t['r_multiple'] for d in res['days'] for t in d['trades'])
total_trades = sum(len(d['trades']) for d in res['days'])
winners = sum(1 for d in res['days'] for t in d['trades'] if t['r_multiple'] > 0)
print(f"With FsV2 gate ON (require_fs_confirmation=True):")
print(f"  Total trades: {total_trades}")
print(f"  Win rate: {winners}/{total_trades} = {winners/total_trades*100:.1f}%")
print(f"  Total R: {total_r:.2f}")

# Without FsV2 gate (old behavior)
old_cfg = dict(DEFAULT_CFG)
old_cfg['require_fs_confirmation'] = False
res2 = run_backtest(df, bl, cfg=old_cfg)
total_r2 = sum(t['r_multiple'] for d in res2['days'] for t in d['trades'])
total_trades2 = sum(len(d['trades']) for d in res2['days'])
winners2 = sum(1 for d in res2['days'] for t in d['trades'] if t['r_multiple'] > 0)
print()
print(f"With FsV2 gate OFF (OLD behavior):")
print(f"  Total trades: {total_trades2}")
print(f"  Win rate: {winners2}/{total_trades2} = {winners2/total_trades2*100:.1f}%")
print(f"  Total R: {total_r2:.2f}")

# Outcome breakdown
def breakdown(res):
    out = {}
    for d in res['days']:
        for t in d['trades']:
            o = t['outcome']
            out[o] = out.get(o, 0) + 1
    return out

print()
print("Outcome breakdown with gate ON:", breakdown(res))
print("Outcome breakdown with gate OFF:", breakdown(res2))