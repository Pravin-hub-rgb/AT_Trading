"""Validate v16 entry distance gate."""
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m, _trade_costs
from src.btc.engines.htf_ltf.v16_entry_dist import simulate_htf_ltf_entry_dist
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

# v12+cd20 baseline (no entry dist gate)
v12 = simulate_htf_ltf_entry_dist(
    candles_htf=c1h, swings_htf=sw1h, candles_ltf=c15, swings_ltf=sw15, fine_ltf=fine,
    sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
    cooldown_bars=20, entry_dist_max=0.0,
)
print(f"v12+cd20 (no gate): n={len(v12['ltf_trades'])} net={sum(t['r_multiple'] for t in v12['ltf_trades']):.2f}")

# v16: entry_dist_max=0.3
v16 = simulate_htf_ltf_entry_dist(
    candles_htf=c1h, swings_htf=sw1h, candles_ltf=c15, swings_ltf=sw15, fine_ltf=fine,
    sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
    cooldown_bars=20, entry_dist_max=0.3,
)
print(f"v16 (entry<=30%):   n={len(v16['ltf_trades'])} net={sum(t['r_multiple'] for t in v16['ltf_trades']):.2f}")

# Count skipped
skipped = len(v12['ltf_trades']) - len(v16['ltf_trades'])
print(f"skipped: {skipped} trades ({skipped/len(v12['ltf_trades'])*100:.1f}%)")

# Per-year
for year in ["2023", "2024", "2025", "2026"]:
    v12_y = [t for t in v12['ltf_trades'] if t['entry_date'][:4] == year]
    v16_y = [t for t in v16['ltf_trades'] if t['entry_date'][:4] == year]
    v12_net = sum(t['r_multiple'] for t in v12_y)
    v16_net = sum(t['r_multiple'] for t in v16_y)
    print(f"  {year}: v12={len(v12_y)}tr/{v12_net:.1f}R  v16={len(v16_y)}tr/{v16_net:.1f}R")
