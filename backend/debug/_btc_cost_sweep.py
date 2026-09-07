"""Cost-sensitivity sweep across TFs + configs — how much of the headline R
survives real trading costs?"""

import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, ".")

from src.btc.btc_routes import _load_window, _compute_swings  # noqa: E402
from src.btc.btc_engine import simulate_btc_trades  # noqa: E402


def compute(tf, eb, mb, trail, be):
    win, _ = _load_window(tf, None)
    candles, flow = win
    swings = _compute_swings(flow, "continuous", min_bars=mb)
    tr = simulate_btc_trades(candles, swings, entry_break=eb, sl_mode="swing",
                             rr_target=3.0, trailing=trail, breakeven_r=be)
    closed = [t for t in tr if t["outcome"] != "open"]
    return closed


def stress(closed, fee_pct, slip_pts):
    """Fees as %/side of notional + slippage pts, both converted into R."""
    tot = 0.0
    for t in closed:
        risk = abs(t["entry_price"] - t["sl"])
        if risk <= 0:
            continue
        px = abs(t["entry_price"])
        fee_r = 2.0 * fee_pct * px / 100.0 / risk
        tot += t["r_multiple"] - slip_pts / risk - fee_r
    return tot


print("%s %6s %7s  %9s %9s %9s %9s %9s" % (
    "config", "tr", "win%", "zero", "0.02%", "0.05%", "0.05%+2pt", "0.03%+5pt"))

for label, tf, eb, mb, trail, be in [
    ("5m decisive trail mb20", "5m", "decisive", 20, "swing", 1.0),
    ("5m flip trail mb14", "5m", "flip", 14, "swing", 1.0),
    ("5m baseline fixed3R", "5m", "decisive", 14, "off", 1.0),
    ("15m decisive trail mb20", "15m", "decisive", 20, "swing", 1.0),
]:
    closed = compute(tf, eb, mb, trail, be)
    base = sum(t["r_multiple"] for t in closed)
    wins = sum(1 for t in closed if t["r_multiple"] > 0)
    win_pct = 100.0 * wins / max(1, len(closed))
    m2 = stress(closed, 0.02, 0.0)
    t5 = stress(closed, 0.05, 0.0)
    t5s = stress(closed, 0.05, 2.0)
    r3s5 = stress(closed, 0.03, 5.0)
    print("%-28s %6d %6.1f  %+9.1f %+9.1f %+9.1f %+9.1f %+9.1f" % (
        label, len(closed), win_pct, base, m2, t5, t5s, r3s5))