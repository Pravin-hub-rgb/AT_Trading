"""Deep diagnosis part 2: R-inflation check + walk-forward validation."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from test_experiments import load_window, simulate_v18_experiments, run_and_report
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.walker import FlowCandle
import statistics

SYMBOL = "BTCUSDT_BYBIT"
def load_swing(tf):
    from src.btc.btc_config import load_btc_df
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

c1h, f1h = load_swing("1h")
c15, f15 = load_swing("15m")
fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                     max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=SYMBOL)

print("=" * 80)
print("DIAGNOSIS 3: R-inflation check — do different sl_bufs change R per trade?")
print("=" * 80)

# Run with different sl_buf values and compare risk in dollars vs risk in R
sw1h = _compute_swings(f1h, "continuous", min_bars=10)
sw15 = _compute_swings(f15, "continuous", min_bars=50)

for sl in [0.001, 0.005, 0.01, 0.02, 0.05]:
    tr = simulate_v18_experiments(c1h, sw1h, c15, sw15, fine,
        sl_buf_atr=sl, ext_stop_r=1.5, chop_thresh=55.0,
        cooldown_bars=0, max_consecutive_losses=3,
        exp_multi_ltf=True, exp_multi_ltf_cd=0,
        exp_regime_persist=2)["ltf_trades"]

    risks_usd = []
    for t in tr:
        if t["dir"] == "long":
            risk_usd = t["entry_price"] - t["sl"]
        else:
            risk_usd = t["sl"] - t["entry_price"]
        if risk_usd > 0:
            risks_usd.append(risk_usd)

    r_vals = [t["r_multiple"] for t in tr]

    # Dollar PnL per trade
    pnls_usd = []
    for t in tr:
        if t["dir"] == "long":
            pnl = (t["exit_price"] - t["entry_price"])
        else:
            pnl = (t["entry_price"] - t["exit_price"])
        pnls_usd.append(pnl)

    print(f"\n  sl_buf={sl:.3f}  {len(tr)}t  R={sum(r_vals):+.1f}  WR={sum(1 for r in r_vals if r>0)/len(tr)*100:.1f}%")
    print(f"    Risk (USD): mean=${statistics.mean(risks_usd):.2f}  median=${statistics.median(risks_usd):.2f}")
    print(f"    PnL (USD/trade): mean=${statistics.mean(pnls_usd):.2f}  total=${sum(pnls_usd):.2f}")
    print(f"    R/trade: mean={statistics.mean(r_vals):.3f}  median={statistics.median(r_vals):.3f}")

print()
print("=" * 80)
print("DIAGNOSIS 4: Walk-forward split (first half train, second half test)")
print("=" * 80)

# Split at midpoint
mid = len(c15) // 2
c15_train = c15[:mid]
c15_test = c15[mid:]
f15_train = f15[:mid]
f15_test = f15[mid:]

# 1h split: find bar closest to midpoint timestamp
mid_ts = c15[mid]["ts"]
import bisect
htf_ts = [c["ts"] for c in c1h]
mid_h = bisect.bisect_right(htf_ts, mid_ts)
c1h_train = c1h[:mid_h]
c1h_test = c1h[mid_h:]
f1h_train = f1h[:mid_h]
f1h_test = f1h[mid_h:]

fine_train = _load_fine_1m(c15_train[0]["ts"], c15_train[-1]["ts"], symbol=SYMBOL)
fine_test = _load_fine_1m(c15_test[0]["ts"], c15_test[-1]["ts"], symbol=SYMBOL)

configs = {
    "BASELINE": dict(sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=58.0,
                     cooldown_bars=10, max_consecutive_losses=3),
    "OPTIMAL": dict(sl_buf_atr=0.001, ext_stop_r=1.5, chop_thresh=55.0,
                    cooldown_bars=0, max_consecutive_losses=3,
                    exp_multi_ltf=True, exp_multi_ltf_cd=0,
                    exp_regime_persist=2),
    "OPTIMAL-conservative-sl": dict(sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=55.0,
                    cooldown_bars=0, max_consecutive_losses=3,
                    exp_multi_ltf=True, exp_multi_ltf_cd=0,
                    exp_regime_persist=2),
}

for name, params in configs.items():
    if "BASELINE" in name:
        sw1h_t = _compute_swings(f1h_train, "continuous", min_bars=20)
        sw15_t = _compute_swings(f15_train, "continuous", min_bars=50)
        sw1h_v = _compute_swings(f1h_test, "continuous", min_bars=20)
        sw15_v = _compute_swings(f15_test, "continuous", min_bars=50)
    else:
        sw1h_t = _compute_swings(f1h_train, "continuous", min_bars=10)
        sw15_t = _compute_swings(f15_train, "continuous", min_bars=50)
        sw1h_v = _compute_swings(f1h_test, "continuous", min_bars=10)
        sw15_v = _compute_swings(f15_test, "continuous", min_bars=50)

    # Train
    train = simulate_v18_experiments(c1h_train, sw1h_t, c15_train, sw15_t, fine_train, **params)["ltf_trades"]
    r_train = [t["r_multiple"] for t in train]

    # Validate
    val = simulate_v18_experiments(c1h_test, sw1h_v, c15_test, sw15_v, fine_test, **params)["ltf_trades"]
    r_val = [t["r_multiple"] for t in val]

    wr_train = sum(1 for r in r_train if r > 0) / len(r_train) * 100 if r_train else 0
    wr_val = sum(1 for r in r_val if r > 0) / len(r_val) * 100 if r_val else 0

    # DD both halves
    def max_dd(rs):
        cum, peak, dd = 0, 0, 0
        for r in rs:
            cum += r
            peak = max(peak, cum)
            dd = max(dd, peak - cum)
        return dd

    print(f"\n  {name}:")
    print(f"    Train: {len(train)}t  {sum(r_train):+.1f}R  WR {wr_train:.1f}%  DD {max_dd(r_train):.1f}R")
    print(f"    Test:  {len(val)}t  {sum(r_val):+.1f}R  WR {wr_val:.1f}%  DD {max_dd(r_val):.1f}R")
    if len(train) > 0 and len(val) > 0:
        print(f"    R-degradation: {(1 - sum(r_val)/sum(r_train)) * 100 if sum(r_train) > 0 else 'N/A':.1f}%")
