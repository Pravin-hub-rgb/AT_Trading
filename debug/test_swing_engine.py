"""Quick smoke test for the new WalkerEngine and FirstSwingEngine."""
import sys
sys.path.insert(0, "c:/Users/Pravin/Desktop/main/AT_Trading/backend")

from src.walker import WalkerEngine, FlowCandle, compute_algo_pivots
from src.swing_engine import FirstSwingEngine, compute_fs_v2_results


# Test 1: Simple green candle sequence - Walker only
candles_day1 = [
    FlowCandle(date="2025-08-28T09:15:00", open=100.0, high=101.0, low=99.5, close=100.5),
    FlowCandle(date="2025-08-28T09:20:00", open=100.5, high=102.0, low=100.3, close=101.5),
    FlowCandle(date="2025-08-28T09:25:00", open=101.5, high=103.0, low=101.2, close=102.5),
    FlowCandle(date="2025-08-28T09:30:00", open=102.5, high=104.0, low=102.0, close=103.5),
    FlowCandle(date="2025-08-28T09:35:00", open=103.5, high=105.0, low=103.0, close=104.5),
]

print("=== Test 1: WalkerEngine on simple uptrend ===")
pivots = compute_algo_pivots(candles_day1)
print(f"Found {len(pivots)} pivots:")
for p in pivots:
    print(f"  {p.time} {p.kind} @ {p.px:.2f} (sealed={p.sealed})")

print()
print("=== Test 2: FirstSwingEngine with realistic timestamps ===")

# Test with realistic timestamps that pass 9:29 cap and have proper swing formation
# First swing scenario: high prints early, then low breaks
# This simulates a selling first swing with CHOP confirmation
candles_fs = [
    FlowCandle(date="2025-08-28T09:15:00", open=100.0, high=101.0, low=99.5, close=100.5),   # bar 0
    FlowCandle(date="2025-08-28T09:20:00", open=100.5, high=102.0, low=100.3, close=101.0),   # bar 1
    FlowCandle(date="2025-08-28T09:25:00", open=101.0, high=101.5, low=100.0, close=100.3),   # bar 2 - high first
    # 9:29 cap passes here
    FlowCandle(date="2025-08-28T09:30:00", open=100.3, high=100.8, low=99.0, close=99.2),     # bar 3 - B1: low breaks eLoPrev=99.5
    FlowCandle(date="2025-08-28T09:35:00", open=99.2, high=99.8, low=98.5, close=98.7),       # bar 4 - lower low extends
    FlowCandle(date="2025-08-28T09:40:00", open=98.7, high=99.3, low=98.2, close=98.5),       # bar 5 - another lower low
    # Walker should seal a low pivot here around 98.2
    FlowCandle(date="2025-08-28T09:45:00", open=98.5, high=99.5, low=98.3, close=99.3),       # bar 6 - CHOP: breaks above the high pivot
    FlowCandle(date="2025-08-28T09:50:00", open=99.3, high=99.8, low=98.8, close=99.0),       # bar 7
    FlowCandle(date="2025-08-28T09:55:00", open=99.0, high=99.5, low=98.5, close=98.8),       # bar 8
]

# Process manually to see state
eng = FirstSwingEngine()
for i, c in enumerate(candles_fs):
    eng.process_bar(c, i)
    print(f"Bar {i} ({c.date[11:16]}): state={eng.state}, dir={eng.dir}, declared={eng.declared}")
    print(f"  eHi={eng.e_hi.px:.2f}, eLo={eng.e_lo.px:.2f}")
    ll = "N/A" if eng.locked_level != eng.locked_level else f"{eng.locked_level:.2f}"  # NaN check
    print(f"  armed={eng.armed}, locked_level={ll}")
    print(f"  breaks: {len(eng.break_marks)}, normal_highs={len(eng.normal_highs)}, normal_lows={len(eng.normal_lows)}")

print()
print("=== Final result ===")
print(f"Declared: {eng.declared}")
print(f"Direction: {eng.dir}")
print(f"Start: idx={eng.start_idx}, px={eng.start_px:.2f}")
print(f"End: idx={eng.end_idx}, px={eng.end_px:.2f}")
print(f"Source: {eng.confirm_source}")
print(f"Breaks: {len(eng.break_marks)}")
for b in eng.break_marks:
    print(f"  {b.kind} {b.dir} at {b.time} @ {b.px:.2f}")

result = eng.get_result("2025-08-28")
if result:
    print()
    print("=== Structured Result ===")
    print(f"Day: {result.day}")
    print(f"Direction: {result.dir}")
    print(f"Segment: {result.seg.dir} {result.seg.start_idx}->{result.seg.end_idx}")
    print(f"Source: {result.source}")
else:
    print("No result (not declared)")

print()
print("=== All tests completed ===")
