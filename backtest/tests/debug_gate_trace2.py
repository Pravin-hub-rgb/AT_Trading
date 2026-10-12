"""Debug script to trace _chop_target gate failures on key swing dates."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

# Enable debug flag BEFORE importing firstswing
import src.firstswing as fs
fs._DEBUG_CHOP_TARGET = True
fs._DEBUG_CHOP_MAX_BARS = 200  # Trace up to 200 bars_seen

from src.btc.btc_routes import _load_window
from src.btc.btc_swing import compute_btc_swings

TF, MIN_BARS, SYMBOL, LIMIT = "15m", 50, "BTCUSDT_BYBIT", 200000

# Load data
candles, flow = _load_window(TF, LIMIT, SYMBOL)[0]
flow = list(flow)

# Run full chain to find target swings
swings = compute_btc_swings(flow, opts={"minBars": MIN_BARS}, max_swings=len(flow) // 2)

print("=" * 80)
print("TARGET SWINGS FROM FULL CHAIN")
print("=" * 80)

for s in swings:
    if s["day"] == "2025-07-20" and s["swing_index"] == 2049:
        print(f"Swing 2049 (2025-07-20): start_idx={s['seg']['start_idx']}, end_idx={s['seg']['end_idx']}, fs_at={s['fs_at_idx']}")
        print(f"  dir={s['dir']}, breaks={[(b['time'], b['kind'], b['px']) for b in s['breaks']]}")
    if s["day"] == "2024-07-16" and s["swing_index"] == 1226:
        print(f"Swing 1226 (2024-07-16): start_idx={s['seg']['start_idx']}, end_idx={s['seg']['end_idx']}, fs_at={s['fs_at_idx']}")
        print(f"  dir={s['dir']}, breaks={[(b['time'], b['kind'], b['px']) for b in s['breaks']]}")
    if s["day"] == "2023-01-03":
        # Print all 2023-01-03 swings
        print(f"Swing {s['swing_index']} (2023-01-03): start_idx={s['seg']['start_idx']}, end_idx={s['seg']['end_idx']}, fs_at={s['fs_at_idx']}")
        print(f"  dir={s['dir']}, breaks={[(b['time'], b['kind'], b['px']) for b in s['breaks']]}")

# Check what time fs_at=243 and fs_at=271 are
print(f"\nCandle 243: {candles[243]['date']}")
print(f"Candle 271: {candles[271]['date']}")

# Now trace specific swings with debug enabled
print("\n" + "=" * 80)
print("TRACE: Swing 2049 (2025-07-20) - full leg")
print("=" * 80)

swing_2049 = None
for s in swings:
    if s["day"] == "2025-07-20" and s["swing_index"] == 2049:
        swing_2049 = s
        break

if swing_2049:
    start_idx = swing_2049["seg"]["start_idx"]
    end_idx = swing_2049["seg"]["end_idx"]
    print(f"Tracing from start_idx={start_idx} to end_idx={end_idx}")
    
    eng = fs.SwingEngine({"minBars": MIN_BARS, "timeCap": "00:00", "defer_same_bar_arm": True})
    for i in range(start_idx, end_idx + 10):
        eng.process_bar(flow[i], i)
        if eng.declared:
            print(f"  -> DECLARED at bar {i}, FS at {eng.confirmed_at_idx}, end_idx={eng.end_idx}")
            break

print("\n" + "=" * 80)
print("TRACE: Swing 1226 (2024-07-16) - full leg")
print("=" * 80)

swing_1226 = None
for s in swings:
    if s["day"] == "2024-07-16" and s["swing_index"] == 1226:
        swing_1226 = s
        break

if swing_1226:
    start_idx = swing_1226["seg"]["start_idx"]
    end_idx = swing_1226["seg"]["end_idx"]
    print(f"Tracing from start_idx={start_idx} to end_idx={end_idx}")
    
    eng = fs.SwingEngine({"minBars": MIN_BARS, "timeCap": "00:00", "defer_same_bar_arm": True})
    for i in range(start_idx, end_idx + 10):
        eng.process_bar(flow[i], i)
        if eng.declared:
            print(f"  -> DECLARED at bar {i}, FS at {eng.confirmed_at_idx}, end_idx={eng.end_idx}")
            break

print("\n" + "=" * 80)
print("TRACE: Swing 6 (2023-01-03) - the one with FLIP at 20:15")
print("=" * 80)

swing_6 = None
for s in swings:
    if s["day"] == "2023-01-03" and s["swing_index"] == 6:
        swing_6 = s
        break

if swing_6:
    start_idx = swing_6["seg"]["start_idx"]
    end_idx = swing_6["seg"]["end_idx"]
    print(f"Tracing from start_idx={start_idx} to end_idx={end_idx}")
    
    eng = fs.SwingEngine({"minBars": MIN_BARS, "timeCap": "00:00", "defer_same_bar_arm": True})
    for i in range(start_idx, end_idx + 10):
        eng.process_bar(flow[i], i)
        if eng.declared:
            print(f"  -> DECLARED at bar {i}, FS at {eng.confirmed_at_idx}, end_idx={eng.end_idx}")
            break

# Also trace swing 5 (2023-01-03) which has B1 at 06:00, FLIP at 06:30, B2 at 11:00
print("\n" + "=" * 80)
print("TRACE: Swing 5 (2023-01-03) - B1 06:00, FLIP 06:30, B2 11:00")
print("=" * 80)

swing_5 = None
for s in swings:
    if s["day"] == "2023-01-03" and s["swing_index"] == 5:
        swing_5 = s
        break

if swing_5:
    start_idx = swing_5["seg"]["start_idx"]
    end_idx = swing_5["seg"]["end_idx"]
    print(f"Tracing from start_idx={start_idx} to end_idx={end_idx}")
    
    eng = fs.SwingEngine({"minBars": MIN_BARS, "timeCap": "00:00", "defer_same_bar_arm": True})
    for i in range(start_idx, end_idx + 10):
        eng.process_bar(flow[i], i)
        if eng.declared:
            print(f"  -> DECLARED at bar {i}, FS at {eng.confirmed_at_idx}, end_idx={eng.end_idx}")
            break

print("\nDone.")