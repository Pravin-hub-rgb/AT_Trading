"""Validate v15 recover_1r engine."""
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m, _trade_costs
from src.btc.engines.htf_ltf.v15_recover_1r import simulate_htf_ltf_recover_1r
from src.walker import FlowCandle

def load_window(tf):
    df = load_btc_df(tf)
    candles = []
    flow = []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({"date": date, "ts": int(row.ts), "open": float(row.open), "high": float(row.high), "low": float(row.low), "close": float(row.close), "volume": 0, "oi": 0})
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high), low=float(row.low), close=float(row.close)))
    return candles, flow

c1h, f1h = load_window("1h")
c15, f15 = load_window("15m")
sw1h = _compute_swings(f1h, "continuous", min_bars=20)
sw15 = _compute_swings(f15, "continuous", min_bars=50)
t0 = min(c1h[0]["ts"], c15[0]["ts"])
t1 = max(c1h[-1]["ts"], c15[-1]["ts"])
fine = _load_fine_1m(t0, t1)

# v12 baseline (b2_vs_flip + cd, no recover_1r)
v12 = simulate_htf_ltf_recover_1r(
    candles_htf=c1h, swings_htf=sw1h,
    candles_ltf=c15, swings_ltf=sw15,
    fine_ltf=fine,
    sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
    cooldown_bars=20, recover_1r=False,
)
print(f"v12 (no recover): n={len(v12['ltf_trades'])} net={sum(t['r_multiple'] for t in v12['ltf_trades']):.2f}")

# v15: recover_1r=True
v15 = simulate_htf_ltf_recover_1r(
    candles_htf=c1h, swings_htf=sw1h,
    candles_ltf=c15, swings_ltf=sw15,
    fine_ltf=fine,
    sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
    cooldown_bars=20, recover_1r=True,
)
print(f"v15 (recover_1r):  n={len(v15['ltf_trades'])} net={sum(t['r_multiple'] for t in v15['ltf_trades']):.2f}")

# Count recover_1r exits
recov_exits = [t for t in v15["ltf_trades"] if t["outcome"] == "recover_1r"]
print(f"recover_1r exits: {len(recov_exits)}")
for t in recov_exits[:10]:
    print(f"  {t['dir']} entry={t['entry_price']:.2f} exit={t['exit_price']:.2f} r={t['r_multiple']:.3f}")
