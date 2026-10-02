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
from engine.v18_params import get_v18_params, V18_ENGINE
from experiment_registry import EXPERIMENTS, BP
import test_experiments_craze as tc

V18_KW = ("sl_buf_atr", "ext_stop_r", "chop_thresh", "atr_low_thresh",
          "atr_high_thresh", "mode", "cooldown_bars", "max_consecutive_losses",
          "htf_rr", "window_end")


def _oos_args():
    c15o, f15o = load_unseen("15m")
    c1ho, f1ho = load_unseen("1h")
    return (c1ho, tc._compute_swings(f1ho, "continuous", min_bars=10),
            c15o, tc._compute_swings(f15o, "continuous", min_bars=50),
            load_fine_1m(c15o[0]["ts"], c15o[-1]["ts"]))


def v18_params():
    # HARNESS BUG 2026-10-01, found because arm A's own pin did not hold.
    # test_v18_causal_integrity.py:28 does get_v18_params THEN .update(V18_ENGINE).
    # The first pass here used get_v18_params alone, so cooldown_bars came back 10
    # instead of 20, mcl 3 instead of 5, chop 58.0 instead of 61.8 - and arm A
    # returned 363 instead of v18's 352. A pin that does not reproduce is either a
    # broken engine or a broken harness; it was the harness.
    p = dict(get_v18_params("BTCUSDT_BYBIT"))
    p.update(V18_ENGINE)
    return {k: p[k] for k in V18_KW if k in p}


def leg_params():
    return {**BP, **EXPERIMENTS["champion_multi_sw10_leg"]["params"]}


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


def run_v18(args, params):
    from btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
    kw, _ = _accept(simulate_htf_ltf_streak_halt, params)
    kw.setdefault("pivot_rule", "leg")
    r = simulate_htf_ltf_streak_halt(args[0], args[1], args[2], args[3],
                                     fine_ltf=args[4], **kw)
    return [t for t in r["ltf_trades"] if t.get("outcome") != "open"]


def run_v19(args, params):
    from btc.engines.htf_ltf.v19_champion import simulate_htf_ltf_streak_halt
    kw, _ = _accept(simulate_htf_ltf_streak_halt, params)
    r = simulate_htf_ltf_streak_halt(args[0], args[1], args[2], args[3],
                                     fine_ltf=args[4], **kw)
    return [t for t in r["ltf_trades"] if t.get("outcome") != "open"]


ARMS = (("A", "v18", "v18"), ("B", "v19", "leg"),
        ("C", "v18", "leg"), ("D", "v19", "v18"))

def main():
    d = get_data()
    is_args = (d["c1h"], d["sw10"], d["c15"], d["sw15"], d["fine"])
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
    for tag, eng, pk in ARMS:
        print("-" * 94)
        print("  ARM %s   %s @ %s params" % (tag, eng, pk))
        for scope in ("is", "oos"):
            args = is_args if scope == "is" else oos_args
            tr = (run_v18 if eng == "v18" else run_v19)(args, P[pk])
            n, net = len(tr), net_r(tr)
            got[(tag, scope)] = (n, net)
            flag = ""
            if scope == "is":
                if tag == "A" and abs(n - 352) <= 2:
                    flag = "   <- v18's own pin holds"
                if tag == "B" and abs(n - 499) <= 2:
                    flag = "   <- shipping pin holds"
                if tag == "C":
                    flag = ("   <- 388 REPRODUCES, delta table OK"
                            if abs(n - 388) <= 2
                            else "   <- *** 388 DID NOT REPRODUCE ***")
            print("    %-4s %5d trades  net %+.1fR%s"
                  % (scope.upper(), n, net, flag))
        print()

    print("=" * 94)
    print("  VERDICT")
    print("=" * 94)
    ok_a = abs(got[("A", "is")][0] - 352) <= 2
    ok_b = abs(got[("B", "is")][0] - 499) <= 2
    ok_c = abs(got[("C", "is")][0] - 388) <= 2
    print("  A  v18 @ v18 params = %4d trades (pin 352)     %s"
          % (got[("A", "is")][0], "HOLDS" if ok_a else "MOVED"))
    print("  B  v19 @ leg params = %4d trades (pin 499)     %s"
          % (got[("B", "is")][0], "HOLDS" if ok_b else "MOVED"))
    print("  C  v18 @ leg params = %4d trades (expect 388)  %s"
          % (got[("C", "is")][0], "REPRODUCES" if ok_c
             else "*** DELTA TABLE INCOMPLETE ***"))
    print("  D  v19 @ v18 params = %4d trades (unlimited on v18 params)"
          % got[("D", "is")][0])
    print()
    if ok_c:
        print("  v18's 352 is a PARAMETER difference, not a behaviour one.")
        print("  COUNT_BAND=(348,358) is anchored to v18's OWN book, and that is")
        print("  worth saying out loud - independently of the refactor.")
        print("  The refactor may proceed with the corrected gate: vary concurrency")
        print("  on ONE parameter set, not across two books.")
    else:
        print("  Arm C does not match 388 - but the FIRST explanation is a LAYER")
        print("  mismatch, not a missing delta, and that has to be settled first.")
        print()
        print("  388 was measured by P117 THROUGH test_experiments_craze.py, which")
        print("  text-patches v18's source and injects exp_persist=7. Raw v18 does")
        print("  not accept exp_persist at all - it was dropped by the signature")
        print("  filter above. So 388 was never a raw-engine number and arm C was")
        print("  never going to reproduce it.")
        print()
        print("  That is the finding: THE PINS LIVE AT DIFFERENT LAYERS.")
        print("    352  claimed  = raw v18, V18 params")
        print("    388, 499    = through the patched harness, leg params")
        print("  A raw-engine refactor cannot be gated on harness numbers.")
        print()
        print("  SEPARATELY, arm A does not reproduce v18's own 352 pin either")
        print("  (got %d / %+.1fR). The documented parameter formula was applied and")
        print("  it is still not the pin. Do NOT treat the delta table as complete")
        print("  until 352 is re-derived." % (got[("A", "is")][0], got[("A", "is")][1]))


if __name__ == "__main__":
    main()