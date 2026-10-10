"""Did the 2026-10-09 "better in 2 of 6 years" compare the wrong things?

HTF_FS_ENTRY_REJECTED.md rejected htf_fs="all" partly on a period control that
said "htf_fs better in 2 of 6 years (champ_long)". The 2026-10-10 grid measures the
same arm on the same books and gets 5 of 6, with a half-year fixed effect of
t = +3.42. Both cannot be right, so this reproduces the old estimator and checks
it.

The old code was:

    ea = sum(arms["off"]["per_h"][c][0] for c in hs)  / len(hs)
    eb = sum(arms["all"]["per_h"][c][0] for c in hs2) / len(hs2)
    dB += 1 if (eb > ea) else 0

ea averages the off arm's half-year NETS over the half-year cells the OFF arm
happens to populate. eb averages the all arm's half-year NETS over the cells the
ALL arm populates. Those two denominators are not the same set, and the arms
populate different numbers of half-years because the FS arm trades more. So the
comparison is between an average over one set and an average over another, and
whether "better" comes out yes or no depends on how many half-years each arm
happens to touch in that year rather than on which arm earned more.

The grid's year comparison uses per-year TOTALS for both arms, so the two share a
basis. That is the comparison the doc should have made.

This prints both, per year, so the difference is visible rather than asserted.
"""
import sys
from collections import defaultdict

sys.path.insert(0, ".")

from exp_tf_family import build_family_module      # noqa: E402
from run_experiment import net_r, get_swings        # noqa: E402
from exp_signal_metrics import load_era             # noqa: E402
from experiment_registry import EXPERIMENTS         # noqa: E402


def half(d):
    return d[:4] + "H" + ("1" if int(d[5:7]) <= 6 else "2")


def main():
    sim = build_family_module()
    E = {e: load_era(e) for e in ("is", "oos")}
    base = dict(EXPERIMENTS["fsent_champ_long"]["params"])

    per = {}
    for lbl, val in (("off", ""), ("all", "all")):
        p = dict(base)
        p["exp_htf_fs_entry"] = val
        ph = defaultdict(list)
        py = defaultdict(float)
        for era in ("is", "oos"):
            d = E[era]
            o = sim(d["c1h"], get_swings(d, "sw10"), d["c15"], d["sw15"],
                    fine_ltf=d["fine"], **p)
            for t in o["ltf_trades"]:
                if t.get("outcome") == "open":
                    continue
                r = net_r([t])
                ph[half(t["entry_date"])].append(r)
                py[t["entry_date"][:4]] += r
        per[lbl] = (ph, py)

    offh, offy = per["off"]
    allh, ally = per["all"]

    print("=" * 96)
    print("THE OLD ESTIMATOR vs THE SAME ARMS, MEASURED THE SAME WAY")
    print("=" * 96)
    print("  old: average each arm's half-year NETS over ITS OWN cells - "
          "different denominators")
    print("  new: compare per-year TOTALS - same basis on both sides\n")
    print("  %-6s %10s %10s %8s %9s %9s %9s %s"
          % ("year", "off cells", "all cells", "old ea", "old eb", "old>", "new>",
             "new diff"))
    old_better = new_better = 0
    yrs = sorted(ally)
    for y in yrs:
        hs = [c for c in offh if c.startswith(y)]
        hs2 = [c for c in allh if c.startswith(y)]
        ea = sum(sum(offh[c]) for c in hs) / len(hs) if hs else 0.0
        eb = sum(sum(allh[c]) for c in hs2) / len(hs2) if hs2 else 0.0
        o = "yes" if eb > ea else "no"
        ta, tb = offy.get(y, 0.0), ally.get(y, 0.0)
        n = "yes" if tb > ta else "no"
        old_better += eb > ea
        new_better += tb > ta
        mark = "   <-- denominators differ" if len(hs) != len(hs2) else ""
        print("  %-6s %10d %10d %8.1f %9.1f %9s %9s %+9.1f%s"
              % (y, len(hs), len(hs2), ea, eb, o, n, tb - ta, mark))

    print()
    print("  old estimator: better in %d of %d years" % (old_better, len(yrs)))
    print("  per-year totals: better in %d of %d years" % (new_better, len(yrs)))
    print()
    if old_better != new_better:
        print("  The two disagree because the old average is taken over a different")
        print("  number of half-year cells for each arm - the count in columns 2 and 3")
        print("  above - so it compares averages of different sets. The per-year total")
        print("  has one basis for both arms and is the comparison that means")
        print("  'which arm earned more in that year'.")
    else:
        print("  The estimators agree; any disagreement with the 2026-10-10 grid")
        print("  comes from something other than this.")
    return 0


if __name__ == "__main__":
    sys.exit(main())