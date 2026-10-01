"""Fine-grained threshold sweep: 0.5, 0.6, 0.7, 0.8, 0.9, 1.0"""
import sys, bisect
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
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

THRESHOLDS = [0.0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]


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


def dd_of(tr):
    eq = 0.0; peak = 0.0; mx = 0.0
    for t in tr:
        eq += float(t["r_multiple"])
        if eq > peak: peak = eq
        d = peak - eq
        if d > mx: mx = d
    return mx


def main():
    print("=" * 100)
    print("  BIAS MOMENTUM FINE SWEEP: 0.5, 0.6, 0.7, 0.8, 0.9, 1.0")
    print("  (cost-adjusted NET R)")
    print("=" * 100)

    data = get_data()
    sim = build_module()
    bm_breaks = compute_bm_ratio(data["sw10"])

    for name, cfg in CONFIGS.items():
        print(f"\n  [{cfg['desc']}]")
        print(f"  {'Thresh':>7} {'n':>4} {'NET':>8} {'DD':>6} {'NET/DD':>7} {'WR':>5} {'AvgR':>7} {'PF':>6} {'dNET':>8} {'dDD':>7}")
        print(f"  {'-'*72}")

        params = dict(cfg["params"])
        r = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                fine_ltf=data["fine"], **params)
        trades_all = r["ltf_trades"] if isinstance(r, dict) else r

        base_net = net_of(trades_all)
        base_dd = dd_of(trades_all)
        base_wr = len([t for t in trades_all if float(t["r_multiple"]) > 0]) / max(len(trades_all), 1) * 100
        base_avg = sum(float(t["r_multiple"]) for t in trades_all) / max(len(trades_all), 1)
        base_pf = sum(float(t["r_multiple"]) for t in trades_all if float(t["r_multiple"]) > 0) / max(abs(sum(float(t["r_multiple"]) for t in trades_all if float(t["r_multiple"]) <= 0)), 0.01)
        base_ndd = abs(base_net / base_dd) if base_dd > 0 else 0

        print(f"  {'BASE':>7} {len(trades_all):>4} {base_net:>+7.1f}R {base_dd:>5.1f} {base_ndd:>6.2f} {base_wr:>4.1f}% {base_avg:>+6.3f} {base_pf:>5.2f}  {'baseline':>12}")

        for thresh in THRESHOLDS[1:]:
            filtered = filter_by_bm(trades_all, bm_breaks, thresh)
            nf = net_of(filtered)
            ddf = dd_of(filtered)
            wrf = len([t for t in filtered if float(t["r_multiple"]) > 0]) / max(len(filtered), 1) * 100
            avgf = sum(float(t["r_multiple"]) for t in filtered) / max(len(filtered), 1)
            pf = sum(float(t["r_multiple"]) for t in filtered if float(t["r_multiple"]) > 0) / max(abs(sum(float(t["r_multiple"]) for t in filtered if float(t["r_multiple"]) <= 0)), 0.01)
            nddf = abs(nf / ddf) if ddf > 0 else 0
            dn = len(filtered) - len(trades_all)
            dnet = nf - base_net
            ddd = ddf - base_dd
            print(f"  {thresh:>7} {len(filtered):>4} {nf:>+7.1f}R {ddf:>5.1f} {nddf:>6.2f} {wrf:>4.1f}% {avgf:>+6.3f} {pf:>5.2f} {dnet:>+7.1f}R {ddd:>+6.1f}")

    print()


if __name__ == "__main__":
    main()
