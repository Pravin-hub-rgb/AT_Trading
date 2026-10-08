"""exp_owner_scorecard - the owner's framework, applied to the four mode candidates.

WHY THIS FILE EXISTS
====================
On 2026-10-08 I rejected three of four mode candidates and disqualified the
fourth using a rule I had invented myself: "reject if drawdown rises above the
base book's 11.88R". The owner's framework - `docs/learn/finding optimal book.md`
- contains no such rule. It says:

    "A strategy making +300R with horrible concentration may be worse than one
     making +220R much more consistently."
    "Net R should be a major factor, but not the king."
    "Don't just record Max DD." ... "How long was I underwater?"
    Ranking: 1 Validity, 2 OOS performance, 3 OOS retention, 4 DD/duration,
    5 worst rolling periods, 6 distribution of winners through time,
    7 tail dependence, 8 parameter robustness, 9 cost robustness,
    10 simplicity, 11 cross-asset, 12 raw Net R.

So drawdown is a measured input, not a veto. It is traded against return, and
the owner's own named measure for that trade is `Net R / Max DD`. The owner has
since confirmed a drawdown budget of 20R, which makes the budget test concrete
instead of assumed.

I had been applying a hard gate where the framework asks for a comparison. This
file does the comparison the framework actually specifies, and it is the reason
the earlier verdicts need revisiting.

THE METRIC SET, MAPPED TO THE OWNER'S BUCKETS
=============================================
  bucket 1  raw profitability   net, expectancy, PF, trade count
  bucket 2  drawdown            max DD, DD as % of return, DD duration in
                                TRADES, recovery in trades, worst rolling
                                20/50/100 trades, worst month
  bucket 3  equity quality      Net R / Max DD, ulcer, positive-month %, and
                                winner gaps: median / p90 / max gap between
                                +3R, +5R and +10R winners
  bucket 4  tail dependence     remove top 1/3/5/10, remove top 0.5/1/2/5/10%,
                                and the CONTRIBUTION of those same slices
  bucket 5  OOS                 expectancy retention, PF retention, DD expansion
  bucket 6  complexity          number of knobs vs the base book

Nothing here is transcribed by hand - every number comes from the engine.

Run:  cd backtest/tests
      python -u exp_owner_scorecard.py
"""
from __future__ import annotations

import json
import math
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

BASE = "fsent_champ_long"
CANDIDATES = {
    "atr_low": "fsent_champ_long_mode_atr_low",
    "fd": "fsent_champ_long_mode_fd",
    "flip_quality": "fsent_champ_long_mode_flip_quality",
    "union": "fsent_champ_long_mode_union",
}
BUDGET_R = 20.0          # owner-confirmed drawdown budget, 2026-10-08
OUT_JSON = Path(__file__).parent / "_owner_scorecard.json"
OUT_MD = Path(__file__).parent / "_owner_scorecard.md"


def roll_worst(rs, k):
    """Worst k-trade window. The owner's bucket 2, and the one a single
    max-DD number hides: a book can have a shallow peak-to-trough that sits
    underwater for a very long time."""
    if len(rs) < k:
        return None
    c = [0.0]
    for x in rs:
        c.append(c[-1] + x)
    return round(min(c[i + k] - c[i] for i in range(len(c) - k)), 1)


def dd_profile(rs):
    """Max DD plus how long it took to make and to recover, in trades.
    Bucket 2's actual complaint is duration, not just depth."""
    cum = peak = 0.0
    mdd = 0.0
    peak_i = trough_i = 0
    cur_peak_i = 0
    for i, x in enumerate(rs):
        cum += x
        if cum > peak:
            peak, cur_peak_i = cum, i
        dd = peak - cum
        if dd > mdd:
            mdd, peak_i, trough_i = dd, cur_peak_i, i
    # recovery: trades from the trough until the old peak is made again
    cum = 0.0
    rec = None
    for i in range(trough_i, len(rs)):
        cum += sum(rs[peak_i:trough_i + 1])
        if cum >= -1e-9:
            rec = i - trough_i
            break
        cum += rs[i]
    under = 0
    run = False
    for x in rs[peak_i:trough_i + len(rs) - trough_i if rec is not None else None]:
        pass
    # underwater length = make + recovery
    make = trough_i - peak_i
    under = (make + rec) if rec is not None else len(rs) - peak_i
    return round(mdd, 1), make, rec, under


