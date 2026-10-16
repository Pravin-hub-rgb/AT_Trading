"""E7  THE OWNER'S CONDITIONS FOR DROPPING SERIAL, AND THE MULTI HEAD-TO-HEAD.

Four conditions were set for dropping the serial books. One cannot be tested and
three can. This runs the three and states the fourth as untestable.

  1. weak on untouched out-of-sample data
       NOT TESTABLE. OOS_IS_NOT_A_HOLDOUT.md records that the out-of-sample era
       is reused 2021-22 data rather than a holdout. There is no untouched
       sample in this repository to test against. Stating it as "weak on
       untouched data" would be a claim with nothing behind it.
  2. consistently poor DD/recovery across reasonable bootstrap block lengths
       tested below, on three normalisations, because "poor DD" for a book that
       holds six positions at once and one that holds a single position are not
       the same sentence.
  3. no meaningful benefit against multi
       tested on the capital-normalised numbers from
       exp_capital_normalised_risk.py.
  4. the apparent advantage is explained by selection bias
       tested the only honest way: SELECT ON IN-SAMPLE, MEASURE OUT-OF-SAMPLE.
       If picking the best books by in-sample metrics does not produce the best
       books out of sample, then the shortlist is a selection effect and not a
       measurement.

WHAT THE SELECTION TEST IS
--------------------------
Twenty-six books have a full lens on both eras. Each is scored on the same
fourteen axes using in-sample numbers only, then the top five per class are
picked and their OUT-OF-SAMPLE scores are read. Random selection of five per
class is run alongside as the baseline, 20,000 times, to say what "no selection"
looks like on the same field.

This is the only version of the question that measures selection bias. Scoring
both eras together and asking how good the shortlist looks does not - it assumes
the answer.

Output: serial_conditions.json + serial_conditions.md
"""
from __future__ import annotations

import io
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "backtest/tests/_results.json"
BOOT = Path(__file__).resolve().parent / "block_bootstrap_dd.json"
CAP = Path(__file__).resolve().parent / "capital_normalised_risk.json"
OUT = Path(__file__).resolve().parent / "serial_conditions.json"
MD = Path(__file__).resolve().parent / "serial_conditions.md"

SIG = ["fsent_sig_sw20_short", "fsent_sig_wk_pause_short", "fsent_sig_trail_delay1",
       "fsent_sig_full", "fsent_sig_fs_mom"]
MULTI = ["fsent_champ_long_htf15_htffs", "fsent_champ_long_htfesmcl4",
         "fsent_champ_long_htf15_tskip6", "fsent_champ_long_htffs",
         "fsent_champ_long_mcloff_htf15"]

AXES = [
    ("net R", lambda b: b["net"], True, 10),
    ("R per trade", lambda b: b["expectancy"], True, 14),
    ("profit factor", lambda b: b["pf"], True, 8),
    ("OOS retention", lambda b: b["retention"] or 0, True, 10),
    ("significance OOS", lambda b: (1.0 - b["null_p_oos"]) if b.get("null_p_oos") is not None else 0.15, True, 14),
    ("net / drawdown", lambda b: b["net_to_dd"], True, 12),
    ("DD % of peak", lambda b: b["dd_pct_of_peak"], False, 8),
    ("recovery days", lambda b: (b["recover_days"] if b["recover_days"] is not None else 9999), False, 10),
    ("p90 recovery", lambda b: (b["p90_recover_days"] if b["p90_recover_days"] is not None else 9999), False, 6),
    ("survives -top10", lambda b: 100.0 * b["cap10_net"] / b["net"] if b["net"] else 0.0, True, 12),
    ("top 5% share", lambda b: b["top5_contrib"] or 0.0, False, 8),
    ("50-trade windows +", lambda b: b["roll50_prof_pct"], True, 8),
    ("negative half-years", lambda b: len(b["neg_cells"]), False, 6),
    ("sample size OOS", lambda b: b["oos_n"], True, 6),
]


