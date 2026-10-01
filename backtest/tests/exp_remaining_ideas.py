"""Remaining open ideas — path-true both-sides (2026-09-24).

Phases (run sequentially in one process):
  A) HTF chop lookback lb sweep: exp31_lb 14/20/30 on champion path
  B) MTF Regime path-true: exp_mtf_mode 1 (last 1h swing match) / 2 (last TWO agree)
  C) Structure Evolution path-true: mag_trend floor + swing-freq ceiling
  D) B3 LIMIT salvage: trigger then retrace-to-signal-close within k bars
  E) Mean reversion / compression — CLOSED (entry-quality budget; MR filter
     used r_multiple lookahead in test_new_paradigms; compression no edge)

Identity basis: sw20 + coarse fills + BASE (340t/+225.3) via identity_gate().
Both-sides: IS (champion/king/swingpause) + OOS 2021-22 required.
Research comparison: report both-sides deltas; no fixed ship threshold.

Run: python backtest/tests/exp_remaining_ideas.py
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


def run(sim, params, c15, sw15, c1h, sw, fine, **flags):
    kw = {**BP, **params, **flags}
    kw.setdefault("exp_partial_r", 0.0)
    out = sim(c1h, sw, c15, sw15, fine_ltf=fine, **kw)
    return out["ltf_trades"] if isinstance(out, dict) else out


def full_stats(tr):
    if not tr:
        return dict(n=0, gross=0.0, net=0.0, wr=0.0, rpt=0.0, aw=0.0, al=0.0,
                    pf=0.0, dd=0.0)
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
    eq = peak = dd = 0.0
    for v in nets:
        eq += v
        if eq > peak:
            peak = eq
        d = peak - eq
        if d > dd:
            dd = d
    return dict(n=len(nets), gross=sum(rs), net=net, wr=wr,
                rpt=net / len(nets), aw=aw, al=al, pf=pf, dd=dd)


def fmt(s):
    pf = s["pf"]
    pfs = "inf" if pf == float("inf") else f"{pf:.2f}"
    return (f"n={s['n']:>4} G={s['gross']:+7.1f} NET={s['net']:+7.1f} "
            f"WR={s['wr']:5.1f}% R/t={s['rpt']:+.3f} "
            f"avgW={s['aw']:+.2f} avgL={s['al']:+.2f} PF={pfs:>5} "
            f"DD={s['dd']:5.1f}")


def both_mark(label, base_is, base_oos, si, so):
    d_is = si["net"] - base_is["net"]
    d_oos = so["net"] - base_oos["net"]
    both = d_is >= 0 and d_oos >= 0
    mark = "  BOTH" if both else ""
    print(f"  {label:<42} IS  {fmt(si)}  dNET {d_is:+7.1f}", flush=True)
    print(f"  {'':<42} OOS {fmt(so)}  dNET {d_oos:+7.1f}{mark}", flush=True)
    return d_is, d_oos, both


def phase(title):
    print("\n" + "=" * 100, flush=True)
    print(f"  {title}", flush=True)
    print("=" * 100, flush=True)


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  REMAINING OPEN IDEAS — path-true both-sides", flush=True)
    print("=" * 100, flush=True)

    data = get_data()
    identity_gate(data)
    sim = craze.build_module()
    c15, sw15, c1h, sw10 = data["c15"], data["sw15"], data["c1h"], data["sw10"]
    fine_is = data["fine"]

    print("loading OOS 2021-22...", flush=True)
    (c15o, f15o), (c1ho, f1ho) = load_unseen("15m"), load_unseen("1h")
    sw15o = _compute_swings(f15o, "continuous", min_bars=SWING["min_bars_15m"])
    sw10o = _compute_swings(f1ho, "continuous", min_bars=10)
    fineo = load_fine_unseen(c15o[0]["ts"], c15o[-1]["ts"])
    print(f"  OOS ready ({time.time()-t0:.0f}s)", flush=True)

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

    def pair(params, sw_is, sw_oos, **flags):
        tis = run(sim, params, c15, sw15, c1h, sw_is, fine_is, **flags)
        tos = run(sim, params, c15o, sw15o, c1ho, sw_oos, fineo, **flags)
        return full_stats(tis), full_stats(tos)

    # ---------- Phase A: lb sweep ----------
    phase("PHASE A — HTF chop lookback (exp31_lb 14/20/30)")
    lb_variants = [
        ("lb=14 (default)", dict(exp31_lb=14)),
        ("lb=20 (untested gap)", dict(exp31_lb=20)),
        ("lb=30 (known)", dict(exp31_lb=30)),
    ]
    for name, params, sw_is, sw_oos in configs:
        print(f"\n  -- {name} --", flush=True)
        b_is, b_oos = pair(params, sw_is, sw_oos)
        print(f"  {'baseline (lb=14 via default)':<42} IS  {fmt(b_is)}", flush=True)
        print(f"  {'':<42} OOS {fmt(b_oos)}", flush=True)
        for label, flags in lb_variants:
            si, so = pair(params, sw_is, sw_oos, **flags)
            both_mark(label, b_is, b_oos, si, so)

    # ---------- Phase B: MTF Regime ----------
    phase("PHASE B — MTF Regime path-true (last 1h swing match)")
    mtf_variants = [
        ("mtf_mode=1 (last swing match)", dict(exp_mtf_mode=1)),
        ("mtf_mode=2 (last TWO agree+match)", dict(exp_mtf_mode=2)),
    ]
    for name, params, sw_is, sw_oos in configs:
        print(f"\n  -- {name} --", flush=True)
        b_is, b_oos = pair(params, sw_is, sw_oos)
        print(f"  {'baseline (mtf off)':<42} IS  {fmt(b_is)}", flush=True)
        print(f"  {'':<42} OOS {fmt(b_oos)}", flush=True)
        for label, flags in mtf_variants:
            si, so = pair(params, sw_is, sw_oos, **flags)
            both_mark(label, b_is, b_oos, si, so)

    # ---------- Phase C: Structure Evolution ----------
    phase("PHASE C — Structure Evolution path-true (mag_trend / freq)")
    struct_variants = [
        ("mag_min=0.80", dict(exp_struct_mag_min=0.80)),
        ("mag_min=1.00", dict(exp_struct_mag_min=1.00)),
        ("mag_min=1.25", dict(exp_struct_mag_min=1.25)),
        ("freq_max=4.0", dict(exp_struct_freq_max=4.0)),
        ("freq_max=6.0", dict(exp_struct_freq_max=6.0)),
        ("mag1.0+freq4", dict(exp_struct_mag_min=1.00, exp_struct_freq_max=4.0)),
    ]
    for name, params, sw_is, sw_oos in configs:
        print(f"\n  -- {name} --", flush=True)
        b_is, b_oos = pair(params, sw_is, sw_oos)
        print(f"  {'baseline (struct off)':<42} IS  {fmt(b_is)}", flush=True)
        print(f"  {'':<42} OOS {fmt(b_oos)}", flush=True)
        for label, flags in struct_variants:
            si, so = pair(params, sw_is, sw_oos, **flags)
            both_mark(label, b_is, b_oos, si, so)

    # ---------- Phase D: B3 LIMIT salvage ----------
    phase("PHASE D — B3 LIMIT salvage (trigger then retrace to signal close)")
    b3_variants = [
        ("b3_k=4 limit", dict(b3_k=4, b3_mode="limit")),
        ("b3_k=8 limit", dict(b3_k=8, b3_mode="limit")),
        ("b3_k=12 limit", dict(b3_k=12, b3_mode="limit")),
        ("b3_k=8 close (ref)", dict(b3_k=8, b3_mode="close")),
    ]
    for name, params, sw_is, sw_oos in configs:
        print(f"\n  -- {name} --", flush=True)
        b_is, b_oos = pair(params, sw_is, sw_oos)
        print(f"  {'baseline (no B3)':<42} IS  {fmt(b_is)}", flush=True)
        print(f"  {'':<42} OOS {fmt(b_oos)}", flush=True)
        for label, flags in b3_variants:
            si, so = pair(params, sw_is, sw_oos, **flags)
            both_mark(label, b_is, b_oos, si, so)

    # ---------- Phase E: documentation only ----------
    phase("PHASE E — Mean reversion / compression — CLOSED (no run)")
    print("  mean_reversion filter in test_new_paradigms uses r_multiple in the",
          flush=True)
    print("  keep decision (lookahead). Compression breakout: no edge on CRAZE",
          flush=True)
    print("  path. Entry-quality budget closed (playbook 3h). NOT re-run.",
          flush=True)

    print(f"\n(done {time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
