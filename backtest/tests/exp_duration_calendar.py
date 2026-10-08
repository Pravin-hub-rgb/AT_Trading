"""exp_duration_calendar - underwater duration in weeks and months, not trades.

WHY
===
I reported "underwater" in trades and it was wrong twice over. The first version
never fired its recovery detector and printed "trades from the peak to the end of
the sample" - 286 for the base book, a number with no meaning. The corrected
version gave trade counts, which is better but still not what the owner's
framework asks for.

`docs/learn/finding optimal book.md` on drawdown duration:

    "Not only 'How deep did it fall?' but 'How long was I underwater?'"
    "A 15R drawdown lasting 15 trades is psychologically very different from 15R
     lasting 100 trades."

Trades are the wrong unit because this book's trade count varies hugely - 528 to
813 across five books that differ by one knob. A book with more trades shows more
"underwater trades" for the same calendar time. Calendar time is comparable
between books, so that is what this reports.

It reports, for the max drawdown and then for EVERY underwater episode:

    depth in R, weeks to make it, weeks to recover, weeks total underwater,
    and recovery as a percentage of the era's total calendar span.

The last one is the honest cross-book comparison: "this book spent 11% of its
history below its high" is comparable between a 528-trade book and an 813-trade
one in a way that trade counts are not.

Run:  cd backtest/tests
      python -u exp_duration_calendar.py
"""
from __future__ import annotations

import json
import statistics as st
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

BOOKS = {
    "BASE": "fsent_champ_long",
    "atr_low": "fsent_champ_long_mode_atr_low",
    "fd": "fsent_champ_long_mode_fd",
    "flip_quality": "fsent_champ_long_mode_flip_quality",
    "union": "fsent_champ_long_mode_union",
}
WEEKS_IN_MONTH = 4.345
OUT_JSON = Path(__file__).parent / "_duration_calendar.json"
OUT_MD = Path(__file__).parent / "_duration_calendar.md"


def ts(t):
    """Trade timestamp -> epoch seconds. entry_date is 'YYYY-MM-DD' on some
    builds and an epoch on others, so both are handled rather than assumed."""
    if isinstance(t, (int, float)):
        return float(t)
    s = str(t).strip()
    if s.isdigit():
        return float(s)
    for f in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, f).replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            continue
    return None


def episodes(rs):
    """Every underwater episode as (peak_i, trough_i, recovery_i or None).

    Rewritten: the first version tracked the peak with a condition that could
    never fire, so it reported exactly one episode per book and always
    unrecovered. The rule is simply - below the running peak, we are underwater;
    the episode closes on the trade that gets back to it. Depth is returned too,
    because "how long" without "how deep" is half the answer.
    """
    out = []
    cum = peak = 0.0
    pk_i = None
    tr_i = None
    depth = 0.0
    for i, x in enumerate(rs):
        cum += x
        if pk_i is None:
            if cum > peak:
                peak, pk_i = cum, i
            continue
        if cum >= peak - 1e-12:
            out.append((pk_i, tr_i, i, depth))
            peak, pk_i, tr_i, depth = cum, i, None, 0.0
        else:
            if tr_i is None:
                tr_i = i
            depth = max(depth, peak - cum)
    if pk_i is not None and tr_i is not None:
        out.append((pk_i, tr_i, None, depth))
    return out


