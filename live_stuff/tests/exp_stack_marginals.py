"""Stack the two both-sides marginal passes: flip-break x regime-skip.

Prior single results (2026-09-23):
  exp_flip_break on swingpause:     dIS +7.6 / dOOS +8.3
  exp_regime_skip=10 on champion:   dIS +30.9 / dOOS +2.3
  exp_regime_skip=10 on swingpause: dIS +4.8 / dOOS +6.2

Test: can stacking improve both sides? Also: flip-break x regime_skip on swingpause (both flags together). No fixed R/year ship gate.

Run: python live_stuff/tests/exp_stack_marginals.py
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


def run(sim, data, params, c15, sw15, c1h, sw, fine, **flags):
    kw = {**BP, **params, **flags}
    kw.setdefault("exp_partial_r", 0.0)
    out = sim(c1h, sw, c15, sw15, fine_ltf=fine, **kw)
    return out["ltf_trades"] if isinstance(out, dict) else out


def main():
    t0 = time.time()
    print("=" * 100)
    print("  STACK MARGINALS — flip-break x regime-skip (both-sides survivors)")
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
    print(f"  OOS ready ({time.time()-t0:.0f}s)", flush=True)

    sp_params = {
        **{k: v for k, v in EXPERIMENTS["dirmatch_swingpause_single_sw10"]["params"].items()
           if k not in ("exp_require_dir_match", "exp_max_swing_age", "exp_dir_causal")}
    }
    ch_params = {**EXPERIMENTS["champion_multi_sw10"]["params"]}
    king_params = {**EXPERIMENTS["utcsat_multi_sw10"]["params"]}

    configs = [
        ("swingpause single", sp_params, sw10, sw10o, [
            ("baseline", {}),
            ("flip-break alone", dict(exp_flip_break=1)),
            ("regime>10 alone", dict(exp_regime_skip=10.0)),
            ("regime>8 alone", dict(exp_regime_skip=8.0)),
            ("regime>12 alone", dict(exp_regime_skip=12.0)),
            ("STACK flip+reg10", dict(exp_flip_break=1, exp_regime_skip=10.0)),
            ("STACK flip+reg8", dict(exp_flip_break=1, exp_regime_skip=8.0)),
            ("STACK flip+reg12", dict(exp_flip_break=1, exp_regime_skip=12.0)),
        ]),
        ("champion_multi_sw10", ch_params, sw10, sw10o, [
            ("baseline", {}),
            ("regime>10 alone", dict(exp_regime_skip=10.0)),
            ("regime>8 alone", dict(exp_regime_skip=8.0)),
            ("flip+reg10", dict(exp_flip_break=1, exp_regime_skip=10.0)),
            ("flip+reg8", dict(exp_flip_break=1, exp_regime_skip=8.0)),
        ]),
        ("utcsat_multi_sw10 (king)", king_params, sw10, sw10o, [
            ("baseline", {}),
            ("regime>10 alone", dict(exp_regime_skip=10.0)),
            ("regime>20 alone", dict(exp_regime_skip=20.0)),
            ("flip+reg10", dict(exp_flip_break=1, exp_regime_skip=10.0)),
            ("flip+reg20", dict(exp_flip_break=1, exp_regime_skip=20.0)),
        ]),
    ]

    for name, params, sw_is, sw_oos, variants in configs:
        print("\n" + "=" * 100, flush=True)
        print(f"  {name}", flush=True)
        print("=" * 100, flush=True)
        print(f"  {'variant':<48} {'IS n':>5} {'IS R':>9} {'dIS':>7} "
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
            dIS, dOOS = ni - base_is_net, no - base_oos_net
            both = dIS >= 0 and dOOS >= 0
            mark = "  BOTH" if both and label != "baseline" else ""
            print(f"  {label:<48} {len(tis):>5} {ri:>+9.1f} {ri-base_is_r:>+7.1f} "
                  f"{len(tos):>6} {ro:>+9.1f} {ro-base_oos_r:>+7.1f}   "
                  f"NET {ni:+.1f}/{no:+.1f}  dNET {dIS:+.1f}/{dOOS:+.1f}{mark}",
                  flush=True)

    print(f"\n(done {time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
