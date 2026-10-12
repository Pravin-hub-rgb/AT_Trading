"""Debug script to trace _chop_target gate failures on specific date ranges."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

# Enable debug flag BEFORE importing firstswing
import src.firstswing as fs
fs._DEBUG_CHOP_TARGET = True

from src.btc.btc_routes import _load_window
from src.btc.btc_swing import compute_btc_swings

TF, MIN_BARS, SYMBOL, LIMIT = "15m", 50, "BTCUSDT_BYBIT", 200000

# Load data
candles, flow = _load_window(TF, LIMIT, SYMBOL)[0]
flow = list(flow)

# Find indices for key dates
def find_date_indices(candles, date_str):
    """Return list of g_idx for candles on a given date."""
    return [i for i, c in enumerate(candles) if c["date"].startswith(date_str)]

# Run trace on first 65 bars (first swing area)
print("=" * 80)
print("TRACE: First 65 bars (first swing at bar 61)")
print("=" * 80)

eng = fs.SwingEngine({"minBars": MIN_BARS, "timeCap": "00:00"})
for i in range(min(65, len(flow))):
    eng.process_bar(flow[i], i)
    if eng.declared:
        print(f"  -> FIRST SWING DECLARED at bar {i} (g_idx={eng.end_idx})")
        break

print("\nDone with first swing trace.")