def main():
    from exp_tf_family import build_family_module
    from run_experiment import net_r, get_swings
    from exp_signal_metrics import load_era
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()
    res = {}
    for era in ("is", "oos"):
        d = load_era(era)
        sw = get_swings(d, "sw10")
        res[era] = {}
        for nm, bk in BOOKS.items():
            o = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=d["fine"],
                    **{**EXPERIMENTS[bk]["params"]})
            tr = [t for t in o["ltf_trades"] if t.get("outcome") != "open"]
            rs = [net_r([t]) for t in tr]
            dts = [ts(t.get("entry_ts", t.get("entry_date"))) for t in tr]
            if any(x is None for x in dts):
                raise SystemExit("%s/%s has unparseable trade dates - refusing to "
                                 "report duration in wall-clock units." % (nm, era))

            span_wk = (max(dts) - min(dts)) / 604800.0
            span_mo = span_wk / WEEKS_IN_MONTH

            # ---- the max drawdown, in calendar units ----
            cum = peak = 0.0
            mdd = 0.0
            pk = tr_i = 0
            cp = 0
            for i, x in enumerate(rs):
                cum += x
                if cum > peak:
                    peak, cp = cum, i
                if peak - cum > mdd:
                    mdd, pk, tr_i = peak - cum, cp, i
            rec_i = None
            s = 0.0
            for j in range(pk, len(rs)):
                s += rs[j]
                if j >= tr_i and s >= -1e-9:
                    rec_i = j
                    break

            make_wk = (dts[tr_i] - dts[pk]) / 604800.0
            if rec_i is not None:
                rec_wk = (dts[rec_i] - dts[tr_i]) / 604800.0
                tot_wk = (dts[rec_i] - dts[pk]) / 604800.0
                recovered = True
            else:
                rec_wk = tot_wk = (dts[-1] - dts[tr_i]) / 604800.0
                recovered = False

            eps = episodes(rs)
            dur_wk, dep = [], []
            for a, b, c2, dp in eps:
                end = c2 if c2 is not None else len(rs) - 1
                dur_wk.append((dts[end] - dts[a]) / 604800.0)
                dep.append(dp)
            closed = [e for e in eps if e[2] is not None]

            res[era][nm] = {
                "n": len(rs),
                "span_weeks": round(span_wk, 1),
                "span_months": round(span_mo, 1),
                "max_dd": round(mdd, 1),
                "make_weeks": round(make_wk, 1),
                "make_months": round(make_wk / WEEKS_IN_MONTH, 1),
                "recover_weeks": round(rec_wk, 1),
                "recover_months": round(rec_wk / WEEKS_IN_MONTH, 1),
                "under_weeks": round(tot_wk, 1),
                "under_months": round(tot_wk / WEEKS_IN_MONTH, 1),
                "recovered": recovered,
                "under_pct_of_era": round(100.0 * tot_wk / span_wk, 1) if span_wk > 0 else None,
                "n_episodes": len(eps),
                "n_unrecovered": len(eps) - len(closed),
                "longest_episode_weeks": round(max(dur_wk), 1) if dur_wk else 0.0,
                "longest_episode_months": round(max(dur_wk) / WEEKS_IN_MONTH, 1) if dur_wk else 0.0,
                "median_episode_weeks": round(st.median(dur_wk), 1) if dur_wk else 0.0,
                "median_episode_months": round(st.median(dur_wk) / WEEKS_IN_MONTH, 1) if dur_wk else 0.0,
                "underwater_pct_of_era_all_eps": round(100.0 * sum(dur_wk) / span_wk, 1) if span_wk > 0 else None,
                "deepest_episode": round(max(dep), 1) if dep else 0.0,
            }

    P = print
    P("=" * 116)
    P("  UNDERWATER DURATION IN CALENDAR TIME - the owner's bucket 2, in units comparable between books")
    P("  trade counts are not comparable: 528 to 813 trades across books that differ by one knob.")
    P("=" * 116)

    for era in ("is", "oos"):
        r = res[era]
        P("\n" + "#" * 116)
        P("# %s   (era spans %.1f months / %.0f weeks)" % (
            era.upper(), r["BASE"]["span_months"], r["BASE"]["span_weeks"]))
        P("#" * 116)
        P("  %-13s %7s %9s %9s %9s %9s %9s %9s %8s" % (
            "book", "maxDD", "make_wk", "make_mo", "recov_wk", "recov_mo", "under_wk", "under_mo", "%of era"))
        for nm in BOOKS:
            m = r[nm]
            P("  %-13s %7.1f %9.1f %9.1f %9.1f %9.1f %9.1f %9.1f %7.1f%%%s" % (
                nm, m["max_dd"], m["make_weeks"], m["make_months"],
                m["recover_weeks"], m["recover_months"], m["under_weeks"],
                m["under_months"], m["under_pct_of_era"],
                "" if m["recovered"] else "  UNRECOVERED at end of era"))

        P("\n  every underwater episode, not just the deepest one:")
        P("  %-13s %5s %11s %11s %12s %11s %10s" % (
            "book", "eps", "longest_mo", "median_mo", "total%of_era", "deepest_R", "unrecov"))
        for nm in BOOKS:
            m = r[nm]
            P("  %-13s %5d %11.1f %11.1f %11.1f%% %11.1f %10d" % (
                nm, m["n_episodes"], m["longest_episode_months"],
                m["median_episode_months"], m["underwater_pct_of_era_all_eps"],
                m["deepest_episode"], m["n_unrecovered"]))

    OUT_JSON.write_text(json.dumps(res, indent=2, default=str) + "\n", encoding="utf-8")
    lines = ["# underwater duration in calendar time", "",
             "Bucket 2 of `docs/learn/finding optimal book.md`, in units comparable",
             "between books. Trade counts are not comparable across this set.", ""]
    for era in ("is", "oos"):
        lines += ["## %s (era spans %.1f months)" % (era.upper(), res[era]["BASE"]["span_months"]), "",
                  "| book | maxDD | make (wk) | make (mo) | recover (wk) | recover (mo) | underwater (wk) | underwater (mo) | % of era | recovered |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
        for nm in BOOKS:
            m = res[era][nm]
            lines.append("| %s | %.1f | %.1f | %.1f | %.1f | %.1f | %.1f | %.1f | %.1f%% | %s |" % (
                nm, m["max_dd"], m["make_weeks"], m["make_months"], m["recover_weeks"],
                m["recover_months"], m["under_weeks"], m["under_months"],
                m["under_pct_of_era"], "yes" if m["recovered"] else "NO"))
        lines += ["", "| book | episodes | longest (mo) | median (mo) | all-episode underwater % of era | deepest (R) | unrecovered |",
                  "|---|---:|---:|---:|---:|---:|---:|"]
        for nm in BOOKS:
            m = res[era][nm]
            lines.append("| %s | %d | %.1f | %.1f | %.1f%% | %.1f | %d |" % (
                nm, m["n_episodes"], m["longest_episode_months"],
                m["median_episode_months"], m["underwater_pct_of_era_all_eps"],
                m["deepest_episode"], m["n_unrecovered"]))
        lines.append("")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    P("\nwrote %s and %s" % (OUT_MD.name, OUT_JSON.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())