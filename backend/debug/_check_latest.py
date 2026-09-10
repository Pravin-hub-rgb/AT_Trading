import sys
sys.path.insert(0, '.')
from src.btc.btc_config import load_btc_df
from src.btc.btc_swing import compute_btc_swings
from src.walker import FlowCandle

df = load_btc_df('15m')
flow = [FlowCandle(date=str(row.timestamp), open=float(row.open), high=float(row.high), low=float(row.low), close=float(row.close)) for row in df.itertuples()]
swings = compute_btc_swings(flow, opts={"minBars": 50}, max_swings=len(flow)//2)

print(f"Total swings: {len(swings)}")
print("\nLast 10 swings:")
for s in swings[-10:]:
    print(f"  sw{s['swing_index']}: {s['break_kind']} {s['dir']} confirmed@{s.get('confirmed_at_time', 'pending')}")

# Find marks after Sept 9
print("\nMarks after Sept 9:")
for s in swings:
    for b in s.get("breaks", []):
        idx = b.get("idx", -1)
        if 0 <= idx < len(flow):
            date = flow[idx].date
            if "2026-09-10" in date:
                print(f"  {date}: {b['kind']} {b['dir']} sw{s['swing_index']} @ {b['px']:.2f}")

# Check if there's an open swing
print(f"\nLast candle: {flow[-1].date}")
print(f"Last confirmed swing: sw{swings[-1]['swing_index']} ({swings[-1]['break_kind']} {swings[-1]['dir']})")
print(f"Open swing: sw{swings[-1]['swing_index']+1} (forming, not yet confirmed)")
