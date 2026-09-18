"""Deep diagnosis of experiment results."""
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

print("=" * 80)
print("DIAGNOSIS 1: What does sl_buf=0.001 mean in real dollars?")
print("=" * 80)

# Compute ATR(14) for 15m
atr_vals = []
for i in range(14, len(c15)):
    h = c15[i]["high"]
    l = c15[i]["low"]
    pc = c15[i-1]["close"]
    tr = max(h - l, abs(h - pc), abs(l - pc))
    if i == 14:
        atr_vals.append(tr)
    else:
        atr_vals.append((atr_vals[-1] * 13 + tr) / 14)

atr_mean = statistics.mean(atr_vals)
atr_median = statistics.median(atr_vals)
atr_min = min(atr_vals)
atr_max = max(atr_vals)
price_mean = statistics.mean([c["close"] for c in c15])

print(f"  15m BTC price range: ${min(c['low'] for c in c15):.0f} - ${max(c['high'] for c in c15):.0f}")
print(f"  15m price mean: ${price_mean:.0f}")
print(f"  15m ATR(14) mean: ${atr_mean:.2f}")
print(f"  15m ATR(14) median: ${atr_median:.2f}")
print(f"  15m ATR(14) range: ${atr_min:.2f} - ${atr_max:.2f}")
print()
print(f"  sl_buf=0.01 (current):  SL buffer = ${0.01 * atr_mean:.2f} = {0.01 * atr_mean / price_mean * 100:.4f}% of price")
print(f"  sl_buf=0.001 (optimal): SL buffer = ${0.001 * atr_mean:.2f} = {0.001 * atr_mean / price_mean * 100:.5f}% of price")
print(f"  sl_buf=0.005:           SL buffer = ${0.005 * atr_mean:.2f} = {0.005 * atr_mean / price_mean * 100:.4f}% of price")
print()

# How many 15m candles have wicks larger than 0.001*ATR?
wick_gt_001 = 0
wick_gt_005 = 0
wick_gt_01 = 0
total_wicks = 0
for i in range(1, len(c15)):
    body_hi = max(c15[i]["open"], c15[i]["close"])
    body_lo = min(c15[i]["open"], c15[i]["close"])
    upper_wick = c15[i]["high"] - body_hi
    lower_wick = body_lo - c15[i]["low"]
    for wick in [upper_wick, lower_wick]:
        total_wicks += 1
        if wick > 0.001 * atr_mean: wick_gt_001 += 1
        if wick > 0.005 * atr_mean: wick_gt_005 += 1
        if wick > 0.01 * atr_mean: wick_gt_01 += 1

print(f"  Candle wick analysis ({total_wicks} total wicks):")
print(f"  Wicks > 0.001*ATR (${0.001*atr_mean:.2f}): {wick_gt_001} ({wick_gt_001/total_wicks*100:.1f}%)")
print(f"  Wicks > 0.005*ATR (${0.005*atr_mean:.2f}): {wick_gt_005} ({wick_gt_005/total_wicks*100:.1f}%)")
print(f"  Wicks > 0.01*ATR (${0.01*atr_mean:.2f}):  {wick_gt_01} ({wick_gt_01/total_wicks*100:.1f}%)")
print()

print("=" * 80)
print("DIAGNOSIS 2: Signal filtering — how many signals pass window check?")
print("=" * 80)

# Count signals at each step for the OPTIMAL combo vs BASELINE
trials = {
    "BASELINE": dict(sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=58.0,
                     cooldown_bars=10, max_consecutive_losses=3),
    "OPTIMAL": dict(sl_buf_atr=0.001, ext_stop_r=1.5, chop_thresh=55.0,
                    cooldown_bars=0, max_consecutive_losses=3,
                    exp_multi_ltf=True, exp_multi_ltf_cd=0,
                    exp_regime_persist=2),
}

fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                     max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=SYMBOL)
sw1h_base = _compute_swings(f1h, "continuous", min_bars=20)
sw15_base = _compute_swings(f15, "continuous", min_bars=50)
sw1h_opt = _compute_swings(f1h, "continuous", min_bars=10)
sw15_opt = _compute_swings(f15, "continuous", min_bars=50)

