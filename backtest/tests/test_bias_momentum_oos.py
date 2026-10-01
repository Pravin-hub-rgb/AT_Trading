"""Bias momentum on OOS 2021-2022 + causal SL."""
import sys, time, bisect
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import build_module, _compute_swings, stats
from engine.v18_params import SWING, get_v18_params
from src.btc.btc_routes import _trade_costs
from replay_harness import INSTRUMENT
from run_experiment import fund
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
    },
    "utcsat_multi": {
        "desc": "utcsat_multi_sw10",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65, "atr_low_thresh": 0.35,
                    "sl_buf_atr": 0.01, "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True, "exp_persist": 7,
                    "exp_skip_utc_sat": 1, "window_end": "exit"},
    },
    "king_single": {
        "desc": "king_single_sw10",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65, "atr_low_thresh": 0.35,
                    "sl_buf_atr": 0.01, "chop_thresh": 58.0, "cooldown_bars": 0,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1, "exp_skip_weekend": 1,
                    "exp_wage_h": 10, "exp_chop15_lo": 55.0, "exp_chop15_hi": 61.0,
                    "exp_atr_ratio_max": 1.4, "window_end": "exit"},
    },
}

THRESHOLDS = [0.0, 0.5]


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
        flow.append(0)  # placeholder
    return candles


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


def compute_bm_ratio(swings_htf):
    bm_breaks = []
    bm_mags = []
    for s in swings_htf:
        seg = s.get("seg") or {}
        spx = float(seg.get("start_px", 0) or 0)
        epx = float(seg.get("end_px", 0) or 0)
        bm_mags.append(abs(epx - spx))
    for i, s in enumerate(swings_htf):
        if i < 1 or bm_mags[i - 1] <= 0:
            continue
        ratio = bm_mags[i] / bm_mags[i - 1]
        for b in (s.get("breaks") or []):
            bt = b.get("time", "")
            if bt:
                bm_breaks.append((bt[:19], ratio))
    bm_breaks.sort(key=lambda z: z[0])
    return bm_breaks


def filter_by_bm(trades, bm_breaks, min_ratio):
    if min_ratio <= 0 or not bm_breaks:
        return trades
    bm_times = [x[0] for x in bm_breaks]
    kept = []
    for t in trades:
        entry_d19 = t["entry_date"][:19]
        idx = bisect.bisect_right(bm_times, entry_d19) - 1
        if idx < 0:
            kept.append(t)
            continue
        if bm_breaks[idx][1] >= min_ratio:
            kept.append(t)
    return kept


def net_of(tr):
    rs = [float(t["r_multiple"]) for t in tr]
    c2, _ = _trade_costs(tr, _g["fee_pct"], 0.0, _g["entry_slip_pct"], _g["exit_slip_pct"])
    return sum(rs) - c2 - fund(tr)


def dd_of(tr):
    equity = 0.0
    peak = 0.0
    mx = 0.0
    for t in tr:
        equity += float(t["r_multiple"])
        if equity > peak: peak = equity
        dd = peak - equity
        if dd > mx: mx = dd
    return mx


def main():
    print("=" * 85)
    print("  BIAS MOMENTUM OOS TEST: batch SL + causal SL, threshold 0.5")
    print("=" * 85)

    from src.walker import FlowCandle

    print("\n  Loading OOS 2021-2022 data...")
    c15 = load_unseen("15m")
    c1h = load_unseen("1h")
    ts_start = min(c15[0]["ts"], c1h[0]["ts"])
    ts_end = max(c15[-1]["ts"], c1h[-1]["ts"])
    fine = load_fine_1m(ts_start, ts_end)
    print(f"  {len(c15):,} 15m | {len(c1h):,} 1h | {len(fine):,} 1m")

    from src.walker import FlowCandle as FC
    f15 = [FC(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"]) for c in c15]
    f1h = [FC(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"]) for c in c1h]

    sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
    sw10 = _compute_swings(f1h, "continuous", min_bars=10)
    print(f"  sw15: {len(sw15)} | sw10: {len(sw10)}")

    bm_breaks = compute_bm_ratio(sw10)
    print(f"  {len(bm_breaks)} break-ratio mappings")

    sim = build_module()

    for causal in [False, True]:
        tag = "CAUSAL SL" if causal else "BATCH SL"
        print(f"\n  {'='*80}")
        print(f"  {tag}")
        print(f"  {'='*80}")
        print(f"\n  {'Config':<22} {'Thresh':>6} {'n':>4} {'NET':>8} {'DD':>6} {'dNET':>8}")
        print(f"  {'-'*55}")

        for name, cfg in CONFIGS.items():
            params = dict(cfg["params"])
            if causal:
                params["exp_causal_sl"] = 1

            r = sim(c1h, sw10, c15, sw15, fine_ltf=fine, **params)
            trades_all = r["ltf_trades"] if isinstance(r, dict) else r
            n_base = net_of(trades_all)
            dd_base = dd_of(trades_all)

            print(f"  {cfg['desc']:<22} {'BASE':>6} {len(trades_all):>4} {n_base:>+7.1f}R {dd_base:>5.1f}  baseline")

            for thresh in THRESHOLDS[1:]:
                filtered = filter_by_bm(trades_all, bm_breaks, thresh)
                nf = net_of(filtered)
                ddf = dd_of(filtered)
                dnet = nf - n_base
                print(f"  {cfg['desc']:<22} {thresh:>6} {len(filtered):>4} {nf:>+7.1f}R {ddf:>5.1f} {dnet:>+7.1f}R")

    print()


if __name__ == "__main__":
    main()