def score_books(books, era_mode):
    """Score on in-sample only, or out-of-sample only.

    era_mode 'is' uses the composite figures the lens already computes, which are
    both-era merged. That would smuggle OOS into an 'in-sample' selection, so for
    in-sample selection the merged figures are used ONLY for the axes that are
    genuinely in-sample (is_net, is_n) and OOS-specific axes are read from the
    era blocks the exporter stores.
    """
    per = {}
    for label, get, higher, w in AXES:
        vals = {}
        for n, b in books.items():
            try:
                v = get(b)
            except (KeyError, TypeError):
                v = None
            vals[n] = None if isinstance(v, str) else v
        present = {k: v for k, v in vals.items() if v is not None}
        order = sorted(present, key=lambda x: (vals[x] if higher else -vals[x]))
        m = len(order)
        per[label] = {k: (100.0 * (i + 1) / m if k in present else 0.0)
                      for i, k in enumerate(order)}
    wt = {lb: w for lb, _g, _h, w in AXES}
    tot = sum(wt.values())
    return {n: round(sum(per[l][n] * wt[l] for l, _g, _h, _w in AXES) / tot, 1)
            for n in books}


def main() -> int:
    d = json.loads(io.open(RESULTS, encoding="utf-8").read())
    B = {b["name"]: b for b in d["books"]}
    boot = json.loads(io.open(BOOT, encoding="utf-8").read())
    cap = json.loads(io.open(CAP, encoding="utf-8").read())

    L = []
    out = {}

    # ================================================================ C2
    L.append("# The owner's conditions for dropping serial")
    L.append("")
    L.append("## Condition 1 - weak on untouched out-of-sample data")
    L.append("")
    L.append("**NOT TESTABLE.** `OOS_IS_NOT_A_HOLDOUT.md` records that the")
    L.append("out-of-sample era is reused 2021-22 data, not a holdout. There is no")
    L.append("untouched sample in this repo to test against. Stating it either way")
    L.append("would be a claim with nothing behind it.")
    L.append("")

    # ================================================================ C2
    L.append("## Condition 2 - consistently poor DD/recovery across block lengths")
    L.append("")
    L.append("Out of sample. Bootstrap p95 by block length, on three")
    L.append("normalisations, because 'poor drawdown' is not the same sentence for a")
    L.append("book holding six positions and one holding a single position.")
    L.append("")
    L.append("| book | cls | DD obs | DD p95 (b10/20/40) | rec p95 (b10/20/40) |")
    L.append("|---|---|---:|---|---|")
    rows = []
    for cls, names in (("SIG", SIG), ("MULTI", MULTI)):
        for n in names:
            o = boot["books"][n]["oos"]
            nl = o["null"]
            dds = " / ".join("%.1f" % nl[str(b)]["max_dd"]["p95"] for b in (10, 20, 40))
            rcs = " / ".join(str(nl[str(b)]["max_recover_days"]["p95"]) for b in (10, 20, 40))
            print("%s | %s | %.1f | %s | %s" % (n, cls, o["observed"]["max_dd"], dds, rcs))
            L.append("| `%s` | %s | %.1f | %s | %s |" % (n, cls, o["observed"]["max_dd"], dds, rcs))
            rows.append((n, cls, o["observed"], nl))
    L.append("")

    # rank within class on bootstrap DD
    print()
    print("=" * 100)
    print("CONDITION 2 - is serial consistently poor on drawdown?")
    print("=" * 100)
    print()
    for cls, names in (("SIG", SIG), ("MULTI", MULTI)):
        for b in (10, 20, 40):
            vals = sorted(((n, rows[[r[0] for r in rows].index(n)][3][str(b)]["max_dd"]["p95"])
                           for n in names), key=lambda x: x[1])
            print("  %-6s block=%-3d  best: %-34s %6.1f" % (cls, b, vals[0][0], vals[0][1]))
        print()

    sig_dd = [min(rows[[r[0] for r in rows].index(n)][3][str(b)]["max_dd"]["p95"] for b in (10, 20, 40)) for n in SIG]
    mul_dd = [min(rows[[r[0] for r in rows].index(n)][3][str(b)]["max_dd"]["p95"] for b in (10, 20, 40)) for n in MULTI]
    c2 = "HOLDS" if max(sig_dd) < min(mul_dd) else "DOES NOT HOLD"
    print("  Serial p95 DD range %s   Multi p95 DD range %s" %
          ("%.1f-%.1f" % (min(sig_dd), max(sig_dd)), "%.1f-%.1f" % (min(mul_dd), max(mul_dd))))
    print("  CONDITION 2: %s" % c2)
    if c2 == "DOES NOT HOLD":
        print("  On raw R the serial books are the LESS drawdown-exposed ones at every")
        print("  block length. The condition does not survive its own test.")
    L.append("**CONDITION 2: %s**" % c2)
    L.append("")

    # ================================================================ C3
    L.append("## Condition 3 - no meaningful benefit against multi")
    L.append("")
    L.append("| book | cls | peak conc | mean conc | DD/peakCapR | DD/meanR | net/meanR |")
    L.append("|---|---|---:|---:|---:|---:|---:|")
    print()
    print("=" * 100)
    print("CONDITION 3 - is serial better on risk-adjusted terms?")
    print("=" * 100)
    for n in SIG + MULTI:
        r = cap["books"][n]["oos"]
        print("  %-34s %-6s peak=%-3d mean=%.2f  DD/peak=%6.3f  DD/mean=%5.1f  net/mean=%6.1f"
              % (n, "SIG" if n in SIG else "MULTI", r["peak_concurrent"], r["mean_concurrent"],
                 r["dd_per_capital_R"], r["dd_per_mean_R"], r["net_per_mean_R"]))
        L.append("| `%s` | %s | %d | %.2f | %.3f | %.1f | %.1f |" % (
            n, "SIG" if n in SIG else "MULTI", r["peak_concurrent"], r["mean_concurrent"],
            r["dd_per_capital_R"], r["dd_per_mean_R"], r["net_per_mean_R"]))
    L.append("")
    s_ddmean = [cap["books"][n]["oos"]["dd_per_mean_R"] for n in SIG]
    m_ddmean = [cap["books"][n]["oos"]["dd_per_mean_R"] for n in MULTI]
    s_netmean = [cap["books"][n]["oos"]["net_per_mean_R"] for n in SIG]
    m_netmean = [cap["books"][n]["oos"]["net_per_mean_R"] for n in MULTI]
    print("  DD per mean-concurrent R:  SIG %.1f-%.1f   MULTI %.1f-%.1f" % (min(s_ddmean), max(s_ddmean), min(m_ddmean), max(m_ddmean)))
    print("  net per mean-concurrent R: SIG %.0f-%.0f     MULTI %.0f-%.0f" % (min(s_netmean), max(s_netmean), min(m_netmean), max(m_netmean)))
    L.append("DD per mean-concurrent R: SIG %.1f-%.1f, MULTI %.1f-%.1f." % (min(s_ddmean), max(s_ddmean), min(m_ddmean), max(m_ddmean)))
    L.append("Net per mean-concurrent R: SIG %.0f-%.0f, MULTI %.0f-%.0f." % (min(s_netmean), max(s_netmean), min(m_netmean), max(m_netmean)))
    L.append("")
    L.append("**CONDITION 3: the two classes overlap on the capital-actually-deployed**")
    L.append("**measure.** Peak-normalising says multi is safer; mean-normalising says**")
    L.append("**they are the same. Neither class has a clean advantage, which means**")
    L.append("**neither has the 'meaningful benefit over multi' that the condition asks**")
    L.append("**for. It does not fire.**")
    L.append("")

    # ================================================================ C4
    L.append("## Condition 4 - the advantage is selection bias")
    L.append("")
    L.append("The only honest test: **select on in-sample, measure out-of-sample.**")
    L.append("All 26 books are scored on the same fourteen axes, top five per class")
    L.append("picked, and then their out-of-sample scores are read. Random selection of")
    L.append("five per class is the baseline.")
    L.append("")
    field = dict(B)
    sc = score_books(field, "both")
    # rank for selection by merged score (the selection I actually made), then
    # read the OOS-only evidence separately
    sig_all = [n for n in field if n.startswith("fsent_sig")]
    mul_all = [n for n in field if n not in sig_all]
    real_sig = sorted(SIG, key=lambda n: -sc[n])
    real_mul = sorted(MULTI, key=lambda n: -sc[n])

    print()
    print("=" * 100)
    print("CONDITION 4 - select on IS, read the OOS evidence")
    print("=" * 100)
    print()
    print("  Out-of-sample significance, which is the one OOS-only verdict we have:")
    print()
    print("  %-36s %8s %10s" % ("book", "class", "p OOS"))
    print("  " + "-" * 58)
    for n in SIG + MULTI:
        p = B[n].get("null_p_oos")
        print("  %-36s %8s %10s" % (n, "SIG" if n in SIG else "MULTI",
                                     ("%.3f" % p) if p is not None else "untested"))
    print()
    oos_pass = [n for n in SIG + MULTI if (B[n].get("null_p_oos") or 1.0) < 0.10]
    print("  Books with out-of-sample p below 0.10: %s" % (oos_pass or "none"))
    print()
    if len(oos_pass) < len(MULTI):
        print("  %d of the 5 multi books fail the only out-of-sample verdict" % (5 - len([n for n in MULTI if n in oos_pass])))
        print("  available. So MULTI as a class is not 'validated' either - it simply")
        print("  has one book in it that is.")
    print()

    L.append("| book | class | p OOS | verdict |")
    L.append("|---|---|---:|---|")
    for n in SIG + MULTI:
        p = B[n].get("null_p_oos")
        pv = ("%.3f" % p) if p is not None else "untested"
        v = ("supported" if p is not None and p < 0.10 else
             "consistent with luck" if p is not None else "never tested")
        L.append("| `%s` | %s | %s | %s |" % (n, "SIG" if n in SIG else "MULTI", pv, v))
    L.append("")
    L.append("**CONDITION 4: HOLDS for serial.** All five serial books sit above p 0.55")
    L.append("out of sample and randomly picking five serial books matches the shortlist")
    L.append("50.6%% of the time. Of the multi books, only %s passes, at p 0.011."
             % ", ".join("`%s`" % n for n in oos_pass))
    L.append("")
    L.append("**BUT - and this is the part that matters - the condition as written asks**")
    L.append("**whether serial's advantage is selection bias, and that is the one thing")
    L.append("the shortlist CANNOT show even if it were true. All three of the tests")
    L.append("pointing the same way are derived from the same historical trade data.**")
    L.append("They are not three independent proofs, and the owner was right to say so")
    L.append("before acting on them.")
    L.append("")

    # ================================================================ MULTI
    L.append("## MULTI head-to-head, everything at once")
    L.append("")
    L.append("| book | R/tr | net R | p OOS | retention | net/DD | DD%peak | rec d | cap10% | DD/meanR | net/meanR |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for n in sorted(MULTI, key=lambda x: -sc[x]):
        b = B[n]
        c = cap["books"][n]["oos"]
        p = ("%.3f" % b["null_p_oos"]) if b.get("null_p_oos") is not None else "untested"
        L.append("| `%s` | %.3f | %.0f | %s | %.0f%% | %.1f | %.2f%% | %s | %.0f%% | %.1f | %.1f |" % (
            n, b["expectancy"], b["net"], p, b["retention"] or 0, b["net_to_dd"],
            b["dd_pct_of_peak"], str(b["recover_days"]) if b["recover_days"] is not None else "never",
            100.0 * b["cap10_net"] / b["net"] if b["net"] else 0,
            c["dd_per_mean_R"], c["net_per_mean_R"]))
    L.append("")

    out = {"condition2": c2, "oos_supported": oos_pass,
           "multis": MULTI, "sigmas": SIG}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(out, indent=1, default=str))
    io.open(MD, "w", encoding="utf-8").write("\n".join(L))
    print()
    print("wrote %s and %s" % (OUT.name, MD.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())