"""The full study, on one continuous timeline, with drawdown as a percentage.

WHAT CHANGED AND WHY
--------------------
Three things were wrong with the previous table and all three are the owner's
objection rather than a stylistic preference.

1. DRAWDOWN WAS IN R, AND A CEILING IN R IS NOT A CEILING IN ANYTHING ELSE.
   "29R" was set as an absolute number and then compared across books that make
   295R and 926R. A drawdown is only meaningful against the equity it fell from.
   Industry standard is drawdown% = (equity - peak) / peak. Reported here three
   ways because they answer different questions:
     - account%   : at risk% per trade. The account loses dd_R x risk% of itself.
     - of_peak%   : the fall measured against the high-water mark at that moment.
                     This is the one that makes 29R-on-a-926R-book look different
                     from 29R-on-a-295R-book, which is the entire point.
     - recovery%  : what it costs to get back, which is asymmetric - a 20% fall
                     needs a 25% gain, a 30% fall needs 42.9%.

2. IS AND OOS WERE SPLIT. The owner is right that half the record was being
   hidden behind a split. The 2021-2022 era and the 2023-2026 era are run and the
   R series is CONCATENATED in chronological order into one continuous curve, so
   half-year and year cells run across the boundary as they would in live
   trading. The 2021/2022 boundary is marked, not removed.

3. 2026H2 IS NOT A HALF-YEAR. The data ends 2026-09-13, so 2026H2 holds roughly
   2.5 months against 6 for every other cell. It is reported, labelled PARTIAL,
   and excluded from every pass/fail count. Calling a 2.5-month cell a half-year
   is how sig_multi_htffs came to look like it had a failing period.

Also added, because the owner asked: rolling 10/20/50-trade windows, measured as
how many of them are profitable. If a book only makes money over the full sample
but loses inside 20-trade stretches, that is a book you cannot actually hold for
a financial year. And top-10% winner spread, reported as both contribution and
survival.

All 11 multi-position books plus the top 15 single-position books, ranked by net,
plus the shipping book always. Wrote _full_study.json.
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
DATA_END = "2026-09-13"
ERAS = [("oos", "2021-01-01", "2022-12-31"), ("is", "2023-01-01", "2026-09-13")]
RISKS = [0.01, 0.02]


def cell(d):
    return d[:4] + "H" + ("1" if int(d[5:7]) <= 6 else "2")


def year(d):
    return d[:4]


def dd_curve(rs, risk=0.01):
    """One walk giving R-drawdown, account% and peak-relative% together.

    `risk` is the share of the ACCOUNT risked per 1R, so risk=0.01 means 1R = 1%
    of the account and a drawdown of 55.48R is 55.48% of the account. That
    multiplication is the whole point: 29.62R is 29.62% on a book that risks 1%
    per trade, not 0.296%.

    Account equity is taken on FIXED notional (cumulated R), not compounded,
    which is the convention Rob Carver argues for and which is what makes the
    percentage comparable between a book that made 295R and one that made 926R.
    Peak-relative drawdown is the fall measured against the high-water mark at
    that moment - the number that separates a 29R dip on a 1200R book from a 29R
    dip on a 295R book.
    """
    cum = pk_r = 0.0
    pk_pct = 0.0
    mdd_r = mdd_acct = mdd_peak = 0.0
    r_at_peak_dd = 0.0
    n = 0
    for r in rs:
        n += 1
        cum += r
        if cum > pk_r:
            pk_r = cum
        d_r = pk_r - cum
        if d_r > mdd_r:
            mdd_r = d_r
        acct = cum * risk * 100.0            # equity, % of fixed notional
        if acct > pk_pct:
            pk_pct = acct
        a = d_r * risk * 100.0               # drawdown, % of fixed notional
        if a > mdd_acct:
            mdd_acct = a
        if pk_pct > 0:
            p = (pk_pct - acct) / pk_pct * 100.0
            if p > mdd_peak:
                mdd_peak = p
                r_at_peak_dd = pk_r
    return {"mdd_r": round(mdd_r, 2),
            "acct_1pct": round(mdd_acct, 2),
            "acct_2pct": round(mdd_r * 2.0, 2),
            "peak_pct_1pct": round(mdd_peak, 2),
            "peak_r_at_dd": round(r_at_peak_dd, 1),
            "peak_r": round(pk_r, 1),
            "trades_in_dd": n}


def recovery_needed(pct):
    """Asymmetric: a d% fall needs d/(1-d) to get back."""
    if pct >= 100:
        return None
    return round(pct / (100.0 - pct) * 100.0, 1)


def rolling(rs, k):
    if len(rs) < k:
        return None
    w = [sum(rs[i:i + k]) for i in range(len(rs) - k + 1)]
    pos = sum(1 for x in w if x > 0)
    return {"windows": len(w), "profitable": pos,
            "profitable_pct": round(100.0 * pos / len(w), 1),
            "worst": round(min(w), 2), "best": round(max(w), 2)}


def main():
    Announce("building engine, loading eras, running the full study on 26 books",
             "~20-30 min for 26 books across both eras")
    sim = build_family_module()
    E = {e: load_era(e) for e in ("is", "oos")}

    multi, serial = [], []
    for k, v in EXPERIMENTS.items():
        if not isinstance(v, dict) or not k.startswith("fsent_"):
            continue
        pins = v.get("pins") or {}
        if not pins.get("n"):
            continue
        row = (pins["net"], k, v.get("swing", "sw10"))
        (multi if (v.get("params") or {}).get("max_positions", None) == 0
         else serial).append(row)
    multi.sort(reverse=True)
    serial.sort(reverse=True)
    books = [r[1] for r in multi] + [r[1] for r in serial[:15]]
    swing_of = {r[1]: r[2] for r in multi + serial}
    if SHIPPING not in books:
        books.insert(0, SHIPPING)

    nulls = json.load(open("_null_audit.json", encoding="utf-8"))
    pmap = defaultdict(dict)
    for r in nulls["rows"]:
        pmap[r["book"]][r["era"]] = r

    bar = Bar(len(books), "full study")
    out = {}

    for key in books:
        swing = swing_of.get(key, "sw10")
        params = dict(EXPERIMENTS[key]["params"])
        series, dates, family = [], [], []
        for era, _s, _e in ERAS:
            d = E[era]
            o = sim(d["c1h"], get_swings(d, swing), d["c15"], d["sw15"],
                    fine_ltf=d["fine"], **params)
            for t in o["ltf_trades"]:
                if t.get("outcome") == "open":
                    continue
                series.append(net_r([t]))
                dates.append(t["entry_date"])
                family.append(era)
        rec = {"n": len(series), "swing": swing,
               "multi": (EXPERIMENTS[key]["params"] or {}).get("max_positions", None) == 0,
               "p_is": pmap[key].get("is", {}).get("p"),
               "p_oos": pmap[key].get("oos", {}).get("p")}

        # --- half-year and year cells on the COMBINED curve -------------------
        hc, yc = defaultdict(list), defaultdict(list)
        for r, dt in zip(series, dates):
            hc[cell(dt)].append(r)
            yc[year(dt)].append(r)
        rec["halves"] = {c: {"net": round(sum(v), 2), "n": len(v),
                             "partial": c == "2026H2"} for c, v in sorted(hc.items())}
        rec["years"] = {c: {"net": round(sum(v), 2), "n": len(v)}
                        for c, v in sorted(yc.items())}
        full_h = [c for c in rec["halves"] if not rec["halves"][c]["partial"]]
        rec["n_half_full"] = len(full_h)
        rec["half_neg"] = sorted(c for c in full_h if rec["halves"][c]["net"] <= 0)
        rec["half_neg_partial"] = sorted(c for c in rec["halves"]
                                         if rec["halves"][c]["partial"]
                                         and rec["halves"][c]["net"] <= 0)
        rec["year_neg"] = sorted(c for c, v in rec["years"].items() if v["net"] <= 0)
        yl = sorted(rec["years"])
        rec["year_full"] = [y for y in yl if y != "2026"]
        rec["year_neg_full"] = sorted(y for y in rec["year_full"]
                                      if rec["years"][y]["net"] <= 0)

        # --- drawdown, all three ways ---------------------------------------
        rec["dd"] = {("%g%%risk" % (r * 100)): dd_curve(series, r) for r in RISKS}
        d1 = rec["dd"]["1%risk"]
        d1["recovery_pct_1pct"] = recovery_needed(d1["acct_1pct"])
        d1["recovery_pct_2pct"] = recovery_needed(d1["acct_2pct"])
        rec["net"] = round(sum(series), 2)
        d1["dd_pct_of_net"] = round(100.0 * d1["mdd_r"] / rec["net"], 1) \
            if rec["net"] > 0 else 0.0

        # --- rolling windows --------------------------------------------------
        rec["rolling"] = {str(k): rolling(series, k) for k in (10, 20, 50)}

        # --- tail spread ------------------------------------------------------
        s = sorted(series, reverse=True)
        tot = rec["net"]
        cut10 = sum(s[:max(1, int(round(len(s) * 0.10)))])
        rec["tail"] = {
            "top10_contrib_pct": round(100.0 * cut10 / tot, 1) if tot else 0.0,
            "survive_rm_top10": round(tot - cut10, 2),
            "survive_rm_top5pct": round(
                tot - sum(s[:max(1, int(round(len(s) * 0.05)))]), 2),
            "max_win": round(s[0], 2),
            "profitable_trades_pct": round(
                100.0 * sum(1 for x in series if x > 0) / len(series), 1),
        }
        out[key] = rec
        # the raw series and dates, so a later question about these books can be
        # answered without re-running 52 backtests. It costs ~1 MB and it is the
        # difference between a two-minute follow-up and a thirty-minute one.
        rec["_series"] = [round(x, 4) for x in series]
        rec["_dates"] = dates
        bar.update(key)

    bar.close("measured")
    json.dump(out, open("_full_study.json", "w", encoding="utf-8"), indent=1)

    # ---------------------------------------------------------------- report --
    def L(v, w=8, d=2):
        return ("%*.*f" % (w, d, v)) if isinstance(v, (int, float)) else "%*s" % (w, "-")

    order = sorted(out, key=lambda k: -out[k]["net"])

    print()
    print("#" * 130)
    print("DRAWDOWN AS A PERCENTAGE  -  at risk per trade, and relative to the peak")
    print("  Hurst/Ooi/Pedersen put trend following at 20-40%% max DD; 1%% risk per R is")
    print("  the usual retail convention. Recovery is asymmetric: d%% needs d/(1-d) to get back.")
    print("#" * 130)
    print("  %-30s %8s %9s %9s %9s %9s %11s %9s"
          % ("book", "net", "DD@1%", "DD@2%", "of peak%", "peak R", "recover@1%", "recover@2%"))
    print("  " + "-" * 126)
    for k in order:
        d = out[k]["dd"]["1%risk"]
        print("  %-30s %8s %9s %9s %9s %9s %11s %9s"
              % (k[:30], L(out[k]["net"], 8), L(d["acct_1pct"], 9),
                 L(d["acct_2pct"], 9), L(d["peak_pct_1pct"], 9),
                 L(d["peak_r"], 9, 1), L(d["recovery_pct_1pct"], 11, 1),
                 L(d["recovery_pct_2pct"], 9, 1)))

    print()
    print("#" * 130)
    print("HALF-YEAR CELLS ON ONE CONTINUOUS CURVE  -  data ends %s" % DATA_END)
    print("  2026H2 holds ~2.5 months, not 6. Shown, labelled PARTIAL, excluded from the count.")
    print("#" * 130)
    print("  %-30s %5s %5s %-42s %s" % ("book", "full", "neg", "worst full half", "p IS / p OOS"))
    print("  " + "-" * 126)
    for k in order:
        r = out[k]
        worst = min((c for c in r["halves"] if not r["halves"][c]["partial"]),
                    key=lambda c: r["halves"][c]["net"], default="-")
        wv = r["halves"][worst]["net"] if worst != "-" else 0
        pp = ("%.4f / %.4f" % (r["p_is"], r["p_oos"])) if r["p_is"] is not None else "   -  /   -  "
        print("  %-30s %5d %5d %-42s %s"
              % (k[:30], r["n_half_full"], len(r["half_neg"]),
                 "%s %+.1f" % (worst, wv), pp))

    print()
    print("#" * 130)
    print("FINANCIAL YEARS  -  the owner holds for a year, so year-to-year is the real unit")
    print("#" * 130)
    print("  %-30s %5s %5s  %s" % ("book", "yrs", "neg", "negative years (2026 is partial)"))
    print("  " + "-" * 126)
    for k in order:
        r = out[k]
        ny = [y for y in r["years"] if r["years"][y]["net"] <= 0]
        print("  %-30s %5d %5d  %s"
              % (k[:30], len(r["year_full"]), len(r["year_neg_full"]),
                 ", ".join("%s(%+.1f)" % (y, r["years"][y]["net"])
                           for y in sorted(ny)) or "none"))

    print()
    print("#" * 130)
    print("ROLLING WINDOWS  -  can this be HELD, or does it only work across the whole sample?")
    print("#" * 130)
    print("  %-30s %-24s %-24s %-24s"
          % ("book", "rolling 10", "rolling 20", "rolling 50"))
    print("  %-30s %-24s %-24s %-24s" % ("", "% profitable / worst", "% profitable / worst",
                                         "% profitable / worst"))
    print("  " + "-" * 126)
    for k in order:
        r = out[k]["rolling"]
        def f(key_):
            x = r[key_]
            return "%.0f%% of %d  worst %+.1f" % (x["profitable_pct"], x["windows"], x["worst"])
        print("  %-30s %-24s %-24s %-24s" % (k[:30], f("10"), f("20"), f("50")))

    print()
    print("#" * 130)
    print("WIN-SPREAD  -  is the profit in many trades or in a handful?")
    print("#" * 130)
    print("  %-30s %8s %10s %12s %12s"
          % ("book", "win%", "max win", "top10 gives", "survives -top10"))
    print("  " + "-" * 126)
    for k in order:
        t = out[k]["tail"]
        print("  %-30s %8s %10s %11s%% %12s"
              % (k[:30], L(t["profitable_trades_pct"], 8, 1), L(t["max_win"], 10),
                 L(t["top10_contrib_pct"], 11, 1), L(t["survive_rm_top10"], 12)))

    print("\n  wrote _full_study.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())