"""Run the finding-optimal-book framework on the new arms, beside the old ones.

The framework lives in docs/learn/finding optimal book.md - thirteen buckets and six
tiers, written for this exact project. It has never been run on the HTF-FS arms,
because they did not exist when it was written. Applying it only to the new books
would also be useless: the owner's question is not "are the new books good" but
"are they BETTER THAN WHAT WE ALREADY HAVE, on the same yardstick".

So every book in the comparison is put through the same measurement, in one run,
and the answer is a column next to the book it has to beat.

Buckets covered, and why these:
  1  profitability        net, expectancy, PF, n
  2  equity quality       max DD, DD as % of net, maxUW, recovery, worst rolling
                          20/50/100, winner gaps, PROFITABLE HALF-YEARS
  3  tail dependence      remove top 1/3/5/10 and top 0.5/1/2/5/10%, plus what
                          the top X% contributes rather than only what survives
                          removing it - the doc asks for both
  5  OOS                  expectancy / PF / WR retention, DD expansion, net
                          retention, sign consistency
  6  complexity           how many parameters differ from the shipping base

Not covered, and it matters: tier 4 (parameter plateau, cost sensitivity,
cross-asset) is a separate harness per axis and is NOT faked here. Tier 0
(validity) is PASS/FAIL and is enforced by exp_fastcheck and the causality audit
instead - a book that failed those is not in this table at all.

Writes _optimalbook_study.json.
"""
import json
import sys
from collections import defaultdict

sys.path.insert(0, ".")

from progress import Announce, Bar                  # noqa: E402
from exp_tf_family import build_family_module      # noqa: E402
from run_experiment import net_r, get_swings        # noqa: E402
from exp_signal_metrics import load_era             # noqa: E402
from experiment_registry import EXPERIMENTS         # noqa: E402

SHIPPING = "fsent_champ_long"

BOOKS = [
    (SHIPPING, "sw10", "OLD - shipping"),
    ("fsent_champ_long_mcloff", "sw10", "OLD - best evidence"),
    ("fsent_champ_long_htf15", "htf15", "OLD"),
    ("fsent_champ_long_htfesmcl4", "sw10", "OLD - htf_fs=all"),
    ("fsent_sig_multi", "sw10", "OLD - best shape"),
    ("fsent_sig_full", "sw10", "OLD"),
    ("fsent_champ_long_htffs", "sw10", "NEW - flip FS"),
    ("fsent_champ_long_htf15_htffs", "htf15", "NEW - flip FS htf15"),
    ("fsent_sig_multi_htffs", "sw10", "NEW - flip FS sig_multi"),
]

CAPS = [10, 15, 20]


def half(d):
    return d[:4] + "H" + ("1" if int(d[5:7]) <= 6 else "2")


def t1(rs):
    n = len(rs)
    w = [r for r in rs if r > 0]
    lo = [r for r in rs if r <= 0]
    gw, gl = sum(w), -sum(lo)
    return {"n": n, "net": round(sum(rs), 2),
            "expect": round(sum(rs) / n, 4),
            "pf": round(gw / gl, 3) if gl > 0 else 99.0,
            "wr": round(100.0 * len(w) / n, 1),
            "avg_win": round(gw / len(w), 3) if w else 0.0,
            "avg_loss": round(-gl / len(lo), 3) if lo else 0.0}


