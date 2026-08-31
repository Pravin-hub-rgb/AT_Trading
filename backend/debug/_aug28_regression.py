"""Check current 28 Aug behavior with both configs."""
import sys, os
# Add src dir first (priority)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
from intraday import simulate_day
from config import DATASET_5M, DATASET_1M
import pandas as pd

df5 = pd.read_csv(DATASET_5M, parse_dates=['date'])
df1 = pd.read_csv(DATASET_1M, parse_dates=['date'])
df5['time'] = pd.to_datetime(df5['time'], format='%H:%M').dt.time
df1['time'] = pd.to_datetime(df1['time'], format='%H:%M').dt.time

day5 = df5[df5['date'].dt.strftime('%Y-%m-%d') == '2026-08-28']
day1 = df1[df1['date'].dt.strftime('%Y-%m-%d') == '2026-08-28']

print(f'5min bars: {len(day5)}, 1min bars: {len(day1)}')

# Test 1: pivot_break + opposite_swing_needed
cfg_pivot = {
    'execution': '1min',
    'swing_mode': 'opposite_swing_needed',
    'entry_method': 'pivot_break',
    'aligned': True,
}
result = simulate_day(day5, day1, cfg_pivot)
trades = result.get('trades', [])
print(f'\n[1] pivot_break + opposite_swing_needed: {len(trades)} trades')
for t in trades:
    print(f'  {t}')
events = result.get('events', [])
fs_events = [e for e in events if any(k in e.get('type', '') for k in ['swing', 'fs', 'second', 'gate', 'skipped', 'entry', 'armed'])]
print(f'  Relevant events:')
for e in fs_events[:30]:
    print(f'    {e}')

# Test 2: pivot_break + swing_mode=none
cfg_none = {
    'execution': '1min',
    'swing_mode': 'none',
    'entry_method': 'pivot_break',
    'aligned': True,
}
result2 = simulate_day(day5, day1, cfg_none)
trades2 = result2.get('trades', [])
print(f'\n[2] pivot_break + swing_mode=none: {len(trades2)} trades')
for t in trades2:
    print(f'  {t}')

# Test 3: pace_break (no pivot) + opposite_swing_needed
cfg_pace = {
    'execution': '1min',
    'swing_mode': 'opposite_swing_needed',
    'entry_method': 'pace_break',
    'aligned': True,
}
result3 = simulate_day(day5, day1, cfg_pace)
trades3 = result3.get('trades', [])
print(f'\n[3] pace_break + opposite_swing_needed: {len(trades3)} trades')
for t in trades3:
    print(f'  {t}')
