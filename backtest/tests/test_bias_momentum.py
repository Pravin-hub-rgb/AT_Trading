"""Test exp_bias_momentum_min filter on all 3 king configs.

Computes |current 1h swing mag| / |prev 1h swing mag| for each trade,
then filters out entries below the threshold. Full-path backtest.
"""
import sys, time, bisect
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data, BP
from test_experiments_craze import build_module

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
        "desc": "utcsat_multi_sw10 (KING MULTI)",
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

THRESHOLDS = [0.0, 0.3, 0.5, 0.8]  # 0.0 = no filter (baseline)


def compute_bm_ratio(swings_htf):
    """Pre-compute (break_time_str[:19], ratio) for each 1h swing."""
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
    """Filter trades: keep only those where bias_momentum >= min_ratio."""
    if min_ratio <= 0 or not bm_breaks:
        return trades  # no filter
    bm_times = [x[0] for x in bm_breaks]
    kept = []
    for t in trades:
        entry_d19 = t["entry_date"][:19]
        idx = bisect.bisect_right(bm_times, entry_d19) - 1
        if idx < 0:
            kept.append(t)  # no ratio data — keep
            continue
        ratio = bm_breaks[idx][1]
        if ratio >= min_ratio:
            kept.append(t)
    return kept


def stats(trades):
    if not trades:
        return {"n": 0, "gross": 0, "wr": 0, "dd": 0, "mx": 0}
    rs = [float(t["r_multiple"]) for t in trades]
    gross = sum(rs)
    wins = sum(1 for r in rs if r > 0)
    peak = 0
    equity = 0
    mx_dd = 0
    mx_streak = 0
    streak = 0
    for r in rs:
        equity += r
        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > mx_dd:
            mx_dd = dd
        if r > 0:
            streak = 0
        else:
            streak += 1
            mx_streak = max(mx_streak, streak)
    return {
        "n": len(rs), "gross": gross, "wr": wins / len(rs) * 100,
        "dd": mx_dd, "mx": mx_streak,
    }


def main():
    print("=" * 80)
    print("  BIAS MOMENTUM FILTER: full-path test on all 3 king configs")
    print("=" * 80)

    print("\n  Loading data...")
    data = get_data()
    print("  Building engine...")
    sim = build_module()

    sw10 = data["sw10"]
    bm_breaks = compute_bm_ratio(sw10)
    print(f"  Pre-computed {len(bm_breaks)} break-to-ratio mappings from {len(sw10)} 1h swings")

    # Show ratio distribution
    ratios = [r for _, r in bm_breaks]
    print(f"  Ratio stats: min={min(ratios):.3f} median={sorted(ratios)[len(ratios)//2]:.3f} max={max(ratios):.3f}")

    all_results = []

    for name, cfg in CONFIGS.items():
        print(f"\n  {'='*60}")
        print(f"  [{cfg['desc']}]")
        print(f"  {'='*60}")

        # Run baseline (no filter)
        params = dict(cfg["params"])
        t0 = time.time()
        r = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                fine_ltf=data["fine"], **params)
        trades_all = r["ltf_trades"] if isinstance(r, dict) else r
        s_all = stats(trades_all)

        # Show bucket analysis for this config
        print(f"\n  Baseline (no filter): {s_all['n']}t / NET={s_all['gross']:+.1f}R / DD={s_all['dd']:.1f}")

        # Bucket analysis
        bm_times = [x[0] for x in bm_breaks]
        bk = defaultdict(list)
        for t in trades_all:
            entry_d19 = t["entry_date"][:19]
            idx = bisect.bisect_right(bm_times, entry_d19) - 1
            if idx < 0:
                bk["?no_match"].append(float(t["r_multiple"]))
                continue
            ratio = bm_breaks[idx][1]
            if ratio < 0.3:
                b = "a:<0.3"
            elif ratio < 0.5:
                b = "b:0.3-0.5"
            elif ratio < 0.8:
                b = "c:0.5-0.8"
            elif ratio < 1.2:
                b = "d:0.8-1.2"
            elif ratio < 2.0:
                b = "e:1.2-2.0"
            else:
                b = "f:>=2.0"
            bk[b].append(float(t["r_multiple"]))

        print(f"  {'Bucket':<12} {'n':>4}  {'NET':>8}  {'avg':>7}  {'WR':>6}")
        for b in sorted(bk):
            lst = bk[b]
            n = len(lst)
            s = sum(lst)
            wr = len([x for x in lst if x > 0]) / max(n, 1) * 100
            print(f"  {b:<12} {n:>4}  {s:>+7.1f}R  {s/max(n,1):>+6.3f}  {wr:>5.1f}%")

        # Test each threshold
        for thresh in THRESHOLDS:
            filtered = filter_by_bm(trades_all, bm_breaks, thresh)
            sf = stats(filtered)
            delta_n = sf["n"] - s_all["n"]
            delta_r = sf["gross"] - s_all["gross"]
            tag = "BASELINE" if thresh == 0 else f"min={thresh}"
            all_results.append({
                "config": name, "desc": cfg["desc"], "thresh": thresh,
                "n": sf["n"], "net": sf["gross"], "dd": sf["dd"],
                "delta_n": delta_n, "delta_r": delta_r,
            })
            print(f"  [{tag:10s}] {sf['n']:>3}t / NET={sf['gross']:>+7.1f}R / DD={sf['dd']:>5.1f}  "
                  f"(dn={delta_n:>+4} dR={delta_r:>+7.1f})")

    # Summary table
    print("\n" + "=" * 90)
    print("  FULL-PATH SUMMARY: exp_bias_momentum_min filter")
    print("=" * 90)
    print(f"\n  {'Config':<22} {'Thresh':>6} {'n':>4} {'NET':>8} {'DD':>6} {'dn':>5} {'dR':>8}")
    print(f"  {'-'*65}")
    for r in all_results:
        bar = ""
        if r["delta_r"] > 0:
            bar = "+" * min(int(r["delta_r"] / 5), 20)
        elif r["delta_r"] < 0:
            bar = "-" * min(int(abs(r["delta_r"]) / 5), 20)
        print(f"  {r['desc']:<22} {r['thresh']:>6} {r['n']:>4} {r['net']:>+7.1f}R {r['dd']:>5.1f} {r['delta_n']:>+5} {r['delta_r']:>+7.1f}R  {bar}")

    print()


if __name__ == "__main__":
    main()
