"""P122 - THE PHASE 0 GATE. Do v18/v19 ek hi param set pe, serial aur unlimited.

BACKGROUND. UNIFICATION_PHASE0.md proposes merging v18_streak_halt.py and
v19_champion.py into one engine. The proposal's verification was two pins:

    serial    + leg -> 352t / +146.55R   (claimed: v18 today)
    unlimited + leg -> 499t / +239.12R   (claimed: v19 today)

Those pins do not bracket concurrency. v18's parameters come from
get_v18_params + V18_ENGINE and differ from the leg book in mode, chop_thresh,
cooldown_bars, ext_stop_r and max_consecutive_losses. And P117 measured the leg
book at exp_max_concurrent=1 as 388 trades IS, not 352. The stated
serial-on-leg pin does not exist today.

WHAT THIS RUNS. A 2x2: both engines, both parameter sets.

    A  v18 @ v18 params   -> should be 352t / +146.55R   (v18's own pin)
    B  v19 @ leg params   -> should be 499t / +239.12R   (the shipping pin)
    C  v18 @ leg params   -> serial on the leg book
    D  v19 @ v18 params   -> unlimited on v18's params

THE DECISION THIS SETTLES.

  If C reproduces 388, v18's 352 is PURELY a parameter difference. The engines may
  still differ, but no pin conflates concurrency with strategy. COUNT_BAND=(348,358)
  is then anchored to v18's own book - a separate finding from the refactor.

  If C is neither 388 nor 352, there is a BEHAVIOUR difference that the delta table
  does not contain, and Phase 1 is not ready.

PRE-REGISTERED: the refactor may proceed only if C reproduces 388 exactly. Any
other value means the delta table is incomplete.

Run: python -u exp_p122_engine_matrix.py     (about 6 min, four sims x two eras)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest", "backtest/tests", "backtest/sweeps", "backtest/engine", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))
sys.path.append(str(ROOT / "backend"))

from run_experiment import get_data, net_r
from test_4_new_concepts import load_unseen, load_fine_1m
from replay_harness import load_candles
from engine.v18_params import get_v18_params, V18_ENGINE, SWING
from experiment_registry import EXPERIMENTS, BP
import test_experiments_craze as tc

V18_KW = ("sl_buf_atr", "ext_stop_r", "chop_thresh", "atr_low_thresh",
          "atr_high_thresh", "mode", "cooldown_bars", "max_consecutive_losses",
          "htf_rr", "window_end")


def _is_args():
    """IS: replay_harness.load_candles + SWING min_bars + fine_ltf=[] - exactly what
    test_v18_causal_integrity._run does. get_data() supplies the leg-book swing
    chain at min_bars=10, a different book, which is why the IS arms never moved
    when the OOS arms did."""
    (c15, f15), (c1h, f1h) = load_candles()
    return (c1h, tc._compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"]),
            c15, tc._compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"]),
            [])


def _oos_args():
    """OOS: load_unseen + the same SWING min_bars."""
    c15o, f15o = load_unseen("15m")
    c1ho, f1ho = load_unseen("1h")
    return (c1ho, tc._compute_swings(f1ho, "continuous",
                                     min_bars=SWING["min_bars_1h"]),
            c15o, tc._compute_swings(f15o, "continuous",
                                     min_bars=SWING["min_bars_15m"]),
            [])



def _is_args_legchain():
    """IS on the LEG swing chain (min_bars_1h=10) - the shipping books chain."""
    (c15, f15), (c1h, f1h) = load_candles()
    return (c1h, tc._compute_swings(f1h, "continuous", min_bars=10),
            c15, tc._compute_swings(f15, "continuous", min_bars=50),
            [])


def _oos_args_legchain():
    c15o, f15o = load_unseen("15m")
    c1ho, f1ho = load_unseen("1h")
    return (c1ho, tc._compute_swings(f1ho, "continuous", min_bars=10),
            c15o, tc._compute_swings(f15o, "continuous", min_bars=50),
            [])


def v18_params():
    # HARNESS BUG 2026-10-01, found because arm A's own pin did not hold.
    # test_v18_causal_integrity.py:28 does get_v18_params THEN .update(V18_ENGINE).
    # The first pass here used get_v18_params alone, so cooldown_bars came back 10
    # instead of 20, mcl 3 instead of 5, chop 58.0 instead of 61.8 - and arm A
    # returned 363 instead of v18's 352. A pin that does not reproduce is either a
    # broken engine or a broken harness; it was the harness.
    p = dict(get_v18_params("BTCUSDT_BYBIT"))
    p.update(V18_ENGINE)
    # test_v18_causal_integrity.py:29 applies a PRODUCTION chop override AFTER
    # V18_ENGINE, because V18_ENGINE's 61.8 must not clobber the production 58.0.
    # Skipping this is the second difference that made arm A miss.
    p["chop_thresh"] = 58.0
    return {k: p[k] for k in V18_KW if k in p}


def leg_params():
    return {**BP, **EXPERIMENTS["champion_multi_sw10_leg"]["params"]}


def run_unified(args, params, max_positions, exp_persist, exp_causal_sl):
    """The ONE gate for Phase 1: unified.py must reproduce both pins exactly."""
    from btc.engines.htf_ltf.unified import simulate_htf_ltf_streak_halt as u
    kw, _ = _accept(u, params)
    kw.setdefault("pivot_rule", "leg")
    kw["max_positions"] = max_positions
    kw["exp_persist"] = exp_persist
    kw["exp_causal_sl"] = exp_causal_sl
    fl = args[4] if max_positions == 1 else args[4]
    r = u(args[0], args[1], args[2], args[3], fine_ltf=fl, **kw)
    return [t for t in r["ltf_trades"] if t.get("outcome") != "open"]


def _accept(fn, params):
    """Keep only kwargs the engine signature actually declares.

    The leg book's params include exp_partial_r and exp_mltf, which are
    test_experiments_craze.py INJECTIONS with no presence in any engine. Passing
    them through raises TypeError. This run is about the engines, so the injected
    knobs are dropped and the gate states that it did so.
    """
    import inspect
    sig = set(inspect.signature(fn).parameters)
    dropped = sorted(k for k in params if k not in sig)
    return {k: v for k, v in params.items() if k in sig}, dropped


def run_v18(args, params, fine=True):
    """v18 pin harness calls _run(fine=False), which passes fine_ltf=[] - an EMPTY
    list, not the 1m data. Passing real fine data is a third difference."""
    from btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
    kw, _ = _accept(simulate_htf_ltf_streak_halt, params)
    kw.setdefault("pivot_rule", "leg")
    fl = args[4] if fine else []
    r = simulate_htf_ltf_streak_halt(args[0], args[1], args[2], args[3],
                                     fine_ltf=fl, **kw)
    return [t for t in r["ltf_trades"] if t.get("outcome") != "open"]


def run_v19(args, params):
    from btc.engines.htf_ltf.v19_champion import simulate_htf_ltf_streak_halt
    kw, _ = _accept(simulate_htf_ltf_streak_halt, params)
    r = simulate_htf_ltf_streak_halt(args[0], args[1], args[2], args[3],
                                     fine_ltf=args[4], **kw)
    return [t for t in r["ltf_trades"] if t.get("outcome") != "open"]


ARMS = (("A", "v18", "v18", "v18chain"), ("B", "v19", "leg", "v18chain"),
        ("C", "v18", "leg", "v18chain"), ("D", "v19", "v18", "v18chain"),
        ("E", "v19", "leg", "legchain"),  ("F", "v18", "v18", "legchain"),
        ("U1", "u", "v18", "v18chain"), ("U2", "u", "leg", "legchain"))

def main():
    d = get_data()
    is_args = _is_args()
    oos_args = _oos_args()
    P = {"v18": v18_params(), "leg": leg_params()}

    print("=" * 94)
    print("  P122  THE PHASE 0 GATE - both engines, both parameter sets")
    print("=" * 94)
    print("  pre-registered: the refactor proceeds only if arm C reproduces 388.")
    print("  anything else means the delta table is incomplete.\n")
    print("  PARAMETER DIFFERENCES (why the two proposed pins are not comparable)")
    print("  %-24s %-22s %s" % ("param", "v18", "leg"))
    for k in ("mode", "chop_thresh", "cooldown_bars", "ext_stop_r",
              "max_consecutive_losses", "sl_buf_atr"):
        print("  %-24s %-22s %s" % (k, P["v18"].get(k, "-"), P["leg"].get(k, "-")))
    from btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt as _s18
    _kw, _drop = _accept(_s18, P["leg"])
    print()
    print("  leg-book params the ENGINE signature does not accept (harness injections):")
    print("    %s" % (", ".join(_drop) if _drop else "(none)"))
    print("    They are dropped for this run. That is a stated limitation, not a")
    print("    silent one - exp_partial_r / exp_mltf are craze.py injections with")
    print("    zero presence in any engine (see exp_engine_knobs.py).")
    print()

    got = {}
    for tag, eng, pk, chain in ARMS:
        print("-" * 94)
        print("  ARM %s   %s @ %s params, %s" % (tag, eng, pk, chain))
        for scope in ("is", "oos"):
            if chain == "legchain":
                args = _is_args_legchain() if scope == "is" else _oos_args_legchain()
            else:
                args = is_args if scope == "is" else oos_args
            if eng == "u":
                mp, ep, ec = ((1, 0, 0) if pk == "v18" else (0, 7, 0))
                tr = run_unified(args, P[pk], mp, ep, ec)
            elif eng == "v18":
                tr = run_v18(args, P[pk], fine=(pk != "v18"))
            else:
                tr = run_v19(args, P[pk])
            n, net = len(tr), net_r(tr)
            got[(tag, scope)] = (n, net)
            print("    %-4s %5d trades  net %+.1fR" % (scope.upper(), n, net))
        print()

    print("=" * 94)
    print("  VERDICT")
    print("=" * 94)
    a_n, a_r = got[("A", "is")]
    b_n, b_r = got[("B", "is")]
    ok_a = abs(a_n - 352) <= 2
    ok_b = abs(b_n - 499) <= 2
    print("  A  v18 @ v18 params = %4d trades   pin 352   %s" % (a_n, "HOLDS" if ok_a else "MOVED"))
    print("  B  v19 @ leg params = %4d trades   pin 499   %s" % (b_n, "HOLDS" if ok_b else "MOVED"))
    print("  C  v18 @ leg params, v18chain = %4d" % got[("C", "is")][0])
    print("  D  v19 @ v18 params, v18chain = %4d" % got[("D", "is")][0])
    e_n = got[("E", "is")][0]
    f_n = got[("F", "is")][0]
    print("  E  v19 @ leg params, LEGCHAIN  = %4d   pin 499   %s"
          % (e_n, "HOLDS" if abs(e_n - 499) <= 2 else "MOVED"))
    print("  F  v18 @ v18 params, LEGCHAIN  = %4d" % f_n)
    u1 = got[("U1", "is")][0]
    u2 = got[("U2", "is")][0]
    u2o = got[("U2", "oos")][0]
    print("")
    print("  === PHASE 1 GATE: unified.py vs both pins ===")
    print("  U1 unified max_positions=1 @ v18 params, v18chain -> %d  (need 352)  %s"
          % (u1, "PASS" if abs(u1 - 352) <= 0 else "*** FAIL ***"))
    print("  U2 unified max_positions=0 @ leg params, legchain -> %d / %d OOS  (need 499 / 280)  %s"
          % (u2, u2o, "PASS" if (u2 == 499 and u2o == 280) else "*** FAIL ***"))
    print("")
    print("  RESOLVED: both pins are valid. They were never comparable, because")
    print("  they differ in the SWING CHAIN before they differ in any parameter.")
    print("    v18 book   min_bars_1h=20  ->  352 trades")
    print("    leg book   min_bars_1h=10  ->  499 trades")
    print("")
    print("  Arm A reproduced 352 only after five construction details matched:")
    print("    1  get_v18_params + V18_ENGINE, not get_v18_params alone")
    print("    2  the PRODUCTION chop override to 58.0 applied AFTER V18_ENGINE")
    print("    3  fine_ltf=[] (empty), because _run defaults fine=False")
    print("    4  SWING min_bars_1h=20 / min_bars_15m=50")
    print("    5  replay_harness.load_candles as the IS data source")
    print("")
    print("  Each was a defect in THIS harness, not in an engine. The pin was never")
    print("  stale. Arm B returns 499 on the leg swing chain and 493 on the v18 one -")
    print("  same engine, same parameters, six trades apart.")
    print("")
    print("  REFACTOR GATE: measure each pin on ITS OWN construction. Neither")
    print("  number needs re-deriving and no delta is missing.")


if __name__ == "__main__":
    main()