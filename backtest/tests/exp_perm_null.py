"""P25 - IS `M` EVEN THE RIGHT BAR? And does decay live on other TFs?

THE USER'S CHALLENGE, WHICH IS METHODOLOGICALLY THE RIGHT ONE
============================================================
"koi bhi M (479.9R) clear nahi hua. sab andar hain. yeh karna jaroori
hai?? research karo kahi bas tum aise he nahi bolre ho"

Correct, and I had been applying the wrong test. P5's M = 479.9R is a
MOVE-BLOCK BOOTSTRAP of the book's own net: "could this +325.8R have come
from reordering the same 500 trades?" That is the right question for the
BOOK. It is the WRONG question for a FILTER.

A filter is not a new book. It is a SUBSET of the same 500 trades, on the
same days, in the same regime, scored on the same outcomes. Comparing its
net to a reshuffle band throws away the pairing and measures the wrong
thing. It is also self-defeating: it is so wide that nothing will ever
clear it, which is a way of saying "never adopt anything" while looking
rigorous.

THE CORRECT NULL IS A PERMUTATION OF THE FILTER ITSELF
======================================================
The claim a filter makes is not "this net is large". It is:

    "the trades I removed are worse than the trades I kept"

That is a discrimination claim, and the right null holds the book, the
outcomes and the SIZE of the removal fixed, and destroys only the link
between the rule and the trades. Concretely: mark exactly as many trades
as the real filter did, chosen at RANDOM. That yields the distribution of
dNet obtainable by a filter of this size that knows nothing.

If the real filter's dNet sits inside that, it is not discriminating.
This is the test the last several experiments were never scored against,
and it is run here for every arm.

SECOND QUESTION: WHICH TIMEFRAME?
=================================
Decay has only ever been built on 15m legs. The user asks whether 5m / 30m
/ 2h / 4h carry a better version. 5m, 30m, 2h and 4h are synthesised here
from the 1m series that is already loaded, so every leg's extreme is still
resolved on real tradeable bars, and the break test still uses only bars
at or before the entry.
"""
from __future__ import annotations

import bisect as bs
import random
import time
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

from run_experiment import get_data, identity_gate, net_r  # noqa: E402
import test_experiments_craze as tc  # noqa: E402
from test_4_new_concepts import load_unseen, load_fine_1m  # noqa: E402
from test_experiments_craze import _compute_swings  # noqa: E402
from engine.v18_params import SWING  # noqa: E402
from exp_decay_switch import PARAMS, legs_by_dir, decay_pair  # noqa: E402

THR, NLEG = 0.75, 4
DRAWS, SEED = 2_000, 20260929
TFS = ("15m", "30m", "1h", "2h", "4h")


class Bar:
    """A real FlowCandle. _compute_swings needs .date as a STRING plus
    .open/.high/.low/.close; `.date` is sliced as date[:10] internally."""
    __slots__ = ("ts", "date", "open", "high", "low", "close")

    def __init__(self, date, o, h, l, c, ts=0):
        self.date, self.open, self.high, self.low, self.close = \
            date, o, h, l, c
        self.ts = ts


def _fmt(ts):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(int(ts)))


