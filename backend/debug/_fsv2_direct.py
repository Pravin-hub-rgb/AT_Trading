"""Direct FsV2 trace on 28 Aug 1-min data."""
import sys
import os
# Add the directory with the modules but make sure 'token' resolves to stdlib
sys.path.insert(0, r'C:\Users\Pravin\Desktop\main\AT_Trading\backend\src')

# Now monkey-patch the token import to prevent shadowing
import importlib
import importlib.util
# Pre-import stdlib token
import token as stdlib_token
sys.modules['token'] = stdlib_token

import pandas as pd
from firstswing import FirstSwingEngine, FlowCandle

# Load 1-min data for 28 Aug
df1 = pd.read_csv(r'C:\Users\Pravin\Desktop\main\AT_Trading\backend\data\nifty_1min.csv')
df1['date'] = df1['date'].astype(str)
day = df1[df1['date'].str.startswith('2026-08-28')].copy()
day['time'] = day['time'].astype(str).str.zfill(8)
print(f'1-min bars: {len(day)}')

# Run FsV2 with default timeCap=09:29
eng = FirstSwingEngine()  # default timeCap=09:29
for idx, row in day.iterrows():
    fc = FlowCandle(
        date=str(row['date']),
        open=row['open'],
        high=row['high'],
        low=row['low'],
        close=row['close'],
    )
    g_idx = day.index.get_loc(idx)
    eng.process_bar(fc, g_idx)

print(f'\n=== FsV2 (timeCap=09:29) on 1-min 28 Aug ===')
if eng.declared:
    print(f'DECLARED! dir={eng.dir}, tier={eng.tier}')
    print(f'  start_idx={eng.start_idx}, start_px={eng.start_px}')
    print(f'  end_idx={eng.end_idx}, end_time={eng.end_time}, end_px={eng.end_px}')
    print(f'  confirmed_at_idx={eng.confirmed_at_idx}, confirmed_at_time={eng.confirmed_at_time}')
    print(f'  confirm_source={eng.confirm_source}')
    # Get the time at confirmed_at_idx
    if eng.confirmed_at_idx is not None and eng.confirmed_at_idx < len(day):
        c = day.iloc[eng.confirmed_at_idx]
        print(f'  bar at conf_idx: {c["time"]} px={c["close"]}')
    if eng.end_idx is not None and eng.end_idx < len(day):
        c = day.iloc[eng.end_idx]
        print(f'  bar at end_idx: {c["time"]} px={c["close"]}')
else:
    print('NOT declared')
