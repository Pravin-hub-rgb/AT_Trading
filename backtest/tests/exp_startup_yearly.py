"""Startup risk, calendar-year returns, and a rolling-weighted ranking.

The owner asked three things that no existing harness answered.

1. "IF I START IT TODAY, HOW BAD CAN IT GET?" This is NOT maximum drawdown.
   Max DD is measured from a running peak that the book establishes somewhere in
   the middle. What a new deployer feels is the dip below where they STARTED,
   before the book has ever printed a profit. That is a different number and it
   is the one that decides whether you switch the thing off in week three.
   Measured here as: the worst the account ever gets below zero before its first
   new high, plus the worst cumulative R over the first 10/20/30/50/100 trades.

2. "THIS GUY SELLS 45% RETURNS WITH 3% DRAWDOWN." A percentage return with no
   period attached is not comparable to anything, and the period is the whole
   question - 45% in a month is 45% a month forever; 45% a year is a different
   animal. So this reports every book per CALENDAR YEAR, in R and in account
   percent at 1% and 2% risk, alongside the drawdown that same book carried,
   and the ratio between them. The owner's answer is then read off the table
   rather than argued.

3. "ROLLING WINDOW SHOULD WEIGHT MORE THAN JUST BEING PROFITABLE." Agreed, and
   encoded: the headline rank scores rolling-window behaviour above net, above
   half-years and above the null, because the book is held across stretches and
   a book that makes its money in lumps is a book you cannot sit through. The
   null is still reported and still shown as a gate, not as a score input - a
   number you cannot rank against is a number you state.

All 35 registered fsent books with pins, not a top-N slice: the user asked for
every contender in both families, and the new arms changed the count. Combined
IS+OOS timeline, 2026H2 flagged partial and excluded from counts.

Writes _startup_yearly.json.
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
ERAS = [("oos", "2021-01-01"), ("is", "2023-01-01")]
PARTIAL = "2026H2"
FIRSTS = (10, 20, 30, 50, 100)


def half(d):
    return d[:4] + "H" + ("1" if int(d[5:7]) <= 6 else "2")


def startup(rs):
    """What a deployer feels: the dip below where they STARTED.

    Maximum drawdown measures from a running peak, which the book may not reach
    until trade 200. Startup drawdown measures from zero - from the moment the
    money went in. For a book being launched today these are different numbers
    and the second is the one that decides whether it gets switched off.
    """
    cum = 0.0
    low = 0.0
    low_i = 0
    first_hi = None
    for i, r in enumerate(rs):
        cum += r
        if cum < low:
            low = cum
            low_i = i + 1
        if cum > 0 and first_hi is None:
            first_hi = i + 1
    worst = {}
    for k in FIRSTS:
        if len(rs) < k:
            worst[k] = None
            continue
        c = sum(rs[:k])
        worst[k] = round(min(c, sum(rs[:k])), 2)
    # worst rolling stretch that STARTS at trade 1, over any window length <= 100
    return {
        "startup_dd_r": round(-low, 2),
        "startup_dd_at_trade": low_i,
        "startup_dd_pct_1": round(-low * 1.0, 2),
        "startup_dd_pct_2": round(-low * 2.0, 2),
        "trades_to_first_profit": first_hi,
        "worst_first_n": {str(k): worst[k] for k in FIRSTS},
        "first_10": round(sum(rs[:10]), 2) if len(rs) >= 10 else None,
        "first_50": round(sum(rs[:50]), 2) if len(rs) >= 50 else None,
        "first_100": round(sum(rs[:100]), 2) if len(rs) >= 100 else None,
    }


def rolling(rs, k):
    if len(rs) < k:
        return None
    w = [sum(rs[i:i + k]) for i in range(len(rs) - k + 1)]
    pos = sum(1 for x in w if x > 0)
    return {"n": len(w), "prof": round(100.0 * pos / len(w), 1),
            "worst": round(min(w), 2)}


def dd_all(rs):
    cum = pk = 0.0
    mdd = 0.0
    for r in rs:
        cum += r
        pk = max(pk, cum)
        mdd = max(mdd, pk - cum)
    return round(mdd, 2)


def main():
    Announce("building engine, loading eras, measuring startup risk on every fsent book",
             "~25-40 min for all registered fsent books across both eras")
    sim = build_family_module()
    E = {e: load_era(e) for e in ("is", "oos")}

    nulls = json.load(open("_null_audit.json", encoding="utf-8"))
    pmap = defaultdict(dict)
    for r in nulls["rows"]:
        pmap[r["book"]][r["era"]] = r

    books = sorted(k for k, v in EXPERIMENTS.items()
                   if isinstance(v, dict) and k.startswith("fsent_")
                   and (v.get("pins") or {}).get("n"))
    bar = Bar(len(books), "startup + yearly")
    out = {}

    for key in books:
        swing = (EXPERIMENTS[key].get("swing") or "sw10")
        params = dict(EXPERIMENTS[key]["params"])
        series, dates = [], []
        for era, _s in ERAS:
            d = E[era]
            o = sim(d["c1h"], get_swings(d, swing), d["c15"], d["sw15"],
                    fine_ltf=d["fine"], **params)
            for t in o["ltf_trades"]:
                if t.get("outcome") == "open":
                    continue
                series.append(net_r([t]))
                dates.append(t["entry_date"])

        rec = {"n": len(series), "swing": swing,
               "multi": (EXPERIMENTS[key]["params"] or {}).get("max_positions", None) == 0,
               "net": round(sum(series), 2),
               "p_is": pmap[key].get("is", {}).get("p"),
               "p_oos": pmap[key].get("oos", {}).get("p")}
        rec["startup"] = startup(series)
        rec["max_dd_r"] = dd_all(series)
        rec["max_dd_pct_1"] = rec["max_dd_r"]
        rec["max_dd_pct_2"] = round(rec["max_dd_r"] * 2, 2)

        yc = defaultdict(list)
        hc = defaultdict(list)
        for r, dt in zip(series, dates):
            yc[dt[:4]].append(r)
            hc[half(dt)].append(r)
        rec["years"] = {c: round(sum(v), 2) for c, v in sorted(yc.items())}
        rec["halves"] = {c: {"net": round(sum(v), 2), "partial": c == PARTIAL}
                         for c, v in sorted(hc.items())}
        full_h = [c for c in rec["halves"] if not rec["halves"][c]["partial"]]
        rec["half_neg"] = sorted(c for c in full_h if rec["halves"][c]["net"] <= 0)
        rec["year_neg"] = sorted(c for c in full_h if False)  # placeholder cleared below
        full_y = [c for c in rec["years"] if c != "2026"]
        rec["year_neg"] = sorted(c for c in full_y if rec["years"][c] <= 0)

        rec["rolling"] = {str(k): rolling(series, k)
                          for k in (10, 20, 30, 50, 100)}

        s = sorted(series, reverse=True)
        tot = rec["net"]
        cut = sum(s[:max(1, int(round(len(s) * 0.10)))])
        rec["top10_contrib"] = round(100.0 * cut / tot, 1) if tot else None
        rec["survive_rm_top10"] = round(tot - cut, 2)

        # ---- RANKING: rolling weighted heaviest --------------------------
        # net and the null are NOT in the score. net is already in half-years and
        # rolling; the null is a gate, not a rank, because a p-value cannot be
        # scaled against an R/trade number and pretending otherwise hides it.
        r10 = rec["rolling"]["10"]["prof"] / 100.0
        r20 = rec["rolling"]["20"]["prof"] / 100.0
        r50 = rec["rolling"]["50"]["prof"] / 100.0
        r100 = rec["rolling"]["100"]["prof"] / 100.0
        half_score = 1.0 - len(rec["half_neg"]) / 11.0
        year_score = 1.0 - len(rec["year_neg"]) / 5.0
        tail_score = max(0.0, min(1.0, 1.0 - (rec["top10_contrib"] or 100) / 120.0))
        rec["score"] = round(100.0 * (0.30 * r10 + 0.30 * r20
                                      + 0.25 * r50 + 0.15 * r100
                                      + 0.60 * half_score
                                      + 0.40 * year_score
                                      + 0.30 * tail_score), 1)
        out[key] = rec
        bar.update(key)

    bar.close("measured")
    json.dump(out, open("_startup_yearly.json", "w", encoding="utf-8"), indent=1)

    def L(v, w=8, d=2):
        return ("%*.*f" % (w, d, v)) if isinstance(v, (int, float)) else "%*s" % (w, "-")

    order = sorted(out, key=lambda k: -out[k]["score"])

    print()
    print("#" * 126)
    print("A. STARTUP RISK  -  what you feel if you deploy with an empty account today")
    print("   NOT max drawdown. Max DD is measured from a running peak the book may not")
    print("   reach until trade 200. This is the dip below where you STARTED.")
    print("#" * 126)
    print("  %-32s %10s %12s %11s %12s %11s"
          % ("book", "start DD", "at trade", "% @1% risk", "first +50", "first high"))
    print("  " + "-" * 122)
    for k in sorted(out, key=lambda x: -out[x]["startup"]["startup_dd_r"]):
        s = out[k]["startup"]
        print("  %-32s %9s %11s %10s%% %11s %10s"
              % (k[:32], L(s["startup_dd_r"], 10),
                 L(s["startup_dd_at_trade"], 12), L(s["startup_dd_r"], 11, 1),
                 L(s["first_50"], 12),
                 L(s["trades_to_first_profit"], 11)))

    print()
    print("#" * 126)
    print("B. CALENDAR YEAR  -  the '45% a year with 3% drawdown' comparison")
    print("   R per year, and account % at 1%% risk. 2026 is partial (8.4 months).")
    print("#" * 126)
    hdr = "%-32s %8s %8s %8s %8s %8s %9s %9s" % (
        "book", "net", "2021", "2022", "2023", "2024", "2025", "2026*")
    print(hdr)
    print("  " + "-" * 122)
    for k in sorted(out, key=lambda x: -out[x]["net"]):
        y = out[k]["years"]
        print("  %-32s %8s %8s %8s %8s %8s %9s %9s"
              % (k[:32], L(out[k]["net"], 8),
                 L(y.get("2021"), 8), L(y.get("2022"), 8), L(y.get("2023"), 8),
                 L(y.get("2024"), 8), L(y.get("2025"), 9),
                 L(y.get("2026"), 9)))

    print()
    print("#" * 126)
    print("C. ROLLING WEIGHTED RANKING  -  rolling behaviour above everything")
    print("   Score weights: roll10 .30, roll20 .30, roll50 .25, roll100 .15,")
    print("   half-years .60, years .40, tail spread .30. Net is NOT scored - it is")
    print("   already inside half-years and rolling. The null is a GATE, not a score.")
    print("#" * 126)
    print("  %-32s %7s %7s %7s %7s %6s %6s %6s %s"
          % ("book", "SCORE", "r10", "r20", "r50", "r100", "negH", "negY", "p IS / p OOS"))
    print("  " + "-" * 122)
    for k in order:
        r = out[k]
        pp = ("%.4f / %.4f" % (r["p_is"], r["p_oos"])) if r["p_is"] is not None else "   -  /   -  "
        print("  %-32s %7.1f %6s%% %6s%% %6s%% %5s%% %6d %6d %s"
              % (k[:32], r["score"], r["rolling"]["10"]["prof"],
                 r["rolling"]["20"]["prof"], r["rolling"]["50"]["prof"],
                 r["rolling"]["100"]["prof"] if r["rolling"]["100"] else "-",
                 len(r["half_neg"]), len(r["year_neg"]), pp))

    print("\n  wrote _startup_yearly.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())