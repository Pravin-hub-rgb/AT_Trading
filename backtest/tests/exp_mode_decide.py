"""exp_mode_decide - route on chop, route on atr, or route on both?

PRECEDES THIS, AND WHAT IT ALREADY SETTLED
==========================================
exp_mode_regime.py measured what the two indicators say about the same bars, and
what fsent_champ_long earns in each joint cell. Two results came out of it, and
they are the reason this harness exists:

  1. They are not the same variable. They disagree on 24.6% of IS bars and
     35.5% of OOS bars. chop is the CHOP index (direction efficiency, 1h);
     atr_high is ATR% of price (bar size, 15m). Neither is a proxy for the
     other, so "the book already routes on this" was never a true answer.

  2. The cell that both indicators disagree about, in the direction that
     matters, is the book's BEST cell - in both eras:

        chop_HIGH / atr_low   IS  n=75  +132.0R  mean +1.76
                              OOS n=42  +109.5R  mean +2.61
        chop_low  / atr_HIGH   IS  n=24   +12.6R  mean +0.52
                              OOS n=70   +30.8R  mean +0.44

     The book routes BOTH of those to the same branch, because that branch is
     chosen on atr_high alone and both cells read as "low vol". So the router
     is currently treating its best and its worst disagreement cell identically.
     That is the specific thing worth fixing, and it is a routing bug rather
     than a missing feature.

SO THIS ASKS THE DECISION QUESTION
==================================
Does routing on chop beat routing on atr, and is there a combination that keeps
the good cell and drops the bad one?

Arms, all measured from the same book with only `mode` moving:

  atr_high        the shipping book - decisive when bars are big
  decisive_vs_flip_chop  the same branch pair, decided by chop instead
    with a chop_thresh grid, because "route on chop" is not one config
  chop_or_atr_low / chop_and_atr_low / soft_chop
    the combinations, so the answer is not "chop or nothing"

The regime filter is NOT a free parameter to maximise. Two guards, both of which
this harness enforces on itself:

  - A winner is only a winner if it is not worse in EITHER era. A value that
    buys IS with OOS is the era-split pattern this repo has now seen seven
    times, and it is a reason to keep shipping.
  - Trade-count and net-R are reported together with mean R and DD, because a
    higher net with a mean that collapses is one trade, not an improvement.

Run:  cd backtest/tests
      python -u exp_mode_decide.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

BOOK = "fsent_champ_long"
OUT_JSON = Path(__file__).parent / "_mode_decide.json"
OUT_MD = Path(__file__).parent / "_mode_decide.md"

# (arm name, mode, chop_thresh or None to keep the book's own value)
ARMS = [("atr_high (shipping)", "atr_high", None)]
ARMS += [("decisive_vs_flip_chop ch=%g" % c, "decisive_vs_flip_chop", c)
         for c in (30, 40, 50, 55, 58, 62, 70)]
ARMS += [
    ("chop_or_atr_low", "chop_or_atr_low", None),
    ("chop_and_atr_low", "chop_and_atr_low", None),
    ("soft_chop", "soft_chop", None),
]


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

    data, sw = {}, {}
    for era in ("is", "oos"):
        data[era] = load_era(era)
        sw[era] = get_swings(data[era], cfg.get("swing") or "sw10")

    def run(era, p):
        out = sim(data[era]["c1h"], sw[era], data[era]["c15"], data[era]["sw15"],
                  fine_ltf=data[era]["fine"], **p)
        tr = [t for t in out["ltf_trades"] if t.get("outcome") != "open"]
        m = compute([net_r([t]) for t in tr], [t.get("entry_date", "") for t in tr])
        return m

    print("=" * 104)
    print("MODE DECISION - %s, post-C17" % BOOK)
    print("=" * 104)
    print("only `mode` moves. Book, swing, entry logic, risk knobs all fixed.\n")

    rows = []
    for name, mode, cthr in ARMS:
        p = dict(base)
        p["mode"] = mode
        if cthr is not None:
            p["chop_thresh"] = cthr
        rec = {"arm": name, "mode": mode, "chop_thresh": p["chop_thresh"]}
        for era in ("is", "oos"):
            m = run(era, p)
            rec[era] = {"n": m["n"], "net": round(m["net"], 2),
                        "dd": round(m.get("max_dd", 0.0), 2)}
        rows.append(rec)

    ship = next(r for r in rows if r["mode"] == "atr_high")
    print("%-28s %-24s %18s %18s %16s" % ("arm", "mode / chop_thresh",
                                          "IS n / net / dd", "OOS n / net / dd", "mean R IS/OOS"))
    for r in rows:
        mi = r["is"]["net"] / r["is"]["n"] if r["is"]["n"] else 0
        mo = r["oos"]["net"] / r["oos"]["n"] if r["oos"]["n"] else 0
        print("%-28s %-24s %18s %18s %16s"
              % (r["arm"][:28], "%s / %s" % (r["mode"], r["chop_thresh"]),
                 "%d / %+.1f / %.1f" % (r["is"]["n"], r["is"]["net"], r["is"]["dd"]),
                 "%d / %+.1f / %.1f" % (r["oos"]["n"], r["oos"]["net"], r["oos"]["dd"]),
                 "%+.2f / %+.2f" % (mi, mo)))

    print()
    print("delta vs shipping (atr_high):")
    print("%-28s %14s %14s   verdict" % ("arm", "d IS", "d OOS"))
    beaten = []
    for r in rows:
        if r is ship:
            continue
        di = r["is"]["net"] - ship["is"]["net"]
        do = r["oos"]["net"] - ship["oos"]["net"]
        if di >= 0 and do >= 0:
            v = "NOT WORSE IN EITHER ERA"
            beaten.append(r)
        elif di > 0 and do < 0:
            v = "era-split (IS for, OOS against)"
        else:
            v = "worse"
        print("%-28s %+14.1f %+14.1f   %s" % (r["arm"][:28], di, do, v))

    print()
    if beaten:
        print("ARMS NOT WORSE IN EITHER ERA - the only candidates:")
        for r in beaten:
            print("   %-28s IS %+8.1f (n=%d, dd %.1f)   OOS %+8.1f (n=%d, dd %.1f)"
                  % (r["arm"], r["is"]["net"], r["is"]["n"], r["is"]["dd"],
                     r["oos"]["net"], r["oos"]["n"], r["oos"]["dd"]))
    else:
        print("No arm beats shipping in both eras. The router is not the problem.")

    # Same guard as the persist sweep: if an arm wins on one trade, say so.
    print()
    print("OUTLIER CHECK on any candidate that is ahead in both eras:")
    if not beaten:
        print("   nothing to check - no candidate.")
    for r in beaten:
        di = r["is"]["net"] - ship["is"]["net"]
        do = r["oos"]["net"] - ship["oos"]["net"]
        p = dict(base)
        p["mode"] = r["mode"]
        for era, d in (("is", di), ("oos", do)):
            n = r[era]["n"] - ship[era]["n"]
            per = d / n if n else float("inf")
            flag = "  <-- carried by %+d trades" % n if abs(n) <= 25 else ""
            print("   %-28s %s advantage %+6.1fR over %+4d trades = %+6.2fR each%s"
                  % (r["arm"], era.upper(), d, n, per, flag))

    OUT_JSON.write_text(json.dumps({"book": BOOK, "rows": rows}, indent=2) + "\n",
                        encoding="utf-8")
    lines = [
        "# mode decision - %s (post-C17)" % BOOK,
        "",
        "Only `mode` moves; everything else fixed. Shipping is `atr_high`.",
        "",
        "| arm | mode | chop_thresh | IS n | IS net | IS dd | OOS n | OOS net | OOS dd |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        star = " **" if r is ship else ""
        lines.append("| %s%s | %s | %s | %d | %.1f | %.1f | %d | %.1f | %.1f |" % (
            r["arm"], star, r["mode"], r["chop_thresh"], r["is"]["n"], r["is"]["net"],
            r["is"]["dd"], r["oos"]["n"], r["oos"]["net"], r["oos"]["dd"]))
    lines += ["", "Shipping arm marked **."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nwrote %s and %s" % (OUT_MD.name, OUT_JSON.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())