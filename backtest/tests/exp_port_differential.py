"""exp_port_differential - the gate for moving a knob out of the patch and
into the shipped engine.

WHY THIS EXISTS

Every pin in experiment_registry.py was produced by the PATCHED engine that
test_experiments_craze.py::_build_module assembles by rewriting the shipped
source text. `unified.py` itself has none of the ~112 harness-only knobs. That
is not a bug - the patch walk is how a research knob gets tested without
touching production - but it means a pin does NOT prove the shipped engine can
produce that book. Four knobs the signal book depends on (exp_skip_weekend,
exp_partial_r, exp_bias_momentum_min, exp_trail_skip_n) lived only in the
patch, so `fsent_sig_full` was not runnable against production at all.

The port moves them in. The risk is silent, not loud: a botched port usually
still runs, it just books a different number of trades. exp_fastcheck cannot
see it, because exp_fastcheck also uses the patched engine - it would compare
the patch against itself and pass.

So this runs BOTH engines on the SAME params and compares the trade lists
byte for byte. If the port is faithful they are identical; if it is not, the
first disagreement prints. Nothing here trusts a recorded number - it trusts
one implementation against the other.

    cd backtest/tests
    python exp_port_differential.py                 # the standard ladder
    python exp_port_differential.py --list          # show the cases
    python exp_port_differential.py --oos-only

A case fails if the two engines disagree on the trade count, on any R, or on
the exit timestamps. Exit timestamps are in the comparison on purpose: a
reordering of trades that preserves n and net is still a different book.
"""
import sys, time, argparse, pathlib

# The ladder. Each case is (label, params-on-top-of-BP). Everything here must be
# expressible in the SHIPPED signature - if a case raises TypeError on the
# shipped engine that is the whole point: it is naming a knob the port has not
# landed yet, which is a louder and more useful failure than a number moving.
CASES = [
    ("all-off (identity)",        {}),
    ("fs_entry_side=short",       {"exp_fs_entry_side": "short"}),
    ("fs_short + weekend OFF",    {"exp_fs_entry_side": "short",
                                   "exp_skip_weekend": 0}),
    ("fs_short + weekend ON",     {"exp_fs_entry_side": "short",
                                   "exp_skip_weekend": 1}),
]


def _sig(trades):
    """The identity of a run: count, every R, and every exit stamp.

    Deliberately not net or DD. Two books can share a net and be different
    books, and a filter that changes WHICH trades exist rather than how much
    they made is exactly the bug this harness exists to catch.
    """
    return (len(trades),
            tuple(round(float(t.get("r_multiple", 0.0)), 6) for t in trades),
            tuple(t.get("exit_ts") for t in trades))


def _run(sim, data, params):
    tr = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
             fine_ltf=data["fine"], **{**dict(re_.BP), **params})["ltf_trades"]
    _trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
    return tr


def _first_diff(a, b):
    """Where two signatures part company, in words rather than as a bool."""
    if a[0] != b[0]:
        return "n %d vs %d" % (a[0], b[0])
    for i, (x, y) in enumerate(zip(a[1], b[1])):
        if x != y:
            return "trade %d R %.6f vs %.6f" % (i, x, y)
    for i, (x, y) in enumerate(zip(a[2], b[2])):
        if x != y:
            return "trade %d exit_ts %s vs %s" % (i, x, y)
    return None
ROOT = pathlib.Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend", ""):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))

import run_experiment as re_
import exp_equity_quality as EQ
from src.btc.btc_routes import _trade_costs, _net_stats
from src.btc.btc_engine import trade_stats
import src.btc.engines.htf_ltf.unified as shipped
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--list", action="store_true", help="print the cases and exit")
    ap.add_argument("--oos-only", action="store_true", help="skip the IS pass")
    a = ap.parse_args(argv)

    if a.list:
        for lbl, p in CASES:
            print("  %-24s %s" % (lbl, p or "{}"))
        return 0

    scopes = ["oos"] if a.oos_only else ["is", "oos"]
    print("=" * 74)
    print("PORT DIFFERENTIAL - shipped unified.py vs the patched engine")
    print("=" * 74)
    t0 = time.time()
    sim = re_.build_module()
    data = {s: EQ.load_scope(s) for s in scopes}
    print("data loaded (%.0fs)\n" % (time.time() - t0))

    fails = []
    for scope in scopes:
        print("--- %s ---" % scope.upper())
        for lbl, params in CASES:
            row = "%-24s" % lbl
            try:
                t_ship = _run(shipped.simulate_htf_ltf_streak_halt, data[scope], params)
            except TypeError as e:
                # A knob the port has not landed yet. That is progress
                # information, not a crash, so it is reported and counted.
                print("%s SHIPPED REJECTS: %s" % (row, e))
                fails.append("%s/%s not in shipped signature: %s" % (scope, lbl, e))
                continue
            t_patch = _run(sim, data[scope], params)

            d = _first_diff(_sig(t_ship), _sig(t_patch))
            ns = _net_stats(trade_stats(t_ship), t_ship)["net_total_r"]
            np_ = _net_stats(trade_stats(t_patch), t_patch)["net_total_r"]
            if d is None:
                print("%s MATCH   n=%-4d net=%+8.2f  (both engines agree)"
                      % (row, len(t_ship), ns))
            else:
                print("%s DIFFER  n=%-4d/%-4d net=%+8.2f/%+8.2f  -> %s"
                      % (row, len(t_ship), len(t_patch), ns, np_, d))
                fails.append("%s/%s: %s" % (scope, lbl, d))
        print()

    print("total %.0fs" % (time.time() - t0))
    if fails:
        print("RESULT: FAIL - %d disagreement(s)" % len(fails))
        for f in fails:
            print("        - %s" % f)
        return 1
    print("RESULT: PASS - shipped and patched agree on every case, both eras.")
    print("        This proves the ported knobs produce the SAME trades in the")
    print("        production engine as they did in the patch. It does not")
    print("        re-derive registry pins - exp_fastcheck.py does that.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())