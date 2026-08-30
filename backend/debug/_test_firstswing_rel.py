import sys
sys.path.insert(0, 'backend')
from src.firstswing import FirstSwingEngine
from src.walker import FlowCandle
import csv
rows=[]
with open('data/nifty_1min.csv') as f:
    r=csv.DictReader(f)
    for row in r:
        if row['timestamp'].startswith('2026-08-28'):
            rows.append(row)
candles=[]
for row in rows:
    candles.append(FlowCandle(date=row['timestamp'], open=float(row['open']), high=float(row['high']), low=float(row['low']), close=float(row['close'])))
eng1=FirstSwingEngine()
for i,c in enumerate(candles):
    eng1.process_bar(c,i)
    if eng1.declared:
        break
seed_px=eng1.end_px
seed_idx=eng1.end_idx
seed_time=eng1.end_time
print('seed', seed_px, seed_idx, seed_time)
# test with relative cap 09:41
from datetime import datetime, timedelta
# compute seed+14
h,m = map(int, seed_time.split(':'))
dt = datetime(2000,1,1,h,m)+timedelta(minutes=14)
rel_cap = dt.strftime('%H:%M')
print('rel_cap', rel_cap)
eng2=FirstSwingEngine(opts={'timeCap': rel_cap})
eng2.reset(seed_px, seed_idx, seed_time)
# reset kept time_cap as 09:29 originally? Our reset doesn't update time_cap, so need to set after reset
eng2.time_cap = rel_cap
for i in range(seed_idx+1, len(candles)):
    eng2.process_bar(candles[i], i)
    if eng2.declared:
        print('declared at', candles[i].date, eng2.dir, eng2.start_time, eng2.start_px, eng2.end_time, eng2.end_px, eng2.break_marks, eng2.confirm_source)
        break
    if i< seed_idx+25:
        print(f"{candles[i].date[11:16]} dir={eng2.dir} armed={eng2.armed} confirmed={eng2.dir_confirmed} declared={eng2.declared} marks={eng2.break_marks} streak={eng2.sustain_streak}")
