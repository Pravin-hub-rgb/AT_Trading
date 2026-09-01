"""Trace ONLY 27 Aug entries."""
import sys
sys.path.insert(0, ".")
from src.intraday_1m_standalone import run_backtest_1min
from src.bias import compute_bias as cb
from src.config import DATA_DIR
import pandas as pd

df1 = pd.read_csv(DATA_DIR / "nifty_1min.csv")
df5 = pd.read_csv(DATA_DIR / "nifty_5min.csv")
daily = pd.read_csv(DATA_DIR / "nifty_daily.csv") if (DATA_DIR / "nifty_daily.csv").exists() else None

df5["timestamp"] = pd.to_datetime(df5["timestamp"])
df1["timestamp"] = pd.to_datetime(df1["timestamp"])
labels = cb(df5, daily)

cfg = {
    "entry_method": "pivot_break",
    "execution": "1min",
    "sl_mode": "prev_pivot",
    "sl_pivot_buffer": 1.0,
    "gap_pct": 0.0027,
    "ft_fail_enabled": True,
    "swing_mode": "opposite_swing_needed",
}

bt = run_backtest_1min(df1, labels, cfg=cfg)

aug27 = next((d for d in bt["days"] if d["date"].startswith("2026-08-27")), None)
if aug27 is None:
    print("Aug27 not in days")
else:
    print(f"Case: {aug27.get('case')}")
    print(f"Trade mode: {aug27.get('trade_mode')}")
    print(f"Trades: {len(aug27.get('trades', []))}")
    print()
    print("=== All events for 27 Aug ===")
    for ev in aug27.get("events", []):
        print(f"  {ev}")
