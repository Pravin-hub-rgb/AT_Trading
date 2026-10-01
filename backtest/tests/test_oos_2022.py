"""Out-of-sample backtest on 2021-2022 unseen data — any strategy.

Loads data from data/unseen/bybit/ (completely separate from data/bybit/).
Runs with exact same parameters AND fine fills as in-sample.

Usage:
    python backtest/tests/test_oos_2022.py                    # run both single + multi
    python backtest/tests/test_oos_2022.py --strategy single  # king single only
    python backtest/tests/test_oos_2022.py --strategy multi   # king multi only
"""
import sys, time, argparse
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import build_module, _compute_swings, stats
from engine.v18_params import SWING, get_v18_params, V18_ENGINE
from src.walker import FlowCandle
from src.btc.btc_routes import _trade_costs
import pandas as pd

INSTRUMENT = "BTCUSDT_BYBIT"
IST_OFFSET_SEC = 5 * 3600 + 30 * 60
UNSEEN_DIR = ROOT / "data" / "unseen" / "bybit"

STRATEGIES = {
    "single": {
        "desc": "KING SINGLE: fullstack + wage10 + cd=0",
        "params": {
            "mode": "atr_high", "atr_high_thresh": 0.65,
            "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
            "chop_thresh": 58.0, "cooldown_bars": 0,
            "max_consecutive_losses": 3, "ext_stop_r": 3.0,
            "exp_partial_r": 0.0, "exp_swingpause": 1,
            "exp_skip_weekend": 1, "exp_wage_h": 10,
            "exp_chop15_lo": 55.0, "exp_chop15_hi": 61.0,
            "exp_atr_ratio_max": 1.4, "window_end": "exit",
        },
        "swing": "sw10",
        "is_n": 200, "is_net": 310.7, "is_dd": 11.2, "is_wr": 32.5, "is_years": 3.8,
    },
    "multi": {
        "desc": "KING MULTI: mltf + persist7 + utc-sat skip",
        "params": {
            "mode": "atr_high", "atr_high_thresh": 0.65,
            "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
            "chop_thresh": 58.0, "cooldown_bars": 8,
            "max_consecutive_losses": 3, "ext_stop_r": 3.0,
            "exp_partial_r": 0.0, "exp_mltf": True,
            "exp_persist": 7, "exp_skip_utc_sat": 1,
            "window_end": "exit",
        },
        "swing": "sw10",
        "is_n": 454, "is_net": 359.0, "is_dd": 14.8, "is_wr": 30.8, "is_years": 3.8,
    },
    "champion_multi": {
        "desc": "CHAMPION MULTI: mltf + persist7 (no utc skip)",
        "params": {
            "mode": "atr_high", "atr_high_thresh": 0.65,
            "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
            "chop_thresh": 58.0, "cooldown_bars": 8,
            "max_consecutive_losses": 3, "ext_stop_r": 3.0,
            "exp_partial_r": 0.0, "exp_mltf": True,
            "exp_persist": 7, "window_end": "exit",
        },
        "swing": "sw10",
        "is_n": 500, "is_net": 325.8, "is_dd": 17.8, "is_wr": 30.8, "is_years": 3.8,
    },
    "fullstack_single": {
        "desc": "FULLSTACK SINGLE: swingpause + weekend + chop band + ATR ratio",
        "params": {
            "mode": "atr_high", "atr_high_thresh": 0.65,
            "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
            "chop_thresh": 58.0, "cooldown_bars": 8,
            "max_consecutive_losses": 3, "ext_stop_r": 3.0,
            "exp_partial_r": 0.0, "exp_swingpause": 1,
            "exp_skip_weekend": 1, "exp_chop15_lo": 55.0,
            "exp_chop15_hi": 61.0, "exp_atr_ratio_max": 1.4,
            "window_end": "exit",
        },
        "swing": "sw10",
        "is_n": 225, "is_net": 282.9, "is_dd": 12.5, "is_wr": 31.1, "is_years": 3.8,
    },
    "chopband_multi": {
        "desc": "CHOPBAND MULTI: mltf + persist7 + chop band",
        "params": {
            "mode": "atr_high", "atr_high_thresh": 0.65,
            "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
            "chop_thresh": 58.0, "cooldown_bars": 8,
            "max_consecutive_losses": 3, "ext_stop_r": 3.0,
            "exp_partial_r": 0.0, "exp_mltf": True,
            "exp_persist": 7, "exp_chop15_lo": 55.0,
            "exp_chop15_hi": 61.0, "window_end": "exit",
        },
        "swing": "sw10",
        "is_n": 432, "is_net": 350.7, "is_dd": 17.6, "is_wr": 31.2, "is_years": 3.8,
    },
    "wage12_single": {
        "desc": "WAGE12 SINGLE: swingpause + weekend + wage 12h",
        "params": {
            "mode": "atr_high", "atr_high_thresh": 0.65,
            "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
            "chop_thresh": 58.0, "cooldown_bars": 8,
            "max_consecutive_losses": 3, "ext_stop_r": 3.0,
            "exp_partial_r": 0.0, "exp_swingpause": 1,
            "exp_skip_weekend": 1, "exp_wage_h": 12,
            "window_end": "exit",
        },
        "swing": "sw10",
        "is_n": 259, "is_net": 278.6, "is_dd": 16.6, "is_wr": 30.9, "is_years": 3.8,
    },
    "fliponly_multi": {
        "desc": "FLIPONLY MULTI: mltf + persist7 + FLIP entries only",
        "params": {
            "mode": "atr_high", "atr_high_thresh": 0.65,
            "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
            "chop_thresh": 58.0, "cooldown_bars": 8,
            "max_consecutive_losses": 3, "ext_stop_r": 3.0,
            "exp_partial_r": 0.0, "exp_mltf": True,
            "exp_persist": 7, "exp_kinds": "FLIP",
            "window_end": "exit",
        },
        "swing": "sw10",
        "is_n": 285, "is_net": 242.7, "is_dd": 24.3, "is_wr": 30.2, "is_years": 3.8,
    },
}


