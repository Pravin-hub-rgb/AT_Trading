"""exp_dual_book - are the two books a portfolio, or the same trade twice?

THE OBSERVATION THAT PROMPTED THIS
==================================
`fsent_champ_long` and `fsent_sig_full` share **zero trades**. Not "mostly the
same trades" - the permutation test in exp_permute_shipping.py found 0 survivors
in both eras and 100% disjointness. They are two different strategies:

    fsent_champ_long   FS entry on longs, break on shorts, MULTI position
                       IS 528t / +533.4R / DD 13.42      OOS 311t / +239.6R / DD 11.88
    fsent_sig_full     FS entry on shorts, break on longs, max_positions=1
                       IS 234t / +295.8R / DD 10.78      OOS 152t / +194.4R / DD 6.96

Both make money in both eras. That has not been treated as a portfolio question,
and it should have been, because the two numbers are close enough to be one
strategy wearing two hats and far enough apart to be a genuine pair.

WHY IT IS NOT OBVIOUS AND WHY THE OBVIOUS ANSWER IS WRONG
==========================================================
"Tie their R together and the DD falls" is the naive answer and it is
arithmetically true, so it is dangerous. Two books at +239.6R and +194.4R do
produce a bigger total. That proves nothing about whether the second book is
adding anything, because a correlated book also sums higher - it just sums higher
AND falls over at the same time.

The question that decides it is CORRELATION, and specifically the correlation of
MONTHLY returns, because that is what capital experiences:

    corr ~ 0   -> the second book earns in months the first was flat. Free money.
    corr ~ +1  -> it is one book at 1.5x size. No diversification to pay for.

This is the same measurement that killed the cell-as-sleeve proposal in
CELL_THREE_WAYS.md, where the cell was +0.65 correlated with the book and sizing
it bought no diversification. Here the correlation is unmeasured, and the two
books are far more different from each other than a cell was from its parent.

WHAT IS MEASURED
================
  1. Monthly return correlation, both eras
  2. Overlap in TIME even though there is no overlap in trades - do they draw
     down in the same months?
  3. The blend curve at several weights, with max DD, drawdown DURATION, ulcer
     and the longest losing run, both eras
  4. Whether the blend survives removing the top trades - the bar that has
     closed every other proposal in this session
  5. Per-side decomposition, since the two books are mirror images: champ takes
     LONG FS, sig takes SHORT FS. If the combination works, the mechanism should
     be visible in the sides.

WHAT WOULD MAKE THIS WORTH ADOPTING
===================================
A blend whose max drawdown is lower than champion's own while its net is higher,
in BOTH eras, and which survives the outlier bar. Not "higher net" - every arm of
every family this session has cleared that and failed something else.

WHAT THIS IS NOT
================
Not a book, not a registry change. Two registered books are measured for a
relationship that nobody has checked. If the answer is "they are one strategy at
1.5x size", that is worth knowing just as much as the opposite.

Run:  cd backtest/tests
      python -u exp_dual_book.py
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

A = "fsent_champ_long"      # FS long,  multi
B = "fsent_sig_full"        # FS short, single position
WEIGHTS = (0.0, 0.25, 0.50, 0.75, 1.0)   # weight on B
OUT_JSON = Path(__file__).parent / "_dual_book.json"
OUT_MD = Path(__file__).parent / "_dual_book.md"


def monthly(rs, dates):
    m = {}
    for r, d in zip(rs, dates):
        k = str(d)[:7]
        m[k] = m.get(k, 0.0) + r
    return m


def curve(mr):
    keys = sorted(mr)
    eq = peak = 0.0
    mdd = 0.0
    dur = best = 0
    ui = 0.0
    for k in keys:
        eq += mr[k]
        peak = max(peak, eq)
        d = peak - eq
        if d > 1e-9:
            dur += 1
        else:
            dur = 0
        mdd = max(mdd, d)
        best = max(best, dur)
        ui += (peak - eq) ** 2
    return {"net": round(sum(mr.values()), 2), "months": len(keys),
            "max_dd": round(mdd, 2), "dd_dur": best,
            "ulcer": round((ui / max(1, len(keys))) ** 0.5, 2)}


def streak(rs):
    cur = best = 0
    for r in rs:
        cur = cur + 1 if r <= 0 else 0
        best = max(best, cur)
    return best


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, net_r, get_swings
    from exp_signal_metrics import load_era
    from exp_full_metrics import compute
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()
    data = {e: load_era(e) for e in ("is", "oos")}
    sw = {e: get_swings(data[e], EXPERIMENTS[A].get("swing") or "sw10") for e in data}

    def run(era, name):
        p = {**BP, **EXPERIMENTS[name]["params"]}
        d = data[era]
        o = sim(d["c1h"], sw[era], d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
        tr = [t for t in o["ltf_trades"] if t.get("outcome") != "open"]
        rs = [net_r([t]) for t in tr]
        return tr, rs, compute(rs, [t.get("entry_date", "") for t in tr])

    print("=" * 100)
    print("TWO BOOKS, ONE TRADE EACH:  %s  +  %s" % (A, B))
    print("=" * 100)
    for name in (A, B):
        p = EXPERIMENTS[name]["params"]
        print("  %-24s side=%-6s max_positions=%-6s" %
              (name, p.get("exp_fs_entry_side", "-"), p.get("max_positions", "0 (multi)")))
    print()

    report = {}
    for era in ("is", "oos"):
        print("#" * 100)
        print("# %s" % era.upper())
        print("#" * 100)
        trA, rsA, mA = run(era, A)
        trB, rsB, mB = run(era, B)
        dsA = [t.get("entry_date", "") for t in trA]
        dsB = [t.get("entry_date", "") for t in trB]

        keys_t = {(int(t["entry_ts"]), t["dir"]) for t in trA}
        keys_b = {(int(t["entry_ts"]), t["dir"]) for t in trB}
        print("trade overlap: %d shared keys of %d and %d" %
              (len(keys_t & keys_b), len(keys_t), len(keys_b)))
        dirs_a = {}
        for t in trA:
            dirs_a[t["dir"]] = dirs_a.get(t["dir"], 0) + 1
        dirs_b = {}
        for t in trB:
            dirs_b[t["dir"]] = dirs_b.get(t["dir"], 0) + 1
        print("directions:   %s -> %s   |   %s -> %s" % (A, dirs_a, B, dirs_b))
        print()

        print("  %-22s %8s %8s %9s %8s %8s" % ("book", "n", "net", "max_dd", "dd_dur", "ulcer"))
        for lbl, m in ((A, mA), (B, mB)):
            print("  %-22s %8d %8.1f %9.2f %8s %8.2f"
                  % (lbl, m["n"], m["net"], m["max_dd"], m.get("dd_dur"), m["ulcer"]))
        print("  %-22s %8d %8d %9s %8s %8s" % ("longest losing run", streak(rsA), streak(rsB), "", "", ""))
        print()

        # ---- correlation ----
        mA_m = monthly(rsA, dsA)
        mB_m = monthly(rsB, dsB)
        keys = sorted(set(mA_m) | set(mB_m))
        xs = [mB_m.get(k, 0.0) for k in keys]
        ys = [mA_m.get(k, 0.0) for k in keys]
        n = len(keys)
        mx, my = sum(xs) / n, sum(ys) / n
        cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / n
        vx = sum((x - mx) ** 2 for x in xs) / n
        vy = sum((y - my) ** 2 for y in ys) / n
        corr = cov / (vx ** 0.5 * vy ** 0.5) if vx > 0 and vy > 0 else 0.0
        print("  MONTHLY RETURN CORRELATION (B vs A): %.3f   over %d months" % (corr, n))
        print("    %-8s %10s %10s" % ("month", A[:8], B[:8]))
        for k in keys:
            print("    %-8s %10.1f %10.1f" % (k, mA_m.get(k, 0.0), mB_m.get(k, 0.0)))
        print()

        # ---- blend ----
        print("  BLEND (weight on %s)" % B)
        print("  %-8s %10s %10s %10s %9s %9s" % ("w", "net", "max_dd", "dd_dur", "ulcer", "vs champ"))
        rows = []
        for w in WEIGHTS:
            blend = {k: (w * mB_m.get(k, 0.0)) + ((1 - w) * mA_m.get(k, 0.0)) for k in keys}
            c = curve(blend)
            # blend trade series for the outlier bar, in entry order
            tagged = []
            for r, d in zip(rsA, dsA):
                tagged.append((str(d), r, "A"))
            for r, d in zip(rsB, dsB):
                tagged.append((str(d), r, "B"))
            tagged.sort(key=lambda z: z[0])
            brs = [r for _, r, _ in tagged]
            srt = sorted(brs, reverse=True)
            c.update({"w": w, "n": len(brs),
                      "without_top1": round(sum(srt[1:]), 2),
                      "without_top5": round(sum(srt[5:]), 2),
                      "top5_share_pct": round(100.0 * sum(srt[:5]) / sum(brs), 2) if sum(brs) else 0.0})
            rows.append(c)
            base = next((r for r in rows if r["w"] == 0.0), None)
            print("  %-8.2f %10.1f %10.1f %10d %9.2f %9s"
                  % (w, c["net"], c["max_dd"], c["dd_dur"], c["ulcer"],
                     "" if w == 0.0 else "%+.1f" % (c["max_dd"] - base["max_dd"])))
        report[era] = {"corr": round(corr, 3), "months": n,
                       "A": {k: mA.get(k) for k in ("n", "net", "max_dd", "dd_dur", "ulcer", "pf", "wr")},
                       "B": {k: mB.get(k) for k in ("n", "net", "max_dd", "dd_dur", "ulcer", "pf", "wr")},
                       "overlap": len(keys_t & keys_b), "blend": rows}
        print()

    print("=" * 100)
    print("VERDICT")
    print("=" * 100)
    for era in ("is", "oos"):
        r = report[era]
        ca = r["A"]
        # a blend that helps must beat champion's DD while netting more, both eras
        helps = [b for b in r["blend"]
                 if b["w"] > 0 and b["net"] > ca["net"] and b["max_dd"] < ca["max_dd"]]
        print("  %s: corr %.3f | champion DD %.2f net %.1f | sig_full DD %.2f net %.1f"
              % (era.upper(), r["corr"], ca["max_dd"], ca["net"],
                 r["B"]["max_dd"], r["B"]["net"]))
        if helps:
            print("     blend beats champion on BOTH net and DD at w=%s"
                  % ", ".join("%.2f" % b["w"] for b in helps))
        else:
            print("     no blend weight beats champion on BOTH net and drawdown")
        if r["overlap"] == 0:
            print("     zero shared trades - these are genuinely different books")
    print()
    print("  Read the correlation line first. Near +1 the second book is the first book")
    print("  at 1.5x size and there is nothing to decide. Near 0 it is a real diversifier")
    print("  and the DD column is the answer.")
    print()
    print("  Nothing adopted. Two registered books were measured against each other; no")
    print("  book was added, removed, re-weighted or re-pinned.")

    OUT_JSON.write_text(json.dumps({"A": A, "B": B, "report": report}, indent=2) + "\n",
                        encoding="utf-8")
    lines = ["# two books, one trade each - %s + %s" % (A, B), "",
             "Zero shared trades. Both make money in both eras.", "",
             "| era | book | n | net | maxDD | dd_dur | ulcer |",
             "|---|---|---:|---:|---:|---:|---:|"]
    for era in ("is", "oos"):
        for tag in ("A", "B"):
            m = report[era][tag]
            lines.append("| %s | %s | %s | %.1f | %.1f | %s | %.1f |" % (
                era.upper(), tag, m["n"], m["net"], m["max_dd"], m["dd_dur"], m["ulcer"]))
        lines.append("| %s | **monthly corr** | %d mo | **%.3f** | | | |"
                     % (era.upper(), report[era]["months"], report[era]["corr"]))
    lines += ["", "| era | w on B | net | maxDD | dd_dur | ulcer | without top1 |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for era in ("is", "oos"):
        for b in report[era]["blend"]:
            lines.append("| %s | %.2f | %.1f | %.1f | %d | %.1f | %.1f |" % (
                era.upper(), b["w"], b["net"], b["max_dd"], b["dd_dur"],
                b["ulcer"], b["without_top1"]))
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nwrote %s and %s" % (OUT_MD.name, OUT_JSON.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())