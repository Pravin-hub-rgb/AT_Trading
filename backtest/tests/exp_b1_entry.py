"""P71 - CAN B1 FIRE ENTRIES? The one mechanical gap left in the engine.

WHAT "B1 ENTRY" MEANS
    btc_swing emits break_kind "B1" / "B2" / "FLIP". B2 is the decisive
    break of a structure extreme; FLIP is the direction change; B1 is the
    weaker first touch of the same extreme. `_collect_signals` has:

        tradeable = {"decisive": ("B2","FLIP"), "b2": ("B2",),
                     "flip": ("FLIP",)}.get(entry_break, ("B2","FLIP"))

    B1 is in NO entry set. Every B1 mark is read, checked, and skipped.
    CLOSED_DO_NOT_REPEAT.md records this as "still open (not closed)": no
    kwarg fires an entry on B1.

    That makes it the cleanest item left - a gap in the engine rather than a
    filter to be searched - and it is worth asking because if B1 fires and
    the extra entries are bad, that is an information win for free.

TWO ARMS, BECAUSE "ADD B1" IS NOT ONE THING
    B1_both   add B1 to the DECISIVE set  -> ("B1","B2","FLIP")
    B1_flip   add B1 to the FLIP set      -> ("B1","FLIP")

    These reach different places. v18 builds its HTF windows from three v7
    calls: flip, decisive and b2. Adding B1 to the flip set touches the
    direction windows; adding it to decisive touches the chop windows. One
    could work while the other bleeds, and reporting them together would
    hide that.

PATCH MECHANISM - source read, patched, exec'd, repo file never written
    The tradeable dict is a function-local literal, so it cannot be extended
    from outside. One insertion adds two new keys; the original keys are
    left byte-identical so the control path is provably unchanged. This is
    the same read-patch-exec approach exp_no_expiry.py used on v7, and it
    is preferred here over a wrapper that rewrites break kinds, because
    relabelling a B1 as a B2 would change what the mark MEANS rather than
    whether it is allowed.

PASS CRITERION - FIXED BEFORE RUNNING
    Beat the champion in BOTH eras in BOTH lanes AND clear M = 193.4R. A
    larger book that nets less is not a result; it is the trade this
    programme has seen nine times. And per P61's lesson, any arm that wins
    in the aggregate must also survive a calendar half-year partition
    before it is called anything.

THE PRIOR
    The book prices roughly a third of its confirmed swings, and P64 just
    established that a different swing SEGMENTATION (ZigZag) was worse than
    the incumbent's tuned min_bars. This is the opposite move - same swings,
    more of their marks priced - so the incumbent's detection quality is
    held fixed and only the trigger set changes.
"""
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen
from test_4_new_concepts import load_fine_1m as load_fine_oos

M_NULL = 193.4
ENGINE = ROOT / "backend" / "src" / "btc" / "btc_engine.py"
ORIG = '        "flip": ("FLIP",),\n    }.get(entry_break, ("B2", "FLIP"))'
PATCH = ('        "flip": ("FLIP",),\n'
         '        "b1_decisive": ("B1", "B2", "FLIP"),\n'
         '        "b1_flip": ("B1", "FLIP"),\n'
         '    }.get(entry_break, ("B2", "FLIP"))')
PIN = {"champion_multi_sw10": ((500, 325.8), (279, 70.1)),
       "utcsat_multi_sw10": ((453, 279.5), (254, 66.9))}


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def dd(rs):
    e = p = d = 0.0
    for x in rs:
        e += x
        p = max(p, e)
        d = max(d, p - e)
    return d


def patched_module():
    """btc_engine with two extra tradeable keys. The original keys are
    untouched, so the control path is byte-identical."""
    src = ENGINE.read_text(encoding="utf-8")
    n = src.count(ORIG)
    if n != 1:
        raise SystemExit("patch site not unique (%d)" % n)
    m = types.ModuleType("btc_engine_b1")
    m.__file__ = str(ENGINE)
    exec(compile(src.replace(ORIG, PATCH), str(ENGINE), "exec"),
         m.__dict__)
    return m


PATCHED = {}


