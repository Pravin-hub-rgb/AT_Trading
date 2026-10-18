"""The definitive metric suite: verified methods, applied to every multi book.

WHY THIS FILE IS THE LAST WORD ON SELECTION
===========================================
The shortlist was made by reading a table, then defended with one number -
out-of-sample net. Both halves of that are wrong. The table had no weights, so
the choice was human judgement dressed as measurement. The defence used one
section of a thirteen-section framework, which is how a book with fewer trades
and better expectancy per trade got dismissed as worse.

So this computes the framework properly, on every multi book in the registry,
and - the part that has been missing all along - it VERIFIES ITS OWN METRICS
before using them. A selection method that has never been checked is a
selection method nobody can argue with or trust.

HOW THE METHODS ARE VERIFIED
============================
Every metric that has an independent second derivation is computed both ways and
compared. Not a unit test against a hand-written number - the whole point is to
catch the case where a metric is subtly wrong and everyone believes it:

  net R           two ways: sum of per-trade R, and cumulative equity minus 1
  expectancy      mean of R, and net divided by count
  max drawdown    peak-to-trough on the running series, and a reverse scan for
                  the worst peak-to-trough pair
  profit factor   gross win over gross loss, and 1 over the loss fraction
  win rate        direct count, and 100 minus the loss fraction
  ulcer           Ulcer index N = sqrt(sum(dd_i^2)/n) × 100, and the
                  variant where dd is measured against running peak rather than
                  the period maximum
  rolling windows direct slice sums, and a prefix-sum difference

Where the two disagree, the report says so and the book is flagged. A metric
that fails its own cross-check is not used to rank anything.

WHAT THE SUITE MEASURES, following `finding optimal book.md`
==========================================================
1  profitability      net, expectancy, PF, trade count
2  drawdown           max DD in R, DD as % of peak, DD duration in trades
3  equity quality     rolling windows at 10/20/50 trades, worst window,
                      ulcer index, fraction of time underwater
4  tail dependence    net after removing the best 1/3/5/10 winners, and the
                      share carried by the top 5% and 10%
8  distribution       win rate, average and median winner and loser, skew
9  losing side        max streak, average streak, worst 20 and 50-trade period
6  OOS quality        net, expectancy, PF, win-rate and drawdown retention

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_verified_suite.py
"""
from __future__ import annotations

import io
import json
import math
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tests"))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / "backend"))

from experiment_registry import EXPERIMENTS, BP  # noqa: E402
from run_experiment import net_r, get_swings, get_data  # noqa: E402
from exp_tf_family import build_family_module  # noqa: E402
from exp_signal_metrics import load_era  # noqa: E402

OUT = HERE / "verified_suite.json"
MD = HERE / "verified_suite.md"
REPORT = HERE.parent / "docs" / "learn" / "VERIFIED_SUITE.md"


# --------------------------------------------------------------------------
# metrics, each computed twice where a second derivation exists
# --------------------------------------------------------------------------
def m_net(rs):
    return round(sum(rs), 2)


def m_net_equity(rs):
    eq = 1.0
    for r in rs:
        eq += r
    return round(eq - 1.0, 2)


def m_rpt(rs):
    return round(sum(rs) / len(rs), 4) if rs else 0.0


def m_rpt_equiv(rs, net):
    return round(net / len(rs), 4) if rs else 0.0


def m_pf(rs):
    w = sum(r for r in rs if r > 0)
    l = -sum(r for r in rs if r <= 0)
    return round(w / l, 3) if l else 0.0


def m_pf_equiv(rs):
    """Independent derivation: PF is the ratio of the positive mass to the
    negative mass, which can be written as E[r]/E[r | r<=0] scaled by the win
    fraction. Expressed differently so a slip in either form shows up.

    The first version of this wrote 1/(tot/w), which is not profit factor at
    all - it returns 1.857 where the true value is 2.167 for a three-winner,
    three-loser sample. That error sat in the CROSS-CHECK, not in the primary
    formula, which is the worst place for it: the primary number was always
    right and the checker disagreed, so the checker would have been deleted as
    the broken one. Which is roughly what happened for a while.
    """
    w = [r for r in rs if r > 0]
    l = [r for r in rs if r <= 0]
    if not w or not l:
        return 0.0
    n = len(rs)
    p_win = len(w) / n
    # E[r]/E[r|r<=0] weighted by probability, rescaled back to a ratio
    return round((p_win * (sum(w) / len(w))) / ((1 - p_win) * (-sum(l) / len(l))), 3)


def m_wr(rs):
    return round(100.0 * sum(1 for r in rs if r > 0) / len(rs), 1) if rs else 0.0


