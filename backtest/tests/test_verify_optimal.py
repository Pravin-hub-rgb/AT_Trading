"""Verify our OPTIMAL against their OPTIMAL — same numbers?"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m, _trade_costs
from src.walker import FlowCandle
from engine.v18_params import get_v18_params

SYMBOL = "BTCUSDT_BYBIT"

def load_window(tf):
    df = load_btc_df(tf, SYMBOL)
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({"date": date, "ts": int(row.ts), "open": float(row.open),
                        "high": float(row.high), "low": float(row.low), "close": float(row.close),
                        "volume": 0, "oi": 0})
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high),
                               low=float(row.low), close=float(row.close)))
    return candles, flow

htf_c, htf_f = load_window("1h")
ltf_c, ltf_f = load_window("15m")
t0 = min(htf_c[0]["ts"], ltf_c[0]["ts"])
t1 = max(htf_c[-1]["ts"], ltf_c[-1]["ts"])
fine = _load_fine_1m(t0, t1, symbol=SYMBOL)

htf_swings_10 = _compute_swings(htf_f, "continuous", min_bars=10)
ltf_swings = _compute_swings(ltf_f, "continuous", min_bars=50)

from test_experiments import simulate_v18_experiments

# Our OPTIMAL: mb1h=10, chop=55, persist=2, cd=0, multi-LTF
r = simulate_v18_experiments(
    htf_c, htf_swings_10, ltf_c, ltf_swings, fine_ltf=fine,
    sl_buf_atr=0.01, ext_stop_r=1.5,
    chop_thresh=55.0, cooldown_bars=0, max_consecutive_losses=3,
    exp_multi_ltf=True, exp_multi_ltf_cd=0,
    exp_regime_persist=2,
)
trades = r["ltf_trades"]
closed = [t for t in trades if t["outcome"] != "open"]
rs = [t["r_multiple"] for t in closed]
wins = [r for r in rs if r > 0]
wr = 100 * len(wins) / len(closed) if closed else 0

g = get_v18_params(SYMBOL)
c2, _ = _trade_costs(closed, g["fee_pct"], 0.0, g["entry_slip_pct"], g["exit_slip_pct"])
net = sum(rs) - c2

print(f"OUR OPTIMAL:     {len(closed)}t  gross {sum(rs):+.1f}  NET {net:+.1f}  WR {wr:.1f}%")
print(f"THEIR OPTIMAL:   515t  gross +456.2  NET +348.0  WR 28.0%")

# Also verify B3-OPT via our harness
# B3 is NOT in our harness — it's their experiment. Can't run B3-OPT here.
# But we CAN verify that our OPTIMAL matches their OPTIMAL.
if len(closed) == 515:
    print(f"\nTRADE COUNT MATCH: 515t")
    # Check if gross matches
    if abs(sum(rs) - 456.2) < 1.0:
        print(f"GROSS MATCH: {sum(rs):.1f} vs 456.2")
    else:
        print(f"GROSS MISMATCH: {sum(rs):.1f} vs 456.2")
    # Check net
    print(f"NET: {net:+.1f} vs 348.0 (diff {net - 348.0:+.1f})")
else:
    print(f"\nTRADE COUNT MISMATCH: {len(closed)} vs 515")
