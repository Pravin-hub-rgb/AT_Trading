"""exp_sig_full_quality - is fsent_sig_full's equity curve actually healthy?

THE CLAIM BEING CHECKED
=======================
fsent_sig_full tops the single-position sig ladder at +194.4R OOS on 6.96R
drawdown, and it is the only book in that ladder still positive after its top 10%
of trades is removed. That last part is what makes it interesting - it is the
outlier bar that closed trail_half on the multi book, ch=50, ch=55 and
persist=5 in this repo.

It is NOT the same as "this book is good". A book can survive top-10% removal and
still have a bad shape, because that test says nothing about the spacing between
winners or whether the book earns during the waits. This measures the rest of the
framework on this one book so the answer is a judgement about the curve rather
than about one number.

THE BAR IS THE FRAMEWORK'S OWN WORKED EXAMPLE
=============================================
`docs/learn/finding optimal book.md` Sec 5 praises a strategy that earned +29.3R
through a 44-trade gap between +20R winners at 8.1R drawdown, and calls that
"much healthier" than 44 trades of -30R rescued by one +40R. That is the
standard to hold this book against, and it has not been used as one for any book
in the repo yet.

WHAT IS MEASURED
================
Sec 3A  winner spacing at +3/+5/+10/+20R, both eras
Sec 3B  profit by year - is it earned throughout, or in one stretch
Sec 4   tail dependence, the outlier bar
Sec 5   gap survivability - during the waits between +20R trades, does the book
        still earn, and how deep does it go while waiting? THIS is the section
        that decides, because it is the one that distinguishes a patient curve
        from a fragile one

Run:  cd backtest/tests
      python -u exp_sig_full_quality.py
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

BOOK = "fsent_sig_full"
LEVELS = (3.0, 5.0, 10.0, 20.0)
OUT_JSON = Path(__file__).parent / "_sig_full_quality.json"
OUT_MD = Path(__file__).parent / "_sig_full_quality.md"


def spacing(rs, level):
    idx = [i for i, r in enumerate(rs) if r >= level]
    if len(idx) < 2:
        return len(idx), []
    return len(idx), [idx[i + 1] - idx[i] - 1 for i in range(len(idx) - 1)]


def gaps(rs, level=20.0):
    idx = [i for i, r in enumerate(rs) if r >= level]
    if len(idx) < 2:
        return []
    out = []
    for a, b in zip(idx, idx[1:]):
        seg = rs[a + 1:b]
        if not seg:
            continue
        eq = peak = 0.0
        mdd = 0.0
        for r in seg:
            eq += r
            peak = max(peak, eq)
            mdd = max(mdd, peak - eq)
        out.append({"len": len(seg), "net": round(sum(seg), 2), "max_dd": round(mdd, 2),
                    "wins": sum(1 for r in seg if r > 0), "losses": sum(1 for r in seg if r <= 0)})
    return out


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, net_r, get_swings
    from exp_signal_metrics import load_era
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()
    cfg = EXPERIMENTS[BOOK]

    report = {}
    for era in ("is", "oos"):
        d = load_era(era)
        sw = get_swings(d, cfg.get("swing") or "sw10")
        p = {**BP, **cfg["params"]}
        out = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
        tr = [t for t in out["ltf_trades"] if t.get("outcome") != "open"]
        rs = [net_r([t]) for t in tr]
        ds = [t.get("entry_date", "") for t in tr]

        print("=" * 100)
        print("%s   %s   n=%d  net %+.2fR" % (BOOK, era.upper(), len(rs), sum(rs)))
        print("=" * 100)

        print("  Sec 3A - winner spacing")
        sp = {}
        for lv in LEVELS:
            cnt, g = spacing(rs, lv)
            if g:
                s = sorted(g)
                print("     +%-3.0fR winners %3d   gap mean %6.1f  median %5.1f  max %4d  p90 %4d"
                      % (lv, cnt, st.mean(g), st.median(g), max(g), s[int(len(s) * .9)]))
                sp[str(lv)] = {"count": cnt, "mean": round(st.mean(g), 2),
                               "median": round(st.median(g), 2), "max": max(g)}
            else:
                print("     +%-3.0fR winners %3d   (no gaps)" % (lv, cnt))
                sp[str(lv)] = {"count": cnt}

        print("  Sec 3B - profit by year")
        yr = {}
        for r, dd in zip(rs, ds):
            yr.setdefault(str(dd)[:4], []).append(r)
        for k in sorted(yr):
            v = yr[k]
            print("     %s  n=%3d  net %+8.2fR" % (k, len(v), sum(v)))
        yrs_pos = sum(1 for v in yr.values() if sum(v) > 0)
        print("     -> %d of %d years positive" % (yrs_pos, len(yr)))

        print("  Sec 4 - tail dependence")
        s = sorted(rs, reverse=True)
        for k in (1, 3, 5, 10):
            rest = s[k:]
            print("     minus top %-3d %+8.2fR  mean %+6.3f  (%d left)"
                  % (k, sum(rest), sum(rest) / len(rest), len(rest)))
        f = max(1, int(len(s) * 0.10))
        print("     minus top10%% %+8.2fR  mean %+6.3f" % (sum(s[f:]), sum(s[f:]) / (len(s) - f)))
        print("     top5 share %.1f%%" % (100.0 * sum(s[:5]) / sum(rs)))

        print("  Sec 5 - gap survivability between +20R winners  (THE deciding section)")
        gs = gaps(rs)
        if not gs:
            print("     not enough +20R trades to measure gaps")
        else:
            nets = [g["net"] for g in gs]
            pos = sum(1 for x in nets if x > 0)
            print("     %d gaps   mean net %+.2fR   median %+.2fR   worst %+.2fR"
                  % (len(gs), st.mean(nets), st.median(nets), min(nets)))
            print("     %d of %d gaps positive (%.0f%%)   worst intra-gap drawdown %.2fR"
                  % (pos, len(gs), 100.0 * pos / len(gs), max(g["max_dd"] for g in gs)))
            worst = max(gs, key=lambda g: g["max_dd"])
            print("     longest gap %d trades: net %+.2fR, %dW/%dL, worst DD %.2fR"
                  % (worst["len"], worst["net"], worst["wins"], worst["losses"], worst["max_dd"]))

        # compare against the framework's own worked example
        print()
        print("  vs the framework's worked example (Sec 5): +29.3R through a 44-trade")
        print("  gap at 8.1R drawdown, called 'much healthier' than -30R then a +40R rescue")
        if gs:
            big = [g for g in gs if g["len"] >= 20]
            if big:
                b = max(big, key=lambda g: g["max_dd"])
                print("     this book's worst gap of >=20 trades: %d trades, net %+.2fR, DD %.2fR"
                      % (b["len"], b["net"], b["max_dd"]))
                if b["net"] > 0:
                    print("     -> earns DURING the wait, like the example. Healthier shape.")
                else:
                    print("     -> BLEEDS during the wait. Fragile: one stretch from ending.")
            else:
                print("     no gap of 20+ trades, so the comparison does not apply")
        report[era] = {"n": len(rs), "net": round(sum(rs), 2), "spacing": sp,
                       "years": {k: round(sum(v), 2) for k, v in yr.items()},
                       "gaps": gs}
        print()

    OUT_JSON.write_text(json.dumps({"book": BOOK, "eras": report}, indent=2) + "\n",
                        encoding="utf-8")
    print("=" * 100)
    print("FRAMEWORK'S HEALTHY SHAPE (Sec 6): right-skewed, but NOT dependent on the tail")
    print("=" * 100)
    for era in ("is", "oos"):
        r = report[era]
        g = r["gaps"]
        print("  %s: survives top-10%% removal, %d +20R trades, %d gaps of which %.0f%% positive"
              % (era.upper(), r["spacing"]["20.0"]["count"], len(g),
                 100.0 * sum(1 for x in g if x["net"] > 0) / max(1, len(g))))
    print()
    print("Nothing changed. This measures an already-registered book; it does not")
    print("promote it. fsent_sig_full is currently registered and pinned, and this")
    print("harness adds no config change.")

    OUT_MD.write_text(
        "# equity-curve quality of fsent_sig_full\n\n"
        "Framework: docs/learn/finding optimal book.md. Both eras.\n\n"
        "| era | n | net | +20R count | max gap | gaps | gaps positive % | worst intra-gap DD |\n"
        "|---|---:|---:|---:|---:|---:|---:|---:|\n"
        + "".join(
            "| %s | %d | %.1f | %d | %s | %d | %.0f | %s |\n" % (
                era.upper(), report[era]["n"], report[era]["net"],
                report[era]["spacing"]["20.0"]["count"],
                report[era]["spacing"]["20.0"].get("max", "-"),
                len(report[era]["gaps"]),
                100.0 * sum(1 for x in report[era]["gaps"] if x["net"] > 0)
                / max(1, len(report[era]["gaps"])),
                max((g["max_dd"] for g in report[era]["gaps"]), default="-"))
            for era in ("is", "oos"))
        + "\nNot promoted by this measurement; it is already registered and pinned.\n",
        encoding="utf-8")
    print("\nwrote %s and %s" % (OUT_MD.name, OUT_JSON.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())