def synth(fine, mins):
    """Aggregate the 1m series into `mins`-minute Bars."""
    step = mins * 60
    out = []
    ts0 = hi = lo = oc = None
    for c in fine:
        t = int(c["ts"])
        b = (t // step) * step
        if b != ts0:
            if ts0 is not None:
                out.append(Bar(_fmt(ts0), oc, hi, lo, oc, ts0))
            ts0, hi, lo, oc = b, float(c["high"]), float(c["low"]), \
                float(c["close"])
        else:
            hi = max(hi, float(c["high"]))
            lo = min(lo, float(c["low"]))
            oc = float(c["close"])
    if ts0 is not None:
        out.append(Bar(_fmt(ts0), oc, hi, lo, oc, ts0))
    return out




def legs_of(bars, min_bars):
    return legs_by_dir(_compute_swings(bars, "continuous", min_bars=min_bars))



def load(scope):
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        return (c1h, _compute_swings(f1h, "continuous", min_bars=10),
                c15, _compute_swings(f15, "continuous",
                                     min_bars=SWING["min_bars_15m"]),
                load_fine_1m(c15[0]["ts"], c15[-1]["ts"]))
    d = get_data()
    identity_gate(d, tc.build_module())
    return d["c1h"], d["sw10"], d["c15"], d["sw15"], d["fine"]


def perm_null(rs, drop_idx, draws, rng):
    """dNet under RANDOM removal of the same SIZE as the real filter.

    dNet = -(net of removed trades), so the whole question is "are the
    trades this rule removed actually worse than a random set of the same
    size". Book, outcomes and count are all held fixed; only the link
    between the rule and the trades is destroyed.
    """
    k = len(drop_idx)
    if k == 0 or k >= len(rs):
        return None
    idx = list(range(len(rs)))
    out = []
    for _ in range(draws):
        s = sum(rs[i] for i in rng.sample(idx, k))
        out.append(-s)
    out.sort()
    return out


def main():
    print("=" * 100)
    print("  P25  IS `M` THE RIGHT BAR?  +  does decay live on another TF?")
    print("=" * 100)
    print(f"  thr={THR} nlegs={NLEG}  draws={DRAWS}")
    print("  Null = random removal of the SAME SIZE - a discrimination")
    print("  test, not a reshuffle-of-the-book test.\n")

    for scope in ("is", "oos"):
        c1h, sw10, c15, sw15, fine = load(scope)
        sim = tc.build_module()
        r = sim(c1h, sw10, c15, sw15, fine_ltf=fine, **PARAMS)
        tr = [t for t in r["ltf_trades"] if t.get("outcome") != "open"]
        base = net_r(tr)
        rs = [float(t["r_multiple"]) for t in tr]
        rng = random.Random(SEED)
        print(f"  --- {scope.upper()}  control n={len(tr)} net={base:+.1f}R")
        print(f"    {'arm':<8} {'keep':>5} {'removed':>7} {'dNet':>8} "
              f"{'p':>7} {'verdict':>10}")

        bars = {"15m": (synth(fine, 15), 50),
                "30m": (synth(fine, 30), 20),
                "1h": (synth(fine, 60), 20),
                "2h": (synth(fine, 120), 20),
                "4h": (synth(fine, 240), 20)}
        for tf in TFS:
            bb, mb = bars[tf]
            ser = ([int(x.ts) for x in bb],
                   [float(x.low) for x in bb],
                   [float(x.high) for x in bb])
            try:
                ups, dns = legs_of(bb, mb)
            except Exception:
                print(f"    {tf:<8} (swing build failed)")
                continue
            drop = []
            for i, t in enumerate(tr):
                v, _ = decay_pair(ups, dns, int(t["entry_ts"]), ser[1], ser[2],
                                  ser[0], n=NLEG)
                if v is not None and v >= THR:
                    drop.append(i)
            if not drop or len(drop) >= len(rs):
                print(f"    {tf:<8} {'-':>5} {len(drop):>7} "
                      f"{'-':>8} {'-':>7} {'no drop':>10}")
                continue
            dnet = -sum(rs[i] for i in drop)
            null = perm_null(rs, drop, DRAWS, rng)
            # UPPER tail: a good filter drops a net-negative set, so its
            # dNet is positive and large. p = P(random dNet >= real dNet).
            p = sum(1 for x in null if x >= dnet) / float(len(null))
            v = ("REAL" if p < 0.05 else ("weak" if p < 0.20 else "NOISE"))
            print(f"    {tf:<8} {len(rs)-len(drop):>5} {len(drop):>7} "
                  f"{dnet:>+8.1f} {p:>7.3f} {v:>10}")
        print()


if __name__ == "__main__":
    main()
