"""The worst case if you deploy on ANY date - not just 2021-01-01.

THE FLAW IN THE STARTUP NUMBER
-------------------------------
exp_startup_yearly.py measured startup drawdown from the beginning of the record,
2021-01-01. It reported 1.01% for the shipping book. That is not a bound on what a
deployer faces. It is one path's number, and it is the number from whichever day
the record happens to begin.

The owner is right that this is uncertain: the peak-to-trough episode that shows as
29.62% for htf15_htffs happened from March to August. Anyone who started in March
saw the whole 29.62% immediately. Anyone who started in January 2021 saw 1%. Both are
real and they are the same book.

So the question is not "what happened on day one of this particular backtest". It is:

    for EVERY possible start date, if I put money in and hold for a year,
    what is the worst peak-to-trough I would have seen?

That is a bound, not an anecdote. It answers "what could happen if I deploy today"
without knowing today's position in the cycle - which is the actual situation.

METHOD
------
For each book, for every trade index i, take series[i:] with equity starting at
ZERO (the money you put in that day) and walk forward 12 calendar months. Record:
  - the worst peak-to-trough inside that year
  - the net at 12 months
Then report the distribution across all ~800 start points: median, 10th percentile
(the bad luck tail) and the worst single start. Same again for 24 months.

No backtests re-run - this is arithmetic on the saved series and dates in
_full_study.json.

Writes _anystart.json.
"""
import json
import sys
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, ".")

ACCOUNT = 500000.0
RISK = 0.01


def dparse(s):
    return datetime.strptime(str(s)[:10], "%Y-%m-%d")


def worst_in_window(rs, idx, limit):
    """Worst peak-to-trough starting at idx, equity starting at zero."""
    cum = 0.0
    pk = 0.0
    mdd = 0.0
    net = None
    for j in range(idx, len(rs)):
        cum += rs[j]
        pk = max(pk, cum)
        mdd = max(mdd, pk - cum)
        if j - idx + 1 >= limit:
            break
    net = cum
    return mdd, net


def pct(xs, q):
    if not xs:
        return None
    s = sorted(xs)
    i = int(q * (len(s) - 1))
    return round(s[i], 2)


def main():
    d = json.load(open("_full_study.json", encoding="utf-8"))
    keys = [k for k in d if d[k].get("_series")]
    out = {}

    for k in keys:
        rs = d[k]["_series"]
        ds = d[k]["_dates"]
        dts = [dparse(x) for x in ds]
        span0 = dts[0]
        rec = {}

        for label, days in (("12m", 365), ("24m", 730), ("36m", 1095)):
            mdd_list = []
            net_list = []
            for i in range(len(rs)):
                # find the window end by date
                if (dts[-1] - dts[i]).days < days:
                    break
                j = i
                while j < len(rs) and (dts[j] - dts[i]).days < days:
                    j += 1
                cum = 0.0
                pk = 0.0
                mdd = 0.0
                for x in range(i, min(j + 1, len(rs))):
                    cum += rs[x]
                    pk = max(pk, cum)
                    mdd = max(mdd, pk - cum)
                mdd_list.append(mdd)
                net_list.append(cum)
            rec[label] = {
                "starts": len(mdd_list),
                "mdd_worst": round(max(mdd_list), 2) if mdd_list else None,
                "mdd_p10": pct(mdd_list, 0.10),
                "mdd_median": pct(mdd_list, 0.50),
                "mdd_p90": pct(mdd_list, 0.90),
                "net_worst": round(min(net_list), 2) if net_list else None,
                "net_p10": pct(net_list, 0.10),
                "net_median": pct(net_list, 0.50),
                "pct_starts_negative": round(
                    100.0 * sum(1 for x in net_list if x < 0) / len(net_list), 1)
                if net_list else None,
                "pct_starts_positive": round(
                    100.0 * sum(1 for x in net_list if x > 0) / len(net_list), 1)
                if net_list else None,
            }
        out[k] = rec
        print("  %-32s  12m worst %6.2fR   12m median %6.2fR   12m best-start %+7.1fR"
              % (k[:32], rec["12m"]["mdd_worst"], rec["12m"]["mdd_median"],
                 rec["12m"]["net_worst"]))

    json.dump(out, open("_anystart.json", "w", encoding="utf-8"), indent=1)

    def L(v, w=8, d=2):
        return ("%*.*f" % (w, d, v)) if isinstance(v, (int, float)) else "%*s" % (w, "-")

    for label, days in (("12m", "1 year"), ("24m", "2 years"), ("36m", "3 years")):
        print()
        print("#" * 132)
        print("ANY-START WORST CASE - holding %s.  Equity starts at ZERO on every possible start date." % days)
        print("  Worst  = the single unluckiest start date in the whole record")
        print("  p10    = the bad-luck tail: 10%% of start dates were at least this bad")
        print("  Median = the typical start")
        print("#" * 132)
        print("  %-32s %9s %9s %9s | %9s %9s | %8s %8s %8s"
              % ("book", "worstDD", "p10 DD", "med DD", "worstNet", "p10 Net",
                 "%start+", "%start-", "starts"))
        print("  " + "-" * 128)
        for k in sorted(keys, key=lambda x: -out[x][label]["mdd_worst"]):
            r = out[k][label]
            print("  %-32s %9s %9s %9s | %9s %9s | %7s%% %7s%% %8d"
                  % (k[:32], L(r["mdd_worst"], 9), L(r["mdd_p10"], 9),
                     L(r["mdd_median"], 9), L(r["net_worst"], 9),
                     L(r["net_p10"], 9), L(r["pct_starts_positive"], 8, 1),
                     L(r["pct_starts_negative"], 8, 1), r["starts"]))

    print()
    print("  wrote _anystart.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())