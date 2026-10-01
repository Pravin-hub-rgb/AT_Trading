"""Pivot-break trail (fix/more ideas.md) — path-true both-sides (2026-09-23).

exp_pivot_trail=1: instead of same-dir swing-start ratchet, trail to the
intervening min(low)/max(high) whenever a pivot high/low breaks.
  LONG  — pivot high = up-swing end; on break, SL = min low since last break/entry
  SHORT — pivot low  = down-swing end; on break, SL = max high since last break/entry

Identity basis: sw20 + coarse fills + BASE (340t/+225.3) via identity_gate().
Both-sides: IS (champion/king/swingpause) + OOS 2021-22 required.

Run: python backtest/tests/exp_pivot_trail.py
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


def run(sim, data, params, c15, sw15, c1h, sw, fine, **flags):
    kw = {**BP, **params, **flags}
    kw.setdefault("exp_partial_r", 0.0)
    out = sim(c1h, sw, c15, sw15, fine_ltf=fine, **kw)
    return out["ltf_trades"] if isinstance(out, dict) else out


def main():
    t0 = time.time()
    print("=" * 100)
    print("  PIVOT-BREAK TRAIL — exp_pivot_trail path-true both-sides")
    print("=" * 100)

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
    print(f"  OOS {len(c15o)}x15m, {len(c1ho)}x1h ({time.time()-t0:.0f}s)", flush=True)

    configs = [
        ("champion_multi_sw10", {**EXPERIMENTS["champion_multi_sw10"]["params"]},
         sw10, sw10o),
        ("utcsat_multi_sw10 (king)", {**EXPERIMENTS["utcsat_multi_sw10"]["params"]},
         sw10, sw10o),
        ("swingpause single", {
            **{k: v for k, v in EXPERIMENTS["dirmatch_swingpause_single_sw10"]["params"].items()
               if k not in ("exp_require_dir_match", "exp_max_swing_age", "exp_dir_causal")}
        }, sw10, sw10o),
    ]

    variants = [
        ("baseline (swing-start trail)", {}),
        ("pivot-break trail", dict(exp_pivot_trail=1)),
        # stack with trail_max_dist quality gate (known interaction)
        ("pivot + trail_max_dist=1.0", dict(exp_pivot_trail=1, exp_trail_max_dist=1.0)),
        ("pivot + trail_max_dist=0.6", dict(exp_pivot_trail=1, exp_trail_max_dist=0.6)),
        # stack with regime skip (marginal both-sides pass)
        ("pivot + regime>10", dict(exp_pivot_trail=1, exp_regime_skip=10.0)),
    ]

    for name, params, sw_is, sw_oos in configs:
        print("\n" + "=" * 100, flush=True)
        print(f"  PATH-TRUE — {name}", flush=True)
        print("=" * 100, flush=True)
        print(f"  {'variant':<40} {'IS n':>5} {'IS R':>9} {'dIS':>7} "
              f"{'OOS n':>6} {'OOS R':>9} {'dOOS':>7}", flush=True)
        base_is_r = base_oos_r = base_is_net = base_oos_net = None
        for label, flags in variants:
            tis = run(sim, data, params, c15, sw15, c1h, sw_is, fine_is, **flags)
            tos = run(sim, data, params, c15o, sw15o, c1ho, sw_oos, fineo, **flags)
            ri = sum(float(t["r_multiple"]) for t in tis)
            ro = sum(float(t["r_multiple"]) for t in tos)
            ni, no = net_r(tis), net_r(tos)
            if base_is_r is None:
                base_is_r, base_oos_r = ri, ro
                base_is_net, base_oos_net = ni, no
            both = (ri - base_is_r) >= 0 and (ro - base_oos_r) >= 0
            mark = "  BOTH" if both and label != "baseline (swing-start trail)" else ""
            print(f"  {label:<40} {len(tis):>5} {ri:>+9.1f} {ri-base_is_r:>+7.1f} "
                  f"{len(tos):>6} {ro:>+9.1f} {ro-base_oos_r:>+7.1f}   "
                  f"NET {ni:+.1f}/{no:+.1f}  dNET {ni-base_is_net:+.1f}/{no-base_oos_net:+.1f}{mark}",
                  flush=True)

    print(f"\n(done {time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
