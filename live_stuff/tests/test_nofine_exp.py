"""Verify experiment harness no-fine path."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings
from test_experiments import simulate_v18_experiments
from src.walker import FlowCandle

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
htf_swings = _compute_swings(htf_f, "continuous", min_bars=20)
ltf_swings = _compute_swings(ltf_f, "continuous", min_bars=50)

# Experiment harness WITHOUT fine data
r = simulate_v18_experiments(
    htf_c, htf_swings, ltf_c, ltf_swings, fine_ltf=None,
    sl_buf_atr=0.01, ext_stop_r=1.5,
    chop_thresh=58.0, cooldown_bars=10, max_consecutive_losses=3,
)
trades = r["ltf_trades"]
closed = [t for t in trades if t["outcome"] != "open"]
open_t = [t for t in trades if t["outcome"] == "open"]
rs = [t["r_multiple"] for t in closed]
print(f"EXPERIMENT HARNESS no-fine: {len(trades)}t total, {len(closed)} closed, {len(open_t)} open")
if closed:
    wins = [r for r in rs if r > 0]
    print(f"  Closed: {sum(rs):+.1f}R  WR {100*len(wins)/len(closed):.1f}%")
if open_t:
    open_r = [t["r_multiple"] for t in open_t]
    print(f"  Open trades: {len(open_t)}")
    print(f"  R range: {min(open_r):.1f} to {max(open_r):.1f}")
    print(f"  First 5 open:")
    for t in open_t[:5]:
        print(f"    {t['entry_date']} {t['dir']} r={t['r_multiple']:.1f}")
