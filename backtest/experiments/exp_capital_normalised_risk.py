"""E6  CAPITAL-NORMALISED RISK - is multi's lower drawdown real, or just more net?

THE QUESTION THIS ANSWERS
-------------------------
> "Multi ek saath multiple positions kholti hai, toh uske aggregate exposure,
>  correlated positions aur capital requirements ko bhi account karna padega.
>  Lower DD alone ka matlab automatically better strategy nahi."

Correct, and it is the one thing the whole comparison has been missing.

Every drawdown in this repo is measured in R, and R is one trade's risk. That is
the right unit WITHIN a book and the wrong unit ACROSS books. A multi book that
holds six positions at once is committing six R of risk simultaneously while a
serial book commits one. Its "29R drawdown" was taken while carrying up to six
times the exposure, and its drawdown as a share of net looks small partly because
it made more net, not because it was better behaved.

So the comparison has to be at equal capital, not equal trade.

WHAT IS COMPUTED
----------------
  peak_concurrent   the most positions ever open at once, measured from the
                    book's own entry and exit timestamps
  capital_r         peak_concurrent, i.e. how many R of capital the book needs
                    to be able to hold everything it wants to hold
  dd_per_capital_R  max_dd divided by capital_R - the account drawdown one R of
                    deployable capital would have suffered
  net_per_capital_R net divided by capital_r - the return per R of capital

dd_per_capital_R is the number that makes serial and multi comparable. A multi
book that looks better on plain max_dd can turn out to be worse here, because
its drawdown was measured against a bigger risk budget.

WHAT THIS IS AND IS NOT
-----------------------
It is a re-normalisation of the same equity curve, not a new backtest. It does
not model margin calls, funding on the extra exposure, or the correlation between
concurrent positions. It answers one question - what would this drawdown look
like if we both had the same capital to lose - and stops there.

Known prior: RISK_CONCURRENCY.md measured peak concurrency at 6 IS and 5 OOS for
the champion and found a risk-sum cap had no edge. This file does not revisit
that; it uses the concurrency number for a different purpose.

Output: capital_normalised_risk.json
"""
from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

HERE = Path(__file__).resolve().parent
OUT = HERE / "capital_normalised_risk.json"

import exp_repin_stale as repin                                  # noqa: E402
import test_experiments_craze as craze                           # noqa: E402
from exp_signal_metrics import load_era                          # noqa: E402
from registry import EXPERIMENTS                                # noqa: E402

SHORTLIST = [
    "fsent_sig_sw20_short", "fsent_sig_wk_pause_short", "fsent_sig_trail_delay1",
    "fsent_sig_full", "fsent_sig_fs_mom",
    "fsent_champ_long_htf15_htffs", "fsent_champ_long_htfesmcl4",
    "fsent_champ_long_htf15_tskip6", "fsent_champ_long_htffs",
    "fsent_champ_long_mcloff_htf15",
]
CLS = {b: ("SIG" if b.startswith("fsent_sig") else "MULTI") for b in SHORTLIST}


def net_r(t):
    from exp_equity_quality import net_r as _nr
    return float(_nr([t]))


def trades_of(sim, data, cfg):
    sw = {"sw10": data["sw10"], "sw20": data["sw20"],
          "sw15": data["sw15"], "htf15": data["htf15"]}[cfg["swing"]]
    tr = sim(data["c1h"], sw, data["c15"], data["sw15"], fine_ltf=data["fine"],
             **{**dict(repin.re_.BP), **cfg["params"]})["ltf_trades"]
    repin._trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
    return [t for t in tr if t.get("outcome") != "open"]


def peak_concurrent(trades):
    """Most positions open at once, from each trade's own entry and exit stamps.

    Strictly causal: a trade occupies a slot on [entry_ts, exit_ts] inclusive.
    """
    if not trades:
        return 0
    ev = []
    for t in trades:
        ev.append((int(t["entry_ts"]), 1))
        ev.append((int(t["exit_ts"]), -1))
    # closes before opens on the same stamp: a position that closes at the entry
    # bar is not occupying a slot against the trade entering on it
    ev.sort(key=lambda x: (x[0], x[1]))
    cur = peak = 0
    for _ts, delta in ev:
        cur += delta
        if cur > peak:
            peak = cur
    return peak


def mean_concurrent(trades):
    if not trades:
        return 0.0
    ev = []
    for t in trades:
        ev.append((int(t["entry_ts"]), 1))
        ev.append((int(t["exit_ts"]), -1))
    ev.sort(key=lambda x: (x[0], x[1]))
    # area under the concurrency curve / total span
    cur = 0.0
    area = 0.0
    prev = ev[0][0]
    span = ev[-1][0] - ev[0][0]
    for ts, delta in ev:
        area += cur * (ts - prev)
        prev = ts
        cur += delta
    return area / span if span else 0.0


def main() -> int:
    t0 = time.time()
    sim = craze.build_module()
    eras = {e: load_era(e) for e in ("is", "oos")}
    print("E6  CAPITAL-NORMALISED RISK - serial vs multi at equal capital")
    print("max_dd is in R, and R is ONE trade's risk. Multi holds up to six of\n"
          "them at once, so its drawdown was measured against a bigger budget.\n")

    out = {"books": {}}
    for book in SHORTLIST:
        cfg = EXPERIMENTS[book]
        rec = {"cls": CLS[book]}
        for era in ("is", "oos"):
            tr = trades_of(sim, eras[era], cfg)
            rs = np.array([net_r(t) for t in tr], dtype=float)
            c = np.cumsum(rs)
            run_max = np.maximum.accumulate(c)
            max_dd = float(np.max(run_max - c))
            net = float(c[-1])
            pk = peak_concurrent(tr)
            mc = mean_concurrent(tr)
            rec[era] = {
                "n": len(rs), "net": round(net, 2), "max_dd": round(max_dd, 2),
                "peak_concurrent": pk, "mean_concurrent": round(mc, 2),
                "capital_r": pk,
                "dd_per_capital_R": round(max_dd / pk, 3) if pk else None,
                "net_per_capital_R": round(net / pk, 3) if pk else None,
                # the other normalisation, and it matters because mean
                # concurrency came out around 1 for BOTH classes
                "dd_per_mean_R": round(max_dd / mc, 3) if mc else None,
                "net_per_mean_R": round(net / mc, 2) if mc else None,
                # the number that misleads: big book, small ratio
                "dd_pct_of_net": round(100.0 * max_dd / net, 2) if net else None,
            }
        out["books"][book] = rec
        print("  %-34s done" % book)

    print()
    sig = [b for b in SHORTLIST if CLS[b] == "SIG"]
    mul = [b for b in SHORTLIST if CLS[b] == "MULTI"]
    print("=" * 122)
    print("AT EQUAL CAPITAL  (out of sample)")
    print("=" * 122)
    print("  PEAK normalises by the most positions ever open - the capital you must")
    print("  have. MEAN normalises by positions actually held - the capital you use.")
    print()
    print("%-32s %5s %6s %7s %9s %11s %10s %10s %10s"
          % ("book", "cls", "peak", "mean", "maxDD R", "DD/peakCapR", "DD/meanR", "net/peak", "net/mean"))
    print("-" * 122)
    for cls in ("SIG", "MULTI"):
        for book in SHORTLIST:
            if CLS[book] != cls:
                continue
            r = out["books"][book]["oos"]
            print("%-32s %5s %6d %7.2f %9.2f %11.3f %10.1f %10.2f %10.1f"
                  % (book, cls, r["peak_concurrent"], r["mean_concurrent"],
                     r["max_dd"], r["dd_per_capital_R"], r["dd_per_mean_R"],
                     r["net_per_capital_R"], r["net_per_mean_R"]))
        print()

    print("=" * 122)
    print("THE POINT THAT MATTERS MOST")
    print("=" * 122)
    sm = [out["books"][b]["oos"]["mean_concurrent"] for b in sig]
    mm = [out["books"][b]["oos"]["mean_concurrent"] for b in mul]
    sp = [out["books"][b]["oos"]["peak_concurrent"] for b in sig]
    mp = [out["books"][b]["oos"]["peak_concurrent"] for b in mul]
    print("  PEAK concurrency   SIG %s        MULTI %s" % (sp, mp))
    print("  MEAN concurrency   SIG %.2f-%.2f    MULTI %.2f-%.2f" % (min(sm), max(sm), min(mm), max(mm)))
    print()
    print("  The multi books are NOT running many positions most of the time. Their")
    print("  mean concurrency is under 1.1, which is barely above the serial books'")
    print("  0.29-0.43. What they have is a rare spike to 6-9 that the serial books")
    print("  physically cannot have.")
    print()
    print("  So peak-normalising penalises them for an event that is unusual rather")
    print("  than typical, and mean-normalising says they deploy about the same")
    print("  capital as a serial book most of the time. Neither normalisation alone")
    print("  is the answer, and the honest summary is that the 'multi vs serial'")
    print("  risk comparison was being made on a number that did not measure it.")

    print("=" * 122)
    print("WHAT CHANGES WHEN YOU NORMALISE")
    print("=" * 122)
    def best(names, key, rev=True):
        vals = [(b, out["books"][b]["oos"][key]) for b in names
                if out["books"][b]["oos"][key] is not None]
        return (min if rev else max)(vals, key=lambda x: x[1])

    print("  Ranked by raw max_dd (the misleading way, lower better):")
    print("    SIG    best: %s (%s)" % best(sig, "max_dd"))
    print("    MULTI  best: %s (%s)" % best(mul, "max_dd"))
    print()
    print("  Ranked by drawdown per R of capital (the fair way, lower better):")
    bs = best(sig, "dd_per_capital_R")
    bm = best(mul, "dd_per_capital_R")
    print("    SIG    best: %s (%s)" % bs)
    print("    MULTI  best: %s (%s)" % bm)
    print()
    print("  Ranked by net per R of capital (return on the capital, higher better):")
    print("    SIG    best: %s (%s)" % best(sig, "net_per_capital_R", rev=False))
    print("    MULTI  best: %s (%s)" % best(mul, "net_per_capital_R", rev=False))
    print()
    print("  A multi book that wins on max_dd and loses on DD/capitalR was never")
    print("  safer - it was simply holding more risk at once while the ratio of")
    print("  drawdown to total return kept looking tidy.")

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(out, indent=1, default=float))
    print()
    print("wrote %s  (%.0fs)" % (OUT.name, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())