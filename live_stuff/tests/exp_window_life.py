"""P50 - HOW LONG DOES A 1h WINDOW ACTUALLY LIVE, AND WHAT DOES THE 16-DAY
CAP COST? The diagnostic behind P4's "turn the cap off" direction.

THE QUESTION
    A window ends at -1R, +3R, or 16 days. So the honest question is what the
    duration distribution actually looks like - and specifically how many
    windows are being KILLED by the 16-day cap while still open. P49 found
    that removing the cap is 4/4 positive and adds trades, which is only
    explicable if the cap is truncating windows that were still working.
    This measures that directly instead of inferring it from a net.

THE COMPARISON IS THE ANSWER
    The same window is tracked in both the capped and uncapped books by its
    start timestamp. Windows present at cap=16 and absent at cap=999 were
    truncated by the cap. For each, what did the leg do afterwards - did it
    reach +3R, die at -1R, or just keep running? That is the whole story.

NO NEW CLAIM IS PROMISED HERE
    This is a measurement of a pinned book plus one patched run. It explains
    P49's result; it does not by itself clear M = 193.4R, and the sweep
    there was not monotone, so the direction is the finding and not any
    number.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("live_stuff/tests", "live_stuff", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen, load_fine_1m
from test_experiments_craze import _compute_swings
from engine.v18_params import SWING

LANES = (
    ("champion_multi_sw10", "sw10", (500, 325.8), (279, 70.1)),
    ("utcsat_multi_sw10", "sw10", (454, 358.9), (253, 60.2)),
)


def get(scope, swtag):
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        return (c1h, _compute_swings(f1h, "continuous", min_bars=10),
                c15, _compute_swings(f15, "continuous",
                                     min_bars=SWING["min_bars_15m"]),
                load_fine_1m(c15[0]["ts"], c15[-1]["ts"]))
    d = get_data()
    identity_gate(d, tc.build_module())
    return d["c1h"], d[swtag], d["c15"], d["sw15"], d["fine"]


def run_cap(cap, a, params):
    from src.btc.engines import v7_timecap as v7
    orig = v7.simulate_btc_trades_v7

    def wrapped(*ar, **kw):
        kw["cap_days"] = cap
        return orig(*ar, **kw)

    v7.simulate_btc_trades_v7 = wrapped
    try:
        return tc.build_module()(*a, **params)
    finally:
        v7.simulate_btc_trades_v7 = orig


def q(v, p):
    s = sorted(v)
    if not s:
        return 0.0
    return s[min(len(s) - 1, int(len(s) * p))]


def main():
    print("=" * 100)
    print("  P50  HOW LONG DOES A 1h WINDOW LIVE, AND WHAT DOES THE 16-DAY "
          "CAP KILL?")
    print("=" * 100)
    for key, swtag, ispin, oospin in LANES:
        params = {**BP, **EXPERIMENTS[key]["params"]}
        print("  --- %s" % key)
        for scope, pin in (("is", ispin), ("oos", oospin)):
            a = get(scope, swtag)
            rc = run_cap(16, a, params)
            ru = run_cap(999, a, params)
            tc_ = [t for t in rc["ltf_trades"] if t.get("outcome") != "open"]
            tu = [t for t in ru["ltf_trades"] if t.get("outcome") != "open"]
            netc, nc = net_r(tc_), len(tc_)
            netu, nu = net_r(tu), len(tu)
            if abs(nc - pin[0]) > 2 or abs(netc - pin[1]) > 1.5:
                print("    [%s] CONTROL FAILED %dt %+.1fR -- STOP"
                      % (scope, nc, netc))
                return
            print("    [%s] capped %dt %+.1fR  ->  uncapped %dt %+.1fR  "
                  "(dNet %+.1fR)" % (scope.upper(), nc, netc, nu, netu,
                                     netu - netc))
            # HTF leg books, not the LTF book
            for nm, res in (("capped  ", rc), ("uncapped", ru)):
                legs = list(res.get("htf_trades_flip") or []) + \
                    list(res.get("htf_trades_b2") or [])
                dur = []
                for L in legs:
                    d = (int(L["exit_ts"]) - int(L["entry_ts"])) / 86400.0
                    dur.append(d)
                if not dur:
                    continue
                at_cap = sum(1 for d in dur if 15.5 <= d <= 16.5)
                print("      %s %d HTF legs  duration p10 %.2f  p50 %.2f  "
                      "p90 %.2f  max %.2f days   at the 16d cap: %d (%.1f%%)"
                      % (nm, len(dur), q(dur, .1), q(dur, .5), q(dur, .9),
                         max(dur), at_cap, 100.0 * at_cap / len(dur)))
            # which windows the cap removed
            def starts(res):
                s = {}
                for key_ in ("htf_trades_flip", "htf_trades_b2"):
                    for L in (res.get(key_) or []):
                        s[int(L["entry_ts"])] = L
                return s
            sc, su = starts(rc), starts(ru)
            killed = [t for t in su if t not in sc]
            if killed:
                kr = [float(su[t].get("r_multiple", 0) or 0) for t in killed]
                kd = [(int(su[t]["exit_ts"]) - t) / 86400.0 for t in killed]
                won = sum(1 for x in kr if x >= 2.99)
                lost = sum(1 for x in kr if x <= -0.99)
                print("      TRUNCATED BY THE CAP: %d windows. Uncapped they "
                      "lived p50 %.1f  max %.1f days and finished %+.1fR "
                      "total" % (len(killed), q(kd, .5), max(kd), sum(kr)))
                print("      of those, %d reached the +3R target, %d died at "
                      "-1R, %d neither (%.0f%% / %.0f%% / %.0f%%)"
                      % (won, lost, len(kr) - won - lost,
                         100.0 * won / len(kr), 100.0 * lost / len(kr),
                         100.0 * (len(kr) - won - lost) / len(kr)))
            # LTF trades that only exist uncapped
            kc = {(int(t["entry_ts"]), t["dir"]) for t in tc_}
            extra = [t for t in tu if (int(t["entry_ts"]), t["dir"]) not in kc]
            if extra:
                er = [float(t["r_multiple"]) for t in extra]
                print("      LTF trades that exist ONLY when uncapped: %d, "
                      "worth %+.1fR  (WR %.1f%%)"
                      % (len(extra), sum(er),
                         100.0 * sum(1 for x in er if x > 0) / len(er)))
            print()
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()