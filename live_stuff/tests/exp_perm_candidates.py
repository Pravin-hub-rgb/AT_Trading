"""P26 - SCORE THE C16 SURVIVORS UNDER THE CORRECT NULL, WITH MULTIPLE-TESTING
CORRECTION. `M` was the wrong bar; P25 showed a filter must be scored
against random filters of the SAME SIZE, not against a reshuffle of the
book's own net.

This re-scores the P16/P19 candidates under that test:

    decay<0.75            15m structural (P15 incumbent)
    decay<0.90            the looser variant that P23 preferred
    nest1h>0.25           alone
    age>0.5d              alone
    age>1.0d              alone
    nest1h>0.4            alone
    nest1h>0.25 + age>0.5d   the P16 recommendation

Multiple testing: eight arms are looked at. A raw p < 0.05 on the best of
eight is what a grid produces BY CONSTRUCTION (~0.05 * 8 chance hits under
the null). So both raw p AND the Benjamini-Hochberg adjusted p are printed.
An arm only counts as real if it survives the adjustment in BOTH eras.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("live_stuff/tests", "live_stuff", "backend"):
    sys.path.insert(0, str(ROOT / p))

from exp_newbar_search import build, sim_holder  # noqa: E402
from test_experiments_craze import build_module  # noqa: E402
import random  # noqa: E402

DRAWS, SEED = 10_000, 20260929

ARMS = [
    ("decay<0.75", lambda r: r["decay"] < 0.75),
    ("decay<0.90", lambda r: r["decay"] < 0.90),
    ("nest1h>0.25", lambda r: r["nest1h"] > 0.25),
    ("nest1h>0.4", lambda r: r["nest1h"] > 0.4),
    ("age>0.5d", lambda r: r["age"] > 0.5),
    ("age>1.0d", lambda r: r["age"] > 1.0),
    ("nest1h>0.25+age>0.5d", lambda r: r["nest1h"] > 0.25 and r["age"] > 0.5),
    ("nest1h>0.25+age>1.0d", lambda r: r["nest1h"] > 0.25 and r["age"] > 1.0),
]


def perm(rs, drop, draws, rng):
    """dNet if a random set of the SAME SIZE were removed instead."""
    k = len(drop)
    idx = list(range(len(rs)))
    out = sorted(-sum(rs[i] for i in rng.sample(idx, k)) for _ in range(draws))
    return out


def main():
    print("=" * 96)
    print("  P26  CANDIDATES UNDER THE CORRECT NULL  (+ BH correction)")
    print("=" * 96)
    print(f"  draws={DRAWS}  arms={len(ARMS)}")
    print("  A filter is only REAL if it beats a random filter of the same")
    print("  size, in BOTH eras, after multiple-testing correction.\n")
    sim_holder[0] = build_module()

    res = {}
    for sc in ("is", "oos"):
        rows, per, n, bnet = build(sc)
        rs = [r["r"] for r in rows]
        rng = random.Random(SEED)
        # net of the whole book, for reference
        base = sum(rs) - per * n
        print(f"  --- {sc.upper()}  control n={n} net={base:+.1f}R")
        for lbl, rule in ARMS:
            keep = [i for i, r in enumerate(rows) if rule(r)]
            drop = [i for i in range(n) if i not in set(keep)]
            k = len(drop)
            if k == 0 or k >= n:
                print(f"    {lbl:<22} drop={k:<4} (degenerate)")
                continue
            dnet = -(sum(rs[i] for i in drop) - per * k)
            null = perm(rs, drop, DRAWS, rng)
            # dNet = net(kept) - net(all) = -(net of removed). A GOOD
            # filter drops a NEGATIVE-net set, so dNet is POSITIVE and we
            # need P(null >= dNet) - an UPPER tail. The previous version
            # used a lower tail, which inverts the result entirely.
            p = sum(1 for x in null if x >= dnet) / float(len(null))
            res.setdefault(lbl, {})[sc] = (k, n - k, dnet, p)

        # BH within this era
        ps = sorted((v[sc][3], lbl) for lbl, v in res.items() if sc in v)
        m_ = len(ps)
        adj = {}
        prev = 1.0
        for i in range(m_ - 1, -1, -1):
            p, lbl = ps[i]
            prev = min(prev, p * m_ / (i + 1))
            adj[lbl] = prev
        print(f"\n    {'arm':<22} {'drop':>5} {'keep':>5} {'dNet':>9} "
              f"{'p':>7} {'p_BH':>7}  verdict")
        for lbl, _ in ARMS:
            if sc not in res.get(lbl, {}):
                continue
            k, kn, dnet, p = res[lbl][sc]
            q = adj.get(lbl, 1.0)
            v = "REAL" if (p < 0.05 and q < 0.05) else (
                "weak" if p < 0.10 else "NOISE")
            print(f"    {lbl:<22} {k:>5} {kn:>5} {dnet:>+9.1f} {p:>7.3f} "
                  f"{q:>7.3f}  {v}")
        print()

    print("  === BOTH-ERA SURVIVORS (p<0.05 raw in IS and OOS) ===")
    for lbl, _ in ARMS:
        d = res.get(lbl, {})
        if "is" in d and "oos" in d:
            pi, po = d["is"][3], d["oos"][3]
            both = pi < 0.05 and po < 0.05
            print(f"    {lbl:<22} IS p={pi:.3f}  OOS p={po:.3f}  "
                  f"{'*** BOTH ***' if both else ''}")


if __name__ == "__main__":
    main()
