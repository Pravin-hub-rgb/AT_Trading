"""Apply the pre-registered survivor rule to the 2D grid - computed, not eyeballed.

Separated from `exp_range_pos_width.py` so the rule is applied in code rather
than in the author's head, which is the whole point of writing it down first.

The rule, fixed before the run:
  a comparison SURVIVES only if, across all 4 book cells (champion/utcsat x
  IS/OOS), the ordering has the SAME SIGN in both eras on the trimmed mean,
  is monotone in >=3 of 4 cells, and both extreme cells have n>=15.

Comparisons tested (all read off the produced grid, none invented here):
  A) high position vs low position, at each width bin
  B) mid position vs both edges, at each width bin
  C) wide vs tight width, at each position bin
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "backtest/tests/_range_pos_width.json"
OUT = ROOT / "backtest/tests/_range_pos_width_verdict.json"
CELLS = (("is", "champion"), ("is", "utcsat"),
         ("oos", "champion"), ("oos", "utcsat"))


def get(c, pb, wb):
    return c.get(f"pos{pb}_w{wb}")


def agg(c, pbs, wb):
    """Trimmed-mean-weighted average of several position bins at one width.
    Returns (mean_trimmed, total_n) or (None, 0) if no cell qualifies."""
    vals, ns = [], []
    for pb in pbs:
        g = get(c, pb, wb)
        if g and g["n"] >= 15:
            vals.append(g["trimmed"])
            ns.append(g["n"])
    if not vals:
        return None, 0
    return sum(vals) / len(vals), sum(ns)


def test(books, windows, label, picker):
    """Run one comparison across all 4 cells. Returns the verdict record, or
    None if ANY cell could not be scored (so it is excluded rather than
    silently counted as a failure)."""
    per = []
    for era, lane in CELLS:
        c = books[f"{era}/{lane}"][windows]   # index the WINDOW sub-dict
        res = picker(c)
        if res is None or res[0] is None:
            return None
        d, na, nb = res
        per.append({"era": era, "lane": lane, "diff": round(d, 3),
                    "n_a": na, "n_b": nb, "positive": d > 0})
    sig_is = sum(1 for p in per if p["era"] == "is" and p["positive"])
    sig_oos = sum(1 for p in per if p["era"] == "oos" and p["positive"])
    mono = sum(1 for p in per if p["positive"])
    min_n = min(min(p["n_a"], p["n_b"]) for p in per)
    ok = (sig_is == 2 and sig_oos == 2 and mono >= 3 and min_n >= 15)
    return {"window": windows, "label": label, "per_cell": per,
            "is_sign": f"{sig_is}/2", "oos_sign": f"{sig_oos}/2",
            "monotone": f"{mono}/4", "min_n": min_n,
            "verdict": ("SURVIVOR" if ok else "null")}


def mk_pair_picker(wb):
    """high position minus low position, at one width bin."""
    def pick(c):
        hi, lo = get(c, 3, wb), get(c, 0, wb)
        if not hi or not lo or min(hi["n"], lo["n"]) < 15:
            return (None, 0, 0)
        return (hi["trimmed"] - lo["trimmed"], lo["n"], hi["n"])
    return pick


def mk_edges_picker(wb):
    """both position edges minus the two middle bins, at one width bin."""
    def pick(c):
        e, m = agg(c, (0, 3), wb), agg(c, (1, 2), wb)
        if e is None or m is None or e[0] is None or m[0] is None \
                or m[1] < 15 or e[1] < 15:
            return (None, 0, 0)
        return (e[0] - m[0], m[1], e[1])
    return pick


def mk_width_picker(pb):
    """wide range minus tight range, at one position bin."""
    def pick(c):
        hi, lo = get(c, pb, 2), get(c, pb, 0)
        if not hi or not lo or min(hi["n"], lo["n"]) < 15:
            return (None, 0, 0)
        return (hi["trimmed"] - lo["trimmed"], lo["n"], hi["n"])
    return pick


def main():
    d = json.loads(SRC.read_text(encoding="utf-8"))
    books = d["books"]
    results = []
    for w in d["windows"]:
        for wb in range(3):
            results.append(test(books, w,
                                f"A) pos75-100 - pos0-25 @width{wb}",
                                mk_pair_picker(wb)))
            results.append(test(books, w,
                                f"B) edges - mid @width{wb}",
                                mk_edges_picker(wb)))
        for pb in range(4):
            results.append(test(books, w,
                                f"C) width2 - width0 @pos{pb}",
                                mk_width_picker(pb)))
    results = [r for r in results if r]
    print(f"{'window':<6} {'comparison':<34} {'IS':>4} {'OOS':>4} "
          f"{'mono':>5} {'minN':>5}  verdict")
    print("-" * 78)
    for r in results:
        mark = f"**{r['verdict']}**" if r["verdict"] == "SURVIVOR" else "null"
        print(f"{r['window']:<6} {r['label']:<34} {r['is_sign']:>4} "
              f"{r['oos_sign']:>4} {r['monotone']:>5} {r['min_n']:>5}  {mark}")
    surv = [r for r in results if r["verdict"] == "SURVIVOR"]
    print("-" * 78)
    print(f"{len(surv)} SURVIVOR(S) out of {len(results)} pre-registered comparisons")
    for s in surv:
        print(f"\n  {s['window']} · {s['label']}")
        for p in s["per_cell"]:
            print(f"    {p['era']:<4} {p['lane']:<9} diff {p['diff']:+.3f} "
                  f"(n {p['n_a']} vs {p['n_b']})")
    OUT.write_text(json.dumps({"results": results,
                               "survivors": len(surv),
                               "tested": len(results)}, indent=2,
                              default=str) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
