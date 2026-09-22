"""Monthly R distribution analysis for top OOS configs.
How lumpy is the equity curve?"""
import sys, time
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

import pandas as pd
from test_experiments_craze import build_module, _compute_swings
from engine.v18_params import SWING
from replay_harness import INSTRUMENT
from src.walker import FlowCandle

IST_OFFSET_SEC = 5 * 3600 + 30 * 60
UNSEEN_DIR = ROOT / "data" / "unseen" / "bybit"

CORE = {"mode": "atr_high", "atr_high_thresh": 0.65, "atr_low_thresh": 0.35,
        "sl_buf_atr": 0.01, "chop_thresh": 58.0, "cooldown_bars": 0,
        "max_consecutive_losses": 3, "ext_stop_r": 3.0,
        "exp_partial_r": 0.0, "window_end": "exit"}

TOP_CONFIGS = [
    ("wage10_wknd_bm09",  {"exp_wage_h": 10, "exp_skip_weekend": 1, "exp_bias_momentum_min": 0.9}),
    ("wage10_wknd_bm08",  {"exp_wage_h": 10, "exp_skip_weekend": 1, "exp_bias_momentum_min": 0.8}),
    ("wage10_wknd_bm05",  {"exp_wage_h": 10, "exp_skip_weekend": 1, "exp_bias_momentum_min": 0.5}),
    ("wage10_wknd_base",  {"exp_wage_h": 10, "exp_skip_weekend": 1}),
    ("wage10_wknd_bm06",  {"exp_wage_h": 10, "exp_skip_weekend": 1, "exp_bias_momentum_min": 0.6}),
    ("swpaus_bm09",       {"exp_swingpause": 1, "exp_bias_momentum_min": 0.9}),
    ("wage10_chop_wknd",  {"exp_wage_h": 10, "exp_chop15_lo": 55.0, "exp_chop15_hi": 61.0, "exp_skip_weekend": 1}),
    ("wage10_chop_bm09",  {"exp_wage_h": 10, "exp_chop15_lo": 55.0, "exp_chop15_hi": 61.0, "exp_bias_momentum_min": 0.9}),
    ("king_base",         {"exp_swingpause": 1, "exp_skip_weekend": 1, "exp_wage_h": 10,
                           "exp_chop15_lo": 55.0, "exp_chop15_hi": 61.0, "exp_atr_ratio_max": 1.4}),
]


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
    if not path.exists(): return []
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates(subset="timestamp", keep="last").reset_index(drop=True)
    df["ts"] = (df["timestamp"].astype("int64") // 10**9) - IST_OFFSET_SEC
    df = df[(df["ts"] >= ts_start) & (df["ts"] <= ts_end)]
    return [{"date": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "ts": int(r.ts),
             "open": float(r.open), "high": float(r.high),
             "low": float(r.low), "close": float(r.close)} for r in df.itertuples()]


def main():
    print("=" * 100)
    print("  MONTHLY R DISTRIBUTION — TOP OOS CONFIGS")
    print("=" * 100)

    (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
    fine = load_fine_1m(c1h[0]["ts"], c1h[-1]["ts"])
    sw10 = _compute_swings(f1h, "continuous", min_bars=10)
    sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
    sim = build_module()

    all_monthly = {}

    for cname, gates in TOP_CONFIGS:
        params = dict(CORE); params.update(gates)
        r = sim(c1h, sw10, c15, sw15, fine_ltf=fine, **params)
        trades = r["ltf_trades"] if isinstance(r, dict) else r

        # Monthly R
        monthly = defaultdict(lambda: {"n": 0, "net": 0.0, "rs": []})
        for t in trades:
            m = (t.get("exit_date") or t.get("entry_date") or "")[:7]
            monthly[m]["n"] += 1
            r_val = float(t["r_multiple"])
            monthly[m]["net"] += r_val
            monthly[m]["rs"].append(r_val)

        all_monthly[cname] = dict(monthly)

    # Print monthly table
    all_months = sorted(set(m for d in all_monthly.values() for m in d.keys()))
    print(f"\n  {'Month':<10}", end="")
    for cname, _ in TOP_CONFIGS:
        short = cname.replace("_base", "").replace("wage10_", "w10_").replace("wage10_chop_", "w10c_")
        print(f" {short:>10}", end="")
    print()
    print(f"  {'-' * (10 + 11 * len(TOP_CONFIGS))}")

    # Track per-config stats
    config_stats = {}
    for cname, _ in TOP_CONFIGS:
        config_stats[cname] = {"green": 0, "red": 0, "months": 0, "big_win": 0, "big_loss": 0,
                                "max_win": 0, "max_loss": 0, "rs": []}

    for m in all_months:
        print(f"  {m:<10}", end="")
        for cname, _ in TOP_CONFIGS:
            md = all_monthly[cname].get(m, {"net": 0, "n": 0, "rs": []})
            net = md["net"]
            st = config_stats[cname]
            st["months"] += 1
            st["rs"].extend(md["rs"])
            if net >= 0:
                st["green"] += 1
            else:
                st["red"] += 1
            if net > 5: st["big_win"] += 1
            if net < -5: st["big_loss"] += 1
            st["max_win"] = max(st["max_win"], net)
            st["max_loss"] = min(st["max_loss"], net)

            short = cname.replace("_base", "").replace("wage10_", "w10_").replace("wage10_chop_", "w10c_")
            if net >= 0:
                print(f" {net:>+9.1f}", end="")
            else:
                print(f" {net:>+9.1f}", end="")
        print()

    # Distribution stats
    print(f"\n{'='*100}")
    print(f"  MONTHLY R DISTRIBUTION STATS")
    print(f"{'='*100}")
    print(f"\n  {'Config':<25} {'Green%':>7} {'>5R':>5} {'<-5R':>5} {'MaxW':>7} {'MaxL':>7} {'Avg':>6} {'Med':>6} {'Std':>6} {'<-3R%':>7}")
    print(f"  {'-'*90}")

    for cname, _ in TOP_CONFIGS:
        st = config_stats[cname]
        rs_all = st["rs"]
        if not rs_all: continue
        avg = sum(rs_all) / len(rs_all)
        sorted_rs = sorted(rs_all)
        med = sorted_rs[len(sorted_rs)//2]
        variance = sum((r - avg)**2 for r in rs_all) / len(rs_all)
        std = variance ** 0.5
        neg3 = sum(1 for r in rs_all if r < -3) / len(rs_all) * 100

        green_pct = st["green"] / max(st["months"], 1) * 100
        print(f"  {cname:<25} {green_pct:>6.0f}% {st['big_win']:>5} {st['big_loss']:>5} {st['max_win']:>+6.1f}R {st['max_loss']:>+6.1f}R {avg:>+5.2f} {med:>+5.2f} {std:>5.2f} {neg3:>6.1f}%")

    # Underwater analysis per config
    print(f"\n{'='*100}")
    print(f"  UNDERWATER ANALYSIS (OOS)")
    print(f"{'='*100}")
    print(f"\n  {'Config':<25} {'MaxUW':>7} {'UW%':>6} {'R10DD':>7} {'R20DD':>7} {'R50DD':>7} {'ConsecLoss':>11}")
    print(f"  {'-'*75}")

    for cname, gates in TOP_CONFIGS:
        params = dict(CORE); params.update(gates)
        r = sim(c1h, sw10, c15, sw15, fine_ltf=fine, **params)
        trades = r["ltf_trades"] if isinstance(r, dict) else r
        rs = [float(t["r_multiple"]) for t in trades]
        eq = []; c = 0.0
        for rv in rs: c += rv; eq.append(c)

        # Max consecutive loss
        streak = 0; mx_loss = 0
        for rv in rs:
            if rv <= 0: streak += 1; mx_loss = max(mx_loss, streak)
            else: streak = 0

        # Underwater
        peak = 0; max_uw = 0; uw_count = 0
        cur_uw = 0
        for cv in eq:
            if cv > peak: peak = cv; cur_uw = 0
            else: cur_uw += 1
            max_uw = max(max_uw, cur_uw)
            if cur_uw > 0: uw_count += 1
        uw_pct = uw_count / max(len(eq), 1) * 100

        # Rolling DDs
        def rdd(eq, w):
            mx = 0
            for i in range(len(eq)):
                s = max(0, i - w + 1)
                mx = max(mx, max(eq[s:i+1]) - eq[i])
            return mx

        r10 = rdd(eq, 10) if len(eq) >= 10 else 0
        r20 = rdd(eq, 20) if len(eq) >= 20 else 0
        r50 = rdd(eq, 50) if len(eq) >= 50 else 0

        print(f"  {cname:<25} {max_uw:>6}t {uw_pct:>5.0f}% {r10:>6.1f}R {r20:>6.1f}R {r50:>6.1f}R {mx_loss:>10}t")

    # Top 5 trades per config
    print(f"\n{'='*100}")
    print(f"  TOP 5 + BOTTOM 5 TRADES (how lumpy?)")
    print(f"{'='*100}")

    for cname, gates in TOP_CONFIGS:
        params = dict(CORE); params.update(gates)
        r = sim(c1h, sw10, c15, sw15, fine_ltf=fine, **params)
        trades = r["ltf_trades"] if isinstance(r, dict) else r
        sorted_t = sorted(trades, key=lambda t: float(t["r_multiple"]), reverse=True)
        top5 = sorted_t[:5]
        bot5 = sorted_t[-5:]
        top5_r = sum(float(t["r_multiple"]) for t in top5)
        bot5_r = sum(float(t["r_multiple"]) for t in bot5)
        total = sum(float(t["r_multiple"]) for t in trades)
        top5_pct = top5_r / max(abs(total), 0.01) * 100

        print(f"\n  {cname}:")
        top_strs = ["{:+.1f}R".format(float(t["r_multiple"])) for t in top5]
        bot_strs = ["{:+.1f}R".format(float(t["r_multiple"])) for t in bot5]
        print("    Top 5:  {}  = {:+.1f}R ({:.0f}% of total)".format(", ".join(top_strs), top5_r, top5_pct))
        print("    Bot 5:  {}  = {:+.1f}R".format(", ".join(bot_strs), bot5_r))


if __name__ == "__main__":
    main()