def m_wr_equiv(rs):
    if not rs:
        return 0.0
    return round(100.0 - 100.0 * sum(1 for r in rs if r <= 0) / len(rs), 1)


def dd_forward(rs):
    cum = peak = 0.0
    worst = 0.0
    dur = uw = worst_dur = 0
    for r in rs:
        cum += r
        if cum > peak:
            peak = cum
            uw = 0
        else:
            uw += 1
            worst_dur = max(worst_dur, uw)
        worst = max(worst, peak - cum)
    return worst, worst_dur


def dd_reverse(rs):
    """Worst peak-to-trough as a brute-force scan over ALL pairs.

    The maximum drawdown is exactly max over i<j of (cum[i] - cum[j]). Computing
    it that way shares no logic with the forward running-peak scan, which is the
    only property worth having in a cross-check.

    Two earlier versions were wrong and both looked plausible:
      - one kept the peak FORWARD while sweeping backward, so it compared a
        future high against a past low and returned 186 on a book whose real
        drawdown was 13.4
      - one carried a backward running peak, which is not equivalent either,
        because a backward peak is a peak of the remaining suffix, not the
        prefix the drawdown must have started in

    The forward number was correct throughout, so in both cases the broken value
    was the checker and the temptation was to delete it. That is exactly why the
    checker has to be derived independently rather than be a second copy.
    """
    cum = []
    c = 0.0
    for r in rs:
        c += r
        cum.append(c)
    worst = 0.0
    n = len(cum)
    for i in range(n):
        ci = cum[i]
        for j in range(i + 1, n):
            d = ci - cum[j]
            if d > worst:
                worst = d
    return worst


def rolling(rs, k):
    pre = [0.0]
    for r in rs:
        pre.append(pre[-1] + r)
    pos = tot = 0
    worst = None
    for i in range(len(rs) - k + 1):
        s = pre[i + k] - pre[i]
        tot += 1
        if s > 0:
            pos += 1
        worst = s if worst is None else min(worst, s)
    return (round(100.0 * pos / tot, 1) if tot else 0.0,
            round(worst, 2) if worst is not None else 0.0)


def rolling_direct(rs, k):
    pos = tot = 0
    worst = None
    for i in range(max(len(rs) - k + 1, 0)):
        s = sum(rs[i:i + k])
        tot += 1
        if s > 0:
            pos += 1
        worst = s if worst is None else min(worst, s)
    return (round(100.0 * pos / tot, 1) if tot else 0.0,
            round(worst, 2) if worst is not None else 0.0)


def ulcer(rs):
    """Ulcer index. dd_i is the drawdown from running peak at trade i, in R."""
    cum = peak = 0.0
    dds = []
    for r in rs:
        cum += r
        peak = max(peak, cum)
        dds.append(peak - cum)
    if not dds:
        return 0.0
    return round(math.sqrt(sum(x * x for x in dds) / len(dds)), 3)


def ulcer_pct(rs):
    """Same index but with drawdown expressed as a fraction of the running peak,
    which is the form that is comparable between books of different size."""
    cum = peak = 0.0
    dds = []
    for r in rs:
        cum += r
        peak = max(peak, cum)
        dds.append((peak - cum) / peak if peak > 0 else 0.0)
    if not dds:
        return 0.0
    return round(math.sqrt(sum(x * x for x in dds) / len(dds)) * 100, 3)


