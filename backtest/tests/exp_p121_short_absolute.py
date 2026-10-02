"""P121 - the short side in ABSOLUTE terms, on the shipping book. Origin as control.

WHY THIS RUN. The short-side asymmetry has been cited twice and only once holds
up. P91 measured shorts at -0.4415/trade IS and -0.7471/trade OOS in absolute
terms while the same books read +53.2R and +68.4R in R - a real, absolute,
measured divergence. But that was on the pre-C16 book.

P119 then showed +81.5R -> +5.9R on shorts under cap-1 and it was cited as
corroboration. It is not: that is an R-multiple observation, and R is precisely
the metric P91 shows to be misleading on shorts. P119's own harness said so at
:182 and the label was still upgraded. So the shipping book has ZERO absolute
short-side measurements and the cited "two sightings" is one absolute sighting on
a superseded book plus one R sighting.

P91 was also run before C16 moved the SL pivot. The shipping book has different
stops, so P91's -0.44/-0.75 need not hold on the book that actually ships. That is
not a reason to doubt P91 - it is a reason the number needs re-deriving.

THE MEASURE - absolute price return per unit notional. Not r_multiple. Not net_r.

    long    (exit - entry) / entry
    short   (entry - exit) / entry

Summed per side, per era, longs and shorts separately. Method transfers unchanged
from exp_entry_fill_absolute.py.

NOT A FILTER PROPOSAL. If shorts are negative in absolute, that CANNOT become
"size down shorts" or "drop shorts". The decline-edge rule forbids it, side
filters tax the other side (P84/P86), and this asks what the book is made of,
not how to improve it. Characterisation only.

PRE-REGISTERED, before the run:

  short absolute > 0 in BOTH eras   P91's deficit is book- or era-specific
  short absolute < 0 in BOTH eras   CONFIRMED on the shipping book
  signs differ                      era-split

REQUIRED CONTROL - the origin book, same measure. This is mandatory, not
optional. Without it a confirmed deficit cannot be attributed to the shipping
book's stops rather than to P91's original book, and the point of the run is to
test whether C16 moved the short side.

  origin and leg DISAGREE in sign    C16 moved the short side. That is a NEW
                                     finding and makes C16 causal rather than
                                     incidental. It is the most interesting
                                     outcome available here.

NOT A THIRD SIGHTING. If this confirms, it is two independent absolute
observations on different books. Three would need a genuinely separate method.

Run: python -u exp_p121_short_absolute.py     (about 4 min)
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

BOOKS = (("champion_multi_sw10", "ORIGIN  (P91's book, pre-C16)"),
         ("champion_multi_sw10_leg", "LEG  (SHIPPING)"))


def _oos_args():
    c15o, f15o = load_unseen("15m")
    c1ho, f1ho = load_unseen("1h")
    return (c1ho, tc._compute_swings(f1ho, "continuous", min_bars=10),
            c15o, tc._compute_swings(f15o, "continuous", min_bars=50),
            load_fine_1m(c15o[0]["ts"], c15o[-1]["ts"]))


def raw_return(t):
    """P91 CONVENTION: (exit-entry)/entry, signed the SAME way for both sides.

    For a short this is the NEGATIVE of PnL. Profitable short -> exit below entry
    -> raw negative. This is what P91 tabulated.
    """
    e = float(t["entry_price"])
    if e <= 0:
        return None
    return (float(t["exit_price"]) - e) / e


def abs_return(t):
    """ECONOMIC PnL convention: sign-corrected for direction.

    long  (exit-entry)/entry
    short (entry-exit)/entry      <- negated vs P91
    """
    e = float(t["entry_price"])
    x = float(t["exit_price"])
    if e <= 0:
        return None
    raw = (x - e) / e
    if str(t.get("dir", "")).lower().startswith("s"):
        return -raw
    return raw


def split(tr):
    lo = [t for t in tr if str(t.get("dir", "")).lower().startswith("l")]
    sh = [t for t in tr if str(t.get("dir", "")).lower().startswith("s")]
    return lo, sh


def summarise(tr):
    lo, sh = split(tr)
    al = [abs_return(t) for t in lo if t.get("exit_price") is not None]
    ash = [abs_return(t) for t in sh if t.get("exit_price") is not None]
    rl = [raw_return(t) for t in lo if t.get("exit_price") is not None]
    rsh = [raw_return(t) for t in sh if t.get("exit_price") is not None]
    return (len(lo), sum(al), sum(al) / len(al) if al else 0.0,
            len(sh), sum(ash), sum(ash) / len(ash) if ash else 0.0,
            sum(rl), sum(rsh))


def main():
    d = get_data()
    is_args = (d["c1h"], d["sw10"], d["c15"], d["sw15"], d["fine"])
    oos_args = _oos_args()
    sim = tc.build_module()

    print("=" * 100)
    print("  P121  THE SHORT SIDE IN ABSOLUTE TERMS - shipping book, origin as control")
    print("=" * 100)
    print("  measure = (exit-entry)/entry, long; (entry-exit)/entry, short. Per unit")
    print("  notional. NOT r_multiple. This is P91's method, unchanged.")
    print("  characterisation only - NOT a filter proposal.\n")

    signs = {}
    for name, tag in BOOKS:
        params = {**BP, **EXPERIMENTS[name]["params"]}
        print("-" * 100)
        print("  BOOK %s   %s" % (name, tag))
        print("  %-4s %5s %9s %9s %9s | %5s %9s %9s %9s %11s"
              % ("era", "nL", "L PnL", "L/trade", "L in R", "nS",
                 "S PnL", "S/trade", "S in R", "S RAW = P91"))
        for scope in ("is", "oos"):
            args = is_args if scope == "is" else oos_args
            tr = [t for t in sim(*args, **dict(params))["ltf_trades"]
                  if t.get("outcome") != "open"]
            lo, sh = split(tr)
            nl, lsum, lmean, ns, ssum, smean, lraw, sraw = summarise(tr)
            lr = sum(float(t["r_multiple"]) for t in lo)
            sr = sum(float(t["r_multiple"]) for t in sh)
            signs[(name, scope)] = 1 if ssum > 0 else (-1 if ssum < 0 else 0)
            print("  %-4s %5d %+9.4f %9.4f %+9.1f | %5d %+9.4f %9.4f %+9.1f %+9.4f"
                  % (scope.upper(), nl, lsum, lmean, lr, ns, ssum, smean, sr, sraw))
            print("       (whole book %d trades, %+.1fR net)"
                  % (len(tr), net_r(tr)))
        print()

    print("=" * 100)
    print("  PRE-REGISTERED READING")
    print("=" * 100)
    leg = [signs[("champion_multi_sw10_leg", s)] for s in ("is", "oos")]
    org = [signs[("champion_multi_sw10", s)] for s in ("is", "oos")]

    if leg[0] == leg[1] and leg[0] < 0:
        print("  SHORT ABSOLUTE < 0 IN BOTH ERAS on the shipping book.")
        print("  -> P91's short-side deficit CONFIRMED on the book that ships.")
    elif leg[0] == leg[1] and leg[0] > 0:
        print("  SHORT ABSOLUTE > 0 IN BOTH ERAS on the shipping book.")
        print("  -> P91's deficit does NOT hold here. It is book- or era-specific,")
        print("     and P91's -0.44/-0.75 should not be quoted for the shipping book.")
    else:
        print("  SHORT ABSOLUTE SIGNS DIFFER ACROSS ERAS.")
        print("  -> era-split. The tenth appearance of that shape in this programme.")

    print()
    if leg != org:
        print("  CONTROL FIRES: origin and leg DISAGREE in sign.")
        print("  -> C16 MOVED THE SHORT SIDE. That makes C16 causal rather than")
        print("     incidental, and it is the most interesting outcome available.")
    else:
        print("  CONTROL: origin and leg agree in sign. C16 did not move it.")
    print()
    print("  P91 reference (pre-C16, origin book): shorts -0.4415/trade IS,")
    print("  -0.7471/trade OOS, against +53.2R / +68.4R in R.")
    print()
    print("  If this confirms, it is TWO independent absolute observations on")
    print("  different books. Not three.")


if __name__ == "__main__":
    main()