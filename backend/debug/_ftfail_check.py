import sys
sys.path.insert(0, '.')
sys.path = [p for p in sys.path if 'src' not in p]
sys.path.insert(0, '.')
import pandas as pd
from src.intraday import run_backtest, DEFAULT_CFG
from src.bias import compute_bias
from src.config import DATA_DIR

df = pd.read_csv(DATA_DIR / 'nifty_5min.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
daily_df = pd.read_csv(DATA_DIR / 'nifty_daily.csv') if (DATA_DIR / 'nifty_daily.csv').exists() else None
bl = [lb for lb in compute_bias(df, daily_df) if lb['date'] in set(df['timestamp'].astype(str).str[:10])]

# Test WITH ft_fail
res_on = run_backtest(df, bl, cfg=dict(DEFAULT_CFG, ft_fail_enabled=True))
# Test WITHOUT ft_fail
res_off = run_backtest(df, bl, cfg=dict(DEFAULT_CFG, ft_fail_enabled=False))

with open('../debug/_ftfail_result.txt', 'w') as f:
    f.write('=== WITH ft_fail_enabled=True ===\n')
    f.write(f"Total: {res_on['stats']['trades']} trades, R={res_on['stats']['total_r']}\n")
    for d in res_on['days']:
        if d['date'] in {'2026-07-08','2026-07-09','2026-07-15'} and d['trades']:
            f.write(f"  {d['date']}: {len(d['trades'])} trades, outcomes={[t['outcome'] for t in d['trades']]}\n")
    
    f.write('\n=== WITH ft_fail_enabled=False ===\n')
    f.write(f"Total: {res_off['stats']['trades']} trades, R={res_off['stats']['total_r']}\n")
    for d in res_off['days']:
        if d['date'] in {'2026-07-08','2026-07-09','2026-07-15'} and d['trades']:
            f.write(f"  {d['date']}: {len(d['trades'])} trades, outcomes={[t['outcome'] for t in d['trades']]}\n")

print("Done")