def t2(rs, cells):
    cum = pk = mdd = 0.0
    und = cur = longest = 0
    ulc = []
    peak_at = 0
    worst_at = 0
    for i, r in enumerate(rs):
        cum += r
        if cum > pk:
            pk = cum
            peak_at = i
        dd = pk - cum
        ulc.append(dd)
        if dd > mdd:
            mdd, worst_at = dd, i
        if cum < pk:
            und += 1
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 0
    # time to recover from the deepest point
    rec = None
    tgt = pk
    run = 0.0
    for i in range(worst_at, len(rs)):
        run += rs[i]
        if run >= mdd:
            rec = i - worst_at
            break
    n = len(rs)
    worst_roll = {}
    for k in (20, 50, 100):
        worst_roll[k] = round(min(sum(rs[i:i + k]) for i in range(n - k + 1)), 2) \
            if n >= k else None
    # gaps between meaningful winners
    gaps = {}
    for thr in (3, 5, 10, 20):
        idx = [i for i, r in enumerate(rs) if r >= thr]
        if len(idx) < 2:
            gaps[thr] = None
            continue
        g = [idx[i + 1] - idx[i] for i in range(len(idx) - 1)]
        g.sort()
        gaps[thr] = {"n": len(idx), "median": g[len(g) // 2],
                     "p90": g[int(len(g) * 0.9)], "max": g[-1]}
    pos = sorted(c for c, v in cells.items() if sum(v) > 0)
    neg = sorted(c for c, v in cells.items() if sum(v) <= 0)
    return {"max_dd": round(mdd, 2),
            "dd_pct_net": round(100.0 * mdd / sum(rs), 1) if sum(rs) > 0 else 0.0,
            "net_per_dd": round(sum(rs) / mdd, 1) if mdd > 0 else 99.0,
            "maxUW": longest, "uw_pct": round(100.0 * und / n, 1),
            "ulcer": round(sum(ulc) / n, 2),
            "recovery_trades": rec,
            "worst_roll": worst_roll, "gaps": gaps,
            "pos_halves": len(pos), "neg_halves": len(neg),
            "neg_list": neg, "pos_list": pos}


def t3(rs):
    n = len(rs)
    s = sorted(rs, reverse=True)
    total = sum(rs)
    rem_abs = {}
    for k in (1, 3, 5, 10):
        rem_abs["top%d" % k] = round(total - sum(s[:k]), 2)
    rem_pct, contrib = {}, {}
    for f in (0.005, 0.01, 0.02, 0.05, 0.10, 0.20):
        k = max(1, int(round(n * f)))
        cut = sum(s[:k])
        lbl = "top%s%%" % (round(f * 100, 1))
        rem_pct[lbl] = round(total - cut, 2)
        contrib[lbl] = round(100.0 * cut / total, 1) if total else 0.0
    caps = {}
    for c in CAPS:
        caps["cap%d" % c] = round(sum(min(r, c) for r in rs), 2)
    return {"remove_abs": rem_abs, "remove_pct": rem_pct,
            "contrib_pct": contrib, "caps": caps, "max_win": round(s[0], 2)}


def main():
    Announce("building engine, loading eras, running the framework on nine books",
             "~10-15 min for nine books across both eras")
    sim = build_family_module()
    E = {e: load_era(e) for e in ("is", "oos")}
    base_params = EXPERIMENTS[SHIPPING]["params"]
    bar = Bar(len(BOOKS), "optimal-book framework")
    out = {}

    for key, swing, note in BOOKS:
        params = dict(EXPERIMENTS[key]["params"])
        rec = {"note": note, "swing": swing,
               "params_differing": sorted(
                   k for k in set(base_params) | set(params)
                   if base_params.get(k) != params.get(k))}
        for era in ("is", "oos"):
            d = E[era]
            o = sim(d["c1h"], get_swings(d, swing), d["c15"], d["sw15"],
                    fine_ltf=d["fine"], **params)
            allt = o["ltf_trades"]
            closed = [t for t in allt if t.get("outcome") != "open"]
            rs = [net_r([t]) for t in closed]
            cells = defaultdict(list)
            for t, r in zip(closed, rs):
                cells[half(t["entry_date"])].append(r)
            rec[era] = {"t1": t1(rs), "t2": t2(rs, cells), "t3": t3(rs),
                        "cells": {c: round(sum(v), 2) for c, v in sorted(cells.items())}}
        out[key] = rec
        bar.update(key)

    bar.close("measured")

    def L(v, w=8, d=2):
        return ("%*.*f" % (w, d, v)) if isinstance(v, (int, float)) else "%*s" % (w, "-")

    for era, title in (("is", "IN SAMPLE"),
                       ("oos", "OUT OF SAMPLE (reused 2021-22, NOT a holdout)")):
        print()
        print("#" * 128)
        print("TIER 1 - PROFITABILITY      " + title)
        print("#" * 128)
        print("  %-28s %6s %9s %9s %7s %7s %8s %8s"
              % ("book", "n", "net", "expect", "PF", "wr%", "avgW", "avgL"))
        for key, _s, note in BOOKS:
            a = out[key][era]["t1"]
            print("  %-28s %6d %9s %9s %7s %7s %8s %8s   %s"
                  % (key[:28], a["n"], L(a["net"], 9), L(a["expect"], 9, 3),
                     L(a["pf"], 7), L(a["wr"], 7, 1), L(a["avg_win"], 8, 2),
                     L(a["avg_loss"], 8, 2), note))

        print()
        print("#" * 128)
        print("TIER 2 - EQUITY QUALITY      " + title)
        print("#" * 128)
        print("  %-28s %7s %7s %8s %7s %7s %7s %9s %9s  %s"
              % ("book", "maxDD", "DD/Net", "net/DD", "maxUW", "uw%", "ulcer",
                 "roll20", "roll50", "HALVES"))
        for key, _s, note in BOOKS:
            a = out[key][era]["t2"]
            print("  %-28s %7s %7s %8s %7d %7s %7s %9s %9s  %d+ / %d-"
                  % (key[:28], L(a["max_dd"], 7), L(a["dd_pct_net"], 7, 1),
                     L(a["net_per_dd"], 8, 1), a["maxUW"], L(a["uw_pct"], 7, 1),
                     L(a["ulcer"], 7), L(a["worst_roll"][20], 9),
                     L(a["worst_roll"][50], 9), a["pos_halves"], a["neg_halves"]))

        print()
        print("     HALF-YEAR CELLS (each one positive or negative)")
        for key, _s, note in BOOKS:
            c = out[key][era]["cells"]
            bad = out[key][era]["t2"]["neg_list"]
            cells = " ".join("%s%+.0f" % (k, v) for k, v in c.items())
            flag = ("   <-- NEGATIVE: " + ", ".join(bad)) if bad else "   all positive"
            print("  %-28s %s%s" % (key[:28], cells[:78], flag))

        print()
        print("#" * 128)
        print("TIER 3 - TAIL DEPENDENCE      " + title)
        print("#" * 128)
        print("  %-28s %7s %7s %7s %7s | %8s %8s %8s | %8s %8s"
              % ("book", "rm top1", "rm top3", "rm top5", "rm top10",
                 "rm top2%", "rm top5%", "rm top10%",
                 "top5% contr", "top10% contr"))
        for key, _s, note in BOOKS:
            a = out[key][era]["t3"]
            print("  %-28s %7s %7s %7s %7s | %8s %8s %8s | %10s%% %10s%%"
                  % (key[:28], L(a["remove_abs"]["top1"], 7),
                     L(a["remove_abs"]["top3"], 7), L(a["remove_abs"]["top5"], 7),
                     L(a["remove_abs"]["top10"], 7),
                     L(a["remove_pct"]["top2.0%"], 8), L(a["remove_pct"]["top5.0%"], 8),
                     L(a["remove_pct"]["top10.0%"], 8),
                     L(a["contrib_pct"]["top5.0%"], 10, 1),
                     L(a["contrib_pct"]["top10.0%"], 10, 1)))

    print()
    print("#" * 128)
    print("TIER 5 - OOS RETENTION")
    print("#" * 128)
    print("  %-28s %9s %9s %9s %9s %9s %8s"
          % ("book", "expect", "PF", "WR", "net", "DD exp", "sign"))
    print("  " + "-" * 122)
    ret = {}
    for key, _s, note in BOOKS:
        a, b = out[key]["is"]["t1"], out[key]["oos"]["t1"]
        e = (b["expect"] / a["expect"]) if a["expect"] else 0
        pf = b["pf"] / a["pf"] if a["pf"] else 0
        wr = b["wr"] / a["wr"] if a["wr"] else 0
        nr = b["net"] / a["net"] if a["net"] else 0
        de = (out[key]["oos"]["t2"]["max_dd"] / out[key]["is"]["t2"]["max_dd"]
              if out[key]["is"]["t2"]["max_dd"] else 0)
        sign = "both +" if a["net"] > 0 and b["net"] > 0 else "SIGN FLIP"
        ret[key] = {"expectancy_retention": round(100 * e, 1),
                    "pf_retention": round(100 * pf, 1),
                    "wr_retention": round(100 * wr, 1),
                    "net_retention": round(100 * nr, 1),
                    "dd_expansion": round(de, 2), "sign": sign}
        print("  %-28s %8.0f%% %8.0f%% %8.0f%% %8.0f%% %8.2fx %8s"
              % (key[:28], 100 * e, 100 * pf, 100 * wr, 100 * nr, de, sign))

    print()
    print("#" * 128)
    print("TIER 6 - COMPLEXITY (parameters differing from the shipping base)")
    print("#" * 128)
    for key, _s, note in BOOKS:
        d = out[key]["params_differing"]
        print("  %-28s %2d   %s   %s" % (key[:28], len(d), d if d else "(none)", note))

    out["_retention"] = ret
    json.dump(out, open("_optimalbook_study.json", "w", encoding="utf-8"), indent=1)
    print("\n  wrote _optimalbook_study.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())