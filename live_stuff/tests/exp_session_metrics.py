"""Full metrics dump for 2026-09-23 session results (HMM / atr_high / maxconc / regime / stack)."""
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


def metrics(trades):
    rs = [float(t["r_multiple"]) for t in trades]
    n = len(rs)
    if n == 0:
        return None
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r < 0]
    zeros = [r for r in rs if r == 0]
    gross = sum(rs)
    wr = 100.0 * len(wins) / n
    avg = gross / n
    avg_w = sum(wins) / len(wins) if wins else 0.0
    avg_l = sum(losses) / len(losses) if losses else 0.0
    pf = (sum(wins) / abs(sum(losses))) if losses and sum(losses) < 0 else float("inf")
    # DD on cumulative R
    peak = cum = dd = 0.0
    cur = mx = 0
    for r in rs:
        cum += r
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
        if r < 0:
            cur += 1
            mx = max(mx, cur)
        else:
            cur = 0
    # expectancy / profit factor alt
    exp_per = avg
    # R multiple distribution
    best = max(rs)
    worst = min(rs)
    med = sorted(rs)[n // 2]
    # years span for R/yr
    yrs = {}
    for t, r in zip(trades, rs):
        d = t.get("exit_date") or t.get("entry_date") or ""
        if d[:4].isdigit():
            yrs[d[:4]] = yrs.get(d[:4], 0) + r
    return {
        "n": n, "net": net_r(trades), "gross": gross, "wr": wr,
        "avg_r": avg, "avg_w": avg_w, "avg_l": avg_l, "pf": pf,
        "dd": dd, "max_loss_streak": mx, "best": best, "worst": worst,
        "med": med, "n_win": len(wins), "n_loss": len(losses), "n_flat": len(zeros),
        "years": yrs,
    }


def fmt(m, tag):
    if m is None:
        print(f"  {tag:<42} (no trades)")
        return
    print(f"  {tag:<42} n={m['n']:4d}  NET={m['net']:+8.1f}  WR={m['wr']:5.1f}%  "
          f"R/tr={m['avg_r']:+.3f}  avgW={m['avg_w']:+.2f}  avgL={m['avg_l']:+.2f}  "
          f"PF={m['pf']:.2f}  DD={m['dd']:.1f}  streak={m['max_loss_streak']}  "
          f"best={m['best']:+.1f}  worst={m['worst']:+.1f}")


def main():
    t0 = time.time()
    print("=" * 120)
    print("  FULL METRICS — 2026-09-23 session (HMM / atr_high / maxconc / regime / stack)")
    print("=" * 120)

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

    sp = {
        **{k: v for k, v in EXPERIMENTS["dirmatch_swingpause_single_sw10"]["params"].items()
           if k not in ("exp_require_dir_match", "exp_max_swing_age", "exp_dir_causal")}
    }
    ch = {**EXPERIMENTS["champion_multi_sw10"]["params"]}
    king = {**EXPERIMENTS["utcsat_multi_sw10"]["params"]}

    # (config_name, params, variants)
    plan = [
        ("CHAMPION multi", ch, [
            ("baseline (ath=0.65)", {}),
            # HMM
            ("HMM ct=61", dict(mode="hmm", chop_thresh=61.0)),
            ("HMM ct=58", dict(mode="hmm", chop_thresh=58.0)),
            # atr_high
            ("ath=0.40", dict(atr_high_thresh=0.40)),
            ("ath=0.70", dict(atr_high_thresh=0.70)),
            # maxconc
            ("cap=5", dict(exp_max_concurrent=5)),
            ("cap=4", dict(exp_max_concurrent=4)),
            ("cap=3", dict(exp_max_concurrent=3)),
            # regime
            ("regime>10", dict(exp_regime_skip=10.0)),
            ("regime>8", dict(exp_regime_skip=8.0)),
            # stack
            ("flip+reg10", dict(exp_flip_break=1, exp_regime_skip=10.0)),
        ]),
        ("KING utcsat multi", king, [
            ("baseline (ath=0.65)", {}),
            ("HMM ct=61", dict(mode="hmm", chop_thresh=61.0)),
            ("ath=0.40", dict(atr_high_thresh=0.40)),
            ("ath=0.70", dict(atr_high_thresh=0.70)),
            ("cap=5", dict(exp_max_concurrent=5)),
            ("regime>20", dict(exp_regime_skip=20.0)),
            ("flip+reg10", dict(exp_flip_break=1, exp_regime_skip=10.0)),
        ]),
        ("SWINGPAUSE single", sp, [
            ("baseline", {}),
            ("HMM ct=50", dict(mode="hmm", chop_thresh=50.0)),
            ("HMM ct=58", dict(mode="hmm", chop_thresh=58.0)),
            ("ath=0.50", dict(atr_high_thresh=0.50)),
            ("ath=0.55", dict(atr_high_thresh=0.55)),
            ("cap=5 (noop)", dict(exp_max_concurrent=5)),
            ("regime>10", dict(exp_regime_skip=10.0)),
            ("flip-break alone", dict(exp_flip_break=1)),
            ("STACK flip+reg8", dict(exp_flip_break=1, exp_regime_skip=8.0)),
            ("STACK flip+reg10", dict(exp_flip_break=1, exp_regime_skip=10.0)),
            ("STACK flip+reg12", dict(exp_flip_break=1, exp_regime_skip=12.0)),
        ]),
    ]

    for cfg_name, params, variants in plan:
        for side, c15x, sw15x, c1hx, swx, finex, ylabel in [
            ("IS  2023-2026", c15, sw15, c1h, sw10, fine_is, "IS"),
            ("OOS 2021-2022", c15o, sw15o, c1ho, sw10o, fineo, "OOS"),
        ]:
            print(f"\n{'=' * 120}", flush=True)
            print(f"  {cfg_name}  —  {side}", flush=True)
            print(f"{'=' * 120}", flush=True)
            for label, flags in variants:
                tr = run(sim, data, params, c15x, sw15x, c1hx, swx, finex, **flags)
                m = metrics(tr)
                fmt(m, label)
                if m and label.startswith("baseline"):
                    base_net = m["net"]
                elif m:
                    pass
            # print yearly R for baseline + best stack / regime
            print(f"  {'':42} yearly R:", end="")
            # recompute for baseline and last variant of interest
            for label, flags in variants:
                if label in ("baseline (ath=0.65)", "baseline", "STACK flip+reg8", "regime>10", "cap=5", "HMM ct=61"):
                    tr = run(sim, data, params, c15x, sw15x, c1hx, swx, finex, **flags)
                    m = metrics(tr)
                    if m:
                        ys = "  ".join(f"{y}:{v:+.1f}" for y, v in sorted(m["years"].items()))
                        print(f"\n    {label:<42} {ys}", end="")
            print()

    print(f"\n(done {time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
