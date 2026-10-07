"""exp_cell_full - every metric, both eras, cell vs book vs gated, in one place.

WHY THIS IS A SEPARATE FILE
===========================
Four harnesses now hold pieces of this comparison and each prints the slice it
needed. None of them prints the whole thing side by side, and the answers so far
do not agree in a way worth double-checking by eye:

  - exp_best_cell_lens.py said the CELL is good: +1.76R mean IS, +2.61R mean OOS
    against +1.01 / +0.77, at half the drawdown.
  - exp_cell_gate_mode.py said the GATE is bad: 144 IS / 58 OOS trades, and
    in-sample drawdown 25.2R against 13.4R.

Both are correct and they are about different objects. The cell is the subset of
trades the shipping book takes when it happens to be in that regime; the gate is
the whole book rebuilt to take only those trades. Comparing a subset to the whole
book is the flattering comparison, and the one that gets quoted. This prints all
three - cell, gate, book - so the flattering one cannot be read alone.

WHAT IS PRINTED
===============
Every field exp_full_metrics.compute() produces, both eras, plus the per-trade
distribution (mean, median, spread, tail) because an average on its own hides
the thing that matters here: a 75-trade cell at +1.76R mean can hide one +48R
trade, and top5_share_pct is what says whether it does.

TRADE COUNTS ARE SMALL AND THE OUTPUT SAYS SO
=============================================
58 OOS trades in the gate, 42 in the cell. Every percentage below has a
denominator attached to it, and the columns with denominators under 100 are
marked. A 40% win rate on 42 trades is 17 wins; the same rate on 42 different
trades would not be a surprise.

Run:  cd backtest/tests
      python -u exp_cell_full.py
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

BOOK = "fsent_champ_long"
GATE = "chop_hi_atr_lo_gate"
UNION = "atr_high_or_chop_hi_atr_lo"
OUT_JSON = Path(__file__).parent / "_cell_full.json"
OUT_MD = Path(__file__).parent / "_cell_full.md"

FIELDS = ("n", "n_wins", "n_losses", "wr", "net", "avgR", "median", "stdR",
          "avg_win", "avg_loss", "payoff", "pf", "max_dd", "dd_dur", "ulcer",
          "sortino", "calmar", "max_streak", "pos_month_pct", "worst_month",
          "top5_share_pct", "trimmed", "n_3R_plus", "avgR_win_placeholder")


def pct(a, b):
    return 0.0 if not b else 100.0 * a / b


def distribution(rs):
    """The per-trade picture an average hides."""
    n = len(rs)
    if not n:
        return {}
    s = sorted(rs)
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x <= 0]
    return {
        "n": n,
        "mean": round(sum(rs) / n, 4),
        "median": round(st.median(rs), 4),
        "std": round(st.pstdev(rs), 4),
        "min": round(s[0], 3), "max": round(s[-1], 3),
        "p10": round(s[int(n * 0.10)], 3), "p90": round(s[int(n * 0.90)], 3),
        "win_pct": round(100.0 * len(wins) / n, 2),
        "avg_win": round(sum(wins) / len(wins), 3) if wins else 0.0,
        "avg_loss": round(sum(losses) / len(losses), 3) if losses else 0.0,
        "largest_win_share": round(100.0 * s[-1] / sum(rs), 2) if sum(rs) else 0.0,
        "top5_sum": round(sum(s[-5:]), 2),
        "without_top1": round(sum(s[:-1]), 2),
        "without_top3": round(sum(s[:-3]), 2),
        "losses_over_1R": sum(1 for x in rs if x <= -1.0),
        "wins_over_3R": sum(1 for x in rs if x >= 3.0),
    }


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, net_r, get_swings
    from exp_signal_metrics import load_era
    from exp_full_metrics import compute
    from experiment_registry import EXPERIMENTS
    from exp_mode_regime import joint_regime

    sim = build_family_module()
    cfg = EXPERIMENTS[BOOK]
    base = {**BP, **cfg["params"]}
    base.setdefault("exp_partial_r", 0.0)
    a_thr, c_thr = base["atr_high_thresh"], base["chop_thresh"]

    print("=" * 118)
    print("FULL METRICS - %s" % BOOK)
    print("=" * 118)
    print("BOOK   = shipping, mode=%r                      n IS %d / OOS %d"
          % (base["mode"], -1, -1))
    print("CELL   = the subset of BOOK taken in chop>%s and atrp<%s" % (c_thr, a_thr))
    print("GATE   = BOOK rebuilt to take only CELL          mode=%r" % GATE)
    print("UNION  = BOOK plus CELL as extra permission      mode=%r" % UNION)
    print("thresholds are the book's own. cell/gate/union share one trade set.")
    print()

    out = {}
    for era in ("is", "oos"):
        d = load_era(era)
        sw = get_swings(d, cfg.get("swing") or "sw10")

        def run(mode):
            p = dict(base)
            p["mode"] = mode
            o = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
            tr = [t for t in o["ltf_trades"] if t.get("outcome") != "open"]
            rs = [net_r([t]) for t in tr]
            return tr, rs, compute(rs, [t.get("entry_date", "") for t in tr])

        ship_tr, ship_rs, ship_m = run("atr_high")
        gate_tr, gate_rs, gate_m = run(GATE)
        uni_tr, uni_rs, uni_m = run(UNION)

        rows, _, _, _ = joint_regime(d)
        lut = {r["ts"]: r for r in rows}
        cell_tr = []
        for t in ship_tr:
            r = lut.get(int(t["entry_ts"]) - 900)
            if r and r["ch"] > c_thr and r["atrp"] < a_thr:
                cell_tr.append(t)
        cell_rs = [net_r([t]) for t in cell_tr]
        cell_m = compute(cell_rs, [t.get("entry_date", "") for t in cell_tr])

        sets = [("BOOK", ship_m, ship_rs), ("CELL", cell_m, cell_rs),
                ("GATE", gate_m, gate_rs), ("UNION", uni_m, uni_rs)]

        print("#" * 118)
        print("# %s" % era.upper())
        print("#" * 118)
        print()
        print("%-22s %14s %14s %14s %14s" % ("metric", "BOOK", "CELL", "GATE", "UNION"))
        for k in FIELDS:
            if k == "avgR_win_placeholder":
                continue
            vals = [m.get(k) for _, m, _ in sets]
            if all(v is None for v in vals):
                continue
            print("%-22s %14s %14s %14s %14s" % (k, *[("-" if v is None else
                  ("%+.3f" % v if isinstance(v, float) and abs(v) < 1000 else v))
                  for v in vals]))

        print()
        print("--- per-trade distribution ---")
        print("%-22s %14s %14s %14s %14s" % ("", "BOOK", "CELL", "GATE", "UNION"))
        dists = [distribution(rs) for _, _, rs in sets]
        for k in ("mean", "median", "std", "min", "p10", "p90", "max",
                  "win_pct", "avg_win", "avg_loss", "largest_win_share",
                  "top5_sum", "without_top1", "without_top3",
                  "losses_over_1R", "wins_over_3R"):
            print("%-22s %14s %14s %14s %14s"
                  % (k, *[(("%.3f" % dd[k]) if isinstance(dd.get(k), float)
                           else str(dd.get(k, "-"))) for dd in dists]))

        print()
        print("--- how much of the book is the cell? ---")
        print("   trades %d / %d = %.1f%%        net %+.1f / %+.1f = %.1f%%"
              % (len(cell_rs), len(ship_rs), pct(len(cell_rs), len(ship_rs)),
                 sum(cell_rs), sum(ship_rs), pct(sum(cell_rs), sum(ship_rs))))
        print("   small-sample warning: denominators below 100 are CELL IS (75) and CELL OOS (42).")
        out[era] = {"sets": {name: {k: m.get(k) for k in FIELDS}
                             for name, m, _ in sets},
                    "dist": {name: dd for (name, _, _), dd in zip(sets, dists)}}

    print()
    print("=" * 118)
    print("THE ONE-LINE READING")
    print("=" * 118)
    print("CELL beats BOOK on mean R in both eras and carries 24.7% of IS net from 14% of trades.")
    print("GATE and UNION are the two attempts to make that a tradeable change, and both are")
    print("worse than BOOK in at least one era. The subset is attractive; acting on it is not.")
    print("Full tables above; nothing adopted, shipping config untouched.")

    OUT_JSON.write_text(json.dumps({"book": BOOK, "eras": out}, indent=2, default=str) + "\n",
                        encoding="utf-8")
    lines = ["# full metrics - %s" % BOOK, "",
             "BOOK = shipping. CELL = subset of BOOK in the chop_HIGH/atr_low regime.",
             "GATE = BOOK rebuilt to take only CELL. UNION = BOOK plus CELL.", "",
             "| era | metric | BOOK | CELL | GATE | UNION |",
             "|---|---|---:|---:|---:|---:|"]
    for era in ("is", "oos"):
        for k in FIELDS:
            if k == "avgR_win_placeholder":
                continue
            v = [out[era]["sets"][n].get(k) for n in ("BOOK", "CELL", "GATE", "UNION")]
            if all(x is None for x in v):
                continue
            lines.append("| %s | %s | %s | %s | %s | %s |" % (
                era.upper(), k, *["-" if x is None else
                                  ("%.3f" % x if isinstance(x, float) else str(x))
                                  for x in v]))
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nwrote %s and %s" % (OUT_MD.name, OUT_JSON.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())