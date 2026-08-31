"""Find what pivot level was actually broken for 2nd entry."""
import sys
sys.path.insert(0, '.')
from src.intraday import _prep_day
from src.walker import WalkerEngine, FlowCandle
import pandas as pd
from src.config import DATA_DIR

df1 = pd.read_csv(DATA_DIR / 'nifty_1min.csv')
df1['ts_str'] = df1['timestamp'].astype(str).str[:10]
day_1m = df1[df1['ts_str'] == '2026-08-28'].reset_index(drop=True)
day_1m['timestamp'] = pd.to_datetime(day_1m['timestamp'])

prepped = _prep_day(day_1m)
walker = WalkerEngine()
all_pivots = []
for idx, mc in enumerate(prepped):
    mc_dt = f"2026-08-28T{mc['time']}:00"
    fc = FlowCandle(date=mc_dt, open=mc["open"], high=mc["high"], low=mc["low"], close=mc["close"])
    new_p = walker.process_bar(fc, idx)
    for p in new_p:
        all_pivots.append({'idx': idx, 'time': mc['time'], 'kind': p.kind, 'px': p.px, 'walker_idx': p.idx})

# Show pivots between 09:42 and 10:05
print("=== Pivots around 09:42-10:05 ===")
for p in all_pivots:
    if '09:42' <= p['time'] <= '10:05':
        print(f"  idx={p['idx']}, time={p['time']}, kind={p['kind']}, px={p['px']}")

# User says next pivot is at 09:47, break at 09:49
# 09:47: H=24153.30, L=24148.10
# Check if LOW pivot was sealed at 24148.10
# 09:48: H=24155.20 (higher than 09:47 H=24153.30, so 09:47 is NOT a H pivot)
# 09:48: L=24148.90 (higher than 09:47 L=24148.10, so 09:47 IS a LOW pivot)

# So expected SL for SHORT after 09:47 LOW break = 09:47 LOW = 24148.1
# But the engine fired at 10:01 with SL=24161.3 (09:59 HIGH)

# User wants: 09:49 entry SHORT @ close=24146.95, SL=24148.1 (09:47 LOW pivot) or the most recent HIGH
print("\n=== User's expected: SHORT entry at 09:49 close=24146.95 ===")
print("Expected SL: 09:47 LOW=24148.1 (or 09:48 H=24155.2?)")

# Let's see all pivots with indices for clarity
print("\n=== All pivots 09:30-10:05 with idx ===")
for p in all_pivots:
    if '09:30' <= p['time'] <= '10:05':
        print(f"  walker_idx={p['walker_idx']}, prepped_idx={p['idx']}, time={p['time']}, kind={p['kind']}, px={p['px']}")