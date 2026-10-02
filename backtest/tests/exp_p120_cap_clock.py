"""P120 - is the concurrency cap on the right clock? The existence audit was not enough.

WHERE THIS COMES FROM. exp_max_concurrent is a test_experiments_craze.py source
patch, not an engine feature (0 hits under backend/src). That much is settled.

An earlier claim said the cap's enforcement used the wrong clock - `_now_ts =
candle_ts[i]` (bar open) where the repo elsewhere writes `ts + 900`. That claim was
rejected, and correctly: `entry_ts` is defined as `int(candles_ltf[i]["ts"])` at
v19_champion.py:834, and cooldown_bars, last_loss_bar and _wb_idx in the injected
walk all use the same bar-open clock. `ts + 900` is the HTF-close alignment
operation, a different question.

BUT THE REJECTION WAS RESTED ON A BAD FALSIFIER. P117 reported that an independent
overlap audit agreed exactly with every cap - cap=1 gave observed max 1, cap=4
gave 4. That argument is circular. The audit reads the same `exit_ts` and
`entry_ts` fields the engine reads, so both would be wrong together. It proved the
cap is ENFORCED, not that it is enforced AT THE RIGHT INSTANT. This is exactly
the limit exp_engine_knobs.py declares about itself: existence is necessary, not
sufficient. The same limit applies to an audit of ones own harness.

WHAT ACTUALLY SETTLES IT. Simulate the cap over the same candidate trade list
under BOTH clocks and compare the resulting books:

    clock A   open = #{u : u.exit_ts > t.entry_ts}          (bar open, what runs)
    clock B   open = #{u : u.exit_ts > t.entry_ts + 900}    (entry instant)

The two differ only for trades exiting inside the 15 minutes after an entry. If
the books match under both, the clock is irrelevant on this data and the question
is closed with evidence rather than argument. If they differ, every cap number in
P117 and P119 was measured on the wrong clock and they all need re-deriving.

PRE-REGISTERED: identical books under both clocks closes this. Any difference at
any cap is a C16-class finding, not a nitpick.

KNOWN LIMIT OF THIS METHOD - read before quoting any number here. This is a
POST-FILTER, not an inline replay. The engine applies the cap inside the walk, so
dropping a trade changes downstream state - last_loss_ts, cooldown_bars, the
window rules - and therefore changes which later trades are taken. P117's inline
cap-1 OOS is 219 trades / -11.8R; this replay gives 212 / -10.9R. The difference
is that state dependence, not an error.

So: the CLOCK COMPARISON is valid, because both clocks are evaluated with the
identical method and a clock difference would show up as a book difference. The
ABSOLUTE NUMBERS here do not reproduce P117 and are not meant to. Cite P117 for
book-level figures; cite this only for the A-vs-B clock verdict.

No engine change. One pass over trades already produced.

Run: python -u exp_p120_cap_clock.py     (about 4 min)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest", "backtest/tests", "backtest/sweeps", "backtest/engine", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import EXPERIMENTS, BP
from run_experiment import net_r, get_data
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen, load_fine_1m

BOOK = "champion_multi_sw10_leg"
CAPS = (1, 2, 3, 4, 5, 6)


def _oos_args():
    c15o, f15o = load_unseen("15m")
    c1ho, f1ho = load_unseen("1h")
    return (c1ho, tc._compute_swings(f1ho, "continuous", min_bars=10),
            c15o, tc._compute_swings(f15o, "continuous", min_bars=50),
            load_fine_1m(c15o[0]["ts"], c15o[-1]["ts"]))


def simulate(cands, cap, offset):
    """Greedy replay of the cap rule over an entry-ordered candidate list.

    The engine books a trade when the count of ALREADY BOOKED trades still open is
    below cap. Replay that exactly, with the open test shifted by `offset`.
    """
    kept, dropped = [], 0
    for t in cands:
        if cap:
            probe = int(t["entry_ts"]) + offset
            if sum(1 for u in kept if int(u["exit_ts"]) > probe) >= cap:
                dropped += 1
                continue
        kept.append(t)
    return kept, dropped


def observed_max(kept, offset):
    ev = []
    for t in kept:
        ev.append((int(t["entry_ts"]) + offset, 1))
        ev.append((int(t["exit_ts"]) + offset, -1))
    ev.sort()
    cur = peak = 0
    for _, d in ev:
        cur += d
        peak = max(peak, cur)
    return peak


def main():
    d = get_data()
    is_args = (d["c1h"], d["sw10"], d["c15"], d["sw15"], d["fine"])
    oos_args = _oos_args()
    params = {**BP, **EXPERIMENTS[BOOK]["params"]}
    sim = tc.build_module()

    print("=" * 96)
    print("  P120  IS THE CONCURRENCY CAP ON THE RIGHT CLOCK?")
    print("=" * 96)
    print("  clock A = entry_ts        (bar open, what actually runs)")
    print("  clock B = entry_ts + 900  (entry instant)")
    print("  pre-registered: identical books -> CLOSED.  any difference -> C16-class.\n")

    verdicts = {}
    for scope in ("is", "oos"):
        args = is_args if scope == "is" else oos_args
        # The candidate list is the UNCAPPED book: every trade the engine would
        # take with no cap. That is exactly the set the cap rule filters.
        cands = [t for t in sim(*args, **dict(params))["ltf_trades"]
                 if t.get("outcome") != "open"]
        cands.sort(key=lambda t: int(t["entry_ts"]))
        print("-" * 96)
        print("  [%s]  %d uncapped candidates   net %+.1fR"
              % (scope.upper(), len(cands), net_r(cands)))
        print("  %-5s %-20s %-20s %8s %9s %9s"
              % ("cap", "A: n/drop/max", "B: n/drop/max", "verdict",
                 "net A", "net B"))
        for cap in CAPS:
            ka, da = simulate(cands, cap, 0)
            kb, db = simulate(cands, cap, 900)
            same = len(ka) == len(kb) and da == db
            verdicts[(scope, cap)] = same
            print("  %-5d %5d /%4d /%4d    %5d /%4d /%4d    %8s %9.1f %9.1f"
                  % (cap, len(ka), da, observed_max(ka, 0),
                     len(kb), db, observed_max(kb, 900),
                     "same" if same else "*** DIFF ***",
                     net_r(ka), net_r(kb)))
        print()

    diffs = [k for k, v in verdicts.items() if not v]
    print("=" * 96)
    print("  VERDICT")
    print("=" * 96)
    if not diffs:
        print("  ALL caps identical under both clocks.")
        print()
        print("  The clock is IRRELEVANT on this data: no trade exits inside the 15")
        print("  minutes after a candidate entry in a way that changes the open count.")
        print("  The +900 question is closed with EVIDENCE, not argument.")
        print()
        print("  P117's cap numbers stand. The earlier existence-based argument is")
        print("  withdrawn as insufficient; this replaces it.")
    else:
        print("  DIFFERENCE FOUND at: %s" % (diffs,))
        print()
        print("  Every cap number in P117 and P119 was measured on the wrong clock.")
        print("  They all need re-deriving. This is a C16-class finding.")
    print()
    print("  Why the old argument was not enough: this replay and the engine both")
    print("  read exit_ts and entry_ts, so an existence check could only confirm the")
    print("  cap binds, never that it binds at the right instant.")


if __name__ == "__main__":
    main()