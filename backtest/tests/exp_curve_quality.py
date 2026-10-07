"""exp_curve_quality - equity-curve quality, champion vs trail_half.

WHY THIS FILE EXISTS
====================
fsent_champ_trailhalf pins +42.5R more out of sample than fsent_champ_long and
was not adopted, because 2.37x the in-sample drawdown buys that +42R. Net R and
max DD decide nothing on their own. They are the two easiest numbers to move by
taking fewer, larger trades, which is exactly what exp_trail_half does.

So this measures the thing that separates a book that made its money patiently
from one that made it in bursts: the SHAPE of the equity curve, and specifically
what happens during the stretches between the big winners.

THE FRAMEWORK IS NOT MINE
=========================
`docs/learn/finding optimal book.md` is the owner's framework, and this follows
its sections rather than inventing a new score. The parts implemented here are
the ones that discriminate between two books that both make money:

  Sec 3A  winner spacing    - gaps between meaningful winners (+3/+5/+10/+20R)
  Sec 3B  winner spread     - is profit generated throughout the era?
  Sec 4   tail dependence   - what survives removing the top 1/3/5/10 and top 5/10%
  Sec 5   gap survivability - DURING the gaps, is expectancy still positive?
  Sec 6   the healthy shape - is it right-skewed without DEPENDENT on the tail

Section 5 is the important one and the one most often skipped. A book can show
long gaps between +20R winners and be perfectly healthy, or the same gaps and be
one bad month from ending. The difference is whether it earns during the wait.
This measures that directly, per gap, rather than in aggregate.

THE ANSWER THIS IS BUILT TO GIVE
================================
Not "which book is better" - that is an adoption decision against a drawdown
budget, and EQUITY_LENS_EXT_AND_NOHALT.md already holds the rule for it. What
this gives is the evidence that rule needs: whether trail_half's extra 4.6R of
drawdown buys a genuinely more robust curve or just a steeper one.

Run:  cd backtest/tests
      python -u exp_curve_quality.py
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

BOOKS = ("fsent_champ_long", "fsent_champ_trailhalf")
OUT_JSON = Path(__file__).parent / "_curve_quality.json"
OUT_MD = Path(__file__).parent / "_curve_quality.md"

WINNER_LEVELS = (3.0, 5.0, 10.0, 20.0)
TAIL_DROP = (1, 3, 5, 10)
TAIL_PCT = (0.05, 0.10)


def spacing(rs, level):
    """Framework Sec 3A. Gaps between trades of at least `level` R.

    Returns (count, gaps) where gaps are trade counts between consecutive
    qualifying trades. A gap of 0 means they are adjacent.
    """
    idx = [i for i, r in enumerate(rs) if r >= level]
    if len(idx) < 2:
        return len(idx), []
    gaps = [idx[i + 1] - idx[i] - 1 for i in range(len(idx) - 1)]
    return len(idx), gaps


def gap_stats(gaps):
    if not gaps:
        return {}
    s = sorted(gaps)
    return {"n": len(gaps), "mean": round(st.mean(gaps), 2),
            "median": round(st.median(gaps), 2), "max": max(gaps),
            "p90": s[int(len(s) * 0.9)]}


def tail_drop(rs):
    """Framework Sec 4. Net and mean after removing the biggest trades."""
    s = sorted(rs, reverse=True)
    out = {}
    for k in TAIL_DROP:
        if len(s) > k:
            rest = s[k:]
            out["top%d_removed" % k] = {"net": round(sum(rest), 2),
                                       "mean": round(sum(rest) / len(rest), 3),
                                       "trades_left": len(rest)}
    for f in TAIL_PCT:
        k = max(1, int(len(s) * f))
        rest = s[k:]
        out["top%02d_pct_removed" % int(f * 100)] = {"net": round(sum(rest), 2),
                                                    "mean": round(sum(rest) / len(rest), 3),
                                                    "trades_left": len(rest)}
    out["top5_share_pct"] = round(100.0 * sum(s[:5]) / sum(rs), 2) if sum(rs) else 0.0
    return out


def gap_survivability(rs, level=20.0):
    """Framework Sec 5. Between qualifying trades, does the book still earn?

    For each stretch of non-qualifying trades between two trades of >= level R,
    report that stretch's net, wins, losses and worst peak-to-trough inside it.
    """
    idx = [i for i, r in enumerate(rs) if r >= level]
    if len(idx) < 2:
        return {"gaps": 0, "note": "not enough %gR trades to measure gaps" % level}
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
        out.append({"from_idx": a, "to_idx": b, "len": len(seg),
                    "net": round(sum(seg), 2), "max_dd": round(mdd, 2),
                    "wins": sum(1 for r in seg if r > 0),
                    "losses": sum(1 for r in seg if r <= 0)})
    nets = [g["net"] for g in out]
    pos = sum(1 for n in nets if n > 0)
    return {"gaps": len(out),
            "gap_net_mean": round(st.mean(nets), 2) if nets else 0,
            "gap_net_median": round(st.median(nets), 2) if nets else 0,
            "gap_net_min": min(nets) if nets else 0,
            "gaps_positive": pos,
            "gaps_positive_pct": round(100.0 * pos / len(out), 1) if out else 0,
            "worst_gap_mdd": round(max(g["max_dd"] for g in out), 2) if out else 0,
            "detail": out}


def temporal(rs, ds):
    """Framework Sec 3B. Profit per calendar year and per quarter."""
    def agg(keyfn):
        m = {}
        for r, d in zip(rs, ds):
            m.setdefault(keyfn(d), []).append(r)
        return {k: {"n": len(v), "net": round(sum(v), 2)} for k, v in sorted(m.items())}
    return {"year": agg(lambda d: str(d)[:4]),
            "quarter": agg(lambda d: str(d)[:4] + "Q" + str((int(str(d)[5:7]) - 1) // 3 + 1))}


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, net_r, get_swings
    from exp_signal_metrics import load_era
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()
    sw_is = get_swings(load_era("is"), EXPERIMENTS[BOOKS[0]].get("swing") or "sw10")
    d_oos = load_era("oos")
    sw_oos = get_swings(d_oos, EXPERIMENTS[BOOKS[0]].get("swing") or "sw10")

    def run(era, name):
        p = {**BP, **EXPERIMENTS[name]["params"]}
        d, s = (None, sw_is) if era == "is" else (d_oos, sw_oos)
        if era == "is":
            from exp_signal_metrics import load_era as _le
            d = _le("is")
        out = sim(d["c1h"], s, d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
        tr = [t for t in out["ltf_trades"] if t.get("outcome") != "open"]
        return [net_r([t]) for t in tr], [t.get("entry_date", "") for t in tr]

    report = {}
    for era in ("is", "oos"):
        print("=" * 100)
        print("%s" % era.upper())
        print("=" * 100)
        for name in BOOKS:
            rs, ds = run(era, name)
            print("\n%s   n=%d  net %+.2fR" % (name, len(rs), sum(rs)))

            print("  -- Sec 3A: winner spacing --")
            sp = {}
            for lv in WINNER_LEVELS:
                cnt, gaps = spacing(rs, lv)
                stt = gap_stats(gaps)
                sp[str(lv)] = {"count": cnt, **stt}
                if stt:
                    print("     +%-4.0fR winners: %3d   gap mean %6.1f  median %5.1f  max %4d  p90 %4d"
                          % (lv, cnt, stt["mean"], stt["median"], stt["max"], stt["p90"]))
                else:
                    print("     +%-4.0fR winners: %3d   (no gaps to measure)" % (lv, cnt))

            print("  -- Sec 3B: profit through time --")
            tt = temporal(rs, ds)
            yr = tt["year"]
            for k, v in yr.items():
                print("     %s  n=%3d  net %+8.2fR" % (k, v["n"], v["net"]))
            yrs_pos = sum(1 for v in yr.values() if v["net"] > 0)
            print("     -> %d of %d years positive" % (yrs_pos, len(yr)))

            print("  -- Sec 4: tail dependence --")
            td = tail_drop(rs)
            for k, v in td.items():
                if isinstance(v, dict):
                    print("     %-22s net %+8.2fR  mean %+6.3f  (%d trades left)"
                          % (k, v["net"], v["mean"], v["trades_left"]))
                else:
                    print("     %-22s %.1f%% of net in top 5 trades" % (k, v))

            print("  -- Sec 5: gap survivability (between +20R trades) --")
            gs = gap_survivability(rs)
            if gs.get("gaps"):
                print("     %d gaps   mean net %+.2fR   median %+.2fR   worst %+.2fR"
                      % (gs["gaps"], gs["gap_net_mean"], gs["gap_net_median"], gs["gap_net_min"]))
                print("     %d of %d gaps earn positive R (%.1f%%)   worst intra-gap DD %.2fR"
                      % (gs["gaps_positive"], gs["gaps"], gs["gaps_positive_pct"],
                         gs["worst_gap_mdd"]))
            else:
                print("     %s" % gs.get("note"))
            report.setdefault(name, {})[era] = {
                "n": len(rs), "net": round(sum(rs), 2), "spacing": sp,
                "temporal": tt, "tail": td, "gaps": gs}

    print()
    print("=" * 100)
    print("SIDE BY SIDE - OOS, the era that decides")
    print("=" * 100)
    print("%-30s %10s %10s" % ("", BOOKS[0][7:], BOOKS[1][7:]))
    a, b = report[BOOKS[0]]["oos"], report[BOOKS[1]]["oos"]
    rows = [("net R", a["net"], b["net"]),
            ("trades", a["n"], b["n"]),
            ("top5_share %", a["tail"]["top5_share_pct"], b["tail"]["top5_share_pct"]),
            ("net minus top5", a["tail"]["top5_removed"]["net"], b["tail"]["top5_removed"]["net"]),
            ("net minus top1", a["tail"]["top1_removed"]["net"], b["tail"]["top1_removed"]["net"])]
    for lv in WINNER_LEVELS:
        sa, sb = a["spacing"][str(lv)], b["spacing"][str(lv)]
        rows.append(("+%gR winners" % lv, sa["count"], sb["count"]))
        if sa.get("max") is not None:
            rows.append(("  max gap (+%gR)" % lv, sa["max"], sb["max"]))
    for name in BOOKS:
        pass
    for lbl, va, vb in rows:
        print("%-30s %10s %10s" % (lbl, va, vb))

    ga, gb = a["gaps"], b["gaps"]
    if ga.get("gaps") and gb.get("gaps"):
        print()
        print("gap survivability, +20R trades:")
        print("   %-22s gaps %s | mean net %s | positive %s%% | worst intra-gap DD %s"
              % (BOOKS[0], ga["gaps"], ga["gap_net_mean"], ga["gaps_positive_pct"], ga["worst_gap_mdd"]))
        print("   %-22s gaps %s | mean net %s | positive %s%% | worst intra-gap DD %s"
              % (BOOKS[1], gb["gaps"], gb["gap_net_mean"], gb["gaps_positive_pct"], gb["worst_gap_mdd"]))
        print()
        print("Sec 5 says: a book whose gaps still EARN is healthy even with long")
        print("waits. A book whose gaps bleed is one bad stretch from ending.")
        print("Compare 'mean net' and 'positive %' between the two columns.")

    OUT_JSON.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = ["# equity-curve quality - champion vs trail_half", "",
             "Framework: docs/learn/finding optimal book.md. Both eras.", "",
             "| era | book | n | net | top5_share % | net-top1 | net-top5 | +20R count | gap mean net | gap positive % |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name in BOOKS:
        for era in ("is", "oos"):
            r = report[name][era]
            g = r["gaps"]
            lines.append("| %s | %s | %d | %.1f | %.1f | %.1f | %.1f | %s | %s | %s |" % (
                era.upper(), name, r["n"], r["net"], r["tail"]["top5_share_pct"],
                r["tail"]["top1_removed"]["net"], r["tail"]["top5_removed"]["net"],
                r["spacing"]["20.0"].get("count", "-"),
                g.get("gap_net_mean", "-"), g.get("gaps_positive_pct", "-")))
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nwrote %s and %s" % (OUT_MD.name, OUT_JSON.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())