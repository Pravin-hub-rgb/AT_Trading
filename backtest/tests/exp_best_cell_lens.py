"""exp_best_cell_lens - full metrics for the chop_HIGH/atr_low cell.

WHY THIS FILE, GIVEN exp_mode_regime.py ALREADY MEASURED IT
=============================================================
It did, and the finding was the whole reason this exists: fsent_champ_long does
its best work in the joint cell where chop reads HIGH and atr_pct reads LOW, and
the current router sends that cell to flip because it picks the branch on
atr_high alone. But that harness reported n, net R, win % and mean R. The
question now is whether that cell would survive being run as a book, which needs
the fields a regime filter is judged on and a mean R cannot tell you: drawdown,
drawdown DURATION, ulcer, sortino, worst month, longest losing run. A cell with
a better mean R and a 2x longer drawdown is not a book.

THE HONEST PRIOR, BEFORE ANY OF IT IS COMPUTED
==============================================
From exp_mode_decide.py and exp_mode_autopsy.py, both already committed:
  - routing on chop alone produces arms that are ahead on net R and are
    single-trade artifacts
  - ch=50 buys 41R of which one trade supplies 46R, and doubles IS drawdown
  - two separate proposals in this repo rest on the same 2.2-day long
So the prior on "this cell is a good standalone book" is NOT good, and the point
of computing the full lens is to find out which field gives it away. If the
answer turns out to be "nothing, it is fine", that is a real answer too and gets
recorded the same way.

WHAT A WINNER WOULD HAVE TO CLEAR
=================================
Beyond both eras, this has to clear the outlier bar the other two sweeps failed:
the cell must still be worth something with its single largest trade removed. A
cell of 75 IS trades at +1.76R mean does not have room to hide a +18R trade, so
that check is the whole test.

Run:  cd backtest/tests
      python -u exp_best_cell_lens.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

BOOK = "fsent_champ_long"
OUT_JSON = Path(__file__).parent / "_best_cell_lens.json"
OUT_MD = Path(__file__).parent / "_best_cell_lens.md"

LENS = ("net", "max_dd", "max_dd_dur", "ulcer", "sortino", "calmar", "max_uw",
        "pos_month_pct", "worst_month")


def metrics(rs, dates):
    from exp_full_metrics import compute
    return compute(rs, dates)


def pct(a, b):
    if not b:
        return 0.0
    return 100.0 * a / b


def main() -> int:
    import bisect as bs
    from exp_tf_family import build_family_module
    from run_experiment import BP, net_r, get_swings
    from exp_signal_metrics import load_era
    from experiment_registry import EXPERIMENTS
    from exp_mode_regime import joint_regime

    sim = build_family_module()
    cfg = EXPERIMENTS[BOOK]
    base = {**BP, **cfg["params"]}
    base.setdefault("exp_partial_r", 0.0)
    a_thr = base["atr_high_thresh"]
    c_thr = base["chop_thresh"]

    print("=" * 100)
    print("BEST-CELL LENS - %s, cell chop_HIGH / atr_low" % BOOK)
    print("=" * 100)
    print("this is the book's top mean-R cell in both eras (exp_mode_regime.py).")
    print("question: would it survive as a book, and would it survive one less big trade.")
    print()

    cells = {}
    for era in ("is", "oos"):
        d = load_era(era)
        sw = get_swings(d, cfg.get("swing") or "sw10")
        out = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=d["fine"], **base)
        trades = [t for t in out["ltf_trades"] if t.get("outcome") != "open"]

        rows, _, _, _ = joint_regime(d)
        lut = {r["ts"]: r for r in rows}
        sel, rest = [], []
        for t in trades:
            r = lut.get(int(t["entry_ts"]) - 900)
            cell = ("chop_HIGH" if (r and r["ch"] > c_thr) else "chop_low")
            cell += " / " + ("atr_HIGH" if (r and r["atrp"] > a_thr) else "atr_low")
            (sel if cell == "chop_HIGH / atr_low" else rest).append(t)

        def lens_of(ts_list):
            rs = [net_r([t]) for t in ts_list]
            ds = [t.get("entry_date", "") for t in ts_list]
            m = metrics(rs, ds)
            return m, rs

        m_cell, rs_cell = lens_of(sel)
        m_all, rs_all = lens_of(trades)

        cells[era] = {"cell_n": m_cell["n"], "rest_n": m_all["n"] - m_cell["n"],
                      "cell": m_cell, "book": m_all,
                      "rs_cell": rs_cell, "rs_book": rs_all}

        print("-" * 100)
        print("%s" % era.upper())
        print("-" * 100)
        print("%-24s %16s %16s %14s" % ("metric", "CELL only", "whole book", "cell share"))
        for k in LENS:
            cv = m_cell.get(k)
            bv = m_all.get(k)
            if cv is None or bv is None:
                continue
            if k in ("max_dd", "max_dd_dur", "max_uw", "worst_month"):
                sh = "-"
            else:
                sh = "%5.1f%%" % pct(cv, bv)
            print("%-24s %16.2f %16.2f %14s" % (k, cv, bv, sh))
        print("%-24s %16d %16d %14s" % ("n", m_cell["n"], m_all["n"],
                                        "%5.1f%%" % pct(m_cell["n"], m_all["n"])))
        print("%-24s %16s %16s %14s" % ("mean R", "%+.2f" % (m_cell["net"] / max(1, m_cell["n"])),
                                        "%+.2f" % (m_all["net"] / max(1, m_all["n"])), ""))

    # ------------------------------------------------------------------
    # The outlier check, which is the actual test.
    # ------------------------------------------------------------------
    print()
    print("=" * 100)
    print("OUTLIER CHECK - the cell with its single largest trade removed")
    print("=" * 100)
    verdict = True
    for era in ("is", "oos"):
        rs = sorted(cells[era]["rs_cell"], reverse=True)
        top = rs[0]
        rest = sum(rs[1:])
        n = len(rs)
        print("\n%s  n=%d  net %+.2fR  mean %+.2fR" % (era.upper(), n, sum(rs), sum(rs) / n))
        print("   largest trade %+.3fR = %.0f%% of the cell's net" % (top, pct(top, sum(rs))))
        print("   without it     %+.2fR  mean %+.2fR  (%d trades)"
              % (rest, rest / (n - 1), n - 1))
        print("   without the top THREE %+.2fR  mean %+.2fR"
              % (sum(rs[3:]), sum(rs[3:]) / (n - 3)))
        survives = rest > 0
        print("   -> cell still profitable without its best trade: %s" % ("YES" if survives else "NO"))
        if not survives:
            verdict = False
        cells[era]["top_trade"] = round(top, 3)
        cells[era]["without_top"] = round(rest, 2)

    print()
    print("=" * 100)
    print("VERDICT")
    print("=" * 100)
    print("profitable in both eras without its best trade: %s" % ("YES" if verdict else "NO"))
    if not verdict:
        print("That is the same failure as ch=55 (two trades at 21R each) and ch=50")
        print("(one trade supplying 46R). A cell that dies when its best trade is")
        print("removed is a cell with a mean, not a book.")
    print("See exp_mode_decide.py for why every routing arm built on this cell already")
    print("failed the same check, and why a new MODE may still be worth building.")

    for era in cells:
        cells[era] = {k: v for k, v in cells[era].items() if k != "rs_cell"}

    OUT_JSON.write_text(json.dumps({"book": BOOK, "cells": cells,
                                    "thr": {"atr": a_thr, "chop": c_thr}}, indent=2) + "\n",
                        encoding="utf-8")
    lines = [
        "# best-cell lens - %s, chop_HIGH / atr_low (post-C17)" % BOOK,
        "",
        "The book's top mean-R joint cell in both eras, measured alone.",
        "",
        "| metric | IS cell | IS book | OOS cell | OOS book |",
        "|---|---:|---:|---:|---:|",
    ]
    for k in ("n",) + LENS:
        vals = []
        for era in ("is", "oos"):
            vals += [cells[era]["cell"].get(k), cells[era]["book"].get(k)]
        if any(v is None for v in vals):
            continue
        lines.append("| %s | %.2f | %.2f | %.2f | %.2f |" % (k, *vals))
    lines += [
        "",
        "## Outlier check",
        "",
        "| era | n | net | mean R | largest trade | net without it |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for era in ("is", "oos"):
        c = cells[era]
        lines.append("| %s | %d | %.2f | %.2f | %.2f | %.2f |" % (
            era.upper(), c["cell_n"], c["cell"]["net"],
            c["cell"]["net"] / max(1, c["cell_n"]), c["top_trade"], c["without_top"]))
    lines += ["", "Shipping parameters unchanged; this is an analysis of an existing cell."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nwrote %s and %s" % (OUT_MD.name, OUT_JSON.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())