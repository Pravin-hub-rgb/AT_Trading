"""Equity curve smoothness comparison: 0.8 vs 0.9 — rolling DD, worst periods, monthly consistency."""
import sys, bisect
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data
from test_experiments_craze import build_module
from src.btc.btc_routes import _trade_costs
from engine.v18_params import get_v18_params
from replay_harness import INSTRUMENT

_g = get_v18_params(INSTRUMENT)

CONFIGS = {
    "champion_multi": {
        "desc": "champion_multi",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit"},
    },
    "utcsat_multi": {
        "desc": "utcsat_multi",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_skip_utc_sat": 1,
                    "window_end": "exit"},
    },
    "king_single": {
        "desc": "king_single",
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
        return list(trades)
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
    eq = []
    cum = 0.0
    for t in trades:
        cum += float(t["r_multiple"])
        eq.append(cum)
    return eq


def rolling_dd(equity, window):
    """Max drawdown within a rolling window of `window` trades."""
    results = []
    for i in range(len(equity)):
        start = max(0, i - window + 1)
        segment = equity[start:i+1]
        peak = max(segment)
        dd = peak - segment[-1]
        results.append(dd)
    return results


def draw_smooth(equity, width=70, height=18, label=""):
    """ASCII equity curve with smooth markers."""
    if not equity:
        return "  (no trades)"
    vals = equity
    mn = min(vals)
    mx = max(vals)
    if mn > 0: mn = 0
    rng = mx - mn if mx != mn else 1
    lines = []
    for row in range(height, -1, -1):
        threshold = mn + (rng * row / height)
        line = f"{threshold:>+7.1f} |"
        for v in vals:
            pos = int((v - mn) / rng * height) if rng > 0 else 0
            if pos == row:
                line += "*"
            elif pos > row:
                line += " "
            else:
                line += " "
        lines.append(line)
    lines.append(f"         +{'-' * len(vals)}")
    return "\n".join(lines)


def main():
    print("=" * 100)
    print("  EQUITY CURVE SMOOTHNESS: BASE vs 0.8 vs 0.9")
    print("=" * 100)

    data = get_data()
    sim = build_module()
    bm_breaks = compute_bm_ratio(data["sw10"])

    for name, cfg in CONFIGS.items():
        print(f"\n{'#' * 100}")
        print(f"  {cfg['desc']}")
        print(f"{'#' * 100}")

        params = dict(cfg["params"])
        r = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                fine_ltf=data["fine"], **params)
        trades_all = r["ltf_trades"] if isinstance(r, dict) else r

        for thresh in [0.0, 0.8, 0.9]:
            filtered = filter_by_bm(trades_all, bm_breaks, thresh)
            net = net_of(filtered)
            rs = [float(t["r_multiple"]) for t in filtered]
            eq = equity_curve(filtered)

            # Drawdown stats
            peak = 0.0; cum = 0.0; mx_dd = 0; dd_start = 0; dd_end = 0
            cur_dd_start = 0
            for i, r_val in enumerate(rs):
                cum += r_val
                if cum > peak:
                    peak = cum
                    cur_dd_start = i + 1
                dd = peak - cum
                if dd > mx_dd:
                    mx_dd = dd
                    dd_start = cur_dd_start
                    dd_end = i + 1

            # Rolling DD
            rdd20 = rolling_dd(eq, 20)
            rdd50 = rolling_dd(eq, 50)
            max_rdd20 = max(rdd20) if rdd20 else 0
            max_rdd50 = max(rdd50) if rdd50 else 0
            avg_rdd20 = sum(rdd20) / len(rdd20) if rdd20 else 0
            avg_rdd50 = sum(rdd50) / len(rdd50) if rdd50 else 0

            # Max winning/losing streaks by R
            streak = 0; mx_win_streak = 0; mx_loss_streak = 0
            for r_val in rs:
                if r_val > 0:
                    streak += 1
                    mx_win_streak = max(mx_win_streak, streak)
                else:
                    streak = 0
                    mx_loss_streak = max(mx_loss_streak, streak)

            # Time underwater
            peak2 = 0; underwater_bars = 0; max_underwater = 0; cur_uw = 0
            for cum_val in eq:
                if cum_val > peak2: peak2 = cum_val; cur_uw = 0
                else: cur_uw += 1
                max_underwater = max(max_underwater, cur_uw)
                if cur_uw > 0: underwater_bars += 1
            uw_pct = underwater_bars / max(len(eq), 1) * 100

            # Monthly consistency
            monthly = defaultdict(float)
            for t in filtered:
                m = (t.get("exit_date") or t.get("entry_date") or "")[:7]
                monthly[m] += float(t["r_multiple"])
            pos_m = sum(1 for v in monthly.values() if v > 0)
            neg_m = sum(1 for v in monthly.values() if v <= 0)
            total_m = len(monthly)
            cons = pos_m / max(total_m, 1) * 100

            # Worst 5-trade drawdown
            worst_5 = 0
            for i in range(len(rs) - 4):
                chunk = rs[i:i+5]
                chunk_eq = [sum(chunk[:j+1]) for j in range(len(chunk))]
                chunk_peak = max(chunk_eq)
                chunk_dd = chunk_peak - chunk_eq[-1]
                worst_5 = max(worst_5, chunk_dd)

            # Worst 10-trade drawdown
            worst_10 = 0
            for i in range(len(rs) - 9):
                chunk = rs[i:i+10]
                chunk_eq = [sum(chunk[:j+1]) for j in range(len(chunk))]
                chunk_peak = max(chunk_eq)
                chunk_dd = chunk_peak - chunk_eq[-1]
                worst_10 = max(worst_10, chunk_dd)

            tag = "BASE" if thresh == 0.0 else f"min={thresh}"
            print(f"\n  --- {tag} (n={len(filtered)}, NET={net:+.1f}R) ---")
            print(f"  Max Drawdown:      {mx_dd:.1f}R  (trades {dd_start}-{dd_end})")
            print(f"  Worst 5-trade DD:  {worst_5:.1f}R")
            print(f"  Worst 10-trade DD: {worst_10:.1f}R")
            print(f"  Rolling 20t maxDD: {max_rdd20:.1f}R  avg: {avg_rdd20:.1f}R")
            print(f"  Rolling 50t maxDD: {max_rdd50:.1f}R  avg: {avg_rdd50:.1f}R")
            print(f"  Max underwater:    {max_underwater} trades ({uw_pct:.0f}% of time)")
            print(f"  Max win streak:    {mx_win_streak}")
            print(f"  Max loss streak:   {mx_loss_streak}")
            print(f"  Monthly consistency: {pos_m}/{total_m} profitable ({cons:.0f}%)")

        # Side-by-side smoothness
        print(f"\n  SMOOTHNESS COMPARISON:")
        print(f"  {'Metric':<24} {'BASE':>10} {'min=0.8':>10} {'min=0.9':>10} {'winner':>8}")
        print(f"  {'-'*65}")

        configs_data = {}
        for thresh in [0.0, 0.8, 0.9]:
            filtered = filter_by_bm(trades_all, bm_breaks, thresh)
            rs = [float(t["r_multiple"]) for t in filtered]
            eq = equity_curve(filtered)
            net = net_of(filtered)
            peak = 0.0; cum = 0.0; mx_dd = 0
            for r_val in rs:
                cum += r_val
                if cum > peak: peak = cum
                dd = peak - cum
                if dd > mx_dd: mx_dd = dd
            rdd20 = rolling_dd(eq, 20)
            rdd50 = rolling_dd(eq, 50)
            monthly = defaultdict(float)
            for t in filtered:
                m = (t.get("exit_date") or t.get("entry_date") or "")[:7]
                monthly[m] += float(t["r_multiple"])
            pos_m = sum(1 for v in monthly.values() if v > 0)
            total_m = len(monthly)
            peak2 = 0; uw = 0; max_uw = 0; cur_uw = 0
            for cv in eq:
                if cv > peak2: peak2 = cv; cur_uw = 0
                else: cur_uw += 1
                max_uw = max(max_uw, cur_uw)
                if cur_uw > 0: uw += 1
            configs_data[thresh] = {
                "net": net, "dd": mx_dd, "ndd": abs(net/mx_dd) if mx_dd > 0 else 0,
                "rdd20": max(rdd20) if rdd20 else 0,
                "rdd50": max(rdd50) if rdd50 else 0,
                "max_uw": max_uw, "uw_pct": uw/max(len(eq),1)*100,
                "pos_m": pos_m, "total_m": total_m,
                "cons": pos_m/max(total_m,1)*100,
            }

        comparisons = [
            ("Max DD", "dd", ".1f", "lower"),
            ("NET/DD", "ndd", ".2f", "higher"),
            ("Rolling 20t maxDD", "rdd20", ".1f", "lower"),
            ("Rolling 50t maxDD", "rdd50", ".1f", "lower"),
            ("Max underwater", "max_uw", "d", "lower"),
            ("Time underwater %", "uw_pct", ".1f", "lower"),
            ("Monthly consistency", "cons", ".1f", "higher"),
        ]

        for label, key, fmt, better in comparisons:
            b = configs_data[0.0][key]
            m8 = configs_data[0.8][key]
            m9 = configs_data[0.9][key]
            if better == "lower":
                winner = "0.8" if m8 <= m9 else "0.9"
                if b <= m8 and b <= m9: winner = "BASE"
            else:
                winner = "0.8" if m8 >= m9 else "0.9"
                if b >= m8 and b >= m9: winner = "BASE"
            if fmt == "d":
                print(f"  {label:<24} {b:>10d} {m8:>10d} {m9:>10d} {winner:>8}")
            else:
                print(f"  {label:<24} {format(b, fmt):>10} {format(m8, fmt):>10} {format(m9, fmt):>10} {winner:>8}")

        # Equity curve ASCII for 0.8 and 0.9
        print(f"\n  EQUITY CURVES:")
        for thresh in [0.8, 0.9]:
            filtered = filter_by_bm(trades_all, bm_breaks, thresh)
            eq = equity_curve(filtered)
            net = net_of(filtered)
            print(f"\n  --- min={thresh} (n={len(filtered)}, NET={net:+.1f}R) ---")
            # Compact: sample every N trades
            step = max(1, len(eq) // 60)
            sampled = eq[::step] + ([eq[-1]] if eq[-1] != eq[::step][-1] else [])
            print(draw_smooth(sampled, width=70, height=15))

    print()


if __name__ == "__main__":
    main()
