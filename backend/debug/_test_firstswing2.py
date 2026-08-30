import sys
sys.path.insert(0, 'backend')
from src.firstswing import FirstSwingEngine
from src.walker import FlowCandle
import csv
from datetime import datetime, timezone, timedelta
IST = timezone(timedelta(hours=5, minutes=30))
rows=[]
with open('data/nifty_1min.csv') as f:
    r=csv.DictReader(f)
    for row in r:
        if row['timestamp'].startswith('2026-08-28'):
            rows.append(row)
candles=[]
for row in rows:
    ts=row['timestamp']
    candles.append(FlowCandle(date=ts, open=float(row['open']), high=float(row['high']), low=float(row['low']), close=float(row['close'])))
eng1=FirstSwingEngine()
for i,c in enumerate(candles):
    eng1.process_bar(c,i)
    if eng1.declared:
        break
print('first swing', eng1.dir, eng1.start_time, eng1.start_px, eng1.end_time, eng1.end_px, eng1.confirmed_at_time, eng1.break_marks)
seed_px=eng1.end_px
seed_idx=eng1.end_idx
seed_time=eng1.end_time
print('seed', seed_px, seed_idx, seed_time)
eng2=FirstSwingEngine()
eng2.reset(seed_px, seed_idx, seed_time)
for i in range(seed_idx+1, len(candles)):
    eng2.process_bar(candles[i], i)
    if i< seed_idx+20:
        print(f"{candles[i].date[11:16]} idx={i} H={candles[i].high} L={candles[i].low} state={eng2.state} dir={eng2.dir} armed={eng2.armed} confirmed={eng2.dir_confirmed} declared={eng2.declared} marks={eng2.break_marks}")
    if eng2.declared:
        print('second swing declared', eng2.dir, eng2.start_time, eng2.start_px, eng2.end_time, eng2.end_px, eng2.confirmed_at_time, eng2.break_marks, eng2.confirm_source)
        break
if not eng2.declared:
    print('not declared', eng2.state, eng2.dir, eng2.break_marks)
