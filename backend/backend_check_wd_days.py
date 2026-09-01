"""Multi-day whole-day swing validation.

Simulates exactly what the frontend renders for each swing:
  - every break (B1/B2/FLIP) at its global bar -> printed time
  - the FS/SUS confirmation at confirmed_at_idx -> printed time
  - structural sanity per swing + per day.

Run:  cd backend  &&  python ../backend_check_wd_days.py
"""
import sys
sys.path.insert(0, '.')
import pandas as pd
from pathlib import Path
from collections import defaultdict
from src.walker import FlowCandle
from src.swing_engine import compute_whole_day_swings

p = Path('data/nifty_1min.csv')
if not p.exists():
    p = Path('backend/data/nifty_1min.csv')
df = pd.read_csv(p)
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').drop_duplicates(subset='timestamp', keep='last')
candles = [
    FlowCandle(
        date=r['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
        open=float(r['open']), high=float(r['high']),
        low=float(r['low']), close=float(r['close']),
    )
    for _, r in df.iterrows()
]

def tm(i):
    return candles[i].date[11:16] if 0 <= i < len(candles) else '??{%d}' % i

def dt(i):
    return candles[i].date[:10] if 0 <= i < len(candles) else '??'

opts = {'sustain_bars': 7, 'minBars': 14, 'timeCap': '09:29'}
out = compute_whole_day_swings(candles, opts=opts)
by = defaultdict(list)
for s in out:
    by[s['day']].append(s)

DAYS = ['2026-08-25', '2026-08-26', '2026-08-27', '2026-08-28', '2026-08-29', '2026-08-31']
if '2026-08-31' not in by and '2026-08-30' in by:
    DAYS = ['2026-08-25', '2026-08-26', '2026-08-27', '2026-08-28', '2026-08-29']

errors = 0

def err(day, msg):
    global errors
    errors += 1
    print('   !!', day, msg)

for day in DAYS:
    lst = by.get(day)
    if not lst:
        print('=== %s === NO SWINGS' % day)
        continue
    print('=== %s === %d swings' % (day, len(lst)))
    # per-day global day range
    day_candles = [c for c in candles if c.date[:10] == day]
    day_lo = sum(1 for c in candles if c.date[:10] < day)  # first global idx of day
    day_hi = day_lo + len(day_candles) - 1
    prev_end = -1
    for s in lst:
        si = s['swing_index']
        seg = s['seg']
        conf = s['confirmed_at_idx']
        fs = s.get('fs_at_idx', -1)
        kind = s['kind']
        seed = (prev_end + 1) if si > 0 else day_lo
        breaks = s.get('breaks') or []
        br = ', '.join('%s@%s' % (b['kind'], tm(b['idx'])) for b in breaks) if breaks else '(none)'
        conf_s = tm(conf) if conf >= 0 else '(none)'
        fs_s = tm(fs) if fs >= 0 else '(=conf)'

        line = '  %2d %s %s(%d) to %s(%d) %s->%s | breaks[%s] | %s@%s (fs_at %s)' % (
            si, seg['dir'], tm(seg['start_idx']), seg['start_idx'],
            tm(seg['end_idx']), seg['end_idx'],
            round(seg['start_px'], 2), round(seg['end_px'], 2),
            br, kind, conf_s, fs_s,
        )
        print(line)

        # --- structural checks ---
        if not (day_lo <= seg['start_idx'] <= seg['end_idx'] <= day_hi):
            err(day, 'seg out of day range [%d..%d]: %d..%d' % (day_lo, day_hi, seg['start_idx'], seg['end_idx']))
        if prev_end >= 0 and seg['start_idx'] <= prev_end:
            err(day, 'overlap with prev swing end %d at swing %d start %d' % (prev_end, si, seg['start_idx']))
        # direction sanity
        if seg['dir'] == 'S' and seg['end_px'] >= seg['start_px']:
            err(day, 'swing %d marked S but px does not fall: %s->%s' % (si, seg['start_px'], seg['end_px']))
        if seg['dir'] == 'B' and seg['end_px'] <= seg['start_px']:
            err(day, 'swing %d marked B but px does not rise: %s->%s' % (si, seg['start_px'], seg['end_px']))
        # breaks
        for b in breaks:
            if not (seed <= b['idx'] <= (conf if conf >= 0 else day_hi)):
                err(day, 'swing %d break %s@%d outside [seed %d .. conf %d]' % (si, b['kind'], b['idx'], seed, conf))
        # confirmation
        if conf < 0 or not (day_lo <= conf <= day_hi):
            err(day, 'swing %d has bad confirmed_at_idx %d' % (si, conf))
        # structural FS/SUS bar: must be at/after the swing end extreme and in-day
        if fs >= 0:
            if not (day_lo <= fs <= day_hi):
                err(day, 'swing %d fs_at_idx %d out of day' % (si, fs))
            if fs < seg['end_idx']:
                err(day, 'swing %d fs_at_idx(%d) before end_idx(%d)' % (si, fs, seg['end_idx']))
        if not kind:
            err(day, 'swing %d missing kind' % si)
        prev_end = seg['end_idx']

print()
print('TOTAL ERRORS:', errors)
print('days checked:', len([d for d in DAYS if d in by]))