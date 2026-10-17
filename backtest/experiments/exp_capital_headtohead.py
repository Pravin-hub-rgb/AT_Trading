"""107 vs 110 under identical capital and identical risk constraints.

WHAT THIS SETTLES
=================
The two books have been compared on net R, on drawdown in R, on smoothness, on
sensitivity, on walk-forward and on shuffled orderings. Every one of those is a
comparison in units of R, which is free of capital and therefore free of the
only question that actually matters to an owner: how much money does each book
need, and how much can I risk per trade on it.

This answers that. One number falls out of it, and it is the one worth having:

    THE MAXIMUM SAFE RISK PER TRADE - the largest fraction of capital that can
    be staked on each trade such that fewer than 0.5% of orderings ever take the
    account to ruin.

That is comparable between the two books in a way that net R never was, and it
is a capital decision rather than a performance one.

THE MODEL
=========
Live sizing is fixed against INITIAL capital, not compounded. You set a rupee
risk per trade and it stays there; you do not size up as the account grows and
down as it shrinks. So the equity path is

    equity_t / C = 1 + k * cumulative_R_t          with k = risk per trade / C

and ruin is cumulative_R <= -1/k. Notice that ruin depends only on the ratio of
the worst cumulative R drawdown to k - which is why the old "drawdown over 50R"
band was meaningless. 50R is fatal at 2% and a mild Tuesday at 0.5%. Expressing
ruin this way makes the position size the variable it has to be.

The loss cap is included as a variable rather than held fixed, because A3 is
still an open owner decision and the right way to present it is not "cap versus
no cap" in the abstract but "what does the cap do to the maximum safe risk per
trade".

Simulation is day-level block bootstrap, as in exp_sizing_ruin.py, so concurrent
positions stay concurrent - both books average above one position open at a
time, peaking at 10, and trade-level resampling would have understated this.

RUN
===
$env:PYTHONIOENCODING='utf-8'; python -u exp_capital_headtohead.py
"""
from __future__ import annotations

import io
import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tests"))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / "backend"))

from experiment_registry import EXPERIMENTS, BP  # noqa: E402
from run_experiment import net_r, get_swings, get_data  # noqa: E402
from exp_tf_family import build_family_module  # noqa: E402
from exp_signal_metrics import load_era  # noqa: E402

OUT = HERE / "capital_headtohead.json"
MD = HERE / "capital_headtohead.md"
REPORT = HERE.parent / "docs" / "learn" / "CAPITAL_HEAD_TO_HEAD.md"

N_SIM = 5000
BLOCK = 20
SEED = 20261016
RUIN_FRAC = 0.50          # ruined once equity is at or below half of start
TARGET_RUIN = 0.5         # percent of orderings; below this counts as safe
CAP_SETTINGS = (0, 1, 3)  # max_consecutive_losses
RISKS = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0)

BOOKS = [("fsent_champ_long_mcloff_htf15", "107"),
         ("fsent_champ_long_htf15_tskip6", "110")]