for name, params in trials.items():
    sw1h = sw1h_opt if name == "OPTIMAL" else sw1h_base
    sw15 = sw15_opt if name == "OPTIMAL" else sw15_base
    result = simulate_v18_experiments(c1h, sw1h, c15, sw15, fine, **params)
    trades = result["ltf_trades"]
    intervals = result.get("intervals", [])

    outcomes = [t["outcome"] for t in trades]
    r_vals = [t["r_multiple"] for t in trades]
    wins = sum(1 for r in r_vals if r > 0)
    losses = sum(1 for r in r_vals if r <= 0)

    # Drawdown
    cumR = 0
    peak = 0
    max_dd = 0
    for r in r_vals:
        cumR += r
        if cumR > peak: peak = cumR
        dd = peak - cumR
        if dd > max_dd: max_dd = dd

    # Win/loss streaks
    streak = 0
    max_win_streak = 0
    max_loss_streak = 0
    for r in r_vals:
        if r > 0:
            if streak >= 0: streak += 1
            else: streak = 1
            max_win_streak = max(max_win_streak, streak)
        else:
            if streak <= 0: streak -= 1
            else: streak = -1
            max_loss_streak = max(max_loss_streak, abs(streak))

    # Trade frequency
    if trades:
        dates = [t["entry_date"] for t in trades]
        ts = [t["entry_ts"] for t in trades]
        total_days = (ts[-1] - ts[0]) / 86400000
        trades_per_month = len(trades) / (total_days / 30) if total_days > 0 else 0
    else:
        total_days = 0
        trades_per_month = 0

    print(f"\n  {name}:")
    print(f"    Trades: {len(trades)}  ({trades_per_month:.0f}/month)")
    print(f"    Total R: {sum(r_vals):+.1f}")
    print(f"    WR: {wins/len(trades)*100:.1f}%  ({wins}W / {losses}L)")
    print(f"    Max win streak: {max_win_streak}  Max loss streak: {max_loss_streak}")
    print(f"    Max drawdown: {max_dd:.1f}R")
    print(f"    Avg win: {statistics.mean([r for r in r_vals if r > 0]):.2f}R" if wins else "    Avg win: N/A")
    print(f"    Avg loss: {statistics.mean([r for r in r_vals if r <= 0]):.2f}R" if losses else "    Avg loss: N/A")

    # R distribution
    r_ranges = [(-99, -3), (-3, -2), (-2, -1), (-1, -0.5), (-0.5, 0), (0, 1), (1, 2), (2, 3), (3, 5), (5, 10), (10, 99)]
    print(f"    R distribution:")
    for lo, hi in r_ranges:
        cnt = sum(1 for r in r_vals if lo <= r < hi)
        if cnt > 0:
            print(f"      [{lo:+.0f},{hi:+.0f}): {cnt}")

    # Check for suspicious patterns
    print(f"    HTF window types: ", end="")
    types = {}
    for t in trades:
        bk = t["break_kind"]
        types[bk] = types.get(bk, 0) + 1
    for k, v in sorted(types.items()):
        print(f"{k}={v} ", end="")
    print()

    print(f"    Outcome counts: ", end="")
    oc = {}
    for t in trades:
        oc[t["outcome"]] = oc.get(t["outcome"], 0) + 1
    for k, v in sorted(oc.items()):
        print(f"{k}={v} ", end="")
    print()

    # Check for same-bar multiple entries
    entry_bars = [t["entry_idx"] for t in trades]
    dup_bars = sum(1 for i in range(1, len(entry_bars)) if entry_bars[i] == entry_bars[i-1])
    print(f"    Same-bar consecutive entries: {dup_bars}")

    # Check for rapid-fire entries (within 2 bars)
    rapid = sum(1 for i in range(1, len(entry_bars)) if 0 < entry_bars[i] - entry_bars[i-1] <= 2)
    print(f"    Rapid-fire entries (within 2 bars): {rapid}")

    # Check for entries with tiny risk (sl very close to entry)
    tiny_risk = 0
    for t in trades:
        if t["dir"] == "long":
            risk = t["entry_price"] - t["sl"]
        else:
            risk = t["sl"] - t["entry_price"]
        if risk < 0.001 * t["entry_price"]:
            tiny_risk += 1
    print(f"    Entries with risk < 0.1% of price: {tiny_risk}")