def load_unseen_candles(tf: str):
    path = UNSEEN_DIR / f"BTCUSDT_{tf}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Unseen data missing: {path}")
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


def load_fine_1m_unseen(ts_start: int, ts_end: int):
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


def run_strategy(name, cfg, c15, f15, c1h, f1h, fine, sw15, sw10, sim, _g):
    params = cfg["params"]
    sw = sw10 if cfg["swing"] == "sw10" else sw15

    t0 = time.time()
    r = sim(c1h, sw, c15, sw15, fine_ltf=fine, **params)
    elapsed = time.time() - t0
    tr = r["ltf_trades"] if isinstance(r, dict) else r

    n = len(tr)
    if n == 0:
        print(f"\n  [{name}] NO TRADES GENERATED")
        return None

    s = stats(tr)
    c2, _ = _trade_costs(tr, _g["fee_pct"], 0.0, _g["entry_slip_pct"], _g["exit_slip_pct"])
    f_cost = 0.0
    for t in tr:
        e, sl = float(t["entry_price"]), float(t["sl"])
        rk = abs(e - sl)
        if rk > 0 and e > 0:
            f_cost += (int(t.get("bars_held") or 0) * 0.25 / 8.0) * 0.0001 * (e / rk)
    net_r = s["gross"] - c2 - f_cost

    py = defaultdict(float)
    for t in tr:
        yr = (t.get("exit_date") or t.get("entry_date") or "")[:4]
        py[yr] += float(t["r_multiple"])

    sorted_trades = sorted(tr, key=lambda t: float(t["r_multiple"]), reverse=True)

    oos_years = 2.0
    annual_net = net_r / oos_years
    annual_gross = s["gross"] / oos_years

    print(f"\n{'=' * 70}")
    print(f"  {name.upper()}: {cfg['desc']}")
    print(f"{'=' * 70}")
    print(f"\n  Trades:           {n}")
    print(f"  Gross R:          {s['gross']:+.1f}R")
    print(f"  Cost R:           {-c2:.1f}R")
    print(f"  Funding R:        {-f_cost:.1f}R")
    print(f"  NET R:            {net_r:+.1f}R")
    print(f"  Win Rate:         {s['wr']:.1f}%")
    print(f"  Max DD:           {s['dd']:.1f}R")
    print(f"  Avg R:            {s['gross']/n:+.2f}R")
    print(f"  Max Streak:       {s['mx']} consecutive losses")
    ndd = net_r/s['dd'] if s['dd'] > 0 else 0
    ndd_str = f"{ndd:.1f}" if s['dd'] > 0 else "N/A"
    print(f"  NET/Max DD:       {ndd_str}")
    print(f"  Annual NET:       {annual_net:+.1f}R/yr")
    print(f"  Fine fills:       {len(fine):,} 1m candles")

    print(f"\n  --- Yearly Breakdown ---")
    for yr in sorted(py.keys()):
        print(f"    {yr}: {py[yr]:>+7.1f}R")

    print(f"\n  --- Top 5 Winners ---")
    for i, t in enumerate(sorted_trades[:5]):
        print(f"    {i+1}. {float(t['r_multiple']):>+7.1f}R  {t['entry_date'][:10]} -> {t['exit_date'][:10]}  {t['dir']}")
    print(f"\n  --- Top 5 Losers ---")
    for i, t in enumerate(sorted_trades[-5:]):
        print(f"    {i+1}. {float(t['r_multiple']):>+7.1f}R  {t['entry_date'][:10]} -> {t['exit_date'][:10]}  {t['dir']}")

    # Comparison table
    print(f"\n  --- In-sample vs OOS ---")
    print(f"  {'Metric':<20} {'In-sample':>15} {'OOS 21-22':>15}")
    print(f"  {'-'*50}")
    print(f"  {'Trades':<20} {cfg['is_n']:>15} {n:>15}")
    is_net_str = f"+{cfg['is_net']:.1f}R"
    oos_net_str = f"{net_r:+.1f}R"
    print(f"  {'NET R':<20} {is_net_str:>15} {oos_net_str:>15}")
    is_wr_str = f"{cfg['is_wr']:.1f}%"
    oos_wr_str = f"{s['wr']:.1f}%"
    print(f"  {'Win Rate':<20} {is_wr_str:>15} {oos_wr_str:>15}")
    is_dd_str = f"{cfg['is_dd']:.1f}R"
    oos_dd_str = f"{s['dd']:.1f}R"
    print(f"  {'Max DD':<20} {is_dd_str:>15} {oos_dd_str:>15}")
    is_annual_net = cfg['is_net'] / cfg['is_years']
    is_annual_str = f"{is_annual_net:+.1f}R/yr"
    oos_annual_str = f"{annual_net:+.1f}R/yr"
    print(f"  {'Annual NET':<20} {is_annual_str:>15} {oos_annual_str:>15}")

    return {
        "name": name, "n": n, "gross": s["gross"], "net": net_r, "wr": s["wr"],
        "dd": s["dd"], "avg_r": s["gross"]/n, "annual_net": annual_net,
        "yearly": dict(py), "cost": c2, "funding": f_cost,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", nargs="+", default=list(STRATEGIES.keys()),
                    choices=list(STRATEGIES.keys()))
    args = ap.parse_args()

    print("=" * 70)
    print("  OOS BACKTEST: 2021-2022 Unseen Data")
    print("  Data: data/unseen/bybit/ (completely separate)")
    print("=" * 70)

    for tf in ("15m", "1h", "1m"):
        path = UNSEEN_DIR / f"BTCUSDT_{tf}.csv"
        if path.exists():
            lines = sum(1 for _ in open(path)) - 1
            first_line = open(path).readlines()[1].split(",")[0]
            last_line = open(path).readlines()[-1].split(",")[0]
            print(f"  [{tf}] {lines:,} candles: {first_line} -> {last_line}")
        else:
            print(f"  [{tf}] MISSING")

    print("\n  Loading 15m and 1h candles...")
    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_unseen_candles("15m"), load_unseen_candles("1h")
    print(f"  Loaded in {time.time()-t0:.1f}s")

    print("  Loading 1m fine fill data...")
    t0 = time.time()
    ts_start = min(c15[0]["ts"], c1h[0]["ts"])
    ts_end = max(c15[-1]["ts"], c1h[-1]["ts"])
    fine = load_fine_1m_unseen(ts_start, ts_end)
    print(f"  Loaded {len(fine):,} 1m candles in {time.time()-t0:.1f}s")

    print("  Computing sw10 swings...")
    sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
    sw10 = _compute_swings(f1h, "continuous", min_bars=10)
    print(f"  15m swings (mb50): {len(sw15)}, 1h swings (sw10): {len(sw10)}")

    print("  Building patched engine...")
    sim = build_module()
    _g = get_v18_params(INSTRUMENT)

    results = {}
    for name in args.strategy:
        cfg = STRATEGIES[name]
        results[name] = run_strategy(name, cfg, c15, f15, c1h, f1h, fine, sw15, sw10, sim, _g)

    # Leaderboard summary
    valid = [r for r in results.values() if r is not None]
    if len(valid) > 1:
        valid.sort(key=lambda r: r["net"], reverse=True)
        print(f"\n{'=' * 80}")
        print(f"  OOS LEADERBOARD: 2021-2022 Unseen Data (ranked by NET R)")
        print(f"{'=' * 80}")
        print(f"\n  {'#':<3} {'Strategy':<25} {'IS NET':>8} {'OOS NET':>9} {'OOS/IS':>7} {'WR':>6} {'DD':>6} {'Ann.NET':>9}")
        print(f"  {'-'*75}")
        for i, r in enumerate(valid, 1):
            cfg = STRATEGIES[r["name"]]
            is_annual = cfg["is_net"] / cfg["is_years"]
            ratio = r["annual_net"] / is_annual * 100 if is_annual else 0
            is_net_s = f"+{cfg['is_net']:.0f}R"
            oos_net_s = f"+{r['net']:.1f}R"
            ratio_s = f"{ratio:.0f}%"
            wr_s = f"{r['wr']:.1f}%"
            dd_s = f"{r['dd']:.1f}R"
            ann_s = f"+{r['annual_net']:.1f}R/yr"
            print(f"  {i:<3} {r['name']:<25} {is_net_s:>8} {oos_net_s:>9} {ratio_s:>7} {wr_s:>6} {dd_s:>6} {ann_s:>9}")


if __name__ == "__main__":
    main()