def run_arm(sim, translate, args, params):
    """Run the champion with entry_break names translated through
    `translate`, so 'decisive' -> 'b1_decisive' routes to the new key.

    v18 imports _collect_signals from src.btc.btc_engine INSIDE the
    function body - the same late-import shape exp_no_expiry.py exploited
    for v7 - so swapping the attribute on that module redirects the engine
    without touching any file. That is also why the sim must be
    tc.build_module() and not a raw exec of v18: the raw module lacks the
    super-set kwargs the champion's params use.
    """
    import src.btc.btc_engine as be
    orig = be._collect_signals
    patched = PATCHED["_collect_signals"]

    def routed(swings, eb, **kw):
        return patched(swings, translate.get(eb, eb), **kw)

    be._collect_signals = routed
    try:
        res = sim(*args, **params)
    finally:
        be._collect_signals = orig
    return [t for t in res["ltf_trades"] if t.get("outcome") != "open"]


def main():
    print("=" * 100)
    print("  P71  CAN B1 FIRE ENTRIES?")
    print("=" * 100)
    print("  B1 marks are generated, read, and skipped by _collect_signals.")
    print("  Two arms: B1 added to the DECISIVE set, and to the FLIP set.")
    print("  Pass = beat the champion in BOTH eras in BOTH lanes AND clear M.")
    print("  M = %.1fR\n" % M_NULL)

    d = get_data()
    identity_gate(d, tc.build_module())
    (oc15, of15), (oc1h, of1h) = load_unseen("15m"), load_unseen("1h")
    oos_fine = load_fine_oos(oc15[0]["ts"], oc15[-1]["ts"])
    # engine signature is (candles_htf, swings_htf, candles_ltf, swings_ltf, fine)
    src = {"is": (d["c1h"], d["sw10"], d["c15"], d["sw15"], d["fine"]),
           "oos": (oc1h,
                   tc._compute_swings(of1h, "continuous", min_bars=10),
                   oc15,
                   tc._compute_swings(of15, "continuous", min_bars=50),
                   oos_fine)}

    be = patched_module()
    PATCHED.update({"_collect_signals": be._collect_signals})
    sim = tc.build_module()
    print("  btc_engine patched: tradeable gains 'b1_decisive' and")
    print("  'b1_flip'. Original keys untouched, so the control is")
    print("  byte-identical. Repo's file is never written.")
    print("  Also counting raw break kinds per swing chain, because an")
    print("  arm that changes nothing usually means the marks are not")
    print("  where it was assumed they were.\n")

    ARMS = [("control (B1 never enters)", {}),
            ("B1 -> decisive set", {"decisive": "b1_decisive"}),
            ("B1 -> flip set", {"flip": "b1_flip"}),
            ("B1 -> both sets", {"decisive": "b1_decisive",
                                 "flip": "b1_flip"})]

    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        params = {**BP, **EXPERIMENTS[name]["params"]}
        pin = PIN[name]
        print("  " + "=" * 98)
        print("  LANE: %s" % name)
        print("  " + "=" * 98)
        for i, scope in enumerate(("is", "oos")):
            args = src[scope]
            ctl = run_arm(sim, {}, args, params)
            if (abs(len(ctl) - pin[i][0]) > 2
                    or abs(net_r(ctl) - pin[i][1]) > 1.5):
                print("  [%s] CONTROL FAILED %dt %+.1fR vs pin %dt %+.1fR - STOP"
                      % (scope.upper(), len(ctl), net_r(ctl), *pin[i]))
                return
            base = net_r(ctl)
            kinds = {}
            for sw in (args[1], args[3]):
                for s_ in sw:
                    for b in (s_.get("breaks") or []):
                        k = b.get("kind")
                        kinds[k] = kinds.get(k, 0) + 1
            print("  --- [%s] control %dt %+.1fR (PIN ok) | break marks: %s"
                  % (scope.upper(), len(ctl), base,
                     ", ".join("%s=%d" % kv for kv in sorted(kinds.items()))))
            print("      %-26s %6s %9s %7s %6s %6s %11s"
                  % ("arm", "n", "net", "R/t", "PF", "DD", "dNet"))
            for lbl, tr_map in ARMS:
                tr = ctl if not tr_map else run_arm(sim, tr_map, args, params)
                rs = [float(t["r_multiple"]) for t in tr]
                net = net_r(tr)
                dv = net - base
                print("      %-26s %6d %+9.1fR %+7.3f %6.2f %6.1f %+9.1fR%s"
                      % (lbl, len(rs), net, net / len(rs), pf(rs), dd(rs),
                         dv, "  <-- CLEARS M" if abs(dv) > M_NULL else ""))
            print()
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()