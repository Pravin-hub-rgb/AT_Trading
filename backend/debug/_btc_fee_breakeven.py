"""Verify the fee model arithmetic + find breakeven fee rates + 1m check."""

import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, ".")

from src.btc.btc_routes import _load_window, _compute_swings  # noqa: E402
from src.btc.btc_engine import simulate_btc_trades  # noqa: E402


def compute(tf, limit, eb, mb, trail, be):
    win, _ = _load_window(tf, limit)
    candles, flow = win
    swings = _compute_swings(flow, "continuous", min_bars=mb)
    tr = simulate_btc_trades(candles, swings, entry_break=eb, sl_mode="swing",
                             rr_target=3.0, trailing=trail, breakeven_r=be)
    closed = [t for t in tr if t["outcome"] != "open"]
    return closed


def fee_r_each(closed, fee_pct):
    """fee in R for each trade (notional-based, 2 sides), and slippage in R."""
    fees, slps = [], []
    for t in closed:
        risk = abs(t["entry_price"] - t["sl"])
        if risk <= 0:
            fees.append(0.0)
            slps.append(0.0)
            continue
        px = abs(t["entry_price"])
        fees.append(2.0 * fee_pct * px / 100.0 / risk)
        slps.append(2.0 / risk)
    return fees, slps


# manually spot check the arithmetic on the first few trades
closed = compute("5m", None, "decisive", 20, "swing", 1.0)
fees, slps = fee_r_each(closed, 0.05)
print("spot-check (first 5 trades, fee=0.05%%/side):")
for t, f, s in zip(closed[:5], fees[:5], slps[:5]):
    risk = abs(t["entry_price"] - t["sl"])
    print("  px=%9.1f risk=%6.1f feeR=%5.3f slipR(2pt)=%5.3f r=%+.3f -> after=%+.3f" % (
        t["entry_price"], risk, f, s, t["r_multiple"],
        t["r_multiple"] - f - s))

base = sum(t["r_multiple"] for t in closed)
print("\n5m decisive trail mb20: base totalR=%.1f trades=%d" % (base, len(closed)))

# breakeven fee (both sides) for each config
print("\nbreakeven round-trip fee (trades still positive):")
for label, tf, limit, eb, mb, trail, be in [
    ("5m decisive trail mb20", "5m", None, "decisive", 20, "swing", 1.0),
    ("5m flip trail mb14", "5m", None, "flip", 14, "swing", 1.0),
    ("15m decisive trail mb20", "15m", None, "decisive", 20, "swing", 1.0),
    ("1m decisive trail mb20 (50k)", "1m", 50000, "decisive", 20, "swing", 1.0),
]:
    try:
        c = compute(tf, limit, eb, mb, trail, be)
    except Exception as e:
        print("  %-32s SKIP (%s)" % (label, e))
        continue
    base_c = sum(t["r_multiple"] for t in c)
    # avg feeR at 0.01% per side, then scale linearly to find breakeven
    fees01, _ = fee_r_each(c, 0.01)
    total_cost01 = sum(fees01)  # at 0.01%/side
    if total_cost01 > 0:
        breakeven = 0.01 * base_c / total_cost01
    else:
        breakeven = float("inf")
    # also net after 0.05% + 2pt
    fees05, slps = fee_r_each(c, 0.05)
    net = base_c - sum(fees05) - sum(slps)
    print("  %-32s tr=%6d base=%+8.1f  breakevenFee=%.3f%%/side  net@0.05%%+2pt=%+8.1f"
          % (label, len(c), base_c, breakeven, net))