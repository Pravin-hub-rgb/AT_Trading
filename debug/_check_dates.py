import sys
sys.path.insert(0, '.')
sys.path = [p for p in sys.path if 'src' not in p]
sys.path.insert(0, '.')
import pandas as pd
from src.config import DATA_DIR
df = pd.read_csv(DATA_DIR / 'nifty_5min.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
dates = sorted(df['timestamp'].astype(str).str[:10].unique())
print('Date range:', dates[0], 'to', dates[-1])
print('Last 20 dates:', dates[-20:])
TARGETS = {'2026-07-15', '2026-07-09', '2026-07-08'}
for t in TARGETS:
    print(f'Has {t}: {t in set(dates)}')