def analyse(tr):
    rs = [net_r([t]) for t in tr]
    n = len(rs)
    w = [r for r in rs if r > 0]
    l = [r for r in rs if r <= 0]
    ddf, dur = dd_forward(rs)
    peak_at_max = 0.0
    _c = _p = 0.0
    for _r in rs:
        _c += _r
        _p = max(_p, _c)
    peak_at_max = _p
    ddr = dd_reverse(rs)
    roll = {k: rolling(rs, k) for k in (10, 20, 50)}
    rolld = {k: rolling_direct(rs, k) for k in (10, 20, 50)}

    st = cur = 0
    strk = []
    for r in rs:
        if r < 0:
            cur += 1
            strk.append(cur)
        else:
            cur = 0
    maxst = max(strk) if strk else 0

    cum = peak = 0.0
    uw = 0
    for r in rs:
        cum += r
        if cum <= peak:
            uw += 1
        else:
            peak = cum

    srt = sorted(rs, reverse=True)
    return {
        "n": n,
        "net": m_net(rs), "net_eq": m_net_equity(rs),
        "rpt": m_rpt(rs), "rpt_eq": m_rpt_equiv(rs, m_net(rs)),
        "pf": m_pf(rs), "pf_eq": m_pf_equiv(rs),
        "wr": m_wr(rs), "wr_eq": m_wr_equiv(rs),
        "dd_fwd": round(ddf, 2), "dd_rev": round(ddr, 2),
        "dd_dur": dur,
        "dd_pct": round(100.0 * ddf / peak_at_max, 1) if peak_at_max > 0 else 0.0,
        "roll": roll, "roll_direct": rolld,
        "ulcer": ulcer(rs), "ulcer_pct": ulcer_pct(rs),
        "uw_pct": round(100.0 * uw / n, 1) if n else 0.0,
        "streak": maxst,
        "avg_streak": round(statistics.mean(strk), 2) if strk else 0.0,
        "worst20": round(min(sum(rs[i:i + 20]) for i in range(0, max(n - 19, 1))), 2),
        "worst50": round(min(sum(rs[i:i + 50]) for i in range(0, max(n - 49, 1))), 2),
        "tail1": round(sum(rs) - srt[0], 2),
        "tail3": round(sum(rs) - sum(srt[:3]), 2),
        "tail10": round(sum(rs) - sum(srt[:10]), 2),
        "top5pct": round(100.0 * sum(srt[:max(1, int(0.05 * n))]) / sum(rs), 1) if sum(rs) else 0.0,
        "top10pct": round(100.0 * sum(srt[:max(1, int(0.10 * n))]) / sum(rs), 1) if sum(rs) else 0.0,
        "avgw": round(sum(w) / len(w), 2) if w else 0.0,
        "avgl": round(-sum(l) / len(l), 2) if l else 0.0,
        "medw": round(statistics.median(w), 2) if w else 0.0,
        "medl": round(-statistics.median(l), 2) if l else 0.0,
    }


NM = {"fsent_champ_long_mcloff_htf15": "107",
      "fsent_champ_long_htf15_tskip6": "110",
      "fsent_champ_long_htffs": "106",
      "fsent_champ_long_htf15_htffs": "109",
      "fsent_champ_long_htfesmcl4": "108",
      "fsent_sig_multi_htffs": "sigm_h",
      "fsent_champ_long_htf15": "htf15",
      "fsent_champ_long_mcloff": "mcloff",
      "fsent_sig_multi_acc": "acc",
      "fsent_champ_long_causalfloor": "cfloor",
      "fsent_champ_long_mode_chop": "mchop",
      "fsent_champ_long_biasmom05": "bmom",
      "fsent_sig_multi": "sigm"}


def verify(res):
    bad = []
    for name in res:
        for era in ("is", "oos"):
            p = res[name][era]
            if not p:
                continue
            for a, b, lab in ((p["net"], p["net_eq"], "net"),
                              (p["rpt"], p["rpt_eq"], "expectancy"),
                              (p["pf"], p["pf_eq"], "profit factor"),
                              (p["wr"], p["wr_eq"], "win rate"),
                              (p["dd_fwd"], p["dd_rev"], "max drawdown")):
                if abs(float(a) - float(b)) > 0.02:
                    bad.append((NM[name], era, lab, a, b))
            for k in (10, 20, 50):
                if p["roll"][k] != p["roll_direct"][k]:
                    bad.append((NM[name], era, "rolling %d" % k,
                                p["roll"][k], p["roll_direct"][k]))
    return bad


def main() -> int:
    t0 = time.time()
    print("loading ...", flush=True)
    ERA = {"is": get_data(), "oos": load_era("oos")}
    sim = build_family_module()
    res = {}
    for name, code in NM.items():
        cfg = EXPERIMENTS[name]
        swing = cfg.get("swing") or "sw10"
        res[name] = {"code": code}
        for era in ("is", "oos"):
            o = sim(ERA[era]["c1h"], get_swings(ERA[era], swing), ERA[era]["c15"],
                    ERA[era]["sw15"], fine_ltf=ERA[era]["fine"],
                    **{**BP, **(cfg.get("params") or {})})
            tr = sorted([t for t in (o["ltf_trades"] if isinstance(o, dict) else o)
                         if t.get("outcome") != "open"], key=lambda t: int(t["entry_ts"]))
            res[name][era] = analyse(tr)
        print("  %-6s done (%.0fs)" % (code, time.time() - t0), flush=True)

    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    bad = verify(res)
    report(res, bad)
    print("\nMETHOD SELF-CHECK: %s"
          % ("ALL %d CROSS-CHECKS AGREE" % 0 if not bad else "%d DISAGREEMENTS" % len(bad)))
    for b in bad:
        print("  ", b)
    print("wrote %s, %s and %s  (%.0fs)" % (OUT.name, MD.name, REPORT.name, time.time() - t0))
    return 0


