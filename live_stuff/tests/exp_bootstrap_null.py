"""P63 - SIZING THE FORWARD NULL PROPERLY (stationary block bootstrap).

WHY P62 WAS NOT ENOUGH
    P62 cut the champion's trades into disjoint blocks and read max-min as
    the spread. That is a severely biased-low estimator when only a handful
    of blocks exist, so P62 withdrew its own conclusion. This is the
    replacement: a stationary block bootstrap (Politis & Romano) with many
    resamples, which is what the method needs to produce a usable band.

METHOD
    Resample ceil(n/L) blocks of L consecutive trades, each starting at a
    random position INDEPENDENTLY (that is what makes it stationary rather
    than non-overlapping), concatenate to length n, and sum. Repeat many
    times. The 5th-95th percentile of those sums is the null band at that
    sample size: what a random LONGER-RUNNING book of the champion's own
    statistics would produce by chance alone.

    Blocks are consecutive in TIME. An IID bootstrap would be wrong here -
    trades inside one bias window are correlated and regimes persist, so
    resampling trades independently understates the spread, and understating
    a null is how a forward pass ends up confirming noise.

BLOCK LENGTH - PRE-REGISTERED, AND THE WIDEST BAND WINS
    P62's caveat already fixed block length 20 to match
    exp_montecarlo_dd.py, and noted shorter blocks give a wider null while
    much longer ones destroy the serial structure the method exists to
    preserve. L in {10, 20, 40} is therefore a SENSITIVITY check, not a
    search: the band reported is the WIDEST of the three, which is the
    conservative choice, and no L is selected for giving a nicer answer.

WHAT THIS IS FOR
    The queue wants a family-wise forward pass but the forward slice has 2
    trades. This answers the question that actually matters: how many
    forward trades are needed before the pass can rule anything out, i.e.
    before its null band is tighter than M = 193.4R. It is a requirement on
    FUTURE DATA LENGTH, measured from the champion's realised sequences.
"""
import random
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
BLOCKS = (10, 20, 40)
DRAWS = 20000
SEED = 20260929
SIZES = (40, 60, 80, 100, 140, 180, 220, 279)


def sbb(rs, n, L, draws, rnd):
    """Stationary block bootstrap of the SUM of an n-trade slice."""
    m = len(rs)
    if m < L:
        return None
    nb = -(-n // L)
    out = []
    for _ in range(draws):
        tot = 0.0
        for _ in range(nb):
            s = rnd.randrange(0, m - L + 1)
            tot += sum(rs[s:s + L])
        out.append(tot)
    out.sort()
    return out[int(0.05 * draws)], out[int(0.95 * draws)]


def main():
    print("=" * 96)
    print("  P63  SIZING THE FORWARD NULL (STATIONARY BLOCK BOOTSTRAP)")
    print("=" * 96)
    print("  L in %s, %d draws, seed %d." % (str(BLOCKS), DRAWS, SEED))
    print("  The WIDEST band across L is reported - conservative, not chosen.")
    print("  M = %.1fR\n" % M_NULL)

    d = get_data()
    identity_gate(d, tc.build_module())
    (oc15, of15), (oc1h, of1h) = load_unseen("15m"), load_unseen("1h")
    oos_fine = load_fine_oos(oc15[0]["ts"], oc15[-1]["ts"])

    series = {}
    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        params = {**BP, **EXPERIMENTS[name]["params"]}
        a = d["c1h"], d["sw10"], d["c15"], d["sw15"], d["fine"]
        b = (oc1h, tc._compute_swings(of1h, "continuous", min_bars=10),
             oc15, tc._compute_swings(of15, "continuous", min_bars=50),
             oos_fine)
        for scope, args in (("is", a), ("oos", b)):
            tr = [t for t in tc.build_module()(*args, **params)["ltf_trades"]
                  if t.get("outcome") != "open"]
            series[(name, scope)] = [float(t["r_multiple"]) for t in tr]

    for key, rs in series.items():
        rnd = random.Random(SEED)
        print("  --- %s / %s : %d trades" % (key[0], key[1].upper(), len(rs)))
        print("      %5s %14s %14s %14s   %s"
              % ("n", "lo (widest)", "hi (widest)", "band width", "vs M"))
        need = None
        for n in SIZES:
            if n > len(rs):
                continue
            best = None
            for L in BLOCKS:
                r = sbb(rs, n, L, DRAWS, rnd)
                if r is None:
                    continue
                lo, hi = r
                if best is None or (hi - lo) > (best[1] - best[0]):
                    best = (lo, hi)
            if best is None:
                continue
            w = best[1] - best[0]
            ok = w <= M_NULL
            if ok and need is None:
                need = n
            print("      %5d %14.1f %14.1f %14.1f   %s"
                  % (n, best[0], best[1], w,
                     "TIGHTER THAN M" if ok else "wider than M"))
        print("      smallest n whose band is tighter than M: %s"
              % (need or "none tested"))
        print()

    print("  This is the number to plan the forward pass around - unlike")
    print("  P62's, it does not depend on how many disjoint blocks exist.")
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()