def tail(rs):
    """Bucket 4. Removal AND contribution, absolute and percentage, because
    the owner asked for both and they answer different questions."""
    n = len(rs)
    s = sorted(rs)
    net = sum(rs)
    out = {}
    for k in (1, 3, 5, 10):
        rem = net - sum(s[-k:])
        out["drop_top%d" % k] = round(100.0 * rem / net, 1) if net > 0 else None
    for pct in (0.5, 1, 2, 5, 10):
        k = max(1, int(round(n * pct / 100.0)))
        contrib = sum(s[-k:])
        out["contrib_top%g%%" % pct] = round(100.0 * contrib / net, 1) if net > 0 else None
        rem = net - contrib
        out["drop_top%g%%" % pct] = round(100.0 * rem / net, 1) if net > 0 else None
    return out


def gaps(rs, thresh):
    """Bucket 3. The owner's point about winner SPACING: not how many winners,
    but how far apart they come. A +20R trade every 15 trades is a different
    book from one whose +20R trades can vanish for 60."""
    idx = [i for i, x in enumerate(rs) if x >= thresh]
    if len(idx) < 2:
        return None, None, None
    g = [idx[i + 1] - idx[i] for i in range(len(idx) - 1)]
    return (round(st.median(g), 1),
            round(sorted(g)[int(0.9 * (len(g) - 1))], 1),
            max(g))


