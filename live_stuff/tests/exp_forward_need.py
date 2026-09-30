"""P62 - HOW MUCH FORWARD DATA DOES THE DECIDING EXPERIMENT ACTUALLY NEED?

THE PROBLEM WITH THE QUEUE'S FORWARD ENTRY
    The queue says: "One family-wise pass on data/forward/bybit/ -
    adjudicate all unadopted survivors in a single pre-registered pass ...
    ~464 trades, so it can rule on things and confirm none."

    P61 measured the actual forward slice: 12.5 days, 14 1h swings,
    2 champion trades. Not 464. Not 60-70. TWO. The entry is wrong by two
    orders of magnitude and would send someone to spend a day building a
    pass that cannot see anything. It gets corrected below rather than
    quietly left, because a stale queue entry that promises a decision is
    more dangerous than an empty one.

THE QUESTION THIS ANSWERS
    M = 193.4R is the deck-relative null from a two-year block. A forward
    slice is SHORTER, and the queue's own caveat says a shorter block gives
    a WIDER null. So "wait for the forward pass" is not free and is not
    even well-specified: nobody can say how many months of data are needed
    before the pass can rule anything out.

    This measures it. The champion's realised trade sequences are cut into
    CONTIGUOUS blocks of N trades, in time order, and the spread of net R
    across blocks is what an N-trade forward slice would produce by chance
    alone. That spread IS the null at that sample size. The N at which it
    first falls under M = 193.4R is the trade count the deciding experiment
    actually needs.

METHOD - WHY CONTIGUOUS BLOCKS AND NOT IID BOOTSTRAP
    Trades are serially dependent - a window that opens once produces
    several correlated LTF trades, and market regimes persist. An IID
    bootstrap of a serially dependent series understates the spread, and
    understating the null is how a forward pass ends up "confirming"
    noise. Blocks preserve the autocorrelation, so the measured spread is
    conservative rather than flattering.

    Only the champion's own realised r_multiple sequences are used, and
    only their ORDER and GROUPING - no outcome is used to select or filter
    a block, and no threshold is searched.
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
from test_4_new_concepts import load_unseen
from test_4_new_concepts import load_fine_1m as load_fine_oos

M_NULL = 193.4
SIZES = (20, 40, 60, 80, 100, 120, 160, 200)


def blocks(rs, n):
    """Contiguous, non-overlapping blocks of n trades, in time order."""
    return [rs[i:i + n] for i in range(0, len(rs) - n + 1, n)]


def main():
    print("=" * 96)
    print("  P62  HOW MANY FORWARD TRADES DOES THE DECIDING PASS NEED?")
    print("=" * 96)
    print("  The queue promises a ~464-trade forward slice. It has 2.")
    print("  M = %.1fR is a TWO-YEAR null; a shorter slice has a wider one."
          % M_NULL)
    print("  So: cut the champion's realised trades into contiguous blocks\n")

    d = get_data()
    identity_gate(d, tc.build_module())
    (oc15, of15), (oc1h, of1h) = load_unseen("15m"), load_unseen("1h")
    oos_fine = load_fine_oos(oc15[0]["ts"], oc15[-1]["ts"])

    lanes = {}
    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        params = {**BP, **EXPERIMENTS[name]["params"]}
        a = d["c1h"], d["sw10"], d["c15"], d["sw15"], d["fine"]
        b = (oc1h, tc._compute_swings(of1h, "continuous", min_bars=10),
             oc15, tc._compute_swings(of15, "continuous", min_bars=50),
             oos_fine)
        for scope, args in (("is", a), ("oos", b)):
            tr = [t for t in tc.build_module()(*args, **params)["ltf_trades"]
                  if t.get("outcome") != "open"]
            lanes[(name, scope)] = ([float(t["r_multiple"]) for t in tr],
                                    net_r(tr))

    for (name, scope), (rs, net) in lanes.items():
        print("  --- %s / %s : %d trades, %+.1fR" % (name, scope.upper(),
                                                     len(rs), net))
        print("      %6s %7s %10s %10s %10s %10s   %s"
              % ("N", "blocks", "mean", "min", "max", "spread", "under M?"))
        need = None
        for n in SIZES:
            bs = blocks(rs, n)
            if len(bs) < 2:
                print("      %6d %7d   (not enough trades to form 2 blocks)"
                      % (n, len(bs)))
                continue
            tots = [sum(b) for b in bs]
            sp = max(tots) - min(tots)
            ok = sp <= M_NULL
            if ok and need is None:
                need = n
            print("      %6d %7d %+10.1f %+10.1f %+10.1f %10.1f   %s"
                  % (n, len(bs), sum(tots) / len(tots), min(tots), max(tots),
                     sp, "YES" if ok else "no"))
        print("      first N with spread <= M: %s" % (need or "none in range"))
        if need:
            yrs = need / float(len(rs))
            span_yr = 3.7 if scope == "is" else 2.0
            print("      -> %d trades is about %.1f%% of the %s era = ~%.1f "
                  "months of trading time" % (need, 100.0 * yrs,
                                               scope, yrs * span_yr * 12))
        print()

    print("  Read: a forward pass cannot rule anything out until the null it")
    print("  is measured against is tighter than M. That number, not the")
    print("  queue's 464, is the date to plan around.")


if __name__ == "__main__":
    main()