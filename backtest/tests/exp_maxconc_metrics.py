"""Full metrics dump: exp_max_concurrent caps + report helper.
n/NET/WR/R-per-trade/avgW/avgL/PF/DD/streak for cap 0/2/3/4/5 × 3 bases × IS+OOS.
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data, BP, identity_gate, net_r
import test_experiments_craze as craze
from experiment_registry import EXPERIMENTS
from test_4_new_concepts import load_unseen, load_fine_1m as load_fine_unseen
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING


def full_stats(tr):
    if not tr:
        return dict(n=0, net=0.0, wr=0.0, rpt=0.0, aw=0.0, al=0.0, pf=0.0,
                    dd=0.0, streak=0)
    rs = [float(t["r_multiple"]) for t in tr]
    nets = [net_r([t]) for t in tr]
    wins = [r for r in nets if r > 0]
    loss = [r for r in nets if r <= 0]
    net = sum(nets)
    wr = 100.0 * len(wins) / len(nets)
    aw = sum(wins) / len(wins) if wins else 0.0
    al = sum(loss) / len(loss) if loss else 0.0
    gp = sum(wins) if wins else 0.0
    gl = -sum(loss) if loss else 0.0
    pf = gp / gl if gl > 0 else float("inf")
    eq = 0.0
    peak = 0.0
    dd = 0.0
    mx = cur = 0
    for v in nets:
        eq += v
        if eq > peak:
            peak = eq
        d = peak - eq
        if d > dd:
            dd = d
        if v > 0:
            cur += 1
            if cur > mx:
                mx = cur
        else:
            cur = 0
    return dict(n=len(nets), net=net, wr=wr, rpt=net / len(nets),
                aw=aw, al=al, pf=pf, dd=dd, streak=mx)


def fmt(s):
    pf = s["pf"]
    pfs = "inf" if pf == float("inf") else f"{pf:.2f}"
    return (f"n={s['n']:>4} NET={s['net']:+8.1f} WR={s['wr']:5.1f}% "
            f"R/t={s['rpt']:+.3f} avgW={s['aw']:+.2f} avgL={s['al']:+.2f} "
            f"PF={pfs:>5} DD={s['dd']:5.1f} streak={s['streak']:>2}")


def run(sim, params, c15, sw15, c1h, sw, fine, **flags):
    kw = {**BP, **params, **flags}
    kw.setdefault("exp_partial_r", 0.0)
    out = sim(c1h, sw, c15, sw15, fine_ltf=fine, **kw)
    return out["ltf_trades"] if isinstance(out, dict) else out


def main():
    t0 = time.time()
    print("=" * 110)
    print("  MAXCONCURRENT FULL METRICS — cap 0/2/3/4/5 × champion/king/swingpause × IS+OOS")
    print("=" * 110)

    data = get_data()
    identity_gate(data)
    sim = craze.build_module()
    c15, sw15, c1h, sw10 = data["c15"], data["sw15"], data["c1h"], data["sw10"]
    fine_is = data["fine"]

    print("loading OOS...", flush=True)
    (c15o, f15o), (c1ho, f1ho) = load_unseen("15m"), load_unseen("1h")
    sw15o = _compute_swings(f15o, "continuous", min_bars=SWING["min_bars_15m"])
    sw10o = _compute_swings(f1ho, "continuous", min_bars=10)
    fineo = load_fine_unseen(c15o[0]["ts"], c15o[-1]["ts"])
    print(f"  OOS ready ({time.time()-t0:.0f}s)", flush=True)

    configs = [
        ("champion_multi_sw10", {**EXPERIMENTS["champion_multi_sw10"]["params"]}, sw10, sw10o),
        ("utcsat_multi_sw10 (king)", {**EXPERIMENTS["utcsat_multi_sw10"]["params"]}, sw10, sw10o),
        ("swingpause single", {
            **{k: v for k, v in EXPERIMENTS["dirmatch_swingpause_single_sw10"]["params"].items()
               if k not in ("exp_require_dir_match", "exp_max_swing_age", "exp_dir_causal")}
        }, sw10, sw10o),
    ]
    variants = [
        ("baseline (no cap)", {}),
        ("cap=2", dict(exp_max_concurrent=2)),
        ("cap=3", dict(exp_max_concurrent=3)),
        ("cap=4", dict(exp_max_concurrent=4)),
        ("cap=5", dict(exp_max_concurrent=5)),
    ]

    for name, params, sw_is, sw_oos in configs:
        print("\n" + "=" * 110, flush=True)
        print(f"  {name}  multi={params.get('exp_mltf', False)}", flush=True)
        print("=" * 110, flush=True)
        for label, flags in variants:
            tis = run(sim, params, c15, sw15, c1h, sw_is, fine_is, **flags)
            tos = run(sim, params, c15o, sw15o, c1ho, sw_oos, fineo, **flags)
            si, so = full_stats(tis), full_stats(tos)
            print(f"  {label:<22} IS  {fmt(si)}", flush=True)
            print(f"  {'':<22} OOS {fmt(so)}", flush=True)

    print(f"\n(done {time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
