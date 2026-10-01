"""Full-path engine validation: halt_skip_n + skip_decisive on IS and true OOS.

Trade-list autopsy said:
  halt2 (skip first post-3-losses trade): dIS +18.1, dOOS +11.2
  N3 = halt2 + skip regime=decisive:     dIS +18.1, dOOS +30.4

Trade-list filters are NOT path-true (skipping cascades). This runs the
patched engine end-to-end (full path cascade) for champion + utcsat.

Run: python -m backtest.tests.exp_engine_filters
"""
import sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from replay_harness import load_candles, INSTRUMENT
from engine.v18_params import SWING, get_v18_params, V18_ENGINE
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from test_experiments_craze import build_module as build_craze, stats, show, BASE
from test_4_new_concepts import load_unseen, load_fine_1m as load_fine_unseen
from experiment_registry import EXPERIMENTS, BP
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod

_P = dict(get_v18_params(INSTRUMENT)); _P.update(V18_ENGINE)


def run(sim, c1h, sw, c15, sw15, fine, params, **flags):
    r = sim(c1h, sw, c15, sw15, fine_ltf=fine, **{**params, **flags})
    return r["ltf_trades"] if isinstance(r, dict) else r


def net(tr):
    return sum(float(t["r_multiple"]) for t in tr)


def main():
    t0 = time.time()
    print("=" * 100)
    print("  ENGINE FILTERS - halt_skip_n / skip_decisive - full path IS + true OOS")
    print("=" * 100)

    # ---- IDENTITY GATE (patched defaults == shipped) ----
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
    sw10 = _compute_swings(f1h, "continuous", min_bars=10)
    fine_is = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                            max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)
    sim = build_craze()

    r_ship = shipped_mod.simulate_htf_ltf_streak_halt(c1h, sw10, c15, sw15,
                                                      fine_ltf=[], **BASE)
    t_ship = r_ship["ltf_trades"] if isinstance(r_ship, dict) else r_ship
    s_ship = stats(t_ship)
    show("shipped(BASE,no-fine)", s_ship)

    r_id = run(sim, c1h, sw10, c15, sw15, [], BASE)
    s_id = stats(r_id)
    show("patched-defaults", s_id)
    assert s_id["n"] == s_ship["n"] and s_id["rs"] == s_ship["rs"], \
        "IDENTITY GATE FAILED: defaults != shipped"
    print("  IDENTITY OK")

    # ---- configs ----
    variants = [
        ("baseline", {}),
        ("halt_skip=2", dict(exp_halt_skip_n=2)),
        ("skip_decisive", dict(exp_skip_decisive=1)),
        ("halt2+skip_dec (N3)", dict(exp_halt_skip_n=2, exp_skip_decisive=1)),
        ("halt_skip=3", dict(exp_halt_skip_n=3)),
    ]
    keys = ["champion_multi_sw10", "utcsat_multi_sw10"]

    # ---- OOS data (once) ----
    (c15o, f15o), (c1ho, f1ho) = load_unseen("15m"), load_unseen("1h")
    sw15o = _compute_swings(f15o, "continuous", min_bars=SWING["min_bars_15m"])
    sw10o = _compute_swings(f1ho, "continuous", min_bars=10)
    fineo = load_fine_unseen(c15o[0]["ts"], c15o[-1]["ts"])

    for key in keys:
        cfg = EXPERIMENTS[key]
        params = {**BP, **cfg["params"]}
        params.setdefault("exp_partial_r", 0.0)

        print("\n" + "=" * 100)
        print(f"  {key}")
        print("=" * 100)
        print(f"  {'variant':<24} {'IS n':>5} {'IS gross':>10} {'dIS':>8} "
              f"{'OOS n':>6} {'OOS gross':>10} {'dOOS':>8} {'OOS/IS%':>8}")
        base_is = base_oos = None
        for name, flags in variants:
            tis = run(sim, c1h, sw10, c15, sw15, fine_is, params, **flags)
            tos = run(sim, c1ho, sw10o, c15o, sw15o, fineo, params, **flags)
            ni, no = net(tis), net(tos)
            if base_is is None:
                base_is, base_oos = ni, no
            di, do = ni - base_is, no - base_oos
            ratio = 100 * no / ni if ni else -999
            print(f"  {name:<24} {len(tis):>5} {ni:>+10.1f} {di:>+8.1f} "
                  f"{len(tos):>6} {no:>+10.1f} {do:>+8.1f} {ratio:>7.0f}%")

    # ---- utcsat OOS yearly breakdown for N3 ----
    print("\n" + "=" * 100)
    print("  N3 yearly (champion) - path-true engine flags")
    print("=" * 100)
    from collections import defaultdict
    for key in keys:
        cfg = EXPERIMENTS[key]
        params = {**BP, **cfg["params"]}
        params.setdefault("exp_partial_r", 0.0)
        flags = dict(exp_halt_skip_n=2, exp_skip_decisive=1)
        for tag, c1h_, sw_, c15_, sw15_, fine_ in [
            ("IS", c1h, sw10, c15, sw15, fine_is),
            ("OOS", c1ho, sw10o, c15o, sw15o, fineo),
        ]:
            tr = run(sim, c1h_, sw_, c15_, sw15_, fine_, params, **flags)
            py = defaultdict(float)
            for t in tr:
                py[(t.get("exit_date") or "")[:4]] += float(t["r_multiple"])
            print(f"  {key} {tag}: " +
                  "  ".join(f"{y}:{py[y]:+.1f}" for y in sorted(py)))

    print("\n(done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()
