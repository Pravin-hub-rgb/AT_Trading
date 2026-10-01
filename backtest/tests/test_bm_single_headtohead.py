"""Head-to-head OOS comparison: all viable single configs.
IS + OOS side by side, yearly, DD, smoothness, equity curves."""
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

# All viable single configs
CONFIGS = {
    "king_single": {
        "desc": "king single (all gates)",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 0,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_skip_weekend": 1, "exp_wage_h": 10,
                    "exp_chop15_lo": 55.0, "exp_chop15_hi": 61.0,
                    "exp_atr_ratio_max": 1.4, "window_end": "exit"},
    },
    "bare_wage10": {
        "desc": "bare + wage10 (no swing/wknd/chop)",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 0,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_wage_h": 10,
                    "window_end": "exit"},
    },
    "bare_wage10_bm05": {
        "desc": "bare + wage10 + bm0.5",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 0,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_wage_h": 10,
                    "exp_bias_momentum_min": 0.5,
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
    "bare_wage10_bm07": {
        "desc": "bare + wage10 + bm0.7",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 0,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_wage_h": 10,
                    "exp_bias_momentum_min": 0.7,
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
    peak = 0.0; cum = 0.0; dd = 0.0; mx_cur = 0; mx_streak = 0
    for r in rs:
        cum += r
        if cum > peak: peak = cum
        dd = max(dd, peak - cum)
        if r > 0: mx_cur += 1; mx_streak = max(mx_streak, mx_cur)
        else: mx_cur = 0
    ndd = abs(net / dd) if dd > 0 else 0
    avg = net / max(n, 1)

    # Rolling 10t maxDD
    eq = []; c = 0.0
    for r in rs: c += r; eq.append(c)
    r10 = []
    for i in range(len(eq)):
        s = max(0, i - 9)
        r10.append(max(eq[s:i+1]) - eq[i])

    # Yearly
    yearly = defaultdict(lambda: {"n": 0, "net": 0.0, "wins": 0, "rs": []})
    for t in trades:
        y = (t.get("exit_date") or t.get("entry_date") or "")[:4]
        yearly[y]["n"] += 1
        r = float(t["r_multiple"])
        yearly[y]["net"] += r
        yearly[y]["rs"].append(r)
        if r > 0: yearly[y]["wins"] += 1

    return {
        "n": n, "net": net, "wr": wr, "dd": dd, "ndd": ndd, "avg": avg,
        "yearly": dict(yearly), "r10_max": max(r10), "mx_streak": mx_streak,
    }


def equity_ascii(trades, width=70, height=20):
    rs = [float(t["r_multiple"]) for t in trades]
    eq = []; c = 0.0
    for r in rs: c += r; eq.append(c)
    if not eq: return ""
    mn = min(eq); mx = max(eq); rng = mx - mn
    if rng == 0: return ""
    lines = []
    for row in range(height - 1, -1, -1):
        threshold = mn + rng * row / (height - 1)
        line = ""
        for i, v in enumerate(eq):
            idx = int((v - mn) / rng * (height - 1) + 0.5)
            if idx == row:
                line += "*"
            else:
                line += " "
        lines.append(line)
    return "\n".join(lines)


def main():
    print("=" * 90)
    print("  HEAD-TO-HEAD: IS + OOS comparison of all viable single configs")
    print("=" * 90)

    # Load IS data
    from run_experiment import get_data
    is_data = get_data()

    # Load OOS data
    print("\n  Loading OOS data...")
    (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
    ts_start = c1h[0]["ts"]; ts_end = c1h[-1]["ts"]
    fine_oos = load_fine_1m(ts_start, ts_end)
    sw10_oos = _compute_swings(f1h, "continuous", min_bars=10)
    sw15_oos = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
    print(f"  OOS: c1h={len(c1h)}, c15={len(c15)}, fine={len(fine_oos)}")

    sim = build_module()

    all_results = {}
    for cname, cfg in CONFIGS.items():
        p = cfg["params"]

        # IS
        t0 = time.time()
        r = sim(is_data["c1h"], is_data["sw10"], is_data["c15"], is_data["sw15"],
                fine_ltf=is_data["fine"], **p)
        trades_is = r["ltf_trades"] if isinstance(r, dict) else r
        dt_is = time.time() - t0
        is_res = analyze(trades_is, cfg["desc"])

        # OOS
        t0 = time.time()
        r = sim(c1h, sw10_oos, c15, sw15_oos, fine_ltf=fine_oos, **p)
        trades_oos = r["ltf_trades"] if isinstance(r, dict) else r
        dt_oos = time.time() - t0
        oos_res = analyze(trades_oos, cfg["desc"])

        all_results[cname] = {
            "desc": cfg["desc"],
            "is": is_res, "oos": oos_res,
            "trades_is": trades_is, "trades_oos": trades_oos,
            "dt_is": dt_is, "dt_oos": dt_oos,
        }

    # Summary table
    print(f"\n{'='*90}")
    print(f"  SIDE-BY-SIDE COMPARISON")
    print(f"{'='*90}")
    print(f"\n  {'Config':<35} {'IS':>5} {'IS NET':>8} {'IS DD':>6} {'IS N/D':>6} {'OOS':>5} {'OOS NET':>8} {'OOS DD':>6} {'OOS N/D':>7}")
    print(f"  {'-'*95}")

    for cname, res in all_results.items():
        d = res["desc"]
        i = res["is"]; o = res["oos"]
        print(f"  {d:<35} {i['n']:>4}t {i['net']:>+7.1f}R {i['dd']:>5.1f} {i['ndd']:>5.2f}  {o['n']:>4}t {o['net']:>+7.1f}R {o['dd']:>5.1f} {o['ndd']:>6.2f}")

    # Yearly OOS breakdown
    print(f"\n{'='*90}")
    print(f"  YEARLY OOS BREAKDOWN")
    print(f"{'='*90}")
    all_years = set()
    for res in all_results.values():
        all_years.update(res["oos"]["yearly"].keys())

    print(f"\n  {'Config':<35}", end="")
    for y in sorted(all_years):
        print(f" {y:>8}", end="")
    print(f" {'TOTAL':>8}")
    print(f"  {'-'*65}")

    for cname, res in all_results.items():
        d = res["desc"]
        print(f"  {d:<35}", end="")
        total = 0
        for y in sorted(all_years):
            yd = res["oos"]["yearly"].get(y, {"net": 0, "n": 0})
            total += yd["net"]
            print(f" {yd['net']:>+7.1f}R", end="")
        print(f" {total:>+7.1f}R")

    # Monthly OOS for best 2 configs
    print(f"\n{'='*90}")
    print(f"  MONTHLY OOS DETAIL")
    print(f"{'='*90}")
    for cname, res in all_results.items():
        oos = res["oos"]
        monthly = defaultdict(lambda: {"n": 0, "net": 0.0})
        for t in res["trades_oos"]:
            m = (t.get("exit_date") or t.get("entry_date") or "")[:7]
            monthly[m]["n"] += 1
            monthly[m]["net"] += float(t["r_multiple"])

        print(f"\n  {res['desc']}:")
        pos_m = 0; neg_m = 0
        for m in sorted(monthly.keys()):
            d = monthly[m]
            if d["net"] >= 0: pos_m += 1
            else: neg_m += 1
            bar = "+" * min(int(d["net"]), 40) if d["net"] > 0 else "-" * min(int(-d["net"]), 40)
            print(f"    {m}: {d['n']:>3}t {d['net']:>+7.1f}R  {bar}")
        print(f"    Green months: {pos_m}/{pos_m+neg_m} ({pos_m/(pos_m+neg_m)*100:.0f}%)")

    # Smoothness comparison
    print(f"\n{'='*90}")
    print(f"  SMOOTHNESS (OOS)")
    print(f"{'='*90}")
    print(f"\n  {'Config':<35} {'R10 maxDD':>10} {'MaxStreak':>10} {'AvgR':>7}")
    print(f"  {'-'*65}")
    for cname, res in all_results.items():
        o = res["oos"]
        print(f"  {res['desc']:<35} {o['r10_max']:>9.1f}R {o['mx_streak']:>9} {o['avg']:>+6.3f}")

    # Equity curves (ASCII)
    print(f"\n{'='*90}")
    print(f"  EQUITY CURVES (OOS)")
    print(f"{'='*90}")
    for cname, res in all_results.items():
        eq_str = equity_ascii(res["trades_oos"], width=80, height=15)
        print(f"\n  {res['desc']}:")
        if eq_str:
            for line in eq_str.split("\n"):
                print(f"  |{line}")
        print(f"  +{'─' * 80}")

    # Final ranking
    print(f"\n{'='*90}")
    print(f"  RANKING BY OOS NET/DD (primary) + OOS NET (secondary)")
    print(f"{'='*90}")
    ranked = sorted(all_results.items(), key=lambda x: (-x[1]["oos"]["ndd"], -x[1]["oos"]["net"]))
    for rank, (cname, res) in enumerate(ranked, 1):
        o = res["oos"]
        marker = " ★" if rank == 1 else ""
        print(f"  #{rank}  {res['desc']:<35}  NET/DD={o['ndd']:.2f}  NET={o['net']:+.1f}R  DD={o['dd']:.1f}R  WR={o['wr']:.0f}%{marker}")


if __name__ == "__main__":
    main()
