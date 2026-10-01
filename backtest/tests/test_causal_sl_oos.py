"""Causal SL on OOS 2021-2022 — batch vs causal for top 3 configs."""
import sys, time
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import build_module, _compute_swings, stats
from engine.v18_params import SWING, get_v18_params
from src.btc.btc_routes import _trade_costs
from src.walker import FlowCandle
from run_experiment import fund, INSTRUMENT
import pandas as pd

_g = get_v18_params(INSTRUMENT)
IST_OFFSET_SEC = 5 * 3600 + 30 * 60
UNSEEN_DIR = ROOT / "data" / "unseen" / "bybit"

CONFIGS = {
    "champion_multi": {
        "desc": "champion_multi_sw10",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65, "atr_low_thresh": 0.35,
                    "sl_buf_atr": 0.01, "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True, "exp_persist": 7, "window_end": "exit"},
        "swing": "sw10",
    },
    "utcsat_multi": {
        "desc": "utcsat_multi_sw10",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65, "atr_low_thresh": 0.35,
                    "sl_buf_atr": 0.01, "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True, "exp_persist": 7,
                    "exp_skip_utc_sat": 1, "window_end": "exit"},
        "swing": "sw10",
    },
    "king_single": {
        "desc": "king_single_sw10",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65, "atr_low_thresh": 0.35,
                    "sl_buf_atr": 0.01, "chop_thresh": 58.0, "cooldown_bars": 0,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1, "exp_skip_weekend": 1,
                    "exp_wage_h": 10, "exp_chop15_lo": 55.0, "exp_chop15_hi": 61.0,
                    "exp_atr_ratio_max": 1.4, "window_end": "exit"},
        "swing": "sw10",
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


def net_of(tr):
    rs = [float(t["r_multiple"]) for t in tr]
    c2, _ = _trade_costs(tr, _g["fee_pct"], 0.0, _g["entry_slip_pct"], _g["exit_slip_pct"])
    return sum(rs) - c2 - fund(tr)


def main():
    print("=" * 70)
    print("  CAUSAL SL ON OOS 2021-2022: batch vs causal")
    print("=" * 70)

    print("\n  Loading 15m + 1h...")
    (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
    print("  Loading 1m fine fills...")
    ts_start = min(c15[0]["ts"], c1h[0]["ts"])
    ts_end = max(c15[-1]["ts"], c1h[-1]["ts"])
    fine = load_fine_1m(ts_start, ts_end)
    print(f"  {len(c15):,} 15m | {len(c1h):,} 1h | {len(fine):,} 1m")

    print("  Computing swings...")
    sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
    sw10 = _compute_swings(f1h, "continuous", min_bars=10)
    print(f"  sw15: {len(sw15)} | sw10: {len(sw10)}")

    sim = build_module()

    results = []
    for name, cfg in CONFIGS.items():
        sw = sw10 if cfg["swing"] == "sw10" else sw15

        for causal in [False, True]:
            params = dict(cfg["params"])
            if causal:
                params["exp_causal_sl"] = 1

            t0 = time.time()
            r = sim(c1h, sw, c15, sw15, fine_ltf=fine, **params)
            tr = r["ltf_trades"] if isinstance(r, dict) else r
            s = stats(tr)
            nt = net_of(tr)
            tag = "causal" if causal else "batch"

            py = defaultdict(float)
            for t in tr:
                yr = (t.get("exit_date") or t.get("entry_date") or "")[:4]
                py[yr] += float(t["r_multiple"])

            print(f"  [{name:20s} {tag:6s}] n={s['n']:>3} NET={nt:>+7.1f}R DD={s['dd']:>5.1f} WR={s['wr']:>5.1f}%  2021={py.get('2021',0):>+6.1f} 2022={py.get('2022',0):>+6.1f}  ({time.time()-t0:.1f}s)")

            results.append({
                "name": name, "tag": tag, "desc": cfg["desc"],
                "n": s["n"], "net": nt, "dd": s["dd"], "wr": s["wr"],
                "yearly": dict(py),
            })

    # Summary
    print("\n" + "=" * 80)
    print("  OOS CAUSAL SL SUMMARY")
    print("=" * 80)
    print(f"\n  {'Config':<22} {'Batch NET':>10} {'Causal NET':>11} {'Delta':>8} {'Batch DD':>9} {'Causal DD':>10}")
    print(f"  {'-'*72}")

    for i in range(0, len(results), 2):
        rb = results[i]
        rc = results[i + 1]
        delta = rc["net"] - rb["net"]
        print(f"  {rb['desc']:<22} {rb['net']:>+9.1f}R {rc['net']:>+10.1f}R {delta:>+7.1f}R {rb['dd']:>8.1f}R {rc['dd']:>9.1f}R")

    print()


if __name__ == "__main__":
    main()
