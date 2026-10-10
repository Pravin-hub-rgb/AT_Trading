"""The HTF-side FS entry, on BOTH regime classifiers, and selectively.

WHAT WAS ALREADY MEASURED
-------------------------
HTF_FS_ENTRY_REJECTED.md, 2026-10-09. On three books, all of them mode="atr_high":
`exp_htf_fs_entry="all"` (every HTF regime bucket opens on the FS print instead of
the break) was tested and rejected. flip was "IDENTICAL to off" - which turned out
to be true by construction rather than by finding: the table tested `_hfs_on and
_hfs == "all"` together, so "flip" set the flag and then fell through to the
shipped value for all three buckets. The mode named for the bucket it moves moved
nothing.

TWO GAPS THIS CLOSES
--------------------
1. "dec" - move ONLY the decisive bucket onto FS and leave flip and b2 on their
   breaks. This is the exact analogue of what the LTF side already does with
   exp_fs_entry_side (one side on FS, the other on break), and it is the cell the
   owner kept asking about. "all" collapsed the three buckets into one fs_both
   set and the book stopped distinguishing regimes at all; "dec" keeps flip and b2
   intact, so the regime distinction survives. If "all" failed by being
   degenerate rather than by being FS-entered, "dec" separates those two reasons.

2. mode="chop". Every one of the 31 registered fsent books is mode="atr_high".
   There is no chop-mode book in the registry at all, so the 2026-10-09 test only
   ever spoke to the ATR classifier. The regime classifier and the HTF entry
   trigger interact - the whole job of the classifier is to decide which bucket a
   bar belongs to, and moving a bucket's entry to the FS changes what the bucket
   contains - so an ATR-only result does not generalise to chop.

`exp_htf_fs_entry="flip"` is re-run too, now that it does what it says. That can
only add cells: the default "" path is untouched and no pinned book uses "flip".

Writes _htf_fs_grid.json.
"""
import json
import statistics
import sys
from collections import defaultdict

sys.path.insert(0, ".")

from progress import Announce, Bar                  # noqa: E402
from exp_tf_family import build_family_module      # noqa: E402
from run_experiment import net_r, get_swings        # noqa: E402
from exp_signal_metrics import load_era             # noqa: E402
from experiment_registry import EXPERIMENTS         # noqa: E402

MODES = [("off", ""), ("dec", "dec"), ("flip", "flip"), ("b2", "b2"), ("all", "all")]


def half(d):
    return d[:4] + "H" + ("1" if int(d[5:7]) <= 6 else "2")


def year(d):
    return d[:4]


def dd_of(rs):
    c = pk = m = 0.0
    for x in rs:
        c += x
        pk = max(pk, c)
        m = max(m, pk - c)
    return m


def period_control(off_cells, arm_cells):
    """Half-year fixed effect: subtract each year's own mean from both arms.

    b is what is left of the arm's advantage once every calendar year's average
    is removed. If b is not distinguishable from 0 the gain is a period artifact -
    the same test that rejected htf_fs="all" and flip_quality.
    """
    years = sorted(set(off_cells) | set(arm_cells))
    ra, rb = [], []
    for y in years:
        a = off_cells.get(y, 0.0)
        c = arm_cells.get(y, 0.0)
        m = (a + c) / 2.0
        ra.append(a - m)
        rb.append(c - m)
    if len(ra) < 2:
        return None, None, len(ra), len(rb)
    b = sum(rb) / len(rb) - sum(ra) / len(ra)
    va = statistics.variance(ra) / len(ra)
    vb = statistics.variance(rb) / len(rb)
    se = (va + vb) ** 0.5
    return b, (b / se if se > 0 else 0.0), len(ra), len(rb)


def run(sim, era, d, swing, params):
    o = sim(d["c1h"], get_swings(d, swing), d["c15"], d["sw15"],
            fine_ltf=d["fine"], **params)
    return [t for t in o["ltf_trades"] if t.get("outcome") != "open"]


