"""OOS validation: bare + wage10 + bm0.6 on 2021-2022 unseen data."""
import sys, time
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

import pandas as pd
from test_experiments_craze import build_module, _compute_swings
from engine.v18_params import SWING
from replay_harness import INSTRUMENT
from src.walker import FlowCandle

IST_OFFSET_SEC = 5 * 3600 + 30 * 60
UNSEEN_DIR = ROOT / "data" / "unseen" / "bybit"

CONFIGS = {
    "bare_wage10_base": {
        "desc": "bare + wage10 (no bm)",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 0,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_wage_h": 10,
                    "window_end": "exit"},
    },
    "bare_wage10_bm06": {
        "desc": "bare + wage10 + bm0.6",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 0,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_wage_h": 10,
                    "exp_bias_momentum_min": 0.6,
                    "window_end": "exit"},
    },
}


def load_unseen(tf):
    path = UNSEEN_DIR / f"BTCUSDT_{tf}.csv"
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates(subset="timestamp", keep="last").reset_index(drop=True)
    df["ts"] = (df["timestamp"].astype("int64") // 10**9) - IST_OFFSET_SEC
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({"date": date, "ts": int(row.ts), "open": float(row.open),
                        "high": float(row.high), "low": float(row.low), "close": float(row.close)})
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high),
                               low=float(row.low), close=float(row.close)))
    return candles, flow


def load_fine_1m(ts_start, ts_end):
    path = UNSEEN_DIR / "BTCUSDT_1m.csv"
    if not path.exists():
        return []
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates(subset="timestamp", keep="last").reset_index(drop=True)
    df["ts"] = (df["timestamp"].astype("int64") // 10**9) - IST_OFFSET_SEC
    df = df[(df["ts"] >= ts_start) & (df["ts"] <= ts_end)]
    return [{"date": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "ts": int(r.ts),
             "open": float(r.open), "high": float(r.high),
             "low": float(r.low), "close": float(r.close)} for r in df.itertuples()]


def analyze(trades, label):
    rs = [float(t["r_multiple"]) for t in trades]
    n = len(rs)
    net = sum(rs)
    wins = sum(1 for r in rs if r > 0)
    wr = wins / max(n, 1) * 100
    peak = 0.0; cum = 0.0; dd = 0.0
    for r in rs:
        cum += r
        if cum > peak: peak = cum
        dd = max(dd, peak - cum)
    ndd = abs(net / dd) if dd > 0 else 0
    avg = net / max(n, 1)

    yearly = defaultdict(lambda: {"n": 0, "net": 0.0})
    for t in trades:
        y = (t.get("exit_date") or t.get("entry_date") or "")[:4]
        yearly[y]["n"] += 1
        yearly[y]["net"] += float(t["r_multiple"])

    top5 = sorted(trades, key=lambda t: float(t["r_multiple"]), reverse=True)[:5]
    top5_r = sum(float(t["r_multiple"]) for t in top5)

    print(f"\n  {label}")
    print(f"  Trades:       {n}")
    print(f"  NET R:        {net:+.1f}R")
    print(f"  Avg R/trade:  {avg:+.3f}R")
    print(f"  Win Rate:     {wr:.1f}%")
    print(f"  Max DD:       {dd:.1f}R")
    print(f"  NET/DD:       {ndd:.2f}")
    print(f"  Top 5 contribute: {top5_r:.1f}R out of {net:.1f}R ({top5_r/max(net,0.01)*100:.0f}%)")

    print(f"\n  YEARLY OOS:")
    for y in sorted(yearly.keys()):
        d = yearly[y]
        print(f"    {y}:  {d['n']:>3}t  {d['net']:>+7.1f}R")

    return n, net, dd, wr


def main():
    print("=" * 80)
    print("  OOS VALIDATION (2021-2022): bare + wage10 + bm0.6")
    print("=" * 80)

    print("  Loading OOS data...")
    (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
    ts_start = c1h[0]["ts"]
    ts_end = c1h[-1]["ts"]
    fine = load_fine_1m(ts_start, ts_end)
    print(f"  c1h: {len(c1h)} candles, c15: {len(c15)}, fine: {len(fine)}")

    sw10 = _compute_swings(f1h, "continuous", min_bars=10)
    sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
    print(f"  sw10: {len(sw10)} swings, sw15: {len(sw15)} swings")

    sim = build_module()

    results = {}
    for cname, cfg in CONFIGS.items():
        t0 = time.time()
        params = dict(cfg["params"])
        r = sim(c1h, sw10, c15, sw15, fine_ltf=fine, **params)
        trades = r["ltf_trades"] if isinstance(r, dict) else r
        dt = time.time() - t0
        n, net, dd, wr = analyze(trades, f"{cfg['desc']}  [{dt:.1f}s]")
        results[cname] = {"n": n, "net": net, "dd": dd, "wr": wr}

    # Comparison
    print(f"\n{'='*80}")
    print(f"  OOS COMPARISON")
    print(f"{'='*80}")
    base = results["bare_wage10_base"]
    bm06 = results["bare_wage10_bm06"]
    print(f"\n  {'Config':<35} {'n':>4} {'OOS NET':>8} {'DD':>6} {'WR':>5} {'NET/DD':>7}")
    print(f"  {'-'*70}")
    print(f"  {'bare + wage10 (no bm)':<35} {base['n']:>4} {base['net']:>+7.1f}R {base['dd']:>5.1f} {base['wr']:>4.1f}% {abs(base['net']/base['dd']) if base['dd']>0 else 0:>6.2f}")
    print(f"  {'bare + wage10 + bm0.6':<35} {bm06['n']:>4} {bm06['net']:>+7.1f}R {bm06['dd']:>5.1f} {bm06['wr']:>4.1f}% {abs(bm06['net']/bm06['dd']) if bm06['dd']>0 else 0:>6.2f}")
    print(f"  {'Delta':<35} {bm06['n']-base['n']:>+4} {bm06['net']-base['net']:>+7.1f}R {bm06['dd']-base['dd']:>+5.1f}")


if __name__ == "__main__":
    main()
