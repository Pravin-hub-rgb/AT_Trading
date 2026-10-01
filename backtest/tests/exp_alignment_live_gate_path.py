"""Path-true LIVE-SNAPSHOT gates — the one open salvage path (2026-09-23).

RESULT 2026-09-23: DEAD — no gate ships. See EXPERIMENT_LOG + ANCHOR_BASIS_AUDIT.
  champion live_runmag=2.0: dIS -24.2 / dOOS -36.4 (hurts both)
  champion 3.0/4.0: noise (|d| < 8, mixed signs)
  king 3.0 OOS +21 but IS -7.5 — fails both-sides rule
  batch+causal ref still -108 dIS (selector leak, unchanged)
exp_max_live_runmag/exp_live_state REVERTED from the patcher (dead = clutter).
exp_dir_causal KEPT (D3 audit tool). This harness kept as tombstone record.
NOTE: re-running now raises TypeError on exp_max_live_runmag (intentional).

Salvage trade-list (causal live labels) — only bucket that passed the
§3e/§3f playbook rule (net-negative + negligible big-win):

  live run mag 2%+:  d:2-4 n=58 R=-8.6 bigW=2;  e:4+ n=4 R=-1.3 bigW=0

Everything else under live labels is POSITIVE (cannot cut per playbook):
  live dir   MATCH +297.5 / OPPOSED +147.7   (both good — opposite of leaky 125/125)
  live age   0-10 +175.1 / 11-25 +26.6 / 26-50 +106.8 / 51+ +136.7 (all good)
  body/risk/close_pos buckets all non-negative except risk 2%+ (already F7 DEAD)

Difference vs prior F1 test: exp_max_running_mag uses BATCH _gen_start
(leaky selector, or confirmed-only final start under exp_dir_causal).
This gate used PRECOMPUTED live forming-engine start_idx at bar i
(replay_live_state) — what live actually knows.

Run: python backtest/tests/exp_alignment_live_gate_path.py
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
from exp_alignment_live_state_audit import replay_live_state
from test_4_new_concepts import load_unseen, load_fine_1m as load_fine_unseen
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING


def run(sim, data, params, c15, sw15, c1h, sw, fine, **flags):
    kw = {**BP, **params, **flags}
    kw.setdefault("exp_partial_r", 0.0)
    out = sim(c1h, sw, c15, sw15, fine_ltf=fine, **kw)
    return out["ltf_trades"] if isinstance(out, dict) else out


def show(tag, trades, base_r=None):
    n = len(trades)
    r = sum(float(t["r_multiple"]) for t in trades)
    wr = 100.0 * sum(1 for t in trades if float(t["r_multiple"]) > 0) / max(n, 1)
    nd = net_r(trades)
    d = f"  dR={r - base_r:+.1f}" if base_r is not None else ""
    print(f"  {tag:<44} n={n:4d}  R={r:+8.1f}  WR={wr:5.1f}%  NET={nd:+8.1f}{d}")
    return r, nd


def main():
    t0 = time.time()
    print("=" * 100)
    print("  LIVE-SNAPSHOT GATE PATH-TRUE — exp_max_live_runmag (live start_idx)")
    print("=" * 100)

    data = get_data()
    identity_gate(data)
    sim = craze.build_module()
    fine_is = data["fine"]
    c15, sw15, c1h, sw10 = data["c15"], data["sw15"], data["c1h"], data["sw10"]

    print("replaying live state IS...", flush=True)
    live_is = replay_live_state(data["f15"], craze.MB15)
    print(f"  {len(live_is)} bars ({time.time()-t0:.0f}s)")

    # ---- OOS ----
    (c15o, f15o), (c1ho, f1ho) = load_unseen("15m"), load_unseen("1h")
    sw15o = _compute_swings(f15o, "continuous", min_bars=SWING["min_bars_15m"])
    sw10o = _compute_swings(f1ho, "continuous", min_bars=10)
    fineo = load_fine_unseen(c15o[0]["ts"], c15o[-1]["ts"])
    print(f"replaying live state OOS ({len(f15o)} bars)...", flush=True)
    t1 = time.time()
    live_oos = replay_live_state(f15o, craze.MB15)
    print(f"  {len(live_oos)} bars ({time.time()-t1:.0f}s)")

    # sanity: live_state length must cover all ltf indices
    assert len(live_is) == len(c15), f"live_is {len(live_is)} != c15 {len(c15)}"
    assert len(live_oos) == len(c15o), f"live_oos {len(live_oos)} != c15o {len(c15o)}"

    configs = [
        ("champion_multi_sw10", {**EXPERIMENTS["champion_multi_sw10"]["params"]}),
        ("swingpause single", {
            **{k: v for k, v in EXPERIMENTS["dirmatch_swingpause_single_sw10"]["params"].items()
               if k not in ("exp_require_dir_match", "exp_max_swing_age", "exp_dir_causal")}
        }),
    ]
    if "utcsat_multi_sw10" in EXPERIMENTS:
        configs.append(("utcsat_multi_sw10 (king)",
                        {**EXPERIMENTS["utcsat_multi_sw10"]["params"]}))

    for name, params in configs:
        print("\n" + "=" * 100)
        print(f"  PATH-TRUE — {name}")
        print("=" * 100)
        print(f"  {'variant':<44} {'IS n':>5} {'IS R':>9} {'dIS':>7} "
              f"{'OOS n':>6} {'OOS R':>9} {'dOOS':>7}")
        base_is_r = base_oos_r = None
        variants = [
            ("baseline", {}),
            ("live_runmag=2.0", dict(exp_max_live_runmag=2.0, exp_live_state=live_is)),
            ("live_runmag=3.0", dict(exp_max_live_runmag=3.0, exp_live_state=live_is)),
            ("live_runmag=4.0", dict(exp_max_live_runmag=4.0, exp_live_state=live_is)),
            ("batch runmag=2.0 +dir_causal (ref DEAD)",
             dict(exp_max_running_mag=2.0, exp_dir_causal=1)),
        ]
        for name_v, flags in variants:
            # OOS must use OOS live_state — swap when present
            flags_oos = dict(flags)
            if "exp_live_state" in flags_oos:
                flags_oos["exp_live_state"] = live_oos
            tis = run(sim, data, params, c15, sw15, c1h, sw10, fine_is, **flags)
            tos = run(sim, data, params, c15o, sw15o, c1ho, sw10o, fineo, **flags_oos)
            ri = sum(float(t["r_multiple"]) for t in tis)
            ro = sum(float(t["r_multiple"]) for t in tos)
            if base_is_r is None:
                base_is_r, base_oos_r = ri, ro
            print(f"  {name_v:<44} {len(tis):>5} {ri:>+9.1f} {ri-base_is_r:>+7.1f} "
                  f"{len(tos):>6} {ro:>+9.1f} {ro-base_oos_r:>+7.1f}   "
                  f"NET {net_r(tis):+.1f}/{net_r(tos):+.1f}")

    print(f"\n(done {time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
