"""Focused trace for swing 1226 (2024-07-16) and swing 6 (2023-01-03 Case A)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

import src.firstswing as fs
fs._DEBUG_CHOP_TARGET = True
fs._DEBUG_CHOP_MAX_BARS = 500  # High limit

from src.btc.btc_routes import _load_window
from src.btc.btc_swing import compute_btc_swings

TF, MIN_BARS, SYMBOL, LIMIT = "15m", 50, "BTCUSDT_BYBIT", 200000

candles, flow = _load_window(TF, LIMIT, SYMBOL)[0]
flow = list(flow)

# First, get the full chain to find exact swing parameters
swings = compute_btc_swings(flow, opts={"minBars": MIN_BARS}, max_swings=len(flow) // 2)

# Find swing 1226 (2024-07-16)
swing_1226 = None
for s in swings:
    if s["day"] == "2024-07-16" and s["swing_index"] == 1226:
        swing_1226 = s
        break

if swing_1226:
    print(f"Swing 1226: start_idx={swing_1226['seg']['start_idx']}, end_idx={swing_1226['seg']['end_idx']}, fs_at={swing_1226['fs_at_idx']}")
    print(f"  dir={swing_1226['dir']}, breaks={[(b['time'], b['kind'], b['px']) for b in swing_1226['breaks']]}")
    
    # Trace from start_idx
    eng = fs.SwingEngine({"minBars": MIN_BARS, "timeCap": "00:00", "defer_same_bar_arm": True})
    for i in range(swing_1226['seg']['start_idx'], swing_1226['fs_at_idx'] + 5):
        eng.process_bar(flow[i], i)
        if eng.declared:
            print(f"  -> DECLARED at bar {i}, FS at {eng.confirmed_at_idx}, end_idx={eng.end_idx}")
            break

# Find swing 6 (2023-01-03 Case A)
swing_6 = None
for s in swings:
    if s["day"] == "2023-01-03" and s["swing_index"] == 6:
        swing_6 = s
        break

if swing_6:
    print(f"\nSwing 6: start_idx={swing_6['seg']['start_idx']}, end_idx={swing_6['seg']['end_idx']}, fs_at={swing_6['fs_at_idx']}")
    print(f"  dir={swing_6['dir']}, breaks={[(b['time'], b['kind'], b['px']) for b in swing_6['breaks']]}")
    
    # Check candles around 20:30, 21:30, 23:30
    for idx in [swing_6['seg']['start_idx'], swing_6['fs_at_idx']]:
        if 0 <= idx < len(candles):
            c = candles[idx]
            print(f"  Candle {idx}: {c['date']} O={c['open']} H={c['high']} L={c['low']} C={c['close']}")
    
    # Trace from start_idx
    eng = fs.SwingEngine({"minBars": MIN_BARS, "timeCap": "00:00", "defer_same_bar_arm": True})
    for i in range(swing_6['seg']['start_idx'], swing_6['fs_at_idx'] + 5):
        eng.process_bar(flow[i], i)
        if eng.declared:
            print(f"  -> DECLARED at bar {i}, FS at {eng.confirmed_at_idx}, end_idx={eng.end_idx}")
            break

# Also trace swing 5 (2023-01-03) which has the 06:00 B1, 06:30 FLIP, 11:00 B2
swing_5 = None
for s in swings:
    if s["day"] == "2023-01-03" and s["swing_index"] == 5:
        swing_5 = s
        break

if swing_5:
    print(f"\nSwing 5: start_idx={swing_5['seg']['start_idx']}, end_idx={swing_5['seg']['end_idx']}, fs_at={swing_5['fs_at_idx']}")
    print(f"  dir={swing_5['dir']}, breaks={[(b['time'], b['kind'], b['px']) for b in swing_5['breaks']]}")
    
    eng = fs.SwingEngine({"minBars": MIN_BARS, "timeCap": "00:00", "defer_same_bar_arm": True})
    for i in range(swing_5['seg']['start_idx'], swing_5['fs_at_idx'] + 5):
        eng.process_bar(flow[i], i)
        if eng.declared:
            print(f"  -> DECLARED at bar {i}, FS at {eng.confirmed_at_idx}, end_idx={eng.end_idx}")
            break

print("\nDone.")