def score(rs, dates):
    n = len(rs)
    if n == 0:
        return {}
    s = sorted(rs)
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x < 0]
    gw, gl = sum(wins), -sum(losses)
    mdd, make, rec, under = dd_profile(rs)
    net = sum(rs)

    mon = defaultdict(float)
    for d, x in zip(dates, rs):
        mon[d[:7]] += x

    # ulcer
    up, cum, peak = [], 0.0, 0.0
    for x in rs:
        cum += x
        if cum > peak:
            peak = cum
        if peak > 0:
            up.append(100.0 * (peak - cum) / peak)
    ulcer = math.sqrt(sum(u * u for u in up) / len(up)) if up else 0.0

    streak = run = 0
    for x in rs:
        if x < 0:
            run += 1
            streak = max(streak, run)
        else:
            run = 0

    k = max(1, n // 20)
    r = {
        # bucket 1
        "n": n,
        "net": round(net, 1),
        "expectancy": round(net / n, 4),
        "pf": round(gw / gl, 3) if gl > 1e-9 else None,
        "wr": round(100.0 * len(wins) / n, 1),
        "median": round(st.median(rs), 3),
        "payoff": round((gw / len(wins)) / (gl / len(losses)), 3) if wins and losses else None,
        # bucket 2
        "max_dd": mdd,
        "dd_pct_of_return": round(100.0 * mdd / net, 1) if net > 0 else None,
        "dd_to_make_trades": make,
        "dd_recovery_trades": rec,
        "underwater_trades": under,
        "worst_20": roll_worst(rs, 20),
        "worst_50": roll_worst(rs, 50),
        "worst_100": roll_worst(rs, 100),
        "worst_month": round(min(mon.values()), 1) if mon else None,
        # bucket 3
        "net_per_dd": round(net / mdd, 2) if mdd > 1e-9 else None,
        "ulcer": round(ulcer, 2),
        "pos_month_pct": round(100.0 * sum(1 for v in mon.values() if v > 0) / len(mon), 1) if mon else None,
        "gap3": gaps(rs, 3.0),
        "gap5": gaps(rs, 5.0),
        "gap10": gaps(rs, 10.0),
        # bucket 4
        "top5_share_pct": round(100.0 * sum(s[-k:]) / net, 1) if net > 0 else None,
        # bucket 9 (losing-side)
        "max_streak": streak,
    }
    r.update(tail(rs))
    return r


def main():
    from exp_tf_family import build_family_module
    from run_experiment import net_r, get_swings
    from exp_signal_metrics import load_era
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()
    data, sw = {}, {}
    for era in ("is", "oos"):
        data[era] = load_era(era)
        sw[era] = get_swings(data[era], "sw10")

    def run(era, book):
        p = {**EXPERIMENTS[book]["params"]}
        d = data[era]
        o = sim(d["c1h"], sw[era], d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
        tr = [t for t in o["ltf_trades"] if t.get("outcome") != "open"]
        return [net_r([t]) for t in tr], [t.get("entry_date", "") for t in tr]

    books = {"BASE": BASE}
    books.update(CANDIDATES)
    res = {}
    for era in ("is", "oos"):
        for name, bk in books.items():
            rs, ds = run(era, bk)
            res.setdefault(name, {})[era] = score(rs, ds)

    # bucket 5 - retention
    for name in books:
        a, b = res[name]["is"], res[name]["oos"]
        res[name]["retention"] = {
            "expectancy": round(100.0 * b["expectancy"] / a["expectancy"], 1) if a["expectancy"] > 0 else None,
            "pf": round(100.0 * b["pf"] / a["pf"], 1) if a["pf"] and b["pf"] else None,
            "net": round(100.0 * b["net"] / a["net"], 1) if a["net"] > 0 else None,
            "dd_expansion": round(b["max_dd"] / a["max_dd"], 2) if a["max_dd"] > 0 else None,
        }

    # bucket 6 - complexity
    base_knobs = len(EXPERIMENTS[BASE]["params"])
    for name, bk in books.items():
        res[name]["knobs"] = len(EXPERIMENTS[bk]["params"])

    P = print
    P("=" * 118)
    P("  OWNER'S SCORECARD - docs/learn/finding optimal book.md applied to the 4 mode candidates")
    P("  drawdown budget %0.0fR (owner-confirmed 2026-10-08).  My invented 11.88R veto is NOT used." % BUDGET_R)
    P("=" * 118)

    for era, lbl in (("is", "IN SAMPLE"), ("oos", "OUT OF SAMPLE")):
        P("\n" + "#" * 118)
        P("# BUCKET 1 - raw profitability      |  %s" % lbl)
        P("#" * 118)
        P("  %-13s %5s %10s %8s %7s %7s %8s %6s" % ("book", "n", "net", "expect", "PF", "WR%", "payoff", "med"))
        for name in books:
            m = res[name][era]
            P("  %-13s %5d %10.1f %8.3f %7s %7.1f %8s %6.2f" % (
                name, m["n"], m["net"], m["expectancy"],
                ("%.2f" % m["pf"]) if m["pf"] else "-", m["wr"],
                ("%.2f" % m["payoff"]) if m["payoff"] else "-", m["median"]))

        P("\n" + "#" * 118)
        P("# BUCKET 2 - drawdown, and HOW LONG UNDERWATER  |  %s" % lbl)
        P("#" * 118)
        P("  %-13s %7s %8s %8s %8s %9s %8s %8s %6s %s" % (
            "book", "maxDD", "dd%ret", "make_t", "recov_t", "underwet", "worst20", "worst50", "strk", "budget"))
        for name in books:
            m = res[name][era]
            ok = "PASS" if m["max_dd"] <= BUDGET_R else "OVER"
            P("  %-13s %7.1f %8.1f %8s %8s %9s %8.1f %8.1f %6d %s" % (
                name, m["max_dd"], m["dd_pct_of_return"] or 0, m["dd_to_make_trades"],
                m["dd_recovery_trades"], m["underwater_trades"], m["worst_20"],
                m["worst_50"], m["max_streak"], ok))

        P("\n" + "#" * 118)
        P("# BUCKET 3 - how the money arrives: return per unit of pain, and winner SPACING  |  %s" % lbl)
        P("#" * 118)
        P("  %-13s %9s %7s %8s %16s %16s %16s" % (
            "book", "net/DD", "ulcer", "posMon%", "gap+3R med/p90/max", "gap+5R med/p90/max", "gap+10R med/p90/max"))
        for name in books:
            m = res[name][era]
            def g(v):
                return ("%.0f/%.0f/%.0f" % v) if v else "n/a"
            P("  %-13s %9s %7.1f %8.1f %16s %16s %16s" % (
                name, ("%.2f" % m["net_per_dd"]) if m["net_per_dd"] else "-",
                m["ulcer"], m["pos_month_pct"], g(m["gap3"]), g(m["gap5"]), g(m["gap10"])))

        P("\n" + "#" * 118)
        P("# BUCKET 4 - tail dependence: what is left when the big winners are removed  |  %s" % lbl)
        P("#" * 118)
        P("  %-13s %8s %8s %8s %8s %10s %10s %10s %10s" % (
            "book", "drop1", "drop3", "drop5", "drop10", "drop1%", "drop5%", "drop10%", "top5%share"))
        for name in books:
            m = res[name][era]
            P("  %-13s %8s %8s %8s %8s %10s %10s %10s %10s" % (
                name, m["drop_top1"], m["drop_top3"], m["drop_top5"], m["drop_top10"],
                m["drop_top1%"], m["drop_top5%"], m["drop_top10%"], m["top5_share_pct"]))

    P("\n" + "#" * 118)
    P("# BUCKET 5 - OOS retention, and bucket 6 - complexity")
    P("#" * 118)
    P("  %-13s %10s %9s %9s %9s %8s" % (
        "book", "expect%", "pf%", "net%", "DDexpand", "knobs"))
    for name in books:
        r = res[name]["retention"]
        P("  %-13s %10s %9s %9s %9s %8d" % (
            name, r["expectancy"], r["pf"], r["net"], r["dd_expansion"], res[name]["knobs"]))
    P("\n  base book has %d knobs; every candidate differs by ONE mode string, so complexity is"
      % base_knobs)
    P("  identical across the set. Bucket 6 cannot separate them.")

    OUT_JSON.write_text(json.dumps(res, indent=2, default=str) + "\n", encoding="utf-8")

    lines = ["# owner scorecard - 4 mode candidates vs base", "",
             "Framework: `docs/learn/finding optimal book.md`. Budget %0.0fR." % BUDGET_R,
             "The 11.88R veto I invented on 2026-10-08 is not used here.", "",
             "## bucket 1 - raw profitability", "",
             "| book | era | n | net | expectancy | PF | WR% | payoff |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    for era in ("is", "oos"):
        for name in books:
            m = res[name][era]
            lines.append("| %s | %s | %d | %+.1f | %+.3f | %s | %.1f | %s |" % (
                name, era.upper(), m["n"], m["net"], m["expectancy"],
                ("%.2f" % m["pf"]) if m["pf"] else "-", m["wr"],
                ("%.2f" % m["payoff"]) if m["payoff"] else "-"))
    lines += ["", "## bucket 2 - drawdown and duration", "",
              "| book | era | maxDD | dd%ret | make | recover | underwater | worst20 | worst50 | streak | budget |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for era in ("is", "oos"):
        for name in books:
            m = res[name][era]
            lines.append("| %s | %s | %.1f | %s | %s | %s | %s | %.1f | %.1f | %d | %s |" % (
                name, era.upper(), m["max_dd"], m["dd_pct_of_return"], m["dd_to_make_trades"],
                m["dd_recovery_trades"], m["underwater_trades"], m["worst_20"], m["worst_50"],
                m["max_streak"], "PASS" if m["max_dd"] <= BUDGET_R else "OVER"))
    lines += ["", "## bucket 3 - return per unit of pain, and winner spacing", "",
              "| book | era | net/DD | ulcer | posMon% | gap+3R | gap+5R | gap+10R |",
              "|---|---|---:|---:|---:|---|---|---|"]
    for era in ("is", "oos"):
        for name in books:
            m = res[name][era]
            def g(v):
                return "%.0f/%.0f/%.0f" % v if v else "n/a"
            lines.append("| %s | %s | %s | %.1f | %.1f | %s | %s | %s |" % (
                name, era.upper(), ("%.2f" % m["net_per_dd"]) if m["net_per_dd"] else "-",
                m["ulcer"], m["pos_month_pct"], g(m["gap3"]), g(m["gap5"]), g(m["gap10"])))
    lines += ["", "## bucket 4 - tail dependence", "",
              "| book | era | drop top1 | drop top3 | drop top5 | drop top10 | drop top1% | drop top5% | drop top10% | top5% contribution |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for era in ("is", "oos"):
        for name in books:
            m = res[name][era]
            lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                name, era.upper(), m["drop_top1"], m["drop_top3"], m["drop_top5"], m["drop_top10"],
                m["drop_top1%"], m["drop_top5%"], m["drop_top10%"], m["top5_share_pct"]))
    lines += ["", "## bucket 5 - retention, bucket 6 - complexity", "",
              "| book | expectancy ret% | PF ret% | net ret% | DD expansion | knobs |",
              "|---|---:|---:|---:|---:|---:|"]
    for name in books:
        r = res[name]["retention"]
        lines.append("| %s | %s | %s | %s | %s | %d |" % (
            name, r["expectancy"], r["pf"], r["net"], r["dd_expansion"], res[name]["knobs"]))
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    P("\nwrote %s and %s" % (OUT_MD.name, OUT_JSON.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())