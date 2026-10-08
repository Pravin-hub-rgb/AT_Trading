"""exp_mode_confirm2 - run check 2 on the RIGHT lanes, including for the shipping book.

THE GAP THIS CLOSES
===================
exp_mode_confirm.py tested the four mode candidates on `champion_multi_sw10` and
`utcsat_multi_sw10` and called that "check 2, the second lane". Those are real
books and the test was worth running, but they are the wrong family for this
question:

    champion_multi_sw10   pivot_rule=origin, no exp_fs_entry_side, no exp_mltf
    utcsat_multi_sw10     the same lane, utcsat entry
    fsent_champ_long     pivot_rule=leg, exp_fs_entry_side=long, exp_mltf=True

So the candidates were tested on a **different architecture** and the shipping
book was **never tested on any second lane at all**. The owner's question was the
right one: is the shipping book itself better than these candidates in the same
checks? That could not be answered, because nothing in the previous run measured
it.

The family that actually shares this book's architecture:

    fsent_champ_long      pivot=leg      FS long     528t / +533.4R IS  311t / +239.6R OOS
    fsent_utcsat_long     pivot=leg_no_entry, FS long  525t / +465.0R IS  310t / +238.8R OOS
    fsent_champ_short     pivot=leg      FS short    533t / +600.6R IS  312t / +239.5R OOS

**All three net about 239R out of sample.** That is either a coincidence of the
era or the architecture is carrying the result, and it is cheap to find out which:
each candidate mode is applied to each sibling, and the shipping book's own
architecture is compared against each candidate's, on all of them.

WHAT THIS ANSWERS
=================
  1. Does the candidate beat the shipping book on ITS OWN family's siblings?
  2. Does the shipping book itself survive the same test the candidates failed?
     If the champion also fails on siblings, then "check 2" is a property of the
     era rather than a verdict on the candidates, and saying the candidates were
     disqualified by it would have been wrong.
  3. Is the ~239R across three books a real architecture effect or noise?

Run:  cd backtest/tests
      python -u exp_mode_confirm2.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

# The family that shares fsent_champ_long's architecture, INCLUDING the shipping
# book. This is the honest "second lane" for this question.
FAMILY = ("fsent_champ_long", "fsent_utcsat_long", "fsent_champ_short")
CANDIDATES = ("atr_low", "fd", "flip_quality", "union")
OUT_JSON = Path(__file__).parent / "_mode_confirm2.json"
OUT_MD = Path(__file__).parent / "_mode_confirm2.md"


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, net_r, get_swings
    from exp_signal_metrics import load_era
    from exp_full_metrics import compute
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()
    data, sw = {}, {}
    for era in ("is", "oos"):
        data[era] = load_era(era)
        sw[era] = get_swings(data[era], "sw10")

    def run(era, name, mode=None):
        p = {**BP, **EXPERIMENTS[name]["params"]}
        if mode:
            p["mode"] = mode
        d = data[era]
        o = sim(d["c1h"], sw[era], d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
        tr = [t for t in o["ltf_trades"] if t.get("outcome") != "open"]
        rs = [net_r([t]) for t in tr]
        srt = sorted(rs, reverse=True)
        m = compute(rs, [t.get("entry_date", "") for t in tr])
        return {"n": m["n"], "net": round(m["net"], 2), "max_dd": round(m["max_dd"], 2),
                "mean": round(m["net"] / max(1, m["n"]), 3), "pf": round(m["pf"], 3),
                "wr": round(m["wr"], 1), "ulcer": round(m["ulcer"], 2),
                "streak": m.get("max_streak"), "dd_dur": m.get("dd_dur"),
                "minus_top5": round(sum(srt[5:]), 2) if len(srt) > 5 else None,
                "minus_top10": round(sum(srt[10:]), 2) if len(srt) > 10 else None}

    print("=" * 112)
    print("  CHECK 2 ON THE RIGHT LANES - and the shipping book tested too")
    print("=" * 112)
    print("  exp_mode_confirm.py used champion_multi_sw10 / utcsat_multi_sw10, which are a")
    print("  DIFFERENT architecture (pivot_rule=origin, no FS entry side, no exp_mltf).")
    print("  The family that shares this book's architecture is below, and the shipping")
    print("  book is in it, so it can finally answer the same question.\n")

    report = {}
    for fam in FAMILY:
        print("-" * 112)
        print("  %s   (the shipping book is this row when fam == fsent_champ_long)" % fam)
        print("-" * 112)
        base = {}
        for era in ("is", "oos"):
            base[era] = run(era, fam)
            print("    BASE   %-4s n=%3d net %+7.1f dd %5.1f mean %.2f pf %.2f -top5 %+7.1f"
                  % (era.upper(), base[era]["n"], base[era]["net"], base[era]["max_dd"],
                     base[era]["mean"], base[era]["pf"], base[era]["minus_top5"] or 0))
        report[fam] = {"base": base, "arms": {}}
        for mode in CANDIDATES:
            for era in ("is", "oos"):
                r = run(era, fam, mode)
                b = base[era]
                d = r["net"] - b["net"]
                report[fam]["arms"].setdefault(mode, {})[era] = r
                mark = "  ahead both" if (r["net"] > b["net"] and era == "oos") else ""
                print("    %-18s %-4s n=%3d net %+7.1f dd %5.1f mean %.2f -top5 %+7.1f  d %+7.1f%s"
                      % (mode, era.upper(), r["n"], r["net"], r["max_dd"], r["mean"],
                         r["minus_top5"] or 0, d, mark))
            print()

    # ------------------------------------------------------------------
    # THE QUESTION: is the shipping book better than the candidates, on the
    # same check, on its own family?
    # ------------------------------------------------------------------
    print("=" * 112)
    print("THE QUESTION ANSWERED: does each mode beat its OWN family's base on OOS?")
    print("=" * 112)
    print("  %-14s %-22s %-22s %-22s" % ("mode", "champ_long", "utcsat_long", "champ_short"))
    verdict_rows = {}
    for mode in CANDIDATES:
        cells = []
        wins = 0
        for fam in FAMILY:
            a = report[fam]["arms"][mode]["oos"]
            b = report[fam]["base"]["oos"]
            d = a["net"] - b["net"]
            dd_ok = a["max_dd"] <= b["max_dd"]
            good = d > 0 and dd_ok
            if good:
                wins += 1
            cells.append("%+7.1f dd%5.1f%s" % (d, a["max_dd"], "  OK" if good else ""))
        verdict_rows[mode] = wins
        print("  %-14s %-22s %-22s %-22s  wins %d/3"
              % (mode, cells[0], cells[1], cells[2], wins))

    print()
    print("  AND THE SHIPPING BOOK, same test - do its own SIBLINGS hold?")
    print("  (if the family itself is fragile, 'fails on siblings' is a property of")
    print("   the era rather than a verdict on the candidates)")
    for fam in FAMILY[1:]:
        for era in ("is", "oos"):
            b = report[fam]["base"][era]
            ship = report["fsent_champ_long"]["base"][era]
            print("    %-22s %-4s n=%3d net %+7.1f dd %5.1f   vs champ_long d %+7.1f"
                  % (fam, era.upper(), b["n"], b["net"], b["max_dd"],
                     b["net"] - ship["net"]))

    print()
    print("=" * 112)
    print("READ THIS BEFORE THE TABLE ABOVE")
    print("=" * 112)
    allw = verdict_rows
    if max(allw.values()) == 0:
        print("  No candidate mode beats its own family base out of sample on ANY of")
        print("  the three books that share this architecture. The previous run's verdict")
        print("  - disqualified on the second lane - holds, and now on the right family.")
    else:
        best = max(allw, key=lambda k: allw[k])
        print("  %s wins %d of 3. Read that against the drawdown column before treating"
              % (best, allw[best]))
        print("  it as a candidate; net alone is not the test.")

    print()
    print("  Nothing promoted, nothing removed. The four candidate books stay")
    print("  registered and pinned.")

    OUT_JSON.write_text(json.dumps({"family": list(FAMILY), "report": report}, indent=2) + "\n",
                        encoding="utf-8")
    lines = ["# check 2 on the right lanes, shipping book included", "",
             "Family sharing fsent_champ_long's architecture. Base is each book's own",
             "as-booked config; arms change only `mode`.", "",
             "| family | arm | era | n | net | mean | PF | maxDD | ulcer | streak | -top5 | d net |",
             "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for fam in FAMILY:
        for era in ("is", "oos"):
            b = report[fam]["base"][era]
            lines.append("| %s | **BASE** | %s | %d | %.1f | %.3f | %.2f | %.1f | %.1f | %s | %.1f | |" % (
                fam, era.upper(), b["n"], b["net"], b["mean"], b["pf"], b["max_dd"],
                b["ulcer"], b["streak"], b["minus_top5"] or 0))
            for mode in CANDIDATES:
                a = report[fam]["arms"][mode][era]
                lines.append("| %s | %s | %s | %d | %.1f | %.3f | %.2f | %.1f | %.1f | %s | %.1f | %+.1f |" % (
                    fam, mode, era.upper(), a["n"], a["net"], a["mean"], a["pf"],
                    a["max_dd"], a["ulcer"], a["streak"], a["minus_top5"] or 0,
                    a["net"] - b["net"]))
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nwrote %s and %s" % (OUT_MD.name, OUT_JSON.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())