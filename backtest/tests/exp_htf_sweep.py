"""exp_htf_sweep - sweep the HTF side of the book, scored on the owner's rule.

WHAT "HTF" IS HERE, PRECISELY
=============================
The engine is called as

    sim(c1h, HTF_SWINGS, c15, LTF_SWINGS, fine_ltf=fine)

so the 1-hour candles and the swing series in slot 2 are the HTF plane, and the
15-minute candles and the swing series in slot 4 are the LTF plane. Every trade
signal is formed on the LTF plane; the HTF plane supplies context. Concretely
`swings_htf` feeds:

  * the leg ratio (seg start_px / end_px)
  * the bias-momentum breaks (`exp_bias_momentum_min`, which the sig book runs at
    0.8 and the champ book leaves off)
  * the bias flip series
  * `_sw_ts_dir_mag`, which is the regime the router classifies as flip or
    decisive

So sweeping the HTF side means changing the swing series those four things read.
The 1h swing series is currently `sw10`, built at `min_bars=10` on the 1h flow
candles — that single number sets how many HTF windows exist (1601 today) and
therefore how coarse the context is.

THE OWNER'S RULE IS NOW THE SCORE
==================================
> "kabhi negative nahi hona chahiye"

That is a per-cell robustness criterion, not a return criterion, so it is what
this sweep ranks on. Every arm is scored on:

  * negative half-years out of 12  <- PRIMARY, the owner's rule
  * cells worse than the book's own baseline
  * net, expectancy, max DD
  * both eras, never one

The 12 cells are IS 2023-01→2026-09 (8 cells) and the 2021-22 window (4 cells).
Both eras are held data — see `method/OOS_IS_NOT_A_HOLDOUT.md` — so nothing here
is a forward result and nothing here is an adoption.

Run:  cd backtest/tests
      python -u exp_htf_sweep.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

HTF_MB = [3, 5, 8, 10, 14, 20, 30, 40]
BOOKS = [
    ("champ_long", "fsent_champ_long"),
    ("sig_multi", "fsent_sig_multi"),
]
OUT_JSON = Path(__file__).parent / "_htf_sweep.json"
OUT_MD = Path(__file__).parent / "_htf_sweep.md"


def half(d):
    return "%s-H%s" % (d[:4], "1" if int(d[5:7]) <= 6 else "2")


def main():
    from exp_tf_family import build_family_module
    from run_experiment import net_r, get_swings
    from exp_signal_metrics import load_era
    from experiment_registry import EXPERIMENTS
    from src.btc.btc_routes import _compute_swings

    sim = build_family_module()
    eras = {}
    for e in ("is", "oos"):
        eras[e] = load_era(e)

    def run(era, book, htf_mb):
        d = eras[era]
        sw_htf = _compute_swings(d["f1h"], "continuous", min_bars=htf_mb)
        o = sim(d["c1h"], sw_htf, d["c15"], d["sw15"], fine_ltf=d["fine"],
                **EXPERIMENTS[book]["params"])
        return [t for t in o["ltf_trades"] if t.get("outcome") != "open"]

    cells, res = defaultdict(lambda: defaultdict(float)), {}
    for nm, bk in BOOKS:
        for mb in HTF_MB:
            net = 0.0
            n = 0
            per = defaultdict(list)
            dd_by_era = {}
            for era in ("is", "oos"):
                tr = run(era, bk, mb)
                rs = [net_r([t]) for t in tr]
                net += sum(rs)
                n += len(rs)
                cum = peak = 0.0
                m = 0.0
                for x in rs:
                    cum += x
                    if cum > peak:
                        peak = cum
                    m = max(m, peak - cum)
                dd_by_era[era] = round(m, 2)
                for t, r in zip(tr, rs):
                    per[half(t["entry_date"])].append(r)
                    cells[half(t["entry_date"])][f"{nm}:{mb}"] += r
            neg = [c for c in per if sum(per[c]) < 0]
            res[(nm, mb)] = {
                "n": n, "net": round(net, 2), "dd_is": dd_by_era["is"],
                "dd_oos": dd_by_era["oos"], "cells": len(per),
                "negative_cells": len(neg), "negative_list": sorted(neg),
            }

    base_neg = {}
    for nm, _ in BOOKS:
        r = res[(nm, 10)]
        base_neg[nm] = r["negative_cells"]

    allc = sorted({c for c in cells})
    P = print
    P("=" * 118)
    P("  HTF SWEEP - the 1h swing series the regime router reads, scored on")
    P("  the owner's rule: NEVER NEGATIVE in any half-year.")
    P("=" * 118)
    P("  HTF swing min_bars sweep, both books, both eras, %d half-year cells." % len(allc))
    P("  sw10 (min_bars=10) is what every registered book currently uses.")
    P()

    for nm, _ in BOOKS:
        P("-" * 118)
        P("%s   (current setting min_bars=10: %d negative cell(s))"
          % (nm.upper(), base_neg[nm]))
        P("-" * 118)
        P("  %-9s %6s %10s %9s %9s %14s"
          % ("htf mb", "n", "net", "dd IS", "dd OOS", "NEGATIVE CELLS"))
        for mb in HTF_MB:
            r = res[(nm, mb)]
            mark = "  <- current" if mb == 10 else ""
            P("  %-9s %6d %+10.1f %9.1f %9.1f  %2d of %-3d %s%s"
              % (mb, r["n"], r["net"], r["dd_is"], r["dd_oos"],
                 r["negative_cells"], r["cells"],
                 ",".join(r["negative_list"]) if r["negative_list"] else "NONE",
                 mark))
        P()

    P("=" * 118)
    P("  PER-CELL, so 'never negative' can be checked by eye")
    P("=" * 118)
    keys = [f"{nm}:{mb}" for nm, _ in BOOKS for mb in HTF_MB]
    P("  %-9s" % "cell" + "".join("%11s" % k.split(":")[0][:9] + ":" + k.split(":")[1]
                                  for k in keys))
    for c in allc:
        P("  %-9s" % c + "".join("%11.1f" % cells[c][k] for k in keys))
    P()

    P("=" * 118)
    P("VERDICT - ranked on the owner's rule, not on net")
    P("=" * 118)
    rows = []
    for nm, _ in BOOKS:
        for mb in HTF_MB:
            r = res[(nm, mb)]
            rows.append((r["negative_cells"], -r["net"], nm, mb, r))
    rows.sort()
    clean = [x for x in rows if x[0] == 0]
    print("  arms with ZERO negative half-years: %d of %d" % (len(clean), len(rows)))
    if clean:
        print()
        print("  %-12s %-7s %6s %10s %8s %8s" % ("book", "htf mb", "n", "net", "dd IS", "dd OOS"))
        for _, _, nm, mb, r in clean:
            print("  %-12s %-7s %6d %+10.1f %8.1f %8.1f"
                  % (nm, mb, r["n"], r["net"], r["dd_is"], r["dd_oos"]))
    else:
        print("  none")
    P()
    print("  NOTE: a zero-negative arm is not thereby better. The rule is a filter,")
    print("  and this repo's history is that an arm can satisfy every robustness")
    print("  check and still carry less return than the baseline. Net and DD are")
    print("  printed beside it so the trade is visible rather than implied.")

    OUT_JSON.write_text(json.dumps(
        {"htf_min_bars": HTF_MB,
         "arms": {"%s@%d" % (nm, mb): res[(nm, mb)] for nm, mb in res},
         "cells": {c: dict(cells[c]) for c in allc}},
        indent=2, default=str) + "\n", encoding="utf-8")
    lines = ["# HTF sweep - scored on never-negative", "",
             "HTF plane = 1h candles + the swing series in engine slot 2. That series",
             "feeds the leg ratio, the bias-momentum breaks, the bias flips and",
             "`_sw_ts_dir_mag`, which is the flip/decisive classification. Its",
             "`min_bars` is the HTF knob; the books ship at 10.",
             "", "## ranked on the owner's rule", "",
             "| book | htf min_bars | n | net | dd IS | dd OOS | negative cells | which |",
             "|---|---:|---:|---:|---:|---:|---:|---|"]
    for _, _, nm, mb, r in rows:
        lines.append("| %s | %d | %d | %+.1f | %.1f | %.1f | **%d** of %d | %s |" % (
            nm, mb, r["n"], r["net"], r["dd_is"], r["dd_oos"],
            r["negative_cells"], r["cells"],
            ", ".join(r["negative_list"]) if r["negative_list"] else "none"))
    lines += ["", "## per-cell", "", "| cell | " + " | ".join(
        "%s:%d" % (nm, mb) for nm, _ in BOOKS for mb in HTF_MB) + " |",
        "|---|" + "---:|" * (len(BOOKS) * len(HTF_MB))]
    for c in allc:
        lines.append("| %s | " % c + " | ".join(
            "%.1f" % cells[c][f"{nm}:{mb}"] for nm, _ in BOOKS for mb in HTF_MB) + " |")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    P()
    P("wrote %s and %s" % (OUT_MD.name, OUT_JSON.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())