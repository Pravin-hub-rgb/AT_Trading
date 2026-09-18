"""Collect combo stats + walk-forward stats."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from test_experiments import simulate_v18_experiments
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.walker import FlowCandle
import statistics, bisect, json

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
    if not trades: return {}
    r_vals = [t["r_multiple"] for t in trades]
    wins = [r for r in r_vals if r > 0]
    losses = [r for r in r_vals if r <= 0]
    n = len(r_vals)
    total_r = sum(r_vals)
    wr = len(wins) / n * 100
    avg_win = statistics.mean(wins) if wins else 0
    avg_loss = statistics.mean(losses) if losses else 0
    pf = sum(wins) / abs(sum(losses)) if sum(losses) != 0 else float('inf')
    cum, peak, max_dd = 0, 0, 0
    for r in r_vals:
        cum += r
        peak = max(peak, cum)
        max_dd = max(max_dd, peak - cum)
    streak = 0
    mws, mls = 0, 0
    for r in r_vals:
        if r > 0:
            streak = streak + 1 if streak > 0 else 1
            mws = max(mws, streak)
        else:
            streak = streak - 1 if streak < 0 else -1
            mls = max(mls, abs(streak))
    ts = [t["entry_ts"] for t in trades]
    total_days = (ts[-1] - ts[0]) / 86400000 if len(ts) > 1 else 1
    return {
        "name": name, "trades": n, "total_r": round(total_r, 1),
        "delta_r": round(total_r - baseline_r, 1), "wr": round(wr, 1), "pf": round(pf, 2),
        "avg_win_r": round(avg_win, 2), "avg_loss_r": round(avg_loss, 2),
        "max_dd_r": round(max_dd, 1), "max_win_streak": mws, "max_loss_streak": mls,
        "trades_per_month": round(n / (total_days / 30) if total_days > 0 else 0, 0),
    }

c15, f15 = load_swing("15m")
c1h, f1h = load_swing("1h")
fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                     max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=SYMBOL)
sw1h = _compute_swings(f1h, "continuous", min_bars=10)
sw15 = _compute_swings(f15, "continuous", min_bars=50)
sw1h_20 = _compute_swings(f1h, "continuous", min_bars=20)
sw15_50 = _compute_swings(f15, "continuous", min_bars=50)

results = {}

# === COMBOS ===
combos = [
    ("Multi-LTF+Persist=5 (cd=10, mb1h=20)", dict(mb1h=20, chop=58, cd=10, p=5, mltf=True, cd_ml=10)),
    ("Multi-LTF+Persist=3 (cd=10, mb1h=20)", dict(mb1h=20, chop=58, cd=10, p=3, mltf=True, cd_ml=10)),
    ("Multi-LTF+Persist=5 (cd=10, mb1h=10)", dict(mb1h=10, chop=55, cd=10, p=5, mltf=True, cd_ml=10)),
    ("OPTIMAL cd=0 sl=0.01", dict(mb1h=10, chop=55, cd=0, p=2, mltf=True, cd_ml=0)),
    ("OPTIMAL cd=0 sl=0.001", dict(mb1h=10, chop=55, cd=0, p=2, mltf=True, cd_ml=0)),
    ("MIDDLE cd=5 sl=0.01", dict(mb1h=10, chop=55, cd=5, p=2, mltf=True, cd_ml=5)),
]

for name, p in combos:
    sw1h_c = _compute_swings(f1h, "continuous", min_bars=p["mb1h"])
    tr = simulate_v18_experiments(c1h, sw1h_c, c15, sw15, fine,
        sl_buf_atr=0.01 if "sl=0.01" in name or "cd=" in name else 0.001,
        ext_stop_r=1.5, chop_thresh=p["chop"],
        cooldown_bars=p["cd"], max_consecutive_losses=3,
        exp_multi_ltf=p["mltf"], exp_multi_ltf_cd=p["cd_ml"],
        exp_regime_persist=p["p"])["ltf_trades"]
    results[name] = full_stats(name, tr)

# === WALK-FORWARD: rolling 4-window ===
def get_slice(c15, f15, c1h, f1h, start_pct, end_pct):
    n = len(c15)
    s, e = int(n * start_pct), int(n * end_pct)
    ts_s, ts_e = c15[s]["ts"], c15[e - 1]["ts"]
    htf_ts = [c["ts"] for c in c1h]
    hs = min(bisect.bisect_left(htf_ts, ts_s), len(c1h) - 1)
    he = min(bisect.bisect_right(htf_ts, ts_e), len(c1h))
    return c15[s:e], f15[s:e], c1h[hs:he], f1h[hs:he]

windows = [(0.00, 0.25), (0.25, 0.50), (0.50, 0.75), (0.75, 1.00)]
wf_results = {}
for cfg_name, params, mb_1h, mb_15 in [
    ("BASELINE", dict(sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=58.0, cooldown_bars=10, max_consecutive_losses=3), 20, 50),
    ("OPTIMAL-cd0", dict(sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=55.0, cooldown_bars=0, max_consecutive_losses=3, exp_multi_ltf=True, exp_multi_ltf_cd=0, exp_regime_persist=2), 10, 50),
]:
    wf_results[cfg_name] = []
    for wi, (s, e) in enumerate(windows):
        c15_s, f15_s, c1h_s, f1h_s = get_slice(c15, f15, c1h, f1h, s, e)
        fine_s = _load_fine_1m(c15_s[0]["ts"], c15_s[-1]["ts"], symbol=SYMBOL)
        sw15_s = _compute_swings(f15_s, "continuous", min_bars=mb_15)
        sw1h_s = _compute_swings(f1h_s, "continuous", min_bars=mb_1h)
        tr = simulate_v18_experiments(c1h_s, sw1h_s, c15_s, sw15_s, fine_s, **params)["ltf_trades"]
        r_vals = [t["r_multiple"] for t in tr]
        wins = sum(1 for r in r_vals if r > 0)
        cum, peak, dd = 0, 0, 0
        for r in r_vals:
            cum += r
            peak = max(peak, cum)
            dd = max(dd, peak - cum)
        dates = f"{c15_s[0]['date'][:10]} to {c15_s[-1]['date'][:10]}"
        wf_results[cfg_name].append({
            "window": wi+1, "period": dates, "trades": len(tr),
            "r": round(sum(r_vals), 1), "wr": round(wins/len(tr)*100, 1) if tr else 0,
            "max_dd": round(dd, 1),
        })

# Save all
output = {"combos": results, "walk_forward": wf_results}
with open("experiment_combos_wf.json", "w") as f:
    json.dump(output, f, indent=2)

# Print combos
print("COMBO RESULTS:")
print(f"{'Config':<55} {'Trades':>6} {'TotalR':>8} {'Delta':>8} {'WR':>6} {'PF':>5} {'MaxDD':>6}")
print("=" * 100)
for name, s in results.items():
    if s:
        print(f"{s['name']:<55} {s['trades']:>6} {s['total_r']:>+8.1f} {s['delta_r']:>+8.1f} {s['wr']:>5.1f}% {s['pf']:>5.2f} {s['max_dd_r']:>5.1f}R")

# Print walk-forward
print("\nROLLING WALK-FORWARD:")
for cfg, wins in wf_results.items():
    print(f"\n  {cfg}:")
    for w in wins:
        print(f"    Q{w['window']} {w['period']:>30}  {w['trades']:>4}t  {w['r']:>+7.1f}R  WR {w['wr']:>5.1f}%  DD {w['max_dd']:>5.1f}R")
    total_r = sum(w["r"] for w in wins)
    print(f"    {'TOTAL':>42}  {'':>4}   {total_r:>+7.1f}R")
