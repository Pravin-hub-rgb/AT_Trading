import pandas as pd, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from src import bias as b, config
from src.firstswing import compute_swing_results
from src.walker import FlowCandle
from src.intraday_1m_standalone import run_backtest_1min

p1=config.DATA_DIR/'nifty_1min.csv'
p5=config.DATA_DIR/'nifty_5min.csv'
pdaily=config.DATA_DIR/'nifty_daily.csv'
df1=pd.read_csv(p1)
df5=pd.read_csv(p5)
daily=pd.read_csv(pdaily) if pdaily.exists() else None
df1['timestamp']=pd.to_datetime(df1['timestamp'])
df1_sorted=df1.sort_values('timestamp')
all_cands=[]
for _,row in df1_sorted.iterrows():
    dt=row['timestamp'].strftime('%Y-%m-%dT%H:%M:%S')
    all_cands.append(FlowCandle(date=dt, open=float(row['open']), high=float(row['high']), low=float(row['low']), close=float(row['close'])))
swings=compute_swing_results(all_cands, {'timeCap':'09:29','minBars':14}, swing_count=1)
first_map={s['day']: s['seg']['dir'] for s in swings}

labels=b.compute_bias_with_mode(df5, daily, df1, mode='opposite_first')
bias_map={l['date']:l['bias'] for l in labels}

df1_all=pd.read_csv(p1)
res=run_backtest_1min(df1_all, labels, cfg={'execution':'1min','sl_mode':'avg','rr_target':2.0,'min_sl_pts':13,'breakeven_r':0,'gap_pct':0.0027,'ft_fail_enabled':True,'max_entries':2,'entry_cutoff':'15:15','second_trade_after':'always','bias_mode':'opposite_first'})

mismatches=[]
for day in res['days']:
    d=day['date']
    if not day['trades']:
        continue
    first_whole = first_map.get(d, 'none')
    engine_first = day['swing_direction']
    bias = day['bias']
    expected_whole = 'short' if first_whole=='B' else 'long' if first_whole=='S' else 'none'
    actual = day['trades'][0]['dir']
    if expected_whole != actual:
        mismatches.append((d, first_whole, engine_first, bias, expected_whole, actual, day['trades'][0]['entry_time']))

print(f'Total mismatched vs whole-day first opposite: {len(mismatches)} out of {len([d for d in res["days"] if d["trades"]])} traded days')
for m in mismatches[:30]:
    print(f"{m[0]} whole {m[1]} engine {m[2]} bias {m[3]} exp {m[4]} actual {m[5]} at {m[6]}")

for d in ['2025-06-30','2026-06-30']:
    print('\n---',d,'---')
    print('whole first', first_map.get(d))
    day=next((x for x in res['days'] if x['date']==d), None)
    if day:
        print('engine first', day['swing_direction'], 'bias', day['bias'], 'trades', [(t['dir'], t['entry_time']) for t in day['trades']])
        print('bias label', bias_map.get(d))
        sub=df1[df1['timestamp'].dt.strftime('%Y-%m-%d')==d]
        print('rows', len(sub))
        if len(sub)>0:
            print(sub.head(2).to_string())
    else:
        print('no day found')
        sub=df1[df1['timestamp'].dt.strftime('%Y-%m-%d')==d]
        print('rows', len(sub))
