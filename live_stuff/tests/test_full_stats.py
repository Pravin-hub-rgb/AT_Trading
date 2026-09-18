"""Collect comprehensive stats for ALL experiment configurations."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from test_experiments import simulate_v18_experiments, run_and_report
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.walker import FlowCandle
import statistics, json

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

def full_stats(name, trades, baseline_r=238.0):
    if not trades:
        return {}
    r_vals = [t["r_multiple"] for t in trades]
    wins = [r for r in r_vals if r > 0]
    losses = [r for r in r_vals if r <= 0]
    n = len(r_vals)
    total_r = sum(r_vals)
    wr = len(wins) / n * 100
    avg_win = statistics.mean(wins) if wins else 0
    avg_loss = statistics.mean(losses) if losses else 0
    pf = sum(wins) / abs(sum(losses)) if sum(losses) != 0 else float('inf')

    # Max DD
    cum, peak, dd = 0, 0, 0
    max_dd = 0
    for r in r_vals:
        cum += r
        if cum > peak: peak = cum
        dd = peak - cum
        if dd > max_dd: max_dd = dd

    # Win/loss streaks
    streak = 0
    max_win_streak = 0
    max_loss_streak = 0
    for r in r_vals:
        if r > 0:
            streak = streak + 1 if streak > 0 else 1
            max_win_streak = max(max_win_streak, streak)
        else:
            streak = streak - 1 if streak < 0 else -1
            max_loss_streak = max(max_loss_streak, abs(streak))

    # Avg risk in USD
    risks = []
    for t in trades:
        if t["dir"] == "long":
            risk = t["entry_price"] - t["sl"]
        else:
            risk = t["sl"] - t["entry_price"]
        if risk > 0: risks.append(risk)
    avg_risk_usd = statistics.mean(risks) if risks else 0

    # Trade frequency
    ts = [t["entry_ts"] for t in trades]
    total_days = (ts[-1] - ts[0]) / 86400000 if len(ts) > 1 else 1
    trades_per_month = n / (total_days / 30) if total_days > 0 else 0

    # R distribution
    r_ranges = [(-99, -3), (-3, -2), (-2, -1), (-1, -0.5), (-0.5, 0),
                (0, 0.5), (0.5, 1), (1, 2), (2, 3), (3, 5), (5, 10), (10, 99)]
    r_dist = {}
    for lo, hi in r_ranges:
        cnt = sum(1 for r in r_vals if lo <= r < hi)
        if cnt > 0:
            r_dist[f"[{lo:+.0f},{hi:+.0f})"] = cnt

    # Outcome counts
    outcomes = {}
    for t in trades:
        outcomes[t["outcome"]] = outcomes.get(t["outcome"], 0) + 1

    return {
        "name": name,
        "trades": n,
        "total_r": round(total_r, 1),
        "delta_r": round(total_r - baseline_r, 1),
        "wr": round(wr, 1),
        "pf": round(pf, 2),
        "avg_win_r": round(avg_win, 2),
        "avg_loss_r": round(avg_loss, 2),
        "avg_r_per_trade": round(total_r / n, 3),
        "max_dd_r": round(max_dd, 1),
        "max_win_streak": max_win_streak,
        "max_loss_streak": max_loss_streak,
        "avg_risk_usd": round(avg_risk_usd, 0),
        "trades_per_month": round(trades_per_month, 0),
        "r_distribution": r_dist,
        "outcomes": outcomes,
    }

c15, f15 = load_swing("15m")
c1h, f1h = load_swing("1h")
fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                     max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=SYMBOL)

configs = []

# 1. BASELINE
sw1h = _compute_swings(f1h, "continuous", min_bars=20)
sw15 = _compute_swings(f15, "continuous", min_bars=50)
tr = simulate_v18_experiments(c1h, sw1h, c15, sw15, fine,
    sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=58.0,
    cooldown_bars=10, max_consecutive_losses=3)["ltf_trades"]
configs.append(full_stats("v18 BASELINE (mb1h=20, mb15=50, chop=58, sl=0.01, cd=10, mcl=3, es=1.5)", tr))

# 2. Multi-LTF cd=0
sw1h = _compute_swings(f1h, "continuous", min_bars=20)
sw15 = _compute_swings(f15, "continuous", min_bars=50)
tr = simulate_v18_experiments(c1h, sw1h, c15, sw15, fine,
    sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=58.0,
    cooldown_bars=10, max_consecutive_losses=3,
    exp_multi_ltf=True, exp_multi_ltf_cd=0)["ltf_trades"]
configs.append(full_stats("Multi-LTF cd=0 (mb1h=20, chop=58)", tr))

# 3. Multi-LTF cd=5
tr = simulate_v18_experiments(c1h, sw1h, c15, sw15, fine,
    sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=58.0,
    cooldown_bars=10, max_consecutive_losses=3,
    exp_multi_ltf=True, exp_multi_ltf_cd=5)["ltf_trades"]
configs.append(full_stats("Multi-LTF cd=5 (mb1h=20, chop=58)", tr))

# 4. Persist=5
tr = simulate_v18_experiments(c1h, sw1h, c15, sw15, fine,
    sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=58.0,
    cooldown_bars=10, max_consecutive_losses=3,
    exp_regime_persist=5)["ltf_trades"]
configs.append(full_stats("Persist=5 (mb1h=20, chop=58, cd=10)", tr))

# 5. Multi-LTF + Persist=5, cd=10
tr = simulate_v18_experiments(c1h, sw1h, c15, sw15, fine,
    sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=58.0,
    cooldown_bars=10, max_consecutive_losses=3,
    exp_multi_ltf=True, exp_multi_ltf_cd=10,
    exp_regime_persist=5)["ltf_trades"]
configs.append(full_stats("Multi-LTF + Persist=5, cd=10 (mb1h=20, chop=58)", tr))

# 6. mb1h=10 (SAFE CHANGE)
sw1h_10 = _compute_swings(f1h, "continuous", min_bars=10)
tr = simulate_v18_experiments(c1h, sw1h_10, c15, sw15, fine,
    sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=58.0,
    cooldown_bars=10, max_consecutive_losses=3)["ltf_trades"]
configs.append(full_stats("mb1h=10 only (rest=baseline)", tr))

# 7. mb1h=10 + chop=55
tr = simulate_v18_experiments(c1h, sw1h_10, c15, sw15, fine,
    sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=55.0,
    cooldown_bars=10, max_consecutive_losses=3)["ltf_trades"]
configs.append(full_stats("mb1h=10 + chop=55 (rest=baseline)", tr))

# 8. mb1h=10 + chop=55 + persist=2
tr = simulate_v18_experiments(c1h, sw1h_10, c15, sw15, fine,
    sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=55.0,
    cooldown_bars=10, max_consecutive_losses=3,
    exp_regime_persist=2)["ltf_trades"]
configs.append(full_stats("mb1h=10 + chop=55 + persist=2 (rest=baseline)", tr))

# 9. SAFE COMBO: mb1h=10 + chop=55 + persist=2 + cd=10
tr = simulate_v18_experiments(c1h, sw1h_10, c15, sw15, fine,
    sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=55.0,
    cooldown_bars=10, max_consecutive_losses=3,
    exp_regime_persist=2)["ltf_trades"]
configs.append(full_stats("SAFE: mb1h=10, chop=55, persist=2, cd=10", tr))

# 10. OPTIMAL cd=0: mb1h=10 + chop=55 + persist=2 + cd=0
tr = simulate_v18_experiments(c1h, sw1h_10, c15, sw15, fine,
    sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=55.0,
    cooldown_bars=0, max_consecutive_losses=3,
    exp_multi_ltf=True, exp_multi_ltf_cd=0,
    exp_regime_persist=2)["ltf_trades"]
configs.append(full_stats("OPTIMAL: mb1h=10, chop=55, persist=2, cd=0, sl=0.01", tr))

# 11. OPTIMAL cd=0 + sl=0.001 (MAX R)
tr = simulate_v18_experiments(c1h, sw1h_10, c15, sw15, fine,
    sl_buf_atr=0.001, ext_stop_r=1.5, chop_thresh=55.0,
    cooldown_bars=0, max_consecutive_losses=3,
    exp_multi_ltf=True, exp_multi_ltf_cd=0,
    exp_regime_persist=2)["ltf_trades"]
configs.append(full_stats("MAX R: mb1h=10, chop=55, persist=2, cd=0, sl=0.001", tr))

# 12. OPTIMAL cd=5 (middle ground)
tr = simulate_v18_experiments(c1h, sw1h_10, c15, sw15, fine,
    sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=55.0,
    cooldown_bars=5, max_consecutive_losses=3,
    exp_multi_ltf=True, exp_multi_ltf_cd=5,
    exp_regime_persist=2)["ltf_trades"]
configs.append(full_stats("MIDDLE: mb1h=10, chop=55, persist=2, cd=5, sl=0.01", tr))

# 13. Dual-active windows
tr = simulate_v18_experiments(c1h, sw1h, c15, sw15, fine,
    sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=58.0,
    cooldown_bars=10, max_consecutive_losses=3,
    exp_dual_active=True)["ltf_trades"]
configs.append(full_stats("Dual-active windows (mb1h=20, chop=58)", tr))

# 14. Adaptive halt
tr = simulate_v18_experiments(c1h, sw1h, c15, sw15, fine,
    sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=58.0,
    cooldown_bars=10, max_consecutive_losses=3,
    exp_adaptive_halt=True)["ltf_trades"]
configs.append(full_stats("Adaptive halt (mb1h=20, chop=58)", tr))

# 15. TOD filter 00-04
tr = simulate_v18_experiments(c1h, sw1h, c15, sw15, fine,
    sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=58.0,
    cooldown_bars=10, max_consecutive_losses=3,
    exp_tod_filter=True)["ltf_trades"]
configs.append(full_stats("TOD filter 00-04 (mb1h=20, chop=58)", tr))

# Print table
print("=" * 180)
print(f"{'Config':<65} {'Trades':>6} {'TotalR':>8} {'Delta':>8} {'WR':>6} {'PF':>5} {'AvgW':>6} {'AvgL':>6} {'R/trade':>8} {'MaxDD':>6} {'WStr':>5} {'LStr':>5} {'Risk$':>7} {'Tr/mo':>6}")
print("=" * 180)
for c in configs:
    print(f"{c['name']:<65} {c['trades']:>6} {c['total_r']:>+8.1f} {c['delta_r']:>+8.1f} {c['wr']:>5.1f}% {c['pf']:>5.2f} {c['avg_win_r']:>+6.2f} {c['avg_loss_r']:>+6.2f} {c['avg_r_per_trade']:>+8.3f} {c['max_dd_r']:>5.1f}R {c['max_win_streak']:>5} {c['max_loss_streak']:>5} ${c['avg_risk_usd']:>6.0f} {c['trades_per_month']:>6.0f}")

# Print JSON for doc reference
with open("experiment_results.json", "w") as f:
    json.dump(configs, f, indent=2)
print("\nSaved to experiment_results.json")
