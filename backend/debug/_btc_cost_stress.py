"""Economic stress test for the BTC swing engine — fees + slippage in R units.

The headline results (+392R on 5m) assume zero fees and zero slippage. This
script applies round-trip trading costs and stop-slippage to every closed trade
and shows how the edge degrades. Sizing is normalized so each trade's risk
(entry -> initial SL) equals 1R; fees are a % of notional converted into R.
"""
import statistics
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, ".")

from src.btc.btc_routes import _load_window, _compute_swings  # noqa: E402
from src.btc.btc_engine import simulate_btc_trades  # noqa: E402

win, _ = _load_window("5m", None)
candles, flow = win
swings = _compute_swings(flow, "continuous", min_bars=20)
tr = simulate_btc_trades(
    candles, swings, entry_break="decisive", sl_mode="swing",
    rr_target=3.0, trailing="swing", breakeven_r=1.0,
)
closed = [t for t in tr if t["outcome"] != "open"]

risks = [abs(t["entry_price"] - t["sl"]) for t in closed]
mean_risk = sum(risks) / len(risks)
mean_px = statistics.mean([t["entry_price"] for t in closed])
print("avg entry px=%.0f  avg initial risk=%.0f pts (%.3f%% of px)" % (
    mean_px, mean_risk, 100.0 * mean_risk / mean_px))
print("trades=%d  base totalR=%.2f\n" % (len(closed), sum(t["r_multiple"] for t in closed)))


def stress(entry_fee_pct, exit_fee_pct, slip_pts):
    """Return (totalR after costs, list of per-trade R after costs)."""
    out = []
    for t in closed:
        risk = abs(t["entry_price"] - t["sl"])
        if risk <= 0:
            continue
        px = abs(t["entry_price"])
        # fees: pct of notional, expressed in R
        fee_r = (entry_fee_pct + exit_fee_pct) * px / 100.0 / risk
        # slippage: adverse pts on exit / entry
        sl = slip_pts / risk
        r = t["r_multiple"]
        # win: subtract slippage + fees; loss: add slippage (worse) - fees
        if t["r_multiple"] >= 0:
            r = t["r_multiple"] - sl - fee_r
        else:
            r = t["r_multiple"] - sl - fee_r
        out.append(r)
    return sum(out), out


# Binance USDT-perp taker fee is 0.05%/side; maker 0.02%. Use both + variants.
configs = [
    ("zero cost (baseline)", 0.0, 0.0, 0.0),
    ("maker 0.02%, no slip", 0.02, 0.02, 0.0),
    ("taker 0.05%, no slip", 0.05, 0.05, 0.0),
    ("taker 0.05% + 2pt slip", 0.05, 0.05, 2.0),
    ("taker 0.05% + 10pt slip", 0.05, 0.05, 10.0),
    ("reduced 0.03% + 5pt slip", 0.03, 0.03, 5.0),
]
print("%-28s %10s %8s" % ("scenario", "totalR", "avgR"))
for name, ef, xf, slip in configs:
    tot, rs = stress(ef, xf, slip)
    print("%-28s %+10.2f %+8.3f" % (name, tot, sum(rs) / len(rs)))