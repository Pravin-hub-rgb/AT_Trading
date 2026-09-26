"""Finish remaining open ideas: Structure (swingpause) + B3 LIMIT salvage.

Phase A (lb sweep): DONE — no-op. Champion/king/swingpause all mode=atr_high
  (regime from ATR%, not chop), so exp31_lb does nothing. lb only matters on
  chop-routing modes (b2_vs_flip_chop) — already swept 14..60 historically.
Phase B (MTF): DONE — OOS up but IS collapses on multi; swingpause mtf1
  dIS −18 / dOOS +67.9 fails both-sides. DEAD.
Phase C partial: mag_min kills IS everywhere; freq_max is a no-op (freq
  formula yields <<4 always). Remaining: swingpause mag_min + confirm freq noop.
Phase D: B3 limit salvage — NOT YET RUN.
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


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  REMAINING IDEAS finish — Structure (swingpause) + B3 LIMIT", flush=True)
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

    def pair(params, sw_is, sw_oos, **flags):
        tis = run(sim, params, c15, sw15, c1h, sw_is, fine_is, **flags)
        tos = run(sim, params, c15o, sw15o, c1ho, sw_oos, fineo, **flags)
        return full_stats(tis), full_stats(tos)

    # ---------- Phase C remainder: swingpause struct ----------
    print("\n" + "=" * 100, flush=True)
    print("  PHASE C remainder — Structure on swingpause single", flush=True)
    print("=" * 100, flush=True)
    sp = {
        **{k: v for k, v in EXPERIMENTS["dirmatch_swingpause_single_sw10"]["params"].items()
           if k not in ("exp_require_dir_match", "exp_max_swing_age", "exp_dir_causal")}
    }
    b_is, b_oos = pair(sp, sw10, sw10o)
    print(f"  {'baseline (struct off)':<42} IS  {fmt(b_is)}", flush=True)
    print(f"  {'':<42} OOS {fmt(b_oos)}", flush=True)
    for label, flags in [
        ("mag_min=0.80", dict(exp_struct_mag_min=0.80)),
        ("mag_min=1.00", dict(exp_struct_mag_min=1.00)),
        ("freq_max=4.0", dict(exp_struct_freq_max=4.0)),
    ]:
        si, so = pair(sp, sw10, sw10o, **flags)
        both_mark(label, b_is, b_oos, si, so)

    # ---------- Phase D: B3 LIMIT on all 3 ----------
    print("\n" + "=" * 100, flush=True)
    print("  PHASE D — B3 LIMIT salvage (retrace to signal close)", flush=True)
    print("=" * 100, flush=True)
    configs = [
        ("champion_multi_sw10", {**EXPERIMENTS["champion_multi_sw10"]["params"]},
         sw10, sw10o),
        ("utcsat_multi_sw10 (king)", {**EXPERIMENTS["utcsat_multi_sw10"]["params"]},
         sw10, sw10o),
        ("swingpause single", sp, sw10, sw10o),
    ]
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

    print(f"\n(done {time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