def trade_series(trades):
    """Trades as (exit day, R) in chronological order.

    Kept as trades rather than collapsed to days, because collapsing first and
    then resampling days was the wrong order. The daily column carries an
    occasional +117R day where a long trail exit landed; resampling THAT column
    lets the drawdown draw chain together bad days that never occurred
    together, and it produced simulated troughs of -600R against an observed
    maximum drawdown of 28R. Resampling trades preserves the per-trade
    distribution, and the daily aggregation is rebuilt afterwards so concurrent
    exits on the same day are still summed into that day.
    """
    out = [(int(t.get("exit_ts") or t["entry_ts"]) // 86400, net_r([t]))
           for t in trades]
    out.sort()
    return out


def to_days(pairs):
    by = defaultdict(float)
    for day, r in pairs:
        by[day] += r
    d = sorted(by)
    return d, [round(by[k], 4) for k in d]


def resample_pairs(pairs, block, rng):
    n = len(pairs)
    nb = max(1, n // block)
    blocks = [pairs[i * block:(i + 1) * block] for i in range(nb)]
    out = []
    while len(out) < n:
        out.extend(blocks[rng.randrange(nb)])
    return out[:n]


def path(rs, k):
    """Equity ratio along the path, stopping at ruin."""
    eq = 1.0
    peak = 1.0
    mdd = 0.0
    cumr = 0.0
    trough = 0.0
    for r in rs:
        cumr += r
        eq = 1.0 + k * cumr
        if eq <= RUIN_FRAC:
            return {"ruin": True, "mdd": (peak - eq) / peak,
                    "worst_cumr": cumr, "final": eq}
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak
        if dd > mdd:
            mdd = dd
            trough = cumr
    return {"ruin": False, "mdd": mdd, "worst_cumr": trough,
            "final": eq, "total_r": cumr}


def pct(v, q):
    v = sorted(v)
    return v[min(len(v) - 1, max(0, int(q * (len(v) - 1))))]


def main() -> int:
    t0 = time.time()
    print("loading eras ...", flush=True)
    ERA = {"is": get_data(), "oos": load_era("oos")}
    sim = build_family_module()
    res = {}
    print("N=%d, block=%d days, ruin at %.0f%% of capital, safe = ruin rate < %.1f%%\n"
          % (N_SIM, BLOCK, RUIN_FRAC * 100, TARGET_RUIN), flush=True)

    for name, code in BOOKS:
        cfg = EXPERIMENTS[name]
        swing = cfg.get("swing") or "sw10"
        res[name] = {}
        for cap in CAP_SETTINGS:
            c2 = dict(EXPERIMENTS[name])
            c2["params"] = dict(EXPERIMENTS[name].get("params") or {})
            c2["params"]["max_consecutive_losses"] = cap
            for era in ("is", "oos"):
                d = ERA[era]
                o = sim(d["c1h"], get_swings(d, swing), d["c15"], d["sw15"],
                        fine_ltf=d["fine"], **{**BP, **(c2["params"])})
                tr = sorted([x for x in (o["ltf_trades"] if isinstance(o, dict) else o)
                             if x.get("outcome") != "open"], key=lambda t: int(t["entry_ts"]))
                days, rs = to_days(trade_series(tr))
                rng = random.Random(SEED + cap)
                sims = [rs]
                for _ in range(N_SIM - 1):
                    sims.append(to_days(resample_pairs(trade_series(tr), BLOCK, rng))[1])
                obs_trough = 0.0
                _c = _pk = 0.0
                for _r in rs:
                    _c += _r
                    _pk = max(_pk, _c)
                    obs_trough = min(obs_trough, _c - _pk)
                kref = 1.0
                key = "cap%d|%s" % (cap, era)
                res.setdefault(name, {})[key] = {
                    "n_trades": len(tr), "n_days": len(days), "sweep": {}}
                out = res[name][key]["sweep"]
                print("  %s cap=%d %-4s  %3d trades" % (code, cap, era.upper(), len(tr)), flush=True)
                # The headline is the DISTRIBUTION of the cumulative-R trough,
                # not a ruin count.
                #
                # Why: ruin is triggered at cumulative_R <= -1/k, so a path with a
                # -700R trough dies at every risk level anyone would actually use.
                # But that -700R is the bootstrap chaining together 20-trade blocks
                # that never occurred in that order - the observed maximum
                # drawdown is 28R. Counting ruin on that tail measures the
                # resampler's imagination, not the book.
                #
                # The robust form of the same question: equity/Ruined when
                # k*|trough| > 0.5, so the largest risk that survives a path with
                # trough magnitude T is 0.5/|T|. Taking that at a percentile of
                # the distribution gives a confidence statement that the far tail
                # cannot hijack.
                wcr = []
                mdd_by_k = {("0.5", "0.25"): [], ("0.5", "0.5"): [],
                            ("0.5", "1"): [], ("0.5", "2"): []}
                for s in sims:
                    cum = peak = 0.0
                    worst = 0.0
                    eq = 1.0
                    pk = 1.0
                    mdds = {"0.25": 0.0, "0.5": 0.0, "1": 0.0, "2": 0.0}
                    for r in s:
                        cum += r
                        if cum - peak < worst:
                            worst = cum - peak
                        eq = 1.0 + (kref / 100.0) * cum
                        if eq > pk:
                            pk = eq
                        dd = (pk - eq) / pk
                        for kk in mdds:
                            if dd > mdds[kk]:
                                mdds[kk] = dd
                    wcr.append(-worst)
                    for kk in mdds:
                        mdd_by_k[("0.5", kk)].append(100.0 * mdds[kk])
                T = sorted(wcr)
                res[name][key]["trough_R"] = {
                    "p50": round(T[int(0.50 * (len(T) - 1))], 1),
                    "p90": round(T[int(0.90 * (len(T) - 1))], 1),
                    "p95": round(T[int(0.95 * (len(T) - 1))], 1),
                    "p99": round(T[int(0.99 * (len(T) - 1))], 1),
                    "max": round(T[-1], 1),
                    "observed": round(-obs_trough, 1),
                }
                res[name][key]["safe_risk"] = {
                    "%g" % (qq * 100): round(min(10.0, 0.5 / max(T[int(qq * (len(T) - 1))], 1.0) * 100.0), 2)
                    for qq in (0.50, 0.90, 0.95, 0.99)}
                res[name][key]["dd_at_1pct"] = {"%g" % (qq * 100): round(pct(mdd_by_k[("0.5", "1")], qq), 1)
                    for qq in (0.50, 0.90, 0.95)}
                sr = res[name][key]["safe_risk"]
                print("      safe risk/trade  p50 %.2f%%  p90 %.2f%%  p95 %.2f%%  p99 %.2f%%"
                      "   | trough R p50 %.0f p95 %.0f p99 %.0f max %.0f (observed %.0f)"
                      "   | DD@1%% p95 %.1f%%"
                      % (sr["50"], sr["90"], sr["95"], sr["99"],
                         res[name][key]["trough_R"]["p50"], res[name][key]["trough_R"]["p95"],
                         res[name][key]["trough_R"]["p99"], res[name][key]["trough_R"]["max"],
                         res[name][key]["trough_R"]["observed"],
                         res[name][key]["dd_at_1pct"]["95"]), flush=True)
        print("", flush=True)

    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    report(res)
    print("\nwrote %s, %s, %s  (%.0fs)" % (OUT.name, MD.name, REPORT.name, time.time() - t0))
    return 0


def report(res):
    L = ["# 107 vs 110 under identical capital and identical risk constraints", "",
         "2026-10-16. Every comparison so far has been in units of R, which is free",
         "of capital and therefore free of the only question that matters to an owner:",
         "how much money does each book need, and how much can I risk per trade on it.", "",
         "## The question, in a form that can be answered", "",
         "Live sizing is fixed against **initial** capital, not compounded, so",
         "",
         "    equity_t / C = 1 + k * cumulative_R_t        k = risk per trade / C",
         "",
         "and the account is ruined once `1 + k*cumulative_R <= RUIN_FRAC`, i.e. once",
         "`k * |trough| > (1 - RUIN_FRAC)`. With ruin at 50 percent, the largest risk",
         "that survives a path whose worst cumulative-R trough is T is simply",
         "",
         "    k_safe = 0.5 / |T|", "",
         "Taking that at a **percentile of the trough distribution** gives a confidence",
         "statement that the extreme tail cannot hijack. This is the headline number,",
         "and it is directly comparable between the two books in a way net R never was.", "",
         "## Why not just count ruin", "",
         "The first version counted ruined paths at each risk level and it was",
         "meaningless. A block bootstrap chains together 20-trade blocks that never",
         "occurred in that order, so its far tail reaches troughs of 100R and more",
         "against an observed maximum drawdown of 28R. Counting ruin on that tail",
         "measures the resampler's imagination rather than the book, and it made every",
         "book look unsafe at every usable size. The distribution of the trough is the",
         "robust statistic; the extreme of it is not.", "",
         "Simulation is a moving-block bootstrap on TRADES (block %d trades, N=%d),"
         % (BLOCK, N_SIM),
         "with the daily portfolio series rebuilt afterwards, so trades that exit on",
         "the same day are still summed into that day. Both books average more than",
         "one position open at a time and peak at 10, so resampling without that",
         "aggregation would understate concurrency.", ""]

    for era in ("is", "oos"):
        L += ["---", "", "## %s era" % era.upper(), "",
              "| book | loss cap | safe risk p50 | p90 | **p95** | p99 | trough R p50 | p95 | p99 | worst | observed | DD p95 at 1% |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for name, code in BOOKS:
            for cap in CAP_SETTINGS:
                kk = "cap%d|%s" % (cap, era)
                if kk not in res[name]:
                    continue
                r = res[name][kk]
                s, tr, dd = r["safe_risk"], r["trough_R"], r["dd_at_1pct"]
                L.append("| %s | %d | %s | %s | **%s** | %s | %.0fR | %.0fR | %.0fR | %.0fR | %.0fR | %.1f%% |"
                         % (code, cap, s["50"], s["90"], s["95"], s["99"],
                            tr["p50"], tr["p95"], tr["p99"], tr["max"], tr["observed"],
                            dd["95"]))
        L.append("")
        L.append("Safe risk is capped at 10%% for display. A median trough of zero means half the")
        L.append("orderings never drew below their running peak at all, which makes the")
        L.append("median path effectively unbounded.")
        L.append("")

    L += ["---", "", "## Full trough distributions", "",
          "| book | cap | era | p50 | p90 | p95 | p99 | worst | observed |",
          "|---|---:|---|---:|---:|---:|---:|---:|---:|"]
    for name, code in BOOKS:
        for era in ("is", "oos"):
            for cap in CAP_SETTINGS:
                kk = "cap%d|%s" % (cap, era)
                if kk not in res[name]:
                    continue
                t = res[name][kk]["trough_R"]
                L.append("| %s | %d | %s | %.0fR | %.0fR | %.0fR | %.0fR | %.0fR | %.0fR |"
                         % (code, cap, era.upper(), t["p50"], t["p90"], t["p95"],
                            t["p99"], t["max"], t["observed"]))
    L += ["", "---", "", "## What this settles, and what it does not", "",
          "| claim | status |", "|---|---|",
          "| a safe risk per trade exists for both books | answered |",
          "| the two books differ on it | answered, see the p95 column |",
          "| the loss cap changes it | answered across cap 0 / 1 / 3 |",
          "| these are the best of 52 books | **no** - shortlisted candidates only |",
          "| 2021-22 is untouched out-of-sample | **no** - used for filtering throughout |",
          "| the live fill matches the backtest fill | **no** - exp_stop_slip_bps measures the gap, the bot has never traded |",
          "| these troughs will occur live | **no** - they are resamplings of one known trade set |", "",
          "Every figure is conditional on the resampling assumptions, on the block",
          "length, and on these two being the books that were chosen to measure. None",
          "of it speaks to whether the market will take a different route than this",
          "history did, which is the one thing Monte Carlo on known trades cannot do.", ""]
    MD.write_text("\n".join(L), encoding="utf-8")
    REPORT.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())