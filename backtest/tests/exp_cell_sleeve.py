"""exp_cell_sleeve - if 58 OOS trades cannot be a book, what SIZE can they be?

THE PROBLEM TWO EXPERIMENTS HAVE NOW PRODUCED
=============================================
CELL_GATE_NOT_A_BOOK.md: gating the cell gives 144 IS / 58 OOS trades. Too few
to size a book. Gating also made in-sample drawdown WORSE (25.2R vs 13.4R),
because the cell's drawdowns cluster in time and the rest of the book was
interleaved between them.

exp_cell_filter.py: adding the cell as a permission on top of the whole book
loses out of sample at every persist setting. persist=5 buys +28.8R OOS for
-14.0R IS, which is the era-split pattern this repo has now seen eight times.

So neither direction works as a wholesale change. What is left is the boring
question the owner actually asked, which is about SIZE rather than direction:
if a share of the book went to the cell, what would the drawdown be?

This is NOT a backtest of a new book. It is arithmetic on two already-measured
equity curves, and it is treated as arithmetic: nothing is re-simulated, and no
new number is invented.

WHY SIZE IS THE RIGHT QUESTION AND NOT "WHICH BOOK"
===================================================
The gate measured 58 OOS trades at +37.6R. That is real and outlier-clean, but it
cannot be sized alone. The same trades at reduced weight are not a new strategy -
they are the same trades with a position size, which is exactly the decision an
owner with a drawdown budget makes, and it is reversible by arithmetic rather than
by a new pin, so it can be discussed before anything is measured.

WHAT THIS DELIBERATELY DOES NOT DO
=================================
It does not claim a blend is better, and it does not pretend to produce a
smaller book. A blend that never removes a trade is a sensitivity analysis, not a
candidate. Reading the output as "w=0.5 is a book" would be the exact error that
made the first version of exp_cell_filter.py measure -392R: a shape that looks
like a union and is not one. See the notes at the bottom of this file and
CELL_GATE_NOT_A_BOOK.md.

Run:  cd backtest/tests
      python -u exp_cell_sleeve.py
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
OUT_JSON = Path(__file__).parent / "_cell_sleeve.json"
OUT_MD = Path(__file__).parent / "_cell_sleeve.md"

WEIGHTS = (0.0, 0.15, 0.25, 0.35, 0.50, 0.75, 1.0)


def monthly(rs, dates):
    m = {}
    for r, d in zip(rs, dates):
        key = str(d)[:7]
        m[key] = m.get(key, 0.0) + r
    return m


def curve_stats(monthly_r):
    keys = sorted(monthly_r)
    eq = peak = 0.0
    mdd = 0.0
    dur = best_dur = 0
    ui = 0.0
    for k in keys:
        eq += monthly_r[k]
        peak = max(peak, eq)
        dd = peak - eq
        if dd > 1e-9:
            dur += 1
        else:
            dur = 0
        mdd = max(mdd, dd)
        best_dur = max(best_dur, dur)
        ui += (peak - eq) ** 2
    ulcer = (ui / max(1, len(keys))) ** 0.5
    return {"net": round(sum(monthly_r.values()), 2), "months": len(keys),
            "max_dd": round(mdd, 2), "max_dd_dur": best_dur, "ulcer": round(ulcer, 2)}


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, net_r, get_swings
    from exp_signal_metrics import load_era
    from exp_full_metrics import compute
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()
    cfg = EXPERIMENTS[BOOK]
    base = {**BP, **cfg["params"]}
    base.setdefault("exp_partial_r", 0.0)

    print("=" * 100)
    print("CELL SENSITIVITY - how much of the book rests on the gated cell")
    print("=" * 100)
    print("arithmetic on two already-measured curves. nothing is re-simulated.\n")

    report = {}
    for era in ("is", "oos"):
        d = load_era(era)
        sw = get_swings(d, cfg.get("swing") or "sw10")

        def run(mode):
            p = dict(base)
            p["mode"] = mode
            out = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
            tr = [t for t in out["ltf_trades"] if t.get("outcome") != "open"]
            rs = [net_r([t]) for t in tr]
            return tr, rs, compute(rs, [t.get("entry_date", "") for t in tr])

        ship_tr, ship_rs, ship_m = run("atr_high")
        gate_tr, gate_rs, gate_m = run(GATE)

        print("-" * 100)
        print(era.upper())
        print("-" * 100)
        print("   whole book   n=%3d net %+7.1f dd %5.1f dd_dur %2s ulcer %6.2f streak %2s"
              % (ship_m["n"], ship_m["net"], ship_m["max_dd"], ship_m.get("dd_dur"),
                 ship_m["ulcer"], ship_m.get("max_streak")))
        print("   gated cell   n=%3d net %+7.1f dd %5.1f dd_dur %2s ulcer %6.2f streak %2s"
              % (gate_m["n"], gate_m["net"], gate_m["max_dd"], gate_m.get("dd_dur"),
                 gate_m["ulcer"], gate_m.get("max_streak")))

        ms = monthly(ship_rs, [t.get("entry_date", "") for t in ship_tr])
        mc = monthly(gate_rs, [t.get("entry_date", "") for t in gate_tr])
        keys = sorted(set(ms) | set(mc))
        xs = [mc.get(k, 0.0) for k in keys]
        ys = [ms.get(k, 0.0) for k in keys]
        n = len(keys)
        mx, my = sum(xs) / n, sum(ys) / n
        cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / n
        vx = sum((x - mx) ** 2 for x in xs) / n
        vy = sum((y - my) ** 2 for y in ys) / n
        corr = cov / (vx ** 0.5 * vy ** 0.5) if vx > 0 and vy > 0 else 0.0
        print("   monthly correlation, cell vs whole book: %.3f  (%d months)" % (corr, n))

        print()
        print("   %-8s %9s %9s %9s %9s" % ("weight", "net", "max_dd", "dd_dur", "ulcer"))
        rows = []
        for w in WEIGHTS:
            blend = {k: (w * mc.get(k, 0.0)) + (1 - w) * ms.get(k, 0.0) for k in keys}
            st = curve_stats(blend)
            st["w"] = w
            rows.append(st)
            print("   %-8.2f %9.1f %9.1f %9d %9.2f" % (w, st["net"], st["max_dd"],
                                                      st["max_dd_dur"], st["ulcer"]))
        report[era] = {"ship": ship_m, "gate": gate_m, "corr": round(corr, 3), "rows": rows}
        print()

    print("=" * 100)
    print("READ THIS BEFORE QUOTING ANY NUMBER ABOVE")
    print("=" * 100)
    print("w=0.00 and w=1.00 are BOTH the whole book, because the blend never")
    print("removes a trade - it scales the cell's contribution and keeps everything")
    print("else at full size. So this table answers 'how much of the book's return")
    print("sits in the cell', which is a real question. It does NOT answer 'what")
    print("does a smaller book look like'.")
    print()
    print("A genuinely smaller book would mean re-running the engine with fewer")
    print("trades. That is a new book, and a new book needs both eras and a pin.")
    print("This does not supply one and is not proposing one.")
    print()
    print("The correlation line is the number that decides whether sleeve sizing is")
    print("even free. Near +1 the cell draws down with the rest and sizing buys")
    print("nothing; near 0 it buys diversification at no cost. That is an owner")
    print("decision about a drawdown budget, and the rule for those decisions is")
    print("already written in EQUITY_LENS_EXT_AND_NOHALT.md.")

    OUT_JSON.write_text(json.dumps({"book": BOOK, "report": report}, indent=2) + "\n",
                        encoding="utf-8")
    lines = ["# cell sensitivity - %s" % BOOK, "",
             "How much of the book's monthly return sits in the gated cell.",
             "w=0.00 and w=1.00 are both the whole book; this is a blend curve,",
             "not a candidate.", "",
             "| era | metric | " + " | ".join("w=%.2f" % w for w in WEIGHTS) + " |",
             "|---|---|" + "|".join(["---:"] * len(WEIGHTS)) + "|"]
    for era in ("is", "oos"):
        for k in ("net", "max_dd", "max_dd_dur", "ulcer"):
            vals = [r[k] for r in report[era]["rows"]]
            lines.append("| %s | %s | %s |" % (era.upper(), k, " | ".join("%.2f" % v for v in vals)))
        lines.append("| %s | corr | %.3f |" % (era.upper(), report[era]["corr"]) +
                     " |" * (len(WEIGHTS) - 1))
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nwrote %s and %s" % (OUT_MD.name, OUT_JSON.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())