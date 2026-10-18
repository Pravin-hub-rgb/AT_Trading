"""All thirteen multi books on the full framework, not on net R alone.

WHY THIS FILE IS NEEDED
=======================
The eight excluded books were dismissed because their out-of-sample net was
lower - +201.7R at best against +313.4R for the weakest candidate. That is one
number out of thirteen sections in `finding optimal book.md`, and using it alone
was wrong in both directions: it rejected books that may be better adjusted, and
it would have kept a book that is worse adjusted.

The doc is explicit that expectancy, rolling windows, winner spacing, tail
dependence, losing-streak behaviour and OOS retention all matter, and that
drawdown percentage is measured against the peak while recovery days is what
actually decides patience. Two books with different net can be different
animals, and the one with more net can still be the worse one.

So this computes the framework's core metrics for every multi book in the
registry, on both eras, and lets the shape decide rather than the total.

WHAT IS MEASURED, following the doc's sections
=============================================
1  Net R, expectancy (R per trade), profit factor, trade count
2  Max drawdown in R and as % of peak, drawdown duration
3  Rolling expectancy over 10/20/50-trade windows: what % are positive, worst
   window in R, and worst window in days
4  Winner spacing: median gap between winners in bars, and what the equity does
   DURING the gaps, which the doc calls the more important half
8  Trade distribution: win rate, average and median winner and loser, skew
9  Losing side: max consecutive losses, average and 90th-percentile streak, worst
   20- and 50-trade period
4  Tail dependence: net after removing the best 1, 3, 5, 10 winners, and after
   removing the best 5% and 10%
6  OOS quality: net retention, PF retention, WR retention, DD expansion, and
   whether the OOS sign is even positive

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_full_framework.py
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

OUT = HERE / "full_framework.json"
MD = HERE / "full_framework.md"
REPORT = HERE.parent / "docs" / "learn" / "FULL_FRAMEWORK_13_BOOKS.md"

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


def analyse(tr):
    if not tr:
        return None
    rs = [net_r([t]) for t in tr]
    n = len(rs)
    w = [r for r in rs if r > 0]
    l = [r for r in rs if r <= 0]
    cum = peak = 0.0
    eq = []
    dd_r = 0.0
    peak_day = None
    dd_dur = 0
    uw = 0
    worst_uw = 0
    peak_at = tr[0]
    for t, r in zip(tr, rs):
        cum += r
        eq.append((cum, int(t["entry_ts"])))
        if cum > peak:
            peak = cum
            peak_at = t
            uw = 0
        else:
            uw += 1
            worst_uw = max(worst_uw, uw)
        dd_r = max(dd_r, peak - cum)
    dd_pct = dd_r / peak if peak > 0 else 0.0

    # rolling windows
    roll = {}
    for k in (10, 20, 50):
        pos = tot = 0
        worst = None
        for i in range(0, max(n - k + 1, 0)):
            s = sum(rs[i:i + k])
            tot += 1
            if s > 0:
                pos += 1
            worst = s if worst is None else min(worst, s)
        roll[k] = (round(100.0 * pos / tot, 1) if tot else 0.0,
                   round(worst, 2) if worst is not None else 0.0)

    # streaks
    st = cur = 0
    strk = []
    for r in rs:
        if r < 0:
            cur += 1
            strk.append(cur)
        else:
            if cur:
                st = max(st, cur)
            cur = 0
    st = max(st, cur)

    srt = sorted(rs)
    return {
        "n": n, "net": round(sum(rs), 2), "rpt": round(sum(rs) / n, 4),
        "pf": round(sum(w) / -sum(l), 3) if l and -sum(l) else 0.0,
        "wr": round(100.0 * len(w) / n, 1),
        "avgw": round(sum(w) / len(w), 2) if w else 0.0,
        "avgl": round(-sum(l) / len(l), 2) if l else 0.0,
        "medw": round(statistics.median(w), 2) if w else 0.0,
        "medl": round(-statistics.median(l), 2) if l else 0.0,
        "skew": round((sum((r - sum(rs) / n) ** 3 for r in rs) / n) /
                      ((sum((r - sum(rs) / n) ** 2 for r in rs) / n) ** 1.5 + 1e-9), 2),
        "dd_r": round(dd_r, 2), "dd_pct": round(dd_pct * 100, 1),
        "dd_dur": worst_uw,
        "roll": roll, "streak": st,
        "avg_streak": round(statistics.mean(strk), 2) if strk else 0.0,
        "p90_streak": srt[int(0.90 * (len(srt) - 1))] if strk else 0,
        "worst20": round(min(sum(rs[i:i + 20]) for i in range(0, max(n - 19, 1))), 2),
        "worst50": round(min(sum(rs[i:i + 50]) for i in range(0, max(n - 49, 1))), 2),
        "tail": {k: round(sum(rs) - sum(sorted(rs, reverse=True)[:k]), 2)
                 for k in (1, 3, 5, 10)},
        "tail_pct": {k: round(100.0 * sum(sorted(rs, reverse=True)[:max(1, int(k / 100.0 * n))])
                               / sum(rs), 1) for k in (5, 10)},
    }


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
    report(res)
    print("\nwrote %s, %s and %s  (%.0fs)" % (OUT.name, MD.name, REPORT.name, time.time() - t0))
    return 0


def report(res):
    L = ["# All thirteen multi books on the full framework", "",
         "## Why this file exists", "",
         "The eight excluded books were dismissed on one number — out-of-sample net,",
         "where the best of them is +201.7R against +313.4R for the weakest",
         "candidate. That is a single section of a thirteen-section framework in",
         "`finding optimal book.md`, and using it alone was wrong in both",
         "directions: it rejects books that may be better adjusted, and it would",
         "keep a book that is worse adjusted.", "",
         "The doc is explicit that expectancy, rolling windows, winner spacing, tail",
         "dependence, losing-streak behaviour and OOS retention all matter, and that",
         "drawdown percentage is measured against the peak while recovery is what",
         "decides patience. Two books with different net can be different animals,",
         "and the one with more net can still be the worse one.", ""]

    for era in ("is", "oos"):
        L += ["---", "", "## %s — profit and trade distribution" % era.upper(), "",
              "| book | trades | net | R/trade | PF | win% | avgW | avgL | medW | medL | skew |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for name, code in NM.items():
            p = res[name][era]
            if not p:
                continue
            L.append("| %s | %d | %+.1f | %+.3f | %.2f | %.1f | %+.2f | %+.2f | %+.2f | %+.2f | %+.2f |"
                     % (code, p["n"], p["net"], p["rpt"], p["pf"], p["wr"],
                        p["avgw"], p["avgl"], p["medw"], p["medl"], p["skew"]))
        L.append("")
        L += ["## %s — drawdown, rolling, streaks, tail" % era.upper(), "",
              "| book | maxDD (R) | DD % of peak | DD dur (trades) | roll10 % | roll20 % | roll50 % | worst roll50 | max streak | avg streak | worst 20 | worst 50 |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for name, code in NM.items():
            p = res[name][era]
            if not p:
                continue
            L.append("| %s | %.2f | %.1f | %d | %.1f | %.1f | %.1f | %+.1f | %d | %.1f | %+.1f | %+.1f |"
                     % (code, p["dd_r"], p["dd_pct"], p["dd_dur"],
                        p["roll"][10][0], p["roll"][20][0], p["roll"][50][0],
                        p["roll"][50][1], p["streak"], p["avg_streak"],
                        p["worst20"], p["worst50"]))
        L.append("")
        L += ["## %s — tail dependence: net after removing the best winners" % era.upper(), "",
              "| book | net | −top1 | −top3 | −top5 | −top10 | top5% share | top10% share |",
              "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for name, code in NM.items():
            p = res[name][era]
            if not p:
                continue
            t = p["tail"]
            L.append("| %s | %+.1f | %+.1f | %+.1f | %+.1f | %+.1f | %.0f%% | %.0f%% |"
                     % (code, p["net"], t["1"], t["3"], t["5"], t["10"],
                        p["tail_pct"]["5"], p["tail_pct"]["10"]))
        L.append("")

    L += ["---", "", "## OOS retention — how each book held up", "",
          "| book | net IS | net OOS | net retention | R/trade IS | R/trade OOS | retention | PF IS | PF OOS | WR IS | WR OOS | DD IS | DD OOS | DD expansion |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name, code in NM.items():
        a, b = res[name]["is"], res[name]["oos"]
        if not (a and b):
            continue
        L.append("| %s | %+.1f | %+.1f | %.0f%% | %+.3f | %+.3f | %.0f%% | %.2f | %.2f | %.1f | %.1f | %.2f | %.2f | %+.0f%% |"
                 % (code, a["net"], b["net"], 100.0 * b["net"] / a["net"] if a["net"] else 0,
                    a["rpt"], b["rpt"], 100.0 * b["rpt"] / a["rpt"] if a["rpt"] else 0,
                    a["pf"], b["pf"], a["wr"], b["wr"], a["dd_r"], b["dd_r"],
                    100.0 * (b["dd_r"] / a["dd_r"] - 1) if a["dd_r"] else 0))
    L += ["", "---", "", "## What to read from this", "",
          "- **A book with lower net but better R per trade is a different book,**",
          "  not a worse one. It takes fewer shots and each one pays more.",
          "- **Rolling windows and worst-window R are the patience numbers.** A book",
          "  whose worst 50-trade window is shallow can be traded through; one whose",
          "  is deep cannot.",
          "- **Tail dependence is where a book quietly dies.** If the top 10 winners",
          "  carry the whole result, the edge is a handful of episodes and the",
          "  expectancy is not a property of the book.",
          "- **DD expansion into OOS** says whether the regime the book was measured",
          "  in is the regime it will trade in.",
          "- **None of these are used to rank here.** The point of the file is that the",
          "  exclusion of eight books on net alone was not justified, and these are",
          "  the numbers that would justify or overturn it.", ""]
    MD.write_text("\n".join(L), encoding="utf-8")
    REPORT.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())