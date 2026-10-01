"""
Check why the 2024-01-18 13:30 trade is missing
"""
import sys, os, pickle, types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest", "backtest/tests", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import EXPERIMENTS, BP
import test_experiments_craze as tc
from src.btc.btc_engine import _collect_signals, CandleStore
from src.btc.btc_swing import compute_btc_swings

with open(Path(os.environ["TEMP"]) / "at_datacache.pkl", "rb") as f:
    d = pickle.load(f)

sw15 = tc._compute_swings(d["f15"], "continuous", min_bars=50)
c15 = d["c15"]
store = CandleStore(c15)
sigs = _collect_signals(sw15, "decisive", skip_first=True, selection="stream", candles=c15)

# Find the 2024-01-18 13:30 signal
for s in sigs:
    if s['bar'] == '2024-01-18 13:30:00':
        print(f"Signal: {s}")
        break

# Let's look for swing 803 in the swings
swings = d["sw15"]
for s in swings:
    if s.get("swing_index") == 803:
        print(f"\nSwing 803: dir={s.get('dir')} start_idx={s['seg'].get('start_idx')} end_idx={s['seg'].get('end_idx')} start_px={s['seg'].get('start_px')} end_px={s['seg'].get('end_px')}")
        print(f"  confirmed_at_idx: {s.get('confirmed_at_idx')}")
        print(f"  confirmed_at_time: {s.get('confirmed_at_time')}")
        print(f"  breaks: {s.get('breaks')}")
        for b in s.get('breaks', []):
            print(f"  Break: {b}")
        break