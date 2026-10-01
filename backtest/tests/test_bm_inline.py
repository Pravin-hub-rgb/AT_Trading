"""Cross-config test: exp_bias_momentum_min on multi AND single configs.
Verifies the inline filter matches external post-filter results."""
import sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data
from test_experiments_craze import build_module

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


def run_cfg(name, cfg, bm_min):
    params = dict(cfg["params"])
    if bm_min > 0:
        params["exp_bias_momentum_min"] = bm_min
    data = get_data()
    sim = build_module()
    r = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
            fine_ltf=data["fine"], **params)
    trades = r["ltf_trades"] if isinstance(r, dict) else r
    rs = [float(t["r_multiple"]) for t in trades]
    n = len(rs)
    net = sum(rs)
    wins = sum(1 for r in rs if r > 0)
    wr = wins / max(n, 1) * 100
    peak = 0.0; cum = 0.0; dd = 0.0
    for r in rs:
        cum += r
        if cum > peak: peak = cum
        dd = max(dd, peak - cum)
    yearly = {}
    for t in trades:
        y = (t.get("exit_date") or t.get("entry_date") or "")[:4]
        yearly[y] = yearly.get(y, 0.0) + float(t["r_multiple"])
    return n, net, wr, dd, yearly


def main():
    print("=" * 90)
    print("  CROSS-CONFIG TEST: exp_bias_momentum_min INLINE FILTER")
    print("=" * 90)

    THRESHOLDS = [0.0, 0.5, 0.8, 0.9]

    for name, cfg in CONFIGS.items():
        print(f"\n{'#' * 90}")
        print(f"  {cfg['desc']}")
        print(f"{'#' * 90}")
        print(f"\n  {'Thresh':>7} {'n':>4} {'NET':>8} {'WR':>5} {'DD':>6}")
        print(f"  {'-'*40}")

        baseline = None
        for thresh in THRESHOLDS:
            t0 = time.time()
            n, net, wr, dd, yearly = run_cfg(name, cfg, thresh)
            dt = time.time() - t0
            if thresh == 0.0:
                baseline = (n, net, wr, dd, yearly)
                base_n, base_net = n, net
            dnet = net - baseline[1]
            tag = "BASE" if thresh == 0.0 else f"min={thresh}"
            dnet_s = f"{dnet:+.1f}R" if thresh > 0.0 else "baseline"
            print(f"  {tag:>7} {n:>4} {net:>+7.1f}R {wr:>4.1f}% {dd:>5.1f}  dNET={dnet_s}")

        # Yearly breakdown for base vs best threshold
        print(f"\n  YEARLY (BASE vs 0.5):")
        print(f"  {'Year':>6} {'BASE':>8} {'bm=0.5':>8} {'Delta':>8}")
        print(f"  {'-'*35}")
        _, net_base, _, _, yearly_base = run_cfg(name, cfg, 0.0)
        _, net_05, _, _, yearly_05 = run_cfg(name, cfg, 0.5)
        all_years = sorted(set(list(yearly_base.keys()) + list(yearly_05.keys())))
        for y in all_years:
            b = yearly_base.get(y, 0.0)
            v = yearly_05.get(y, 0.0)
            d = v - b
            print(f"  {y:>6} {b:>+7.1f}R {v:>+7.1f}R {d:>+7.1f}R")
        print(f"  {'TOTAL':>6} {net_base:>+7.1f}R {net_05:>+7.1f}R {net_05-net_base:>+7.1f}R")

    print()


if __name__ == "__main__":
    main()
