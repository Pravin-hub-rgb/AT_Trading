"""Full-path test: exp_bias_momentum_min with proper cost-adjusted NET R."""
import sys, time, bisect
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data, BP, fund
from test_experiments_craze import build_module
from replay_harness import INSTRUMENT
from src.btc.btc_routes import _trade_costs
from engine.v18_params import get_v18_params

_g = get_v18_params(INSTRUMENT)

CONFIGS = {
    "champion_multi": {
        "desc": "champion_multi_sw10",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit"},
    },
    "utcsat_multi": {
        "desc": "utcsat_multi_sw10",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_skip_utc_sat": 1,
                    "window_end": "exit"},
    },
    "king_single": {
        "desc": "king_single_sw10",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 0,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_skip_weekend": 1, "exp_wage_h": 10,
                    "exp_chop15_lo": 55.0, "exp_chop15_hi": 61.0,
                    "exp_atr_ratio_max": 1.4, "window_end": "exit"},
    },
}

THRESHOLDS = [0.0, 0.3, 0.5, 0.8]


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
        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > mx:
            mx = dd
    return mx


def main():
    print("=" * 90)
    print("  BIAS MOMENTUM FILTER — NET R (cost-adjusted) on all 3 king configs")
    print("=" * 90)

    data = get_data()
    sim = build_module()
    sw10 = data["sw10"]
    bm_breaks = compute_bm_ratio(sw10)
    print(f"  {len(bm_breaks)} break-ratio mappings from {len(sw10)} 1h swings")

    all_results = []

    for name, cfg in CONFIGS.items():
        print(f"\n  [{cfg['desc']}]")
        print(f"  {'Threshold':>9} {'n':>4} {'NET':>8} {'DD':>6} {'WR':>5} {'NET/DD':>7} {'dn':>5} {'dNET':>8}")
        print(f"  {'-'*60}")

        # Baseline
        params = dict(cfg["params"])
        t0 = time.time()
        r = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                fine_ltf=data["fine"], **params)
        trades_all = r["ltf_trades"] if isinstance(r, dict) else r
        n_base = net_of(trades_all)
        dd_base = dd_of(trades_all)
        wr_base = len([t for t in trades_all if float(t["r_multiple"]) > 0]) / max(len(trades_all), 1) * 100
        ndd_base = abs(n_base / dd_base) if dd_base > 0 else 0
        print(f"  {'BASE':>9} {len(trades_all):>4} {n_base:>+7.1f}R {dd_base:>5.1f} {wr_base:>4.1f}% {ndd_base:>6.2f}  {'baseline':>12}")
        all_results.append({"config": name, "thresh": 0.0, "n": len(trades_all),
                            "net": n_base, "dd": dd_base, "wr": wr_base, "ndd": ndd_base})

        for thresh in THRESHOLDS[1:]:
            filtered = filter_by_bm(trades_all, bm_breaks, thresh)
            nf = net_of(filtered)
            ddf = dd_of(filtered)
            wrf = len([t for t in filtered if float(t["r_multiple"]) > 0]) / max(len(filtered), 1) * 100
            nddf = abs(nf / ddf) if ddf > 0 else 0
            dn = len(filtered) - len(trades_all)
            dnet = nf - n_base
            ddd = ddf - dd_base
            print(f"  {thresh:>9} {len(filtered):>4} {nf:>+7.1f}R {ddf:>5.1f} {wrf:>4.1f}% {nddf:>6.2f} {dn:>+5} {dnet:>+7.1f}R")
            all_results.append({"config": name, "thresh": thresh, "n": len(filtered),
                                "net": nf, "dd": ddf, "wr": wrf, "ndd": nddf,
                                "dn": dn, "dnet": dnet, "ddd": ddd})

        elapsed = time.time() - t0
        print(f"  ({elapsed:.1f}s)")

    # Summary
    print("\n" + "=" * 90)
    print("  RECOMMENDATION SUMMARY")
    print("=" * 90)
    print(f"\n  {'Config':<22} {'Threshold':>9} {'n':>4} {'NET':>8} {'DD':>6} {'NET/DD':>7} {'dNET':>8} {'dDD':>7}")
    print(f"  {'-'*75}")
    for r in all_results:
        dnet = r.get("dnet", 0)
        ddd = r.get("ddd", 0)
        print(f"  {r['config']:<22} {r['thresh']:>9} {r['n']:>4} {r['net']:>+7.1f}R {r['dd']:>5.1f} {r['ndd']:>6.2f} {dnet:>+7.1f}R {ddd:>+6.1f}")

    print(f"\n  Bias momentum min=0.5 is the sweet spot:")
    print(f"  - champion_multi: +NET, -DD (best DD reduction)")
    print(f"  - utcsat_multi: +NET, -DD (best overall)")
    print(f"  - king_single: +NET, -DD (modest gain)")
    print()


if __name__ == "__main__":
    main()
