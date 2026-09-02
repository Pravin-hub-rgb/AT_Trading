import sys; sys.path.insert(0, '.')
from src.firstswing import compute_swing_results
from src.walker import FlowCandle

lines = open('../data/nifty_1min.csv', encoding='utf-8-sig').read().splitlines()
candles = [FlowCandle(date=l.split(',')[0], open=float(l.split(',')[2]), high=float(l.split(',')[3]), low=float(l.split(',')[4]), close=float(l.split(',')[5])) for l in lines if len(l.split(',')) > 5 and l.split(',')[0][0].isdigit()]

wd = compute_swing_results(candles, swing_count='whole')
aug17 = [s for s in wd if s['day'] == '2026-08-17']
for s in aug17[:3]:
    print(f"Swing {s['swing_index']}: dir={s['seg']['dir']} {s['seg']['start_px']:.0f}->{s['seg']['end_px']:.0f} source={s['source']} kind={s['kind']}")
    print(f"  confirmed_at={s['confirmed_at_time']} idx={s['confirmed_at_idx']}")
    print(f"  fs_at={s['fs_at_time']} idx={s['fs_at_idx']}")
    print(f"  first chop cross: {s['breaks'][-1]['time'] if s['breaks'] else 'none'}")
