"""Direct test: check fs1_1min_confirmed_idx_5 value in simulate_day for 28-Aug."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import src.intraday as intraday

# Monkey-patch simulate_day to capture the 1-min FS gate value
_orig_sim = intraday.simulate_day

_gate_values = {}

def patched_sim(candles, bias, day_date, day_df, m1_day, m5_day, cfg, ctx=None):
    result = _orig_sim(candles, bias, day_date, day_df, m1_day, m5_day, cfg, ctx=ctx)
    gate_val = result.get("fs1_1min_confirmed_idx_5min", "MISSING")
    gate_time = result.get("fs1_1min_confirmed_time", "MISSING")
    fs_dir = result.get("swing_direction", "N/A")
    _gate_values[day_date] = {
        "gate_idx_5": gate_val,
        "gate_time": gate_time,
        "swing_dir": fs_dir,
        "entry_bar_first_trade": result["trades"][0]["entry_bar"] if result["trades"] else None,
        "n_trades": len(result["trades"]),
    }
    print(f"  [{day_date}] gate={gate_val} gate_time={gate_time} swing={fs_dir} trades={len(result['trades'])}")
    return result

intraday.simulate_day = patched_sim

# Run via server's _intraday_backtest
from server import _intraday_backtest
from src.intraday import resolve_cfg

cfg = resolve_cfg({
    "swing_mode": "opposite_swing_needed",
    "entry_method": "pivot_break",
    "execution": "1min",
})

print("=== Running backtest with gate trace ===")
data, _ = _intraday_backtest(cfg)

print("\n=== 28-Aug detail ===")
if "2026-08-28" in _gate_values:
    info = _gate_values["2026-08-28"]
    print(f"  gate_idx_5: {info['gate_idx_5']}")
    print(f"  gate_time: {info['gate_time']}")
    print(f"  swing_dir: {info['swing_dir']}")
    print(f"  first_trade_entry_bar: {info['entry_bar_first_trade']}")
    if isinstance(info['gate_idx_5'], int):
        print(f"  -> Should BLOCK entries before bar {info['gate_idx_5']+1}")
    else:
        print(f"  -> gate is N/A, entries NOT blocked!")
else:
    print("  NOT FOUND in gate values!")
    print(f"  Available dates: {sorted(_gate_values.keys())}")
