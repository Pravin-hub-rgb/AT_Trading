"""Full sweep: raw base -> lb30 -> gate combos -> +bias momentum.
All tested IS + OOS. Starting from scratch."""
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
from src.btc.btc_config import btc_bybit_oos_dir
from src.walker import FlowCandle
from run_experiment import get_data

IST_OFFSET_SEC = 5 * 3600 + 30 * 60
# moved out of the repo: see btc_config.BTC_BYBIT_OOS_DATA_DIR
UNSEEN_DIR = btc_bybit_oos_dir()

# Core engine defaults (no experimental gates)
CORE = {"mode": "atr_high", "atr_high_thresh": 0.65, "atr_low_thresh": 0.35,
        "sl_buf_atr": 0.01, "chop_thresh": 58.0, "cooldown_bars": 0,
        "max_consecutive_losses": 3, "ext_stop_r": 3.0,
        "exp_partial_r": 0.0, "window_end": "exit"}

# Gate combos to test (applied on top of CORE)
GATE_COMBOS = [
    ("raw_base",           {}),
    ("lb30",               {"exp31_lb": 30}),
    ("lb30_wage10",        {"exp31_lb": 30, "exp_wage_h": 10}),
    ("lb30_wage10_wknd",   {"exp31_lb": 30, "exp_wage_h": 10, "exp_skip_weekend": 1}),
    ("lb30_swpaus",        {"exp31_lb": 30, "exp_swingpause": 1}),
    ("lb30_swpaus_wage10", {"exp31_lb": 30, "exp_swingpause": 1, "exp_wage_h": 10}),
    ("wage10",             {"exp_wage_h": 10}),
    ("wage10_wknd",        {"exp_wage_h": 10, "exp_skip_weekend": 1}),
    ("wage10_chop",        {"exp_wage_h": 10, "exp_chop15_lo": 55.0, "exp_chop15_hi": 61.0}),
    ("wage10_chop_wknd",   {"exp_wage_h": 10, "exp_chop15_lo": 55.0, "exp_chop15_hi": 61.0, "exp_skip_weekend": 1}),
    ("king",               {"exp_swingpause": 1, "exp_skip_weekend": 1, "exp_wage_h": 10,
                            "exp_chop15_lo": 55.0, "exp_chop15_hi": 61.0, "exp_atr_ratio_max": 1.4}),
]

# Bias momentum thresholds to test per gate combo
BM_THRESHOLDS = [0.0, 0.5, 0.6, 0.7, 0.8, 0.9]


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


def run_cfg(sim, c1h, sw10, c15, sw15, fine, gates, bm):
    params = dict(CORE)
    params.update(gates)
    if bm > 0:
        params["exp_bias_momentum_min"] = bm
    r = sim(c1h, sw10, c15, sw15, fine_ltf=fine, **params)
    trades = r["ltf_trades"] if isinstance(r, dict) else r
    rs = [float(t["r_multiple"]) for t in trades]
    n = len(rs); net = sum(rs)
    wins = sum(1 for r in rs if r > 0); wr = wins / max(n, 1) * 100
    peak = 0.0; cum = 0.0; dd = 0.0
    for r in rs: cum += r; peak = max(peak, cum); dd = max(dd, peak - cum)
    ndd = abs(net / dd) if dd > 0 else 0
    # yearly
    yearly = defaultdict(float)
    for t in trades:
        y = (t.get("exit_date") or t.get("entry_date") or "")[:4]
        yearly[y] += float(t["r_multiple"])
    return n, net, wr, dd, ndd, dict(yearly)


