"""Bias momentum sweep on BARE single — no swingpause, no wage, no weekend skip.
Just the base single config to see if bias momentum works without cascading gates."""
import sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data
from test_experiments_craze import build_module

THRESHOLDS = [0.0, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

# Bare single: just mode + basic params, NO swingpause/wage/weekend/chopband/ATR-ratio
BARE_SINGLE = {
    "mode": "atr_high", "atr_high_thresh": 0.65,
    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
    "chop_thresh": 58.0, "cooldown_bars": 0,
    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
    "exp_partial_r": 0.0, "window_end": "exit",
}

# Also test with just cd0 (no other gates)
CD0_SINGLE = dict(BARE_SINGLE, cooldown_bars=0)

# Also test with just swingpause (no wage/weekend)
SWPAUSE_SINGLE = dict(BARE_SINGLE, exp_swingpause=1)

# Also test with just wage (no swingpause/weekend)
WAGE10_SINGLE = dict(BARE_SINGLE, exp_wage_h=10)

# Also test with wage+cd0 (no swingpause/weekend)
WAGE10_CD0_SINGLE = dict(BARE_SINGLE, exp_wage_h=10, cooldown_bars=0)

# Full king (for reference)
FULL_SINGLE = dict(BARE_SINGLE, exp_swingpause=1, exp_skip_weekend=1,
                   exp_wage_h=10, exp_chop15_lo=55.0, exp_chop15_hi=61.0,
                   exp_atr_ratio_max=1.4)

CONFIGS = {
    "bare_single": {"desc": "bare single (no gates)", "params": BARE_SINGLE},
    "cd0_single": {"desc": "bare + cd0", "params": CD0_SINGLE},
    "swpause_single": {"desc": "bare + swingpause only", "params": SWPAUSE_SINGLE},
    "wage10_single": {"desc": "bare + wage10 only", "params": WAGE10_SINGLE},
    "wage10_cd0_single": {"desc": "bare + wage10 + cd0", "params": WAGE10_CD0_SINGLE},
    "full_single": {"desc": "full king (all gates)", "params": FULL_SINGLE},
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
    print("=" * 110)
    print("  BIAS MOMENTUM SWEEP — SINGLE CONFIGS (no cascading gates)")
    print("=" * 110)

    for cname, cfg in CONFIGS.items():
        print(f"\n{'#' * 110}")
        print(f"  {cfg['desc']}")
        print(f"{'#' * 110}")
        print(f"\n  {'Thresh':>7} {'n':>4} {'NET':>8} {'WR':>5} {'DD':>6} {'NET/DD':>7} {'dNET':>8}")
        print(f"  {'-'*60}")

        base_n, base_net, base_wr, base_dd, base_yearly = None, None, None, None, None
        for thresh in THRESHOLDS:
            t0 = time.time()
            n, net, wr, dd, yearly = run_cfg(cname, cfg, thresh)
            dt = time.time() - t0
            if thresh == 0.0:
                base_n, base_net, base_wr, base_dd, base_yearly = n, net, wr, dd, yearly
                dnet_s = "baseline"
            else:
                dnet = net - base_net
                dnet_s = f"{dnet:+.1f}R"
            ndd = abs(net / dd) if dd > 0 else 0
            tag = "BASE" if thresh == 0.0 else f"min={thresh}"
            print(f"  {tag:>7} {n:>4} {net:>+7.1f}R {wr:>4.1f}% {dd:>5.1f} {ndd:>6.2f}  {dnet_s}")

        # Yearly breakdown for base vs best threshold
        best_thresh = 0.0
        best_dnet = 0
        for thresh in [0.5, 0.6, 0.7, 0.8]:
            _, net_t, _, _, _ = run_cfg(cname, cfg, thresh)
            dnet = net_t - base_net
            if dnet > best_dnet:
                best_dnet = dnet
                best_thresh = thresh

        if best_thresh > 0:
            _, net_best, _, _, yearly_best = run_cfg(cname, cfg, best_thresh)
            print(f"\n  YEARLY (BASE vs best={best_thresh}):")
            print(f"  {'Year':>6} {'BASE':>8} {f'bm={best_thresh}':>8} {'Delta':>8}")
            print(f"  {'-'*35}")
            all_years = sorted(set(list(base_yearly.keys()) + list(yearly_best.keys())))
            for y in all_years:
                b = base_yearly.get(y, 0.0)
                v = yearly_best.get(y, 0.0)
                d = v - b
                print(f"  {y:>6} {b:>+7.1f}R {v:>+7.1f}R {d:>+7.1f}R")
            print(f"  {'TOTAL':>6} {base_net:>+7.1f}R {net_best:>+7.1f}R {net_best-base_net:>+7.1f}R")

    print()


if __name__ == "__main__":
    main()