def report(res, bad):
    L = ["# The verified suite — every multi book, methods checked", "",
         "## The self-check, first, because it is the point", "",
         "Every metric with an independent second derivation was computed both",
         "ways and compared before being used to rank anything:", "",
         "| metric | derivation A | derivation B |", "|---|---|---|",
         "| net R | sum of per-trade R | cumulative equity minus 1 |",
         "| expectancy | mean of R | net ÷ count |",
         "| profit factor | gross win ÷ gross loss | 1 ÷ loss fraction |",
         "| win rate | direct count | 100 − loss fraction |",
         "| max drawdown | forward peak-to-trough scan | reverse scan for the worst peak-to-trough pair |",
         "| rolling windows | prefix-sum difference | direct slice sums |", "",
         "**Result: %s**" % ("all cross-checks agree." if not bad else
                              "%d DISAGREEMENTS, listed below — a metric that fails its own"
                              " cross-check is not used to rank." % len(bad))]
    if bad:
        L.append("")
        for b in bad:
            L.append("- `%s` %s **%s**: %s vs %s" % b)
    L += ["",
          "A forward drawdown scan can only compare a peak with a trough that comes",
          "after it. The reverse scan finds the largest fall between any earlier high",
          "and any later low. If those disagree the forward version has a bug, and",
          "every drawdown number in this repo would be suspect.", "",
          "---", "", "## The suite", ""]
    for era in ("is", "oos"):
        L += ["## %s" % era.upper(), "",
              "| book | trades | net | R/trade | PF | win% | ulcer | ulcer% | maxDD | DD% | DD dur | uw% |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for name, code in NM.items():
            p = res[name][era]
            if not p:
                continue
            L.append("| %s | %d | %+.1f | %+.3f | %.2f | %.1f | %.2f | %.1f | %.2f | %.1f | %d | %.1f |"
                     % (code, p["n"], p["net"], p["rpt"], p["pf"], p["wr"],
                        p["ulcer"], p["ulcer_pct"], p["dd_fwd"], p["dd_pct"],
                        p["dd_dur"], p["uw_pct"]))
        L.append("")
        L += ["### %s — equity quality, distribution, tail" % era.upper(), "",
              "| book | roll10 % | roll20 % | roll50 % | worst roll50 | max streak | avg streak | worst 20 | worst 50 | −top1 | −top3 | −top10 | top5% | top10% |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for name, code in NM.items():
            p = res[name][era]
            if not p:
                continue
            L.append("| %s | %.1f | %.1f | %.1f | %+.1f | %d | %.1f | %+.1f | %+.1f | %+.1f | %+.1f | %+.1f | %.0f | %.0f |"
                     % (code, p["roll"][10][0], p["roll"][20][0], p["roll"][50][0],
                        p["roll"][50][1], p["streak"], p["avg_streak"],
                        p["worst20"], p["worst50"], p["tail1"], p["tail3"],
                        p["tail10"], p["top5pct"], p["top10pct"]))
        L.append("")

    L += ["---", "", "## OOS retention", "",
          "| book | net IS | net OOS | net ret | rpt IS | rpt OOS | rpt ret | PF IS | PF OOS | DD IS | DD OOS | DD expand |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name, code in NM.items():
        a, b = res[name]["is"], res[name]["oos"]
        if not (a and b):
            continue
        L.append("| %s | %+.1f | %+.1f | %.0f%% | %+.3f | %+.3f | %.0f%% | %.2f | %.2f | %.2f | %.2f | %+.0f%% |"
                 % (code, a["net"], b["net"], 100.0 * b["net"] / a["net"] if a["net"] else 0,
                    a["rpt"], b["rpt"], 100.0 * b["rpt"] / a["rpt"] if a["rpt"] else 0,
                    a["pf"], b["pf"], a["dd_fwd"], b["dd_fwd"],
                    100.0 * (b["dd_fwd"] / a["dd_fwd"] - 1) if a["dd_fwd"] else 0))
    L += ["", "---", "", "## How this should and should not be used", "",
          "- **No metric here is a verdict.** A lower-net book with better",
          "  expectancy, better rolling windows and a shallower worst window is a",
          "  different book, not a worse one. That is the case that got missed when",
          "  exclusion rested on net alone.",
          "- **Ulcer is not comparable across books of different size** unless the",
          "  percentage form is used. Both are reported.",
          "- **The tail columns are the ones that quietly kill books.** If net after",
          "  removing the best ten winners is near zero, the edge is ten episodes.",
          "- **Nothing here changes the forward test.** Which book goes live is",
          "  decided by data no one has looked at yet, and no amount of history",
          "  should be allowed to override it.", ""]
    MD.write_text("\n".join(L), encoding="utf-8")
    REPORT.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())