"""Path-true retest of SALVAGE candidates from D3 autopsy.

All candidates are causal at entry (no final-chain labels).
Identity basis: sw20 + coarse fills + BASE (340t/+225.3), via identity_gate().

Candidates:
  1. exp_max_running_mag — path NEVER run alone (only wired in patcher);
     autopsy said 4%+ = -0.83R. Try cut lines 1.5/2/3/4.
  2. risk_max 2.0 — NEW cut line (1.0/1.5 already DEAD in §3e).
  3. body_min 0.2 — known DEAD path (EXPERIMENT_LOG 2026-09-14); ref only.
  4. SKIP early-exit — trade-list DEAD in salvage E.
  SKIP stacks that already lose R on trade-list (§3e playbook).

Run: python live_stuff/tests/exp_alignment_salvage_path.py
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


def run_one(data, sim, params, label, **extra):
    kw = {**BP, **params, **extra}
    kw.setdefault("exp_partial_r", 0.0)
    out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
              fine_ltf=data["fine"], **kw)
    trades = out["ltf_trades"]
    n = len(trades)
    r_sum = sum(float(t["r_multiple"]) for t in trades)
    wr = 100.0 * sum(1 for t in trades if float(t["r_multiple"]) > 0) / max(n, 1)
    nd = net_r(trades)
    print(f"  {label:<42} n={n:4d}  R={r_sum:+8.1f}  WR={wr:5.1f}%  NET={nd:+8.1f}")
    return n, r_sum, nd


def main():
    t0 = time.time()
    data = get_data()
    identity_gate(data)
    sim = craze.build_module()

    ch_params = {**EXPERIMENTS["champion_multi_sw10"]["params"]}
    print("\n=== CHAMPION multi (ref) ===")
    base = run_one(data, sim, ch_params, "champion (no salvage gate)")
    base_r = base[1]

    print("\n=== A. running_mag (path-true) — raw then exp_dir_causal=1 ===")
    for mag in (0.5, 1.0, 1.5, 2.0, 3.0, 4.0):
        n, rs, nd = run_one(data, sim, ch_params, f"runmag_max={mag}",
                            exp_max_running_mag=mag)
        print(f"      dR vs base = {rs - base_r:+.1f}")
    print("\n--- A2. running_mag with confirmed_at<=i (causal start) ---")
    for mag in (1.5, 2.0, 3.0, 4.0):
        n, rs, nd = run_one(
            data, sim, ch_params, f"runmag={mag} + dir_causal",
            exp_max_running_mag=mag, exp_dir_causal=1)
        print(f"      dR vs base = {rs - base_r:+.1f}")

    print("\n=== B. risk_max cut lines ===")
    for rm in (2.0, 2.5, 3.0):
        n, rs, nd = run_one(data, sim, ch_params, f"risk_max={rm}",
                            exp_risk_max_pct=rm)
        print(f"      dR vs base = {rs - base_r:+.1f}")

    print("\n=== C. body_min (known DEAD ref only) ===")
    n, rs, nd = run_one(data, sim, ch_params, "entry_candle_min=0.2",
                        exp_entry_candle_min=0.2)
    print(f"      dR vs base = {rs - base_r:+.1f}  NET delta = {nd - base[2]:+.1f}")

    # single: swingpause base without dirmatch
    key = "dirmatch_swingpause_single_sw10"
    if key in EXPERIMENTS:
        sp = {**EXPERIMENTS[key]["params"]}
        sp.pop("exp_require_dir_match", None)
        sp.pop("exp_max_swing_age", None)
        sp.pop("exp_dir_causal", None)
        print("\n=== SINGLE swingpause (ref) ===")
        sbase = run_one(data, sim, sp, "single swingpause base")
        sr, snet = sbase[1], sbase[2]
        for mag in (1.5, 2.0, 4.0):
            n, rs, nd = run_one(data, sim, sp, f"single runmag_max={mag}",
                                exp_max_running_mag=mag)
            print(f"      dR vs base = {rs - sr:+.1f}  dNET = {nd - snet:+.1f}")
        print("--- single runmag + dir_causal ---")
        for mag in (1.5, 2.0):
            n, rs, nd = run_one(
                data, sim, sp, f"single runmag={mag} + dir_causal",
                exp_max_running_mag=mag, exp_dir_causal=1)
            print(f"      dR vs base = {rs - sr:+.1f}  dNET = {nd - snet:+.1f}")
        run_one(data, sim, sp, "single + rmax2", exp_risk_max_pct=2.0)

    print(f"\n(done {time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