def main():
    print("=" * 110)
    print("  FULL GATE COMBO + BIAS MOMENTUM SWEEP")
    print("  IS + OOS, all combos, thresholds 0.0-0.9")
    print("=" * 110)

    is_data = get_data()
    sim = build_module()

    print("\n  Loading OOS...")
    (c15o, f15o), (c1ho, f1ho) = load_unseen("15m"), load_unseen("1h")
    fine_oos = load_fine_1m(c1ho[0]["ts"], c1ho[-1]["ts"])
    sw10_oos = _compute_swings(f1ho, "continuous", min_bars=10)
    sw15_oos = _compute_swings(f15o, "continuous", min_bars=SWING["min_bars_15m"])
    print(f"  OOS loaded: c1h={len(c1ho)} fine={len(fine_oos)}")

    # PHASE 1: Find best BM threshold for each gate combo (on IS)
    print(f"\n{'='*110}")
    print(f"  PHASE 1: IS SCREENING — best BM threshold per gate combo")
    print(f"{'='*110}")

    best_bm_per_combo = {}
    all_is = {}

    for gname, gates in GATE_COMBOS:
        print(f"\n  {gname}:")
        print(f"    {'BM':>5} {'n':>4} {'NET':>8} {'WR':>5} {'DD':>6} {'N/D':>6} {'dNET':>8}")
        print(f"    {'-'*50}")

        base_net = None
        best_dnet = 0; best_t = 0.0
        for bm in BM_THRESHOLDS:
            n, net, wr, dd, ndd, _ = run_cfg(
                sim, is_data["c1h"], is_data["sw10"], is_data["c15"], is_data["sw15"],
                is_data["fine"], gates, bm)
            if bm == 0.0:
                base_net = net
                dnet_s = "base"
            else:
                dnet = net - base_net
                dnet_s = f"{dnet:+.1f}R"
                if dnet > best_dnet:
                    best_dnet = dnet
                    best_t = bm
            all_is[(gname, bm)] = (n, net, wr, dd, ndd)
            print(f"    {bm:>5.1f} {n:>4} {net:>+7.1f}R {wr:>4.1f}% {dd:>5.1f} {ndd:>5.2f}  {dnet_s}")

        best_bm_per_combo[gname] = best_t
        print(f"    -> best BM = {best_t}")

    # PHASE 2: OOS test best BM per gate combo + raw base + base (bm=0)
    print(f"\n{'='*110}")
    print(f"  PHASE 2: OOS — head-to-head")
    print(f"{'='*110}")

    oos_results = {}
    for gname, gates in GATE_COMBOS:
        best_bm = best_bm_per_combo[gname]

        # Test base (no bm) and best bm
        for bm_val, tag in [(0.0, "base"), (best_bm, f"best_bm={best_bm}")]:
            n, net, wr, dd, ndd, yearly = run_cfg(
                sim, c1ho, sw10_oos, c15o, sw15_oos, fine_oos, gates, bm_val)
            key = f"{gname}_{tag}"
            oos_results[key] = {"n": n, "net": net, "wr": wr, "dd": dd, "ndd": ndd,
                                "yearly": yearly, "gates": gates, "bm": bm_val}
            y21 = yearly.get("2021", 0)
            y22 = yearly.get("2022", 0)
            print(f"  {key:<40} {n:>4}t  NET={net:>+7.1f}R  DD={dd:>5.1f}  N/D={ndd:>5.2f}  21={y21:>+6.1f}R  22={y22:>+6.1f}R")

    # Also test promising bm thresholds on top gate combos (0.5, 0.6, 0.7, 0.8)
    print(f"\n  EXTRA: OOS threshold sweep on top gate combos...")
    top_combos = ["lb30_wage10", "wage10", "lb30_wage10_wknd", "wage10_chop", "lb30"]
    for gname in top_combos:
        gates = dict(next(g for g in GATE_COMBOS if g[0] == gname)[1])
        for bm in [0.5, 0.6, 0.7, 0.8, 0.9]:
            n, net, wr, dd, ndd, yearly = run_cfg(
                sim, c1ho, sw10_oos, c15o, sw15_oos, fine_oos, gates, bm)
            key = f"{gname}_bm{bm}"
            oos_results[key] = {"n": n, "net": net, "wr": wr, "dd": dd, "ndd": ndd,
                                "yearly": yearly, "gates": gates, "bm": bm}
            y21 = yearly.get("2021", 0)
            y22 = yearly.get("2022", 0)
            print(f"  {key:<40} {n:>4}t  NET={net:>+7.1f}R  DD={dd:>5.1f}  N/D={ndd:>5.2f}  21={y21:>+6.1f}R  22={y22:>+6.1f}R")

    # RANKING
    print(f"\n{'='*110}")
    print(f"  FINAL RANKING: OOS NET/DD (primary) + NET (secondary)")
    print(f"{'='*110}")
    ranked = sorted(oos_results.items(), key=lambda x: (-x[1]["ndd"], -x[1]["net"]))
    for rank, (key, res) in enumerate(ranked[:25], 1):
        y21 = res["yearly"].get("2021", 0)
        y22 = res["yearly"].get("2022", 0)
        print(f"  #{rank:<3} {key:<40} N/D={res['ndd']:>5.2f}  NET={res['net']:>+7.1f}R  DD={res['dd']:>5.1f}  WR={res['wr']:>4.0f}%  21={y21:>+5.1f}  22={y22:>+5.1f}")

    # Also rank by IS NET to see which combos are strong IS
    print(f"\n  IS RANKING (top 15 by IS NET/DD):")
    is_ranked = sorted(all_is.items(), key=lambda x: (-x[1][4], -x[1][1]))
    for rank, ((gname, bm), (n, net, wr, dd, ndd)) in enumerate(is_ranked[:15], 1):
        print(f"  #{rank:<3} {gname:<25} bm={bm:<4} {n:>4}t  NET={net:>+7.1f}R  DD={dd:>5.1f}  N/D={ndd:>5.2f}  WR={wr:>4.0f}%")


if __name__ == "__main__":
    main()
