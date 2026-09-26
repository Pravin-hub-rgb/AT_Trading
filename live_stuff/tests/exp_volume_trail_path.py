"""Path-true volume TRAIL/EXIT — dry-hold BE/exit + no-spike abort + climax.

Loss autopsy (exp_volume_loss_autopsy.py, 351t):
  - entry rvol/pct: win≈loss medians — USELESS as entry gate (confirmed)
  - hold expansion exp<0.7 (dry): 114t WR12% NET -75.3  ← the losses
  - hold expansion exp>=1.3 (flood): 106t WR39% NET +226.6 ← the edge
  - quiet entry + dry hold: 98t WR9% NET -72.1
  - r_max<2 during hold: 87t ALL -1R (never saw a volume spike)
  - SL dry-up: 60t -60R; trail-loss with r_max>=3: 86t -65.9R

Gates (exit-side / trail-side, NOT entry-quality):
  exp_vol_dry_exit=T  after dry_bars, running hold exp < T:
                      -> exit close "voldry"  (or BE if dry_be>0)
  exp_vol_dry_be=1    same but only move SL to entry when in profit
  exp_vol_nospk=R     max rvol since entry < R after nospk_bars & R<=0 -> exit
  exp_vol_exit_r=R    adverse bar with rvol>=R while underwater -> exit close
  exp_vol_route=T     REGIME router: rvol<T -> flip else b2 (and inverse)

Run: python live_stuff/tests/exp_volume_trail_path.py
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
    print("  PATH-TRUE VOLUME TRAIL/EXIT — dry BE/exit + nospk + climax + router")
    print("=" * 100)

    data = get_data()
    identity_gate(data)
    sim = craze.build_module()
    c15, sw15, c1h, sw10 = data["c15"], data["sw15"], data["c1h"], data["sw10"]
    fine_is = data["fine"]

    vmiss = sum(1 for c in c15 if not (c.get("volume") or 0))
    print(f"  IS 15m missing volume: {vmiss}/{len(c15)}", flush=True)

    print("loading OOS...", flush=True)
    (c15o, f15o), (c1ho, f1ho) = load_unseen("15m"), load_unseen("1h")
    sw15o = _compute_swings(f15o, "continuous", min_bars=SWING["min_bars_15m"])
    sw10o = _compute_swings(f1ho, "continuous", min_bars=10)
    fineo = load_fine_unseen(c15o[0]["ts"], c15o[-1]["ts"])
    vmiss_o = sum(1 for c in c15o if not (c.get("volume") or 0))
    print(f"  OOS 15m missing volume: {vmiss_o}/{len(c15o)}  ({time.time()-t0:.0f}s)", flush=True)
    if vmiss > len(c15) * 0.05 or vmiss_o > len(c15o) * 0.05:
        raise SystemExit("volume coverage too sparse")

    configs = [
        ("champion_multi_sw10", {**EXPERIMENTS["champion_multi_sw10"]["params"]}, sw10, sw10o),
        ("utcsat_multi_sw10 (king)", {**EXPERIMENTS["utcsat_multi_sw10"]["params"]}, sw10, sw10o),
        ("swingpause single", {
            **{k: v for k, v in EXPERIMENTS["dirmatch_swingpause_single_sw10"]["params"].items()
               if k not in ("exp_require_dir_match", "exp_max_swing_age", "exp_dir_causal")}
        }, sw10, sw10o),
    ]

    variants = [
        ("baseline", {}),
        # volume ROUTER (regime): quiet->flip, loud->b2
        ("route rvol<0.50 q=flip", dict(exp_vol_route=0.50)),
        ("route rvol<0.75 q=flip", dict(exp_vol_route=0.75)),
        ("route rvol<0.75 q=b2", dict(exp_vol_route=-0.75)),
        ("route rvol<1.00 q=flip", dict(exp_vol_route=1.00)),
        # DRY hold -> early exit (cut the -75R dry cohort)
        ("dry exit exp<0.50 b8", dict(exp_vol_dry_exit=0.50, exp_vol_dry_bars=8)),
        ("dry exit exp<0.70 b8", dict(exp_vol_dry_exit=0.70, exp_vol_dry_bars=8)),
        ("dry exit exp<0.70 b12", dict(exp_vol_dry_exit=0.70, exp_vol_dry_bars=12)),
        ("dry exit exp<0.85 b8", dict(exp_vol_dry_exit=0.85, exp_vol_dry_bars=8)),
        # DRY hold -> BE only when in profit (trail-side)
        ("dry BE exp<0.70 b8", dict(exp_vol_dry_exit=0.70, exp_vol_dry_bars=8, exp_vol_dry_be=1)),
        ("dry BE exp<0.50 b8", dict(exp_vol_dry_exit=0.50, exp_vol_dry_bars=8, exp_vol_dry_be=1)),
        # no-spike abort (r_max<2 certain deaths)
        ("nospk <2.0 b12", dict(exp_vol_nospk=2.0, exp_vol_nospk_bars=12)),
        ("nospk <1.5 b8", dict(exp_vol_nospk=1.5, exp_vol_nospk_bars=8)),
        ("nospk <2.5 b16", dict(exp_vol_nospk=2.5, exp_vol_nospk_bars=16)),
        # climax dump exit
        ("climax rvol>=3 adv", dict(exp_vol_exit_r=3.0)),
        ("climax rvol>=5 adv", dict(exp_vol_exit_r=5.0)),
        # stacks: dry exit + nospk
        ("dry0.7b8 + nospk2b12", dict(exp_vol_dry_exit=0.70, exp_vol_dry_bars=8,
                                      exp_vol_nospk=2.0, exp_vol_nospk_bars=12)),
        ("dry0.7b8BE + nospk2b12", dict(exp_vol_dry_exit=0.70, exp_vol_dry_bars=8,
                                        exp_vol_dry_be=1, exp_vol_nospk=2.0,
                                        exp_vol_nospk_bars=12)),
        ("route0.75 + dry0.7b8", dict(exp_vol_route=0.75, exp_vol_dry_exit=0.70,
                                      exp_vol_dry_bars=8)),
    ]

    results = []
    for name, params, sw_is, sw_oos in configs:
        print("\n" + "=" * 100, flush=True)
        print(f"  {name}", flush=True)
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
            # outcome mix for volume exits
            if flags and any(k.startswith("exp_vol_dry") or k == "exp_vol_nospk"
                             or k == "exp_vol_exit_r" for k in flags):
                from collections import Counter
                oc = Counter(t.get("outcome") for t in tr_i)
                vol_ex = {k: v for k, v in oc.items() if k in ("voldry", "volns", "volx")}
                if vol_ex:
                    print(f"  {'':28} vol-exits IS: {vol_ex}", flush=True)
            results.append((name, label, n_is, g_is, net_is, n_o, g_o, net_o, d_is, d_o))

    print("\n" + "=" * 100, flush=True)
    print("  SUMMARY (research comparison: both-sides deltas; no fixed ship threshold)", flush=True)
    print("=" * 100, flush=True)
    print(f"  {'config':<28} {'variant':<24} {'dIS':>7} {'dOOS':>7} {'NET I/O':>16}", flush=True)
    for name, label, n_is, g_is, net_is, n_o, g_o, net_o, d_is, d_o in results:
        if label == "baseline":
            continue
        # highlight both-sides positive
        mark = " *" if (d_is > 5 and d_o > 5) else ""
        print(f"  {name:<28} {label:<24} {d_is:>+7.1f} {d_o:>+7.1f} "
              f"{net_is:>+7.1f}/{net_o:>+7.1f}{mark}", flush=True)

    print("\n  baselines:", flush=True)
    for name, label, n_is, g_is, net_is, n_o, g_o, net_o, d_is, d_o in results:
        if label == "baseline":
            print(f"  {name:<28} IS n={n_is} {g_is:+.1f}R net={net_is:+.1f} | "
                  f"OOS n={n_o} {g_o:+.1f}R net={net_o:+.1f}", flush=True)

    print(f"\n(done in {time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
