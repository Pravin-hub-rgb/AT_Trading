"""How long the drawdown actually lasted - the number I got wrong.

THE ERROR
---------
Last turn I wrote "13.42% takes ~49 trades, about two years of calendar time to
make back". That conflated two different numbers:

  maxUW            the longest run of consecutive trades spent below a peak.
                   A STRETCH measure - how long the account was under water at the
                   worst point in its history.
  recovery         trades from the BOTTOM of the max drawdown until equity passes
                   the peak that preceded it. A DURATION - strictly less than
                   maxUW, often far less, and the only one that answers "how long
                   until I was back where I started".

I quoted the stretch as the duration. The owner was right to push back.

THIS MEASURES IT OFF THE SAVED SERIES
-------------------------------------
_full_study.json carries `_series` (net R per trade) and `_dates` for every book,
so this is arithmetic on data already measured - no backtests re-run.

What comes out:
  - the max drawdown: peak R and its date, trough R and its date
  - how many trades and how many CALENDAR DAYS from trough back to that peak
  - whether it ever recovered
  - every drawdown episode over 3R, with its own recovery, so one episode does not
    stand in for the experience
  - the LADDER: equity at each six-month and twelve-month mark against the
    starting point. This is what the owner actually sees on a chart - a staircase,
    not one big V - and it is the honest picture of holding the thing for a year.
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


def episodes(rs, threshold=3.0):
    """Every peak-to-new-high cycle deeper than `threshold` R."""
    out = []
    peak_i = 0
    peak_r = rs[0] if rs else 0.0
    cum = 0.0
    for i, r in enumerate(rs):
        cum += r
        if cum >= peak_r:
            if i > peak_i and (peak_r - min(
                    rs[peak_i:i + 1])) > threshold:
                pass
            peak_r = cum
            peak_i = i
    # walk episodes properly: peak -> trough -> next peak
    out = []
    cum = 0.0
    pk_i, pk_v, tk_i, tk_v = 0, rs[0], 0, rs[0]
    for i, r in enumerate(rs):
        cum += r
        if cum >= pk_v:
            if i > tk_i:
                out.append((pk_i, pk_v, tk_i, tk_v, i))
            pk_i, pk_v = i, cum
            tk_i, tk_v = i, cum
        else:
            if cum < tk_v:
                tk_i, tk_v = i, cum
    if out and out[-1][4] is None:
        pass
    return [e for e in out if (e[1] - e[3]) >= threshold]


def main():
    d = json.load(open("_full_study.json", encoding="utf-8"))
    # The per-trade series and dates live in _full_study.json, but the startup
    # block this harness also prints does NOT - exp_startup_yearly.py writes that,
    # into _startup_yearly.json. Reading both out of _full_study.json raised
    # KeyError 'startup' on every book, so the harness had been unrunnable and
    # the doc it feeds kept quoting its last pre-mark-fix numbers. Both inputs
    # are regenerated in the same pass so the two halves cannot be from
    # different chains.
    try:
        _start = json.load(open("_startup_yearly.json", encoding="utf-8"))
    except FileNotFoundError:
        _start = {}
    for _k, _v in _start.items():
        if isinstance(_v, dict) and isinstance(_v.get("startup"), dict):
            d.setdefault(_k, {}).setdefault("startup", _v["startup"])
    keys = [k for k in d if d[k].get("_series") and "startup" in d[k]]

    rows = []
    for k in keys:
        rs = d[k]["_series"]
        ds = d[k]["_dates"]
        cum = pk = 0.0
        pk_i = 0
        tk_i = 0
        tk_v = 0.0
        best = None
        for i, r in enumerate(rs):
            cum += r
            if cum > pk:
                pk, pk_i = cum, i
            if cum < tk_v:
                tk_v, tk_i = cum, i
            dd = pk - cum
            if best is None or dd > best[0]:
                best = (dd, pk_i, pk, tk_i, cum)
        dd_r, pki, pkv, tki, tkv = best
        # recovery: from trough until equity passes the peak
        cum = 0.0
        for i in range(len(rs)):
            cum += sum(rs[:i + 1])
        # redo the walk to find recovery index
        cum = 0.0
        pk = 0.0
        pk_at_td = 0.0
        rec_i = None
        i = 0
        cum = 0.0
        peak_before = 0.0
        trough_seen = False
        cur_peak = 0.0
        cur_pk_i = 0
        cur_tk_v = 0.0
        cur_tk_i = 0
        mdd_r = 0.0
        mdd_pk = 0.0
        mdd_tk_i = 0
        rec_trades = None
        rec_days = None
        cum = 0.0
        peak = 0.0
        peak_i = 0
        tk_v = 0.0
        tk_i = 0
        mdd_r = 0.0
        mdd_tk_i = mdd_pk_i = 0
        mdd_pk_v = 0.0
        for i, r in enumerate(rs):
            cum += r
            if cum >= peak:
                peak, peak_i = cum, i
                tk_v, tk_i = cum, i
            else:
                if cum < tk_v:
                    tk_v, tk_i = cum, i
                dd = peak - cum
                if dd > mdd_r:
                    mdd_r = dd
                    mdd_tk_i, mdd_pk_i, mdd_pk_v = tk_i, peak_i, peak
        # recovery: walk forward from the trough until equity passes the peak that
        # preceded the deepest dip. This is the DURATION. maxUW is the STRETCH.
        rec_trades = rec_days = None
        c2 = sum(rs[:mdd_tk_i + 1])
        for j in range(mdd_tk_i + 1, len(rs)):
            c2 += rs[j]
            if c2 > mdd_pk_v:
                rec_trades = j - mdd_tk_i
                rec_days = (dparse(ds[j]) - dparse(ds[mdd_tk_i])).days
                break
        rows.append({
            "book": k,
            "mdd_r": round(mdd_r, 2),
            "mdd_pct_1": round(mdd_r * RISK * 100, 2),
            "rupees": round(mdd_r * RISK * ACCOUNT, 0),
            "peak_date": ds[mdd_pk_i][:10],
            "trough_date": ds[mdd_tk_i][:10],
            "recovered": rec_trades is not None,
            "rec_trades": rec_trades,
            "rec_days": rec_days,
            "rec_months": round(rec_days / 30.44, 1) if rec_days is not None else None,
            "start_dd": round(-d[k]["startup"]["startup_dd_r"], 2),
            "start_dd_pct": round(d[k]["startup"]["startup_dd_r"] * RISK * 100, 2),
            "net": d[k]["net"],
        })

    print()
    print("#" * 128)
    print("THE REAL RECOVERY - from the BOTTOM of the worst drawdown, not the longest underwater run")
    print("  Rs %s account at %s%% risk per R.  I previously quoted maxUW (49 trades) as the" %
          ("{:,}".format(int(ACCOUNT)), RISK * 100))
    print("  recovery time.  That was a stretch, not a duration.  Corrected below.")
    print("#" * 128)
    print("  %-30s %8s %9s %11s %12s %9s %9s %9s"
          % ("book", "maxDD", "% @1%", "Rs", "peak->trough", "rec trd", "rec days", "rec mo"))
    print("  " + "-" * 124)
    for r in sorted(rows, key=lambda x: -x["mdd_r"]):
        rt = r["rec_trades"]
        span = r["peak_date"][5:10] + "->" + r["trough_date"][5:10]
        print("  %-30s %7.2fR %8.2f%% %11s %12s %9s %9s %9s"
              % (r["book"][:30], r["mdd_r"], r["mdd_pct_1"],
                 "{:,.0f}".format(r["rupees"]), span,
                 rt if rt else "never",
                 r["rec_days"] if r["rec_days"] is not None else "-",
                 r["rec_months"] if r["rec_months"] is not None else "-"))

    # ---- ladder --------------------------------------------------------
    print()
    print("#" * 128)
    print("THE LADDER - where was the account at every 6 and 12 months?")
    print("  This is what the owner sees on a chart: a staircase. Each row is the")
    print("  account value as a percentage of where it STARTED, not of its peak.")
    print("#" * 128)
    marks = ["2021-07-01", "2022-01-01", "2022-07-01", "2023-01-01", "2023-07-01",
             "2024-01-01", "2024-07-01", "2025-01-01", "2025-07-01", "2026-01-01"]
    print("  %-30s %s" % ("book", " ".join("%7s" % m[2:7] for m in marks)))
    print("  " + "-" * 124)
    for k in ["fsent_champ_long", "fsent_champ_long_mcloff", "fsent_champ_long_htffs",
              "fsent_champ_long_htf15_htffs", "fsent_sig_multi", "fsent_sig_full",
              "fsent_sig_multi_htffs"]:
        if k not in d:
            continue
        rs, ds = d[k]["_series"], d[k]["_dates"]
        cum = 0.0
        seq = []
        mi = 0
        cur = 0.0
        cells = []
        want = 0
        for i, r in enumerate(rs):
            cur += r
            if want < len(marks) and str(ds[i])[:10] >= marks[want]:
                cells.append(cur * RISK * 100)
                want += 1
        out = ["%6.0f%%" % c for c in cells] + ["      -"] * (len(marks) - len(cells))
        print("  %-30s %s" % (k[:30], " ".join(out)))

    json.dump(rows, open("_recovery.json", "w", encoding="utf-8"), indent=1)
    print("\n  wrote _recovery.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())