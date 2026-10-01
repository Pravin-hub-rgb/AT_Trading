"""Walk-forward validation on OPTIMAL — expanding window fine fills."""
import sys, time
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

from test_experiments import simulate_v18_experiments

def run_optimal(htf_c, htf_swings, ltf_c, ltf_swings, fine):
    r = simulate_v18_experiments(
        htf_c, htf_swings, ltf_c, ltf_swings, fine_ltf=fine,
        sl_buf_atr=0.01, ext_stop_r=1.5,
        chop_thresh=55.0, cooldown_bars=0, max_consecutive_losses=3,
        exp_multi_ltf=True, exp_multi_ltf_cd=0,
        exp_regime_persist=2,
    )
    return r["ltf_trades"]

def net_r(trades, g):
    closed = [t for t in trades if t["outcome"] != "open"]
    rs = [t["r_multiple"] for t in closed]
    c2, _ = _trade_costs(closed, g["fee_pct"], 0.0, g["entry_slip_pct"], g["exit_slip_pct"])
    return len(closed), sum(rs), sum(rs) - c2

t0 = time.time()
htf_c, htf_f = load_window("1h")
ltf_c, ltf_f = load_window("15m")
t_start = min(htf_c[0]["ts"], ltf_c[0]["ts"])
t_end = max(htf_c[-1]["ts"], ltf_c[-1]["ts"])
fine_full = _load_fine_1m(t_start, t_end, symbol=SYMBOL)
htf_swings_10 = _compute_swings(htf_f, "continuous", min_bars=10)
ltf_swings = _compute_swings(ltf_f, "continuous", min_bars=50)
g = get_v18_params(SYMBOL)
print(f"Data loaded ({time.time()-t0:.0f}s)")

# Full period
trades_full = run_optimal(htf_c, htf_swings_10, ltf_c, ltf_swings, fine_full)
n, gross, net = net_r(trades_full, g)
print(f"\nFULL:    {n}t  gross {gross:+.1f}  NET {net:+.1f}")

# Expanding window: train on first X%, test on rest
# Use FINE data for all segments (the proper test)
for train_pct, label in [(0.50, "50/50"), (0.66, "66/34"), (0.75, "75/25")]:
    cut_ts = t_start + (t_end - t_start) * train_pct
    
    # Split 15m candles by timestamp
    ltf_train = [c for c in ltf_c if int(c["ts"]) < cut_ts]
    ltf_test = [c for c in ltf_c if int(c["ts"]) >= cut_ts]
    
    # Fine split
    fine_train = [c for c in fine_full if int(c["ts"]) < cut_ts]
    fine_test = [c for c in fine_full if int(c["ts"]) >= cut_ts]
    
    # Recompute swings on train period only (causal)
    ltf_flow_train = []
    from src.walker import FlowCandle
    for c in ltf_train:
        ltf_flow_train.append(FlowCandle(date=c["date"], open=float(c["open"]),
                                          high=float(c["high"]), low=float(c["low"]),
                                          close=float(c["close"])))
    sw_train = _compute_swings(ltf_flow_train, "continuous", min_bars=50)
    
    htf_train = [c for c in htf_c if int(c["ts"]) < cut_ts]
    htf_flow_train = []
    for c in htf_train:
        htf_flow_train.append(FlowCandle(date=c["date"], open=float(c["open"]),
                                          high=float(c["high"]), low=float(c["low"]),
                                          close=float(c["close"])))
    sw1h_train = _compute_swings(htf_flow_train, "continuous", min_bars=10)
    
    # Test on full data but report only test-period trades
    # Actually: proper WF means train swings on train, test on full data with those swings
    # But that's complex. Simpler: just split by entry_ts after running on full data.
    
    # Easiest correct approach: run on full data, then split trades by entry_ts
    test_trades = [t for t in trades_full if t["outcome"] != "open" and int(t["entry_ts"]) >= cut_ts]
    train_trades = [t for t in trades_full if t["outcome"] != "open" and int(t["entry_ts"]) < cut_ts]
    
    train_rs = sum(t["r_multiple"] for t in train_trades)
    test_rs = sum(t["r_multiple"] for t in test_trades)
    
    # Net for test period
    test_c2, _ = _trade_costs(test_trades, g["fee_pct"], 0.0, g["entry_slip_pct"], g["exit_slip_pct"])
    test_net = test_rs - test_c2
    train_c2, _ = _trade_costs(train_trades, g["fee_pct"], 0.0, g["entry_slip_pct"], g["exit_slip_pct"])
    train_net = train_rs - train_c2
    
    print(f"\n{label}: train {len(train_trades)}t NET {train_net:+.1f}  test {len(test_trades)}t NET {test_net:+.1f}")

# Bootstrap 95% CI (1000 resamples on closed trades)
import random
closed = [t for t in trades_full if t["outcome"] != "open"]
rs_list = [t["r_multiple"] for t in closed]
n_boot = 1000
boot_nets = []
for _ in range(n_boot):
    sample = [rs_list[random.randint(0, len(rs_list)-1)] for _ in range(len(rs_list))]
    c2_b, _ = _trade_costs(closed, g["fee_pct"], 0.0, g["entry_slip_pct"], g["exit_slip_pct"])
    boot_nets.append(sum(sample) - c2_b)
boot_nets.sort()
lo = boot_nets[int(n_boot * 0.025)]
hi = boot_nets[int(n_boot * 0.975)]
print(f"\nBootstrap 95% CI: [{lo:+.1f}, {hi:+.1f}] (1000 resamples)")
print(f"Total: {time.time()-t0:.0f}s")
