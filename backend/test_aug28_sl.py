"""Test the SL fix for 28 Aug with prev_pivot mode."""
import sys
sys.path.insert(0, '.')
from src.intraday import simulate_day, resolve_cfg
import pandas as pd
from src.config import DATA_DIR
from datetime import datetime

df5 = pd.read_csv(DATA_DIR / 'nifty_5min.csv')
df5['ts_str'] = df5['timestamp'].astype(str).str[:10]
day_5m = df5[df5['ts_str'] == '2026-08-28'].reset_index(drop=True)
day_5m['timestamp'] = pd.to_datetime(day_5m['timestamp'])

df1 = pd.read_csv(DATA_DIR / 'nifty_1min.csv')
df1['ts_str'] = df1['timestamp'].astype(str).str[:10]
day_1m = df1[df1['ts_str'] == '2026-08-28'].reset_index(drop=True)
day_1m['timestamp'] = pd.to_datetime(day_1m['timestamp'])

print("=== 1-min candles from 09:30 to 09:40 ===")
for i, row in day_1m.iterrows():
    time_str = str(row['timestamp'])[11:16]
    if '09:30' <= time_str <= '09:40':
        print(f"  {time_str}: O={row['open']:.2f} H={row['high']:.2f} L={row['low']:.2f} C={row['close']:.2f}")

cfg = resolve_cfg({
    'swing_mode': 'opposite_swing_needed',
    'entry_method': 'pivot_break',
    'execution': '1min',
    'sl_mode': 'prev_pivot',
    'sl_pivot_buffer': 1.0,
})

result = simulate_day(
    day_5m, 'bearish', cfg, m1_day=day_1m, ctx={'gap': 'flat', 'extreme': None}
)

print('\n=== Results ===')
print('Date:', result.get('date'))
print('Trades:', len(result.get('trades', [])))
for t in result.get('trades', []):
    print(f'  Dir: {t["dir"]}, Entry: {t["entry_time"]} @ {t["entry_price"]}')
    print(f'  SL: {t["sl"]}, mode: {t.get("sl_mode_used")}, pivot_ref: {t.get("pivot_ref")}')
    print(f'  Target: {t["target"]}')

print('\nKey events:')
for ev in result.get('events', []):
    if ev.get('type') in ['pace_break', 'day_level_set', 'pending_direct_1m', 'entry']:
        print(f'  {ev}')

# Inspect 1-min pivots used
print('\n=== 1-min pivots from WalkerEngine at 09:36 entry time ===')
from src.walker import WalkerEngine, FlowCandle
walker_1m = WalkerEngine()
highs = []
lows = []
m1_candles = []
for i, row in day_1m.iterrows():
    time_str = str(row['timestamp'])[11:16]
    if '09:3' in time_str or '09:4' in time_str:
        fc = FlowCandle(date=str(row['timestamp']), open=row['open'], high=row['high'], low=row['low'], close=row['close'])
        new_p = walker_1m.process_bar(fc, i)
        for p in new_p:
            if p.kind == 'H':
                highs.append(p)
            else:
                lows.append(p)
        m1_candles.append({'time': time_str, 'idx': i, 'high': row['high'], 'low': row['low']})

print(f'  HIGH pivots: {[(p.time, p.px) for p in highs]}')
print(f'  LOW pivots: {[(p.time, p.px) for p in lows]}')
print(f'  Most recent H pivot: {highs[-1].time} @ {highs[-1].px}' if highs else '  No H pivots')
print(f'  Most recent L pivot: {lows[-1].time} @ {lows[-1].px}' if lows else '  No L pivots')
print(f'  Expected SL for SHORT: {highs[-1].px + 1.0}' if highs else '  No H pivots for SL')