def main():
    Announce("building the engine and loading both eras", "~1 min")
    sim = build_family_module()
    E = {e: load_era(e) for e in ("is", "oos")}

    # The chop arm has no registry entry - it is built here from the shipping
    # base so the comparison is one field apart and not two.
    chop_params = dict(EXPERIMENTS["fsent_champ_long"]["params"])
    chop_params["mode"] = "chop"
    chop_params.setdefault("chop_thresh", 58.0)
    chop_params.setdefault("atr_low_thresh", 0.35)
    chop_params.setdefault("atr_high_thresh", 0.65)

    BOOKS = [("champ_long", "fsent_champ_long", "sw10", False),
             ("htf15", "fsent_champ_long_htf15", "htf15", False),
             ("sig_multi", "fsent_sig_multi", "sw10", False),
             ("chop_sw10", None, "sw10", True)]

    total = len(BOOKS) * len(MODES)
    bar = Bar(total, "HTF-FS x regime grid")
    results = []

    for bk, key, swing, is_chop in BOOKS:
        base = chop_params if is_chop else dict(EXPERIMENTS[key]["params"])
        base = dict(base)
        cells = {}
        for lbl, val in MODES:
            p = dict(base)
            p["exp_htf_fs_entry"] = val
            per_h = defaultdict(list)
            per_y = defaultdict(list)
            rs_all = []
            n = net = 0
            enet, dd = {}, {}
            for era in ("is", "oos"):
                tr = run(sim, era, E[era], swing, p)
                rs = [net_r([t]) for t in tr]
                n += len(rs)
                net += sum(rs)
                enet[era] = sum(rs)
                dd[era] = dd_of(rs)
                rs_all += rs
                for t, r in zip(tr, rs):
                    per_h[half(t["entry_date"])].append(r)
                    per_y[year(t["entry_date"])].append(r)
            neg = sorted(c for c, v in per_h.items() if sum(v) < 0)
            cells[lbl] = {
                "n": n, "net": round(net, 2), "dd_is": round(dd["is"], 2),
                "dd_oos": round(dd["oos"], 2), "net_is": round(enet["is"], 2),
                "net_oos": round(enet["oos"], 2), "neg_cells": neg,
                "n_neg": len(neg), "per_h": {c: round(sum(v), 2)
                                             for c, v in per_h.items()},
                "per_y": {c: round(sum(v), 2) for c, v in per_y.items()},
            }
            bar.update("%s / %s" % (bk, lbl))

        off = cells["off"]
        for lbl, _ in MODES:
            if lbl == "off":
                continue
            a = cells[lbl]
            # BOTH fixed effects. The 2026-10-09 rejection used a HALF-year fixed
            # effect; a year-level one is weaker and would flatter every arm, so
            # reporting only the year number would quietly reverse the earlier
            # verdict. Both are reported and neither is presented alone.
            by, ty, _, _ = period_control(off["per_y"], a["per_y"])
            bh, th, _, _ = period_control(off["per_h"], a["per_h"])
            yrs = sorted(set(off["per_y"]) | set(a["per_y"]))
            better = sum(1 for y in yrs if a["per_y"].get(y, 0) >
                         off["per_y"].get(y, 0))
            results.append({
                "book": bk, "mode": lbl, "regime": "chop" if is_chop else "atr_high",
                "swing": swing,
                "n": a["n"], "d_n": a["n"] - off["n"],
                "net": a["net"], "d_net": round(a["net"] - off["net"], 2),
                "net_is": a["net_is"], "net_oos": a["net_oos"],
                "dd_is": a["dd_is"], "dd_oos": a["dd_oos"],
                "d_dd_is": round(a["dd_is"] - off["dd_is"], 2),
                "n_neg": a["n_neg"], "new_neg": sorted(set(a["neg_cells"]) -
                                                      set(off["neg_cells"])),
                "years_better": better, "years_total": len(yrs),
                "year_b": None if by is None else round(by, 3),
                "year_t": None if ty is None else round(ty, 2),
                "half_b": None if bh is None else round(bh, 3),
                "half_t": None if th is None else round(th, 2),
            })
        results.append({
            "book": bk, "mode": "off", "regime": "chop" if is_chop else "atr_high",
            "swing": swing, "baseline": True,
            "n": off["n"], "net": off["net"], "net_is": off["net_is"],
            "net_oos": off["net_oos"], "dd_is": off["dd_is"], "dd_oos": off["dd_oos"],
            "n_neg": off["n_neg"], "neg_cells": off["neg_cells"],
        })

    print()
    print("=" * 118)
    print("BASELINES - regime classifier x swing, HTF-FS off")
    print("=" * 118)
    print("  %-12s %-10s %6s %9s %9s %7s %7s %6s"
          % ("book", "regime", "n", "net", "d_net", "ddIS", "ddOOS", "neg"))
    for r in results:
        if r.get("baseline"):
            print("  %-12s %-10s %6d %+9.1f %9s %7.2f %7.2f %6d"
                  % (r["book"], r["regime"], r["n"], r["net"], "-",
                     r["dd_is"], r["dd_oos"], r["n_neg"]))

    print()
    print("=" * 118)
    print("HTF-FS ARMS")
    print("=" * 118)
    print("  %-12s %-5s %6s %6s %9s %7s %6s %5s %7s %7s %7s"
          % ("book", "mode", "n", "d_n", "d_net", "ddIS", "dDD", "neg",
             "yr_win", "t_year", "t_half"))
    for r in results:
        if r.get("baseline"):
            continue
        print("  %-12s %-5s %6d %+6d %+9.1f %7.2f %+6.2f %6d %3d/%-3d %+8s %+8s"
              % (r["book"], r["mode"], r["n"], r["d_n"], r["d_net"], r["dd_is"],
                 r["d_dd_is"], r["n_neg"], r["years_better"], r["years_total"],
                 "-" if r["year_t"] is None else "%.2f" % r["year_t"],
                 "-" if r["half_t"] is None else "%.2f" % r["half_t"]))

    json.dump(results, open("_htf_fs_grid.json", "w", encoding="utf-8"), indent=1)
    print("\n  wrote _htf_fs_grid.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())