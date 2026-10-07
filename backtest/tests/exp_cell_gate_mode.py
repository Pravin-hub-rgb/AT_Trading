"""exp_cell_gate_mode - trade ONLY the measured cell, as a gate not a router.

THE BUG IN THE FIRST VERSION, WHICH IS THE POINT OF THIS FILE
============================================================
exp_best_cell_mode.py added mode="chop_hi_atr_lo" and then reported

    MISMATCH - mode is not the rule we measured
    IS: 528 trades, 75 in the target cell

That check was right and the mode was wrong. Every branch in the regime router
is "decisive else flip", so a rule of the form `use = "decisive" if CELL else
"flip"` can never be a subset of CELL - it also admits everything routed to
flip. The check in step 1 was not decoration: it caught that the code did not
implement the measurement, before any of its numbers were read as a result.

exp_mltf_decompose.py then ruled out the other explanation (that exp_mltf was
hiding part of the set) by measuring it: exp_mltf on and off produce identical
trade counts at both max_positions settings this book uses, 528/528 IS and
311/294 OOS. The layer below the regime filter is not the story.

So the fix is a rule of a different shape. `chop_hi_atr_lo_gate` skips any signal
outside the cell and takes the rest as decisive. That is genuinely "trade the
cell", and it can be checked for targeting instead of merely asserted.

WHAT THIS IS FOR, GIVEN THE CELL PASSED THE OUTLIER BAR
=======================================================
The cell survived exp_best_cell_lens.py: profitable in both eras with its single
largest trade removed (+83.4R IS, +83.4R OOS) and with its top three removed
(+41.3R / +45.6R), at max DD 7.6R / 4.7R against 13.4R / 11.9R for the book.
That is the bar every routing arm in exp_mode_decide.py failed. So the cell is
worth trading on its own terms, and the only open question is how much of it
survives being the WHOLE book.

A 75-trade IS cell is thin. If it is also thin after the gate, the answer is
that this is a sleeve, not a book, and the honest output is a note saying so
rather than a pinned registry entry.

Run:  cd backtest/tests
      python -u exp_cell_gate_mode.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

BOOK = "fsent_champ_long"
GATE = "chop_hi_atr_lo_gate"
OUT_JSON = Path(__file__).parent / "_cell_gate_mode.json"
OUT_MD = Path(__file__).parent / "_cell_gate_mode.md"


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

    data, sw = {}, {}
    for era in ("is", "oos"):
        data[era] = load_era(era)
        sw[era] = get_swings(data[era], cfg.get("swing") or "sw10")

    def run(era, mode):
        p = dict(base)
        p["mode"] = mode
        out = sim(data[era]["c1h"], sw[era], data[era]["c15"], data[era]["sw15"],
                  fine_ltf=data[era]["fine"], **p)
        tr = [t for t in out["ltf_trades"] if t.get("outcome") != "open"]
        rs = [net_r([t]) for t in tr]
        m = compute(rs, [t.get("entry_date", "") for t in tr])
        return tr, m, rs

    print("=" * 100)
    print("CELL GATE MODE - %r on %s" % (GATE, BOOK))
    print("=" * 100)
    print("gate: take a trade ONLY where chop>%s AND atrp<%s, and only decisive."
          % (c_thr, a_thr))
    print("this is the cell exp_best_cell_lens.py measured. Thresholds are the")
    print("book's own, unchanged - no threshold is being fitted.\n")

    ship, gated, report = {}, {}, {}
    for era in ("is", "oos"):
        rows, _, _, _ = joint_regime(data[era])
        lut = {r["ts"]: r for r in rows}
        ship[era] = run(era, "atr_high")
        gated[era] = run(era, GATE)
        tr, m, rs = gated[era]

        ncell = 0
        for t in tr:
            r = lut.get(int(t["entry_ts"]) - 900)
            if r and r["ch"] > c_thr and r["atrp"] < a_thr:
                ncell += 1

        print("-" * 100)
        print(era.upper())
        print("-" * 100)
        sm = ship[era][1]
        print("   shipping  n=%4d net %+8.1f dd %5.1f  mean %+.2f"
              % (sm["n"], sm["net"], sm.get("max_dd", 0), sm["net"] / max(1, sm["n"])))
        print("   gated     n=%4d net %+8.1f dd %5.1f  mean %+.2f"
              % (m["n"], m["net"], m.get("max_dd", 0), m["net"] / max(1, m["n"])))
        print("   -> %d of %d gated trades are in the target cell (%.1f%%)  %s"
              % (ncell, m["n"], 100.0 * ncell / max(1, m["n"]),
                 "TARGETING OK" if ncell == m["n"] else "STILL MISMATCH"))
        print("   share of shipping book: %.1f%% of trades, %.1f%% of net"
              % (100.0 * m["n"] / sm["n"], 100.0 * m["net"] / sm["net"]))
        report[era] = {"ship": {k: sm.get(k) for k in
                                ("n", "net", "max_dd", "ulcer", "sortino", "pf",
                                 "pos_month_pct", "worst_month")},
                       "gated": {k: m.get(k) for k in
                                 ("n", "net", "max_dd", "ulcer", "sortino", "pf",
                                  "pos_month_pct", "worst_month")},
                       "in_cell": ncell, "net": round(m["net"], 2), "n_trades": m["n"],
                       "top": round(sorted(rs, reverse=True)[0], 3) if rs else None,
                       "without_top": round(sum(sorted(rs, reverse=True)[1:]), 2) if rs else None,
                       "without_top3": round(sum(sorted(rs, reverse=True)[3:]), 2) if rs else None}

    print()
    print("=" * 100)
    print("OUTLIER BAR - same test that closed every arm in exp_mode_decide.py")
    print("=" * 100)
    ok = True
    for era in ("is", "oos"):
        r = report[era]
        print("   %s  n=%d net %+.1f | largest %+.2fR | without it %+.1fR | without top3 %+.1fR"
              % (era.upper(), r["n_trades"], r["net"], r["top"], r["without_top"], r["without_top3"]))
        if r["without_top"] <= 0:
            ok = False
    print("   survives in both eras: %s" % ("YES" if ok else "NO"))

    print()
    print("=" * 100)
    print("VERDICT")
    print("=" * 100)
    is_n, oos_n = report["is"]["n_trades"], report["oos"]["n_trades"]
    is_net, oos_net = report["is"]["net"], report["oos"]["net"]
    print("gated cell as a standalone book: IS %d trades / %+.1fR, OOS %d trades / %+.1fR"
          % (is_n, is_net, oos_n, oos_net))
    print("outlier bar: %s" % ("passes" if ok else "FAILS"))
    if oos_n < 60:
        print()
        print("The OOS cell holds %d trades. That is too few to size a book from, and" % oos_n)
        print("the era gap is the reason: the same gate yields %d IS trades." % is_n)
        print("This is a SLEEVE, not a book. Registering it as a book would mean")
        print("shipping a 40-trade out-of-sample record.")
        print()
        print("What IS defensible: the cell is the book's best mean-R region and it")
        print("survives its outlier bar, so it is worth measuring further as a filter")
        print("on the existing book rather than as a replacement for it.")
    print("Nothing registered, no pins changed, shipping config untouched.")

    OUT_JSON.write_text(json.dumps({"book": BOOK, "gate": GATE, "report": report}, indent=2) + "\n",
                        encoding="utf-8")
    lines = ["# cell gate mode - %r on %s (post-C17)" % (GATE, BOOK), "",
             "Take only chop>%s AND atrp<%s. Thresholds are the book's own." % (c_thr, a_thr), "",
             "| metric | IS ship | IS gated | OOS ship | OOS gated |",
             "|---|---:|---:|---:|---:|"]
    for k in ("n", "net", "max_dd", "ulcer", "sortino", "pf", "pos_month_pct", "worst_month"):
        v = [report[e]["ship"].get(k) for e in ("is", "oos")]
        v += [report[e]["gated"].get(k) for e in ("is", "oos")]
        if any(x is None for x in v):
            continue
        lines.append("| %s | %.2f | %.2f | %.2f | %.2f |" % (k, *v))
    lines += ["", "| era | n | net | largest trade | without top | without top3 |",
              "|---|---:|---:|---:|---:|---:|"]
    for era in ("is", "oos"):
        r = report[era]
        lines.append("| %s | %d | %.1f | %.2f | %.1f | %.1f |" % (
            era.upper(), r["n_trades"], r["net"], r["top"], r["without_top"], r["without_top3"]))
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nwrote %s and %s" % (OUT_MD.name, OUT_JSON.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())