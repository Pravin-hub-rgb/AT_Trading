"""Idea A — HMM regime router path-true both-sides (2026-09-23).

HMM: 2-state Gaussian on 1h log-returns; train first 45%, forward-filter full
series. mode=hmm  → P(range)*100 > chop_thresh → B2 else FLIP.
     mode=hmm_inv → opposite.

Identity basis: sw20 + coarse fills + BASE (340t/+225.3) via identity_gate().
Both-sides: IS (champion/king/swingpause) + OOS 2021-22 required.

Run: python live_stuff/tests/exp_hmm_path.py
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
    print("  HMM REGIME ROUTER — Idea A path-true both-sides")
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
    print(f"  OOS {len(c15o)}x15m, {len(c1ho)}x1h ({time.time()-t0:.0f}s)", flush=True)

    configs = [
        ("champion_multi_sw10", {**EXPERIMENTS["champion_multi_sw10"]["params"]},
         sw10, sw10o),
        ("swingpause single", {
            **{k: v for k, v in EXPERIMENTS["dirmatch_swingpause_single_sw10"]["params"].items()
               if k not in ("exp_require_dir_match", "exp_max_swing_age", "exp_dir_causal")}
        }, sw10, sw10o),
    ]
    if "utcsat_multi_sw10" in EXPERIMENTS:
        configs.insert(1, ("utcsat_multi_sw10 (king)",
                           {**EXPERIMENTS["utcsat_multi_sw10"]["params"]},
                           sw10, sw10o))

    # variants: mode + chop_thresh (HMM score is 0-100)
    variants = [
        ("baseline", {}),
        ("hmm ct=50", dict(mode="hmm", chop_thresh=50.0)),
        ("hmm ct=55", dict(mode="hmm", chop_thresh=55.0)),
        ("hmm ct=58", dict(mode="hmm", chop_thresh=58.0)),
        ("hmm ct=61", dict(mode="hmm", chop_thresh=61.0)),
        ("hmm_inv ct=58", dict(mode="hmm_inv", chop_thresh=58.0)),
    ]

    for name, params, sw_is, sw_oos in configs:
        print("\n" + "=" * 100, flush=True)
        print(f"  PATH-TRUE — {name}", flush=True)
        print("=" * 100, flush=True)
        print(f"  {'variant':<48} {'IS n':>5} {'IS R':>9} {'dIS':>7} "
              f"{'OOS n':>6} {'OOS R':>9} {'dOOS':>7}", flush=True)
        base_is_r = base_oos_r = None
        base_is_net = base_oos_net = None
        for label, flags in variants:
            tis = run(sim, data, params, c15, sw15, c1h, sw_is, fine_is, **flags)
            tos = run(sim, data, params, c15o, sw15o, c1ho, sw_oos, fineo, **flags)
            ri = sum(float(t["r_multiple"]) for t in tis)
            ro = sum(float(t["r_multiple"]) for t in tos)
            ni, no = net_r(tis), net_r(tos)
            if base_is_r is None:
                base_is_r, base_oos_r = ri, ro
                base_is_net, base_oos_net = ni, no
            print(f"  {label:<48} {len(tis):>5} {ri:>+9.1f} {ri-base_is_r:>+7.1f} "
                  f"{len(tos):>6} {ro:>+9.1f} {ro-base_oos_r:>+7.1f}   "
                  f"NET {ni:+.1f}/{no:+.1f}  dNET {ni-base_is_net:+.1f}/{no-base_oos_net:+.1f}",
                  flush=True)

    print(f"\n(done {time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
