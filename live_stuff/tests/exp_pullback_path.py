"""Path-true A4 pullback gate — skip entries 1.5-3R off the leg extreme.

Autopsy (exp48_leg_progress.py, A4 w0):
  pullback off leg high:
    <0.5R   avgR +0.34
    0.5-1.5 avgR +2.46 (86t)  ← the good band (0.5-1.5 retest)
    1.5-3R  avgR -0.54 (24t)  ← no-man's land (candidate gate)
    >=3R    not reported as good
  lb30: 1.5-3R avgR +0.12 (flat) — gate is A4-specific, not universal.

Gate (craze kwargs, default off):
  exp_pb_lo / exp_pb_hi  skip if pullback_R in [lo, hi]
  Causal: leg anchor = first window of same-dir streak (past closed windows);
  extreme = max/min 1h high/low from anchor to signal bar.

Run: python live_stuff/tests/exp_pullback_path.py
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data, BP, identity_gate, net_r
import test_experiments_craze as craze
from experiment_registry import EXPERIMENTS
from test_4_new_concepts import load_unseen, load_fine_1m as load_fine_unseen
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING


def run(sim, params, c15, sw15, c1h, sw, fine, **flags):
    kw = {**BP, **params, **flags}
    kw.setdefault("exp_partial_r", 0.0)
    out = sim(c1h, sw, c15, sw15, fine_ltf=fine, **kw)
    return out["ltf_trades"] if isinstance(out, dict) else out


def full(trades):
    rs = [float(t["r_multiple"]) for t in trades]
    n = len(rs)
    if n == 0:
        return "n=0"
    net = sum(rs)
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x <= 0]
    wr = 100.0 * len(wins) / n
    peak = cum = dd = 0.0
    for x in rs:
        cum += x
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    pw = sum(wins)
    pl = abs(sum(losses))
    pf = (pw / pl) if pl > 0 else float("inf")
    avgw = (pw / len(wins)) if wins else 0.0
    avgl = (pl / len(losses)) if losses else 0.0
    pf_s = f"{pf:.2f}" if pf != float("inf") else "inf"
    return (f"n={n:4d} NET={net:+8.1f} WR={wr:5.1f}% R/t={net/n:+.3f} "
            f"PF={pf_s:>5} avgW={avgw:+.2f} avgL={avgl:.2f} DD={dd:.1f}")


def main():
    t0 = time.time()
    print("=" * 100)
    print("  PATH-TRUE A4 PULLBACK GATE — skip pb in [lo,hi] off leg extreme")
    print("=" * 100)

    data = get_data()
    identity_gate(data)
    sim = craze.build_module()
    c15, sw15, c1h, sw10, sw20 = (data["c15"], data["sw15"], data["c1h"],
                                   data["sw10"], data["sw20"])
    fine_is = data["fine"]

    print("loading OOS...", flush=True)
    (c15o, f15o), (c1ho, f1ho) = load_unseen("15m"), load_unseen("1h")
    sw15o = _compute_swings(f15o, "continuous", min_bars=SWING["min_bars_15m"])
    sw10o = _compute_swings(f1ho, "continuous", min_bars=10)
    fineo = load_fine_unseen(c15o[0]["ts"], c15o[-1]["ts"])
    print(f"  OOS loaded ({time.time()-t0:.0f}s)", flush=True)

    # A4 = lb30 + chop55 + persist2, sw10 swings, ext1.5
    # Also test lb30 (flat autopsy) + champion for generality
    configs = [
        ("A4 w0 ext1.5", sw10, sw10o, {
            **{k: v for k, v in EXPERIMENTS.get("a4_w24_ext1.5", {}).get("params", {}).items()
               if k not in ("exp_wage_h",)},
        }),
        ("lb30 w0 ext1.5", sw20, sw20o if False else sw10o, {  # sw20o built below
            "exp31_lb": 30, "ext_stop_r": 1.5,
        }),
    ]
    # Build sw20 for OOS properly
    sw20o = _compute_swings(f1ho, "continuous", min_bars=SWING["min_bars_1h"])
    configs[1] = ("lb30 w0 ext1.5", sw20, sw20o, {"exp31_lb": 30, "ext_stop_r": 1.5})

    # Fix A4 params if registry empty
    a4_params = {"exp31_lb": 30, "chop_thresh": 55.0, "exp_persist": 2,
                 "ext_stop_r": 1.5}
    configs[0] = ("A4 w0 ext1.5", sw10, sw10o, a4_params)

    variants = [
        ("baseline", {}),
        ("pb 1.5-3.0 (no-man)", dict(exp_pb_lo=1.5, exp_pb_hi=3.0)),
        ("pb 1.5-4.0", dict(exp_pb_lo=1.5, exp_pb_hi=4.0)),
        ("pb 1.0-3.0", dict(exp_pb_lo=1.0, exp_pb_hi=3.0)),
        ("pb >=1.5 (open hi)", dict(exp_pb_lo=1.5)),
        ("pb >=2.0 (open hi)", dict(exp_pb_lo=2.0)),
        ("pb 1.5-3.0 + skip <0.5", dict(exp_pb_lo=0.5, exp_pb_hi=3.0)),  # also cut too-close
    ]

    results = []
    for name, sw_is, sw_oos, params in configs:
        print("\n" + "=" * 100, flush=True)
        print(f"  {name}  params={params}", flush=True)
        print("=" * 100, flush=True)
        base_is = base_oos = None
        for label, flags in variants:
            tr_i = run(sim, params, c15, sw15, c1h, sw_is, fine_is, **flags)
            tr_o = run(sim, params, c15o, sw15o, c1ho, sw_oos, fineo, **flags)
            n_is, n_o = len(tr_i), len(tr_o)
            g_is = sum(float(t["r_multiple"]) for t in tr_i)
            g_o = sum(float(t["r_multiple"]) for t in tr_o)
            net_is, net_o = net_r(tr_i), net_r(tr_o)
            if base_is is None:
                base_is = (n_is, g_is, net_is)
                base_oos = (n_o, g_o, net_o)
            d_is, d_o = g_is - base_is[1], g_o - base_oos[1]
            print(f"  {label:<28} IS  {full(tr_i)}", flush=True)
            print(f"  {'':28} OOS {full(tr_o)}", flush=True)
            print(f"  {'':28} dIS={d_is:+.1f} dOOS={d_o:+.1f} "
                  f"NET I/O={net_is:+.1f}/{net_o:+.1f}", flush=True)
            results.append((name, label, n_is, g_is, net_is, n_o, g_o, net_o, d_is, d_o))

    print("\n" + "=" * 100, flush=True)
    print("  SUMMARY (research comparison: both-sides deltas; no fixed ship threshold)", flush=True)
    print("=" * 100, flush=True)
    print(f"  {'config':<22} {'variant':<24} {'dIS':>7} {'dOOS':>7} {'NET I/O':>16}", flush=True)
    for name, label, n_is, g_is, net_is, n_o, g_o, net_o, d_is, d_o in results:
        if label == "baseline":
            continue
        mark = " *" if (d_is > 5 and d_o > 5) else ""
        print(f"  {name:<22} {label:<24} {d_is:>+7.1f} {d_o:>+7.1f} "
              f"{net_is:>+7.1f}/{net_o:>+7.1f}{mark}", flush=True)

    print("\n  baselines:", flush=True)
    for name, label, n_is, g_is, net_is, n_o, g_o, net_o, d_is, d_o in results:
        if label == "baseline":
            print(f"  {name:<22} IS n={n_is} {g_is:+.1f}R net={net_is:+.1f} | "
                  f"OOS n={n_o} {g_o:+.1f}R net={net_o:+.1f}", flush=True)

    print(f"\n(done in {time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
