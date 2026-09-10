"""Test: verify B1 mark at Sept 10 4:30."""
import sys
sys.path.insert(0, '.')
from src.btc.btc_config import load_btc_df
from src.btc.btc_swing import compute_btc_swings
from src.walker import FlowCandle
from src.live.live_mark_detector import LiveMarkDetector

# Load 15m data
df = load_btc_df('15m')
candles = []
for row in df.itertuples():
    date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    candles.append({"date": date, "ts": int(row.ts), "open": float(row.open),
                    "high": float(row.high), "low": float(row.low), "close": float(row.close)})

flow = [FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"]) for c in candles]

# Backtest alignment
swings = compute_btc_swings(flow, opts={"minBars": 50}, max_swings=len(flow) // 2)

# Find last confirmed swing
last_confirmed = None
for s in reversed(swings):
    if s.get("break_kind") and s.get("confirmed_at_idx", -1) >= 0:
        last_confirmed = s
        break

print(f"Last confirmed swing: sw{last_confirmed['swing_index']} ({last_confirmed['dir']})")
print(f"  end_idx: {last_confirmed['seg']['end_idx']}")
print(f"  end_px: {last_confirmed['seg']['end_px']:.2f}")
print(f"  breaks: {len(last_confirmed.get('breaks', []))}")
for b in last_confirmed.get("breaks", []):
    idx = b["idx"]
    if idx < len(candles):
        print(f"    {b['kind']} {b['dir']} @ {b['px']:.2f} ({candles[idx]['date']})")

# Now test live mark detector
print("\n--- Live Mark Detector ---")
detector = LiveMarkDetector("15m", db=None)
detector.align_from_backtest(swings, candles)

print(f"\nDetector state after alignment:")
print(f"  swing_index: {detector.swing_index}")
print(f"  dir: {detector.dir}")
print(f"  anchor: {detector.anchor:.2f}")
print(f"  extreme: {detector.extreme:.2f}")
print(f"  start_idx: {detector.start_idx}")

# Feed remaining candles and look for marks around Sept 10 4:30
print("\n--- Feeding candles after alignment ---")
start_feed = detector.start_idx
for i in range(start_feed, min(start_feed + 100, len(candles))):
    c = candles[i]
    fc = FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"])
    mark = detector.process_bar(fc, i)
    if mark:
        print(f"  MARK: {mark['kind']} {mark['dir']} @ {mark['px']:.2f} ({mark['time']})")
    # Also print candles around Sept 10 4:30
    if "2026-09-10 04:" in c["date"] or "2026-09-10 05:" in c["date"]:
        print(f"  candle: {c['date']} O={c['open']:.2f} H={c['high']:.2f} L={c['low']:.2f} C={c['close']:.2f}")

print(f"\nFinal detector state:")
print(f"  swing_index: {detector.swing_index}")
print(f"  dir: {detector.dir}")
print(f"  anchor: {detector.anchor:.2f}")
print(f"  extreme: {detector.extreme:.2f}")
