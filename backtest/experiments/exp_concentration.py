"""How concentrated is each candidate's profit in time - and in one month?

WHY
===
The owner spotted that December 2023 may be carrying a large share of the
in-sample profit for both candidates, and that other books which also had it
appear to have been removed. Concentration is not on any of the four validation
techniques' checklists and it is not something a drawdown or a shuffled path
can show you, because none of them care WHERE the money arrived. A book whose
profit is one month of an otherwise flat series is a different object from a
book that earns steadily, and the difference survives every test the four
techniques run.

This answers three things per book:
  - which single month carries the most, and how much of the total it is
  - the same for calendar years
  - what the book looks like with its best month removed

That last one is the useful one. Removing the best month is a crude but honest
upper bound on "how much of this is one lucky run".

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_concentration.py
"""
from __future__ import annotations

import io
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tests"))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / "backend"))

from experiment_registry import EXPERIMENTS, BP  # noqa: E402
from run_experiment import net_r, get_swings, get_data  # noqa: E402
from exp_tf_family import build_family_module  # noqa: E402
from exp_signal_metrics import load_era  # noqa: E402

OUT = HERE / "concentration.json"
MD = HERE / "concentration.md"

BOOKS = [("fsent_champ_long_mcloff_htf15", "107"),
         ("fsent_champ_long_htf15_tskip6", "110"),
         ("fsent_champ_long_htffs", "106"),
         ("fsent_champ_long_htf15_htffs", "109"),
         ("fsent_champ_long_htfesmcl4", "108")]


def buckets(trades, fmt):
    b = defaultdict(float)
    for t in trades:
        d = str(t.get("entry_date") or "")[:10]
        if len(d) >= 7:
            b[fmt(d)] += net_r([t])
    return b


def main() -> int:
    ERA = {"is": get_data(), "oos": load_era("oos")}
    sim = build_family_module()
    res = {}
    L = ["# Profit concentration in time", "",
         "The four validation techniques do not ask where the money arrived. A",
         "book whose in-sample profit is one month of an otherwise flat series",
         "passes all four and is still a different object from one that earns",
         "steadily.", "",
         "| book | era | trades | net | best month | best month R | share of net | worst month | net without best month |",
         "|---|---|---:|---:|---|---:|---:|---:|---:|"]
    for name, code in BOOKS:
        cfg = EXPERIMENTS[name]
        swing = cfg.get("swing") or "sw10"
        res[name] = {}
        for era in ("is", "oos"):
            d = ERA[era]
            o = sim(d["c1h"], get_swings(d, swing), d["c15"], d["sw15"],
                    fine_ltf=d["fine"], **{**BP, **(cfg.get("params") or {})})
            tr = sorted([x for x in (o["ltf_trades"] if isinstance(o, dict) else o)
                         if x.get("outcome") != "open"], key=lambda t: int(t["entry_ts"]))
            mo = buckets(tr, lambda s: s[:7])
            yr = buckets(tr, lambda s: s[:4])
            tot = sum(mo.values())
            bm = max(mo, key=lambda k: mo[k]) if mo else "-"
            wm = min(mo, key=lambda k: mo[k]) if mo else "-"
            without = tot - mo[bm] if mo else 0.0
            res[name][era] = {
                "n": len(tr), "net": round(tot, 2),
                "months": {k: round(v, 2) for k, v in sorted(mo.items())},
                "years": {k: round(v, 2) for k, v in sorted(yr.items())},
                "best_month": bm, "best_month_r": round(mo[bm], 2) if mo else 0.0,
                "best_share_pct": round(100.0 * mo[bm] / tot, 1) if mo and tot else 0.0,
                "worst_month": wm, "worst_month_r": round(mo[wm], 2) if mo else 0.0,
                "net_without_best": round(without, 2),
                "neg_months": sum(1 for v in mo.values() if v < 0),
            }
            r = res[name][era]
            L.append("| %s | %s | %d | %+.1f | %s | %+.1f | %.0f%% | %s (%+.1f) | %+.1f |"
                     % (code, era.upper(), len(tr), tot, bm, r["best_month_r"],
                        r["best_share_pct"], wm, r["worst_month_r"], without))
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")

    L += ["", "---", "", "## Monthly net R, IS era", "",
          "Only the months that matter are printed in full for 107 and 110; the rest",
          "are summarised, because the question is where the profit sits, not the",
          "whole ledger.", ""]
    for name, code in BOOKS[:2]:
        mo = res[name]["is"]["months"]
        big = sorted(mo.items(), key=lambda kv: -kv[1])[:6]
        L += ["### %s — top 6 months, of %d" % (code, len(mo)), "",
              "| month | net R |", "|---|---:|"]
        for k, v in big:
            L.append("| %s | %+.1f |" % (k, v))
        L += ["", "Yearly: " + " · ".join("%s %+.1f" % (k, res[name]["is"]["years"][k])
                                           for k in sorted(res[name]["is"]["years"])), ""]

    L += ["---", "", "## How to read this", "",
          "- **share of net above roughly 25 percent for a single month** means the",
          "  book has a period it depends on. That is not disqualifying by itself,",
          "  but it is a different risk from steady accrual and the sizing answer",
          "  should differ.",
          "- **net without best month** is the floor. A book that goes negative there",
          "  is one good run away from being a losing strategy.",
          "- **negative months count** is the floor check in the other direction. Many",
          "  small negative months with steady positives is a healthy shape; one big",
          "  positive month is a fragile one.",
          "- None of the four validation techniques can see this. They care about the",
          "  distribution of trades, not about where in calendar time the trades",
          "  landed.", ""]
    io.open(MD, "w", encoding="utf-8").write("\n".join(L))
    print("\n".join(L[:16]))
    print("\nwrote %s and %s" % (OUT.name, MD.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())