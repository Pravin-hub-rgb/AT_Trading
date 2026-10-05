"""P79 - PREFIX INVARIANCE. The question that decides whether any of this
is live-tradable at all.

THE QUESTION THE OWNER ASKED
    "I am going to build a bot for live trading - is this not a lookahead,
    or something like that?"

    That question is prior to every other question in this programme. A
    strategy that cannot be replayed live is a strategy that cannot be
    traded, no matter how good its backtest is.

THE ONE-LINE TEST
    Take the candle series, compute the swing chain on it. Then truncate the
    series at some bar T and compute the chain again. Compare the swings
    that both runs produced, for the region before T.

      INVARIANT      the early swings are identical. A live system walking
                     the same bars one at a time would reproduce exactly what
                     the backtest saw. Nothing is looking ahead.
      NOT INVARIANT  the early swings differ once the series is extended.
                     The full-history run used information from AFTER the
                     swing it recorded. That is lookahead, and it is fatal for
                     live, however good the P&L is.

    Truncation is done at several cut points so the result is not an
    artefact of one boundary, and both the 1h and 15m chains are tested
    because the book uses both.

WHY THE REPO ALREADY SUSPECTS THE BAD ANSWER
    method/TRANSCRIPT_THESIS_BACKLOG.md line 37 records: "Prefix audit remains
    non-invariant for baseline and age-2 candidate because of the shared
    full-history swing-chain boundary caveat. Gate-level mark lookup is
    causal, but live replay equivalence still needs dedicated validation."

    So: the MARKS were found causal, but the CHAIN as a whole was recorded
    as non-invariant, and the validation was never done. This file is that
    validation, done properly - across cut points and both timeframes - and
    it measures WHERE the divergence begins, because "non-invariant" without
    a location cannot be acted on.

WHAT THIS DOES AND DOES NOT DECIDE
    It decides whether the swing chain is replayable live. It does not judge
    any candidate, and a negative result here does not invalidate the
    champion's numbers as backtest numbers - it bounds what they can be
    used FOR.

MATCHING RULE - EXACT, NOT FUZZY
    Swings are compared on the tuple the engine actually uses downstream
    (swing_index, dir, confirmed_at_idx, seg.start_px, seg.end_px), exact
    equality. A tolerant match would hide exactly the small differences
    that matter, so the test is deliberately unforgiving.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from run_experiment import get_data
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen
from src.walker import FlowCandle

CUTS = (0.60, 0.75, 0.90)


def as_flow(c):
    return [FlowCandle(date=x["date"], open=x["open"], high=x["high"],
                       low=x["low"], close=x["close"]) for x in c]


def sig(s):
    """The exact tuple downstream code reads. Deliberately unforgiving."""
    seg = s.get("seg") or {}
    return (int(s.get("swing_index", -1)),
            s.get("dir"),
            int(s.get("confirmed_at_idx", -1)),
            round(float(seg.get("start_px") or 0.0), 6),
            round(float(seg.get("end_px") or 0.0), 6))


def compare(full, trunc, cut_n, label):
    """Swings whose confirmed_at_idx lies strictly before the cut, present
    in BOTH runs. Any difference here is lookahead."""
    tf = [s for s in full if int(s.get("confirmed_at_idx", 1 << 30)) < cut_n]
    tmap = {}
    for s in trunc:
        tmap.setdefault(sig(s), []).append(s)
    matched, diff = 0, []
    for s in tf:
        if sig(s) in tmap:
            matched += 1
        else:
            diff.append(s)
    n = len(tf)
    pct = 100.0 * matched / n if n else 0.0
    print("      %-14s cut at bar %6d | swings before cut %5d | identical "
          "%5d (%5.1f%%) | DIFFER %5d"
          % (label, cut_n, n, matched, pct, len(diff)))
    if diff:
        d0 = diff[0]
        print("        first divergence: swing_index=%s dir=%s "
              "confirmed_at_idx=%s start_px=%.2f"
              % (d0.get("swing_index"), d0.get("dir"),
                 d0.get("confirmed_at_idx"),
                 float((d0.get("seg") or {}).get("start_px") or 0.0)))
    return matched, n


def main():
    print("=" * 100)
    print("  P79  PREFIX INVARIANCE - can any of this be live-traded?")
    print("=" * 100)
    print("  Compute the swing chain on the full series, then on a truncated")
    print("  series. Compare the swings both produced BEFORE the cut.")
    print("  Identical = replayable live. Different = lookahead.\n")

    d = get_data()
    print("  --- IS 1h chain (min_bars=10, the champion's own setting)")
    full1h = tc._compute_swings(as_flow(d["c1h"]), "continuous", min_bars=10)
    print("      full chain: %d swings" % len(full1h))
    for f in CUTS:
        n = int(len(d["c1h"]) * f)
        tr = tc._compute_swings(as_flow(d["c1h"][:n]), "continuous",
                               min_bars=10)
        compare(full1h, tr, n, "cut %.0f%%" % (f * 100))

    print("\n  --- IS 15m chain (min_bars=50, the champion's LTF setting)")
    full15 = tc._compute_swings(as_flow(d["c15"]), "continuous",
                                min_bars=tc.MB15)
    print("      full chain: %d swings" % len(full15))
    for f in CUTS:
        n = int(len(d["c15"]) * f)
        tr = tc._compute_swings(as_flow(d["c15"][:n]), "continuous",
                               min_bars=tc.MB15)
        compare(full15, tr, n, "cut %.0f%%" % (f * 100))

    (oc15, of15), (oc1h, of1h) = load_unseen("15m"), load_unseen("1h")
    print("\n  --- OOS 1h chain (held-out era, same test)")
    fullo = tc._compute_swings(as_flow(oc1h), "continuous", min_bars=10)
    print("      full chain: %d swings" % len(fullo))
    for f in CUTS:
        n = int(len(oc1h) * f)
        tr = tc._compute_swings(as_flow(oc1h[:n]), "continuous", min_bars=10)
        compare(fullo, tr, n, "cut %.0f%%" % (f * 100))

    print("\n  Read: 100% identical at every cut = a live walker reproduces")
    print("  the backtest exactly and nothing here is lookahead. Anything")
    print("  below 100% is a bound on what the backtest can be used for.")
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()