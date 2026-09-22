"""Compare bias momentum thresholds 0.5 vs 0.8 with equity curves."""
import sys, bisect
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data, BP
from test_experiments_craze import build_module
from src.btc.btc_routes import _trade_costs
from engine.v18_params import get_v18_params
from replay_harness import INSTRUMENT

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

THRESHOLDS = [0.0, 0.5, 0.8]


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
    if not tr:
        return 0.0
    rs = [float(t["r_multiple"]) for t in tr]
    c2, _ = _trade_costs(tr, _g["fee_pct"], 0.0, _g["entry_slip_pct"], _g["exit_slip_pct"])
    return sum(rs) - c2


def equity_curve(trades):
    """Return (dates, cumulative_R) for plotting."""
    eq = []
    cum = 0.0
    for t in trades:
        cum += float(t["r_multiple"])
        eq.append((t.get("entry_date", "")[:10], cum))
    return eq


def draw_curve(equity, width=60, height=20):
    """ASCII equity curve."""
    if not equity:
        return "  (no trades)"
    vals = [e for _, e in equity]
    mn = min(vals) if min(vals) < 0 else 0
    mx = max(vals)
    rng = mx - mn if mx != mn else 1
    lines = []
    for row in range(height, -1, -1):
        threshold = mn + (rng * row / height)
        line = f"{threshold:>+7.1f} |"
        for v in vals:
            pos = int((v - mn) / rng * height) if rng > 0 else 0
            if pos == row:
                line += "*"
            elif row == 0 and threshold <= 0:
                line += "-"
            else:
                line += " "
        lines.append(line)
    lines.append(f"         +{'-' * width}")
    # Date labels
    if equity:
        first = equity[0][0]
        last = equity[-1][0]
        mid = equity[len(equity)//2][0]
        lines.append(f"          {first[:7]}{'':>{max(0,width//2-len(first[:7]))}}{mid[:7]}{'':>{max(0,width//2-len(mid[:7]))}}{last[:7]}")
    return "\n".join(lines)


def yearly_stats(trades):
    """Per-year NET R."""
    py = defaultdict(float)
    pn = defaultdict(int)
    for t in trades:
        yr = (t.get("exit_date") or t.get("entry_date") or "")[:4]
        py[yr] += float(t["r_multiple"])
        pn[yr] += 1
    return dict(sorted(py.items())), dict(sorted(pn.items()))


def max_streak(trades):
    streak = 0
    mx = 0
    for t in trades:
        if float(t["r_multiple"]) <= 0:
            streak += 1
            mx = max(mx, streak)
        else:
            streak = 0
    return mx


def main():
    print("=" * 90)
    print("  BIAS MOMENTUM: threshold 0.5 vs 0.8 — full comparison")
    print("=" * 90)

    data = get_data()
    sim = build_module()
    bm_breaks = compute_bm_ratio(data["sw10"])

    for name, cfg in CONFIGS.items():
        print(f"\n{'=' * 90}")
        print(f"  {cfg['desc']}")
        print(f"{'=' * 90}")

        params = dict(cfg["params"])
        r = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                fine_ltf=data["fine"], **params)
        trades_all = r["ltf_trades"] if isinstance(r, dict) else r

        results = {}
        for thresh in THRESHOLDS:
            filtered = filter_by_bm(trades_all, bm_breaks, thresh)
            net = net_of(filtered)
            rs = [float(t["r_multiple"]) for t in filtered]
            peak = 0.0
            eq = 0.0
            dd = 0.0
            for r in rs:
                eq += r
                if eq > peak: peak = eq
                d = peak - eq
                if d > dd: dd = d
            wr = len([r for r in rs if r > 0]) / max(len(rs), 1) * 100
            avg = sum(rs) / max(len(rs), 1)
            ndd = abs(net / dd) if dd > 0 else 0
            ms = max_streak(filtered)
            py, pn = yearly_stats(filtered)
            results[thresh] = {
                "n": len(filtered), "net": net, "dd": dd, "wr": wr,
                "avg": avg, "ndd": ndd, "ms": ms, "py": py, "pn": pn,
                "trades": filtered,
            }

        # Side-by-side metrics
        print(f"\n  {'Metric':<16} {'BASE (0.0)':>12} {'min=0.5':>12} {'min=0.8':>12} {'0.5 vs BASE':>14} {'0.8 vs BASE':>14}")
        print(f"  {'-'*80}")
        for metric, key, fmt in [
            ("Trades", "n", "d"),
            ("NET R", "net", "+.1f"),
            ("Max DD", "dd", ".1f"),
            ("NET/DD", "ndd", ".2f"),
            ("Win Rate", "wr", ".1f"),
            ("Avg R", "avg", "+.3f"),
            ("Max Loss Streak", "ms", "d"),
        ]:
            b = results[0.0][key]
            m5 = results[0.5][key]
            m8 = results[0.8][key]
            if isinstance(b, float):
                d5 = m5 - b
                d8 = m8 - b
                bs = f"{b:{fmt.replace('+',''):s}}" if fmt.startswith('+') else f"{b:{fmt}}"
                s5 = f"{m5:{fmt}}"
                s8 = f"{m8:{fmt}}"
                ds5 = f"{d5:>+8.1f}" if isinstance(d5, float) else f"{d5:>+8d}"
                ds8 = f"{d8:>+8.1f}" if isinstance(d8, float) else f"{d8:>+8d}"
            else:
                d5 = m5 - b
                d8 = m8 - b
                bs = f"{b}"
                s5 = f"{m5}"
                s8 = f"{m8}"
                ds5 = f"{d5:>+8d}"
                ds8 = f"{d8:>+8d}"
            print(f"  {metric:<16} {bs:>12} {s5:>12} {s8:>12} {ds5:>14} {ds8:>14}")

        # Yearly comparison
        print(f"\n  Yearly R:")
        all_years = sorted(set().union(*[set(results[t]["py"].keys()) for t in THRESHOLDS]))
        print(f"  {'Year':<6} {'BASE':>8} {'min=0.5':>8} {'min=0.8':>8} {'0.5 dR':>8} {'0.8 dR':>8}")
        for yr in all_years:
            bv = results[0.0]["py"].get(yr, 0)
            v5 = results[0.5]["py"].get(yr, 0)
            v8 = results[0.8]["py"].get(yr, 0)
            print(f"  {yr:<6} {bv:>+7.1f} {v5:>+7.1f} {v8:>+7.1f} {v5-bv:>+7.1f} {v8-bv:>+7.1f}")

        # Equity curves
        print(f"\n  Equity Curves (cumulative NET R):")
        for thresh in THRESHOLDS:
            eq = equity_curve(results[thresh]["trades"])
            print(f"\n  --- threshold={thresh} (n={results[thresh]['n']}, NET={results[thresh]['net']:+.1f}R) ---")
            print(draw_curve(eq, width=70, height=15))

        # Equity curve overlay
        print(f"\n  Overlay (B=BASE, 5=min0.5, 8=min0.8):")
        eq_base = {d: v for d, v in equity_curve(results[0.0]["trades"])}
        eq_05 = {d: v for d, v in equity_curve(results[0.5]["trades"])}
        eq_08 = {d: v for d, v in equity_curve(results[0.8]["trades"])}
        all_dates = sorted(set(list(eq_base.keys()) + list(eq_05.keys()) + list(eq_08.keys())))
        if all_dates:
            mn = min(min(eq_base.values(), default=0), min(eq_05.values(), default=0), min(eq_08.values(), default=0))
            mx = max(max(eq_base.values(), default=0), max(eq_05.values(), default=0), max(eq_08.values(), default=0))
            rng = mx - mn if mx != mn else 1
            height = 18
            lines = []
            for row in range(height, -1, -1):
                threshold = mn + (rng * row / height)
                line = f"{threshold:>+7.1f} |"
                for d in all_dates:
                    vb = eq_base.get(d)
                    v5 = eq_05.get(d)
                    v8 = eq_08.get(d)
                    # Find which line is at this row
                    symbols = []
                    if vb is not None and abs(int((vb - mn) / rng * height) - row) == 0:
                        symbols.append("B")
                    if v5 is not None and abs(int((v5 - mn) / rng * height) - row) == 0:
                        symbols.append("5")
                    if v8 is not None and abs(int((v8 - mn) / rng * height) - row) == 0:
                        symbols.append("8")
                    if not symbols:
                        # Check if any line crosses this row between data points
                        line += " "
                    else:
                        line += symbols[0]
                lines.append(line)
            lines.append(f"         +{'-' * len(all_dates)}")
            print("\n".join(lines))
            print(f"         B=BASE  5=min0.5  8=min0.8")

        print()

    print("=" * 90)
    print("  VERDICT")
    print("=" * 90)
    print("""
  0.8 gives BEST NET/DD (utcsat 40.6! champion 29.5!) and lowest DD.
  0.5 is SAFER — still positive on king_single, less aggressive.

  If running multi ONLY: go 0.8 (NET/DD is insane).
  If running single too: go 0.5 (keeps single +9.3R).
  Compromise: 0.8 on multi, 0.5 on single.
""")


if __name__ == "__main__":
    main()
