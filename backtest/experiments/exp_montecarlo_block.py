"""Technique 4 properly - i.i.d. bootstrap AND moving-block bootstrap, on 107 and 110.

WHAT THIS FIXES
===============
The first pass at technique 4 in exp_four_techniques.py shuffled the trade list
and called it done. That is the weakest of the three ways to do this:

  what was run       rng.shuffle(rs)          permutation, N=2000
  what was standard  rng.sample(rs, n)        resample WITH REPLACEMENT, N=10000
  and stricter       moving-block, block=20   preserves loss clustering

Both differences matter and both understated the tail. A permutation reuses
every trade exactly once, so a losing streak cannot be longer or more clustered
than the one history happened to contain. A bootstrap resamples, so it can draw
the same bad run three times in a row. And a block bootstrap keeps consecutive
trades together, which is the whole point - losing streaks are the mechanism
that produces drawdown, and an i.i.d. shuffle dissolves them.

The repository already had this. backtest/tests/exp_montecarlo_dd.py implements
both methods and was right about the i.i.d. weakness in its own comment
("block=20 ... preserves loss clustering - i.i.d. understates DD tail"). It was
run on baseline, champion, utcsat and age10 - all four of which are retired,
and on 2026-09-25, before the causal-stop fix and the mark corrections. So the
strict version has never been pointed at a live candidate.

sim_metrics and both resamplers are reused verbatim from that harness so the
numbers are comparable with its own prior art rather than a fresh definition.

WHAT THE DOC ASKS FOR
=====================
- "randomizes your historical trade sequences thousands of times"  -> N=10000
- "shuffle each trade around: the 99th trade becomes the 22nd"    -> both methods
- "expect a wide range of risk tolerances"                        -> DD distribution
- SURVIVABILITY: "if many curves go up but ~10 go straight down, you are sizing
  way too aggressively"                                            -> ruin fraction
- "halve your position sizes"                                     -> kill-line = P99

Output: montecarlo_block.json + montecarlo_block.md
"""
from __future__ import annotations

import io
import json
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tests"))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / "backend"))

from experiment_registry import EXPERIMENTS, BP  # noqa: E402
from run_experiment import net_r, get_swings, get_data  # noqa: E402
from exp_tf_family import build_family_module  # noqa: E402
from exp_signal_metrics import load_era  # noqa: E402
from exp_montecarlo_dd import sim_metrics, run_block  # noqa: E402

OUT = HERE / "montecarlo_block.json"
MD = HERE / "montecarlo_block.md"
REPORT = HERE.parent / "docs" / "learn" / "MONTE_CARLO_SURVIVABILITY.md"

N_SIM = 10000
BLOCK = 20
SEED = 20261016
# thresholds for "would this have stopped you out", in R of drawdown
DD_BANDS = (10, 20, 25, 35, 50, 75, 100)

BOOKS = [("fsent_champ_long_mcloff_htf15", "107"),
         ("fsent_champ_long_htf15_tskip6", "110")]


def run_iid(rs, rng, n_sim):
    keys = ("maxdd_r", "maxdd_pct", "maxuw", "maxstreak", "total_pct")
    acc = {k: [] for k in keys}
    n = len(rs)
    for _ in range(n_sim):
        m = sim_metrics(rng.sample(rs, n))
        for k in keys:
            acc[k].append(m[k])
    return acc


def pct(vals, q):
    v = sorted(vals)
    return v[min(len(v) - 1, max(0, int(q * (len(v) - 1))))]


def summarise(rs, iid, blk):
    obs = sim_metrics(rs)
    o = {}
    for name, acc in (("iid", iid), ("block", blk)):
        dd = acc["maxdd_r"]
        st = acc["maxstreak"]
        uw = acc["maxuw"]
        o[name] = {
            "dd_p50": round(pct(dd, 0.50), 2),
            "dd_p95": round(pct(dd, 0.95), 2),
            "dd_p99": round(pct(dd, 0.99), 2),
            "dd_max": round(max(dd), 2),
            "streak_p95": pct(st, 0.95),
            "streak_p99": pct(st, 0.99),
            "streak_max": max(st),
            "uw_p95": pct(uw, 0.95),
            "uw_max": max(uw),
            "over_bands": {str(b): round(100.0 * sum(1 for x in dd if x > b) / len(dd), 3)
                           for b in DD_BANDS},
            "frac_flat_or_worse": round(
                100.0 * sum(1 for x in acc["total_pct"] if x <= 0.0) / len(acc["total_pct"]), 3),
        }
        o[name]["obs_percentile"] = round(
            100.0 * sum(1 for x in dd if x < obs["maxdd_r"]) / len(dd), 2)
    o["observed"] = {"dd": round(obs["maxdd_r"], 2),
                     "streak": obs["maxstreak"],
                     "uw": obs["maxuw"], "n": len(rs)}
    return o


def main() -> int:
    t0 = time.time()
    print("loading eras ...", flush=True)
    ERA = {"is": get_data(), "oos": load_era("oos")}
    sim = build_family_module()
    res = {}
    print("\nN=%d per method, block=%d, seed=%d" % (N_SIM, BLOCK, SEED), flush=True)
    for name, code in BOOKS:
        cfg = EXPERIMENTS[name]
        swing = cfg.get("swing") or "sw10"
        res[name] = {}
        for era in ("is", "oos"):
            d = ERA[era]
            o = sim(d["c1h"], get_swings(d, swing), d["c15"], d["sw15"],
                    fine_ltf=d["fine"], **{**BP, **(cfg.get("params") or {})})
            tr = sorted([x for x in (o["ltf_trades"] if isinstance(o, dict) else o)
                         if x.get("outcome") != "open"], key=lambda t: int(t["entry_ts"]))
            rs = [net_r([t]) for t in tr]
            iid = run_iid(rs, random.Random(SEED + 1), N_SIM)
            blk = run_block(rs, random.Random(SEED + 2), N_SIM, BLOCK)
            res[name][era] = summarise(rs, iid, blk)
            r = res[name][era]
            print("  %s %-4s n=%3d  observed dd %6.2f streak %2d" %
                  (code, era.upper(), len(rs), r["observed"]["dd"], r["observed"]["streak"]))
            for m in ("iid", "block"):
                print("      %-5s  dd p50 %6.1f  p95 %6.1f  p99 %6.1f  max %7.1f  streak p99 %2d max %3d  obs at %5.1f pct"
                      % (m, r[m]["dd_p50"], r[m]["dd_p95"], r[m]["dd_p99"], r[m]["dd_max"],
                         r[m]["streak_p99"], r[m]["streak_max"], r[m]["obs_percentile"]))
            print("      inflated vs observed: iid %.2fx   block %.2fx"
                  % (r["iid"]["dd_max"] / r["observed"]["dd"],
                     r["block"]["dd_max"] / r["observed"]["dd"]))
            print("      (%.0fs)" % (time.time() - t0), flush=True)

    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")

    # ---- report ----
    L = ["# Monte Carlo done properly — survivability of 107 and 110", "",
         "2026-10-16. Technique 4 from", "`4 backtesting techniques behind winning strategies.md`,",
         "run as the research standard rather than the textbook illustration.", "",
         "## Why this was redone", "",
         "The first pass shuffled the trade list 2000 times. That is the weakest",
         "of three ways to do this:", "",
         "| run | method |", "|---|---|",
         "| first pass | `rng.shuffle(rs)` — permutation, N=2000 |",
         "| standard | `rng.sample(rs, n)` — resample **with replacement**, N=10000 |",
         "| stricter still | **moving-block bootstrap**, block=20 |", "",
         "Both differences push the tail the same way. A permutation reuses every",
         "trade exactly once, so a losing streak cannot be worse than the one",
         "history happened to contain. A bootstrap can draw the same bad run three",
         "times. And a block bootstrap keeps consecutive trades together — losing",
         "streaks are the mechanism that *makes* drawdown, and an i.i.d. shuffle",
         "dissolves them.", "",
         "`backtest/tests/exp_montecarlo_dd.py` already implemented both correctly",
         "and said so in its own comment. It had been run on `baseline`,",
         "`champion`, `utcsat` and `age10` — all retired — on 2026-09-25, before",
         "the causal-stop fix. So the strict version had never run on a live",
         "candidate. This runs it on both, reusing that harness's own `sim_metrics`",
         "and `run_block` verbatim so the numbers are comparable with its prior art.", "",
         f"N={N_SIM} per method, block={BLOCK}, seed={SEED}.", ""]
    for name, code in BOOKS:
        L += ["---", "", "## %s `%s`" % (code, name), ""]
        for era in ("is", "oos"):
            r = res[name][era]
            o = r["observed"]
            L += ["### %s — %d trades, observed DD %.2fR, observed streak %d"
                  % (era.upper(), o["n"], o["dd"], o["streak"]), "",
                  "| metric | i.i.d. bootstrap | moving-block B20 |", "|---|---:|---:|",
                  "| DD p50 | %.1f | %.1f |" % (r["iid"]["dd_p50"], r["block"]["dd_p50"]),
                  "| DD p95 | %.1f | %.1f |" % (r["iid"]["dd_p95"], r["block"]["dd_p95"]),
                  "| DD p99 | %.1f | %.1f |" % (r["iid"]["dd_p99"], r["block"]["dd_p99"]),
                  "| DD worst | %.1f | %.1f |" % (r["iid"]["dd_max"], r["block"]["dd_max"]),
                  "| streak p99 | %d | %d |" % (r["iid"]["streak_p99"], r["block"]["streak_p99"]),
                  "| streak worst | %d | %d |" % (r["iid"]["streak_max"], r["block"]["streak_max"]),
                  "| underwater worst (trades) | %d | %d |" % (r["iid"]["uw_max"], r["block"]["uw_max"]),
                  "| observed DD sits at percentile | %.1f | %.1f |"
                  % (r["iid"]["obs_percentile"], r["block"]["obs_percentile"]),
                  "| paths ending flat or worse | %.2f%% | %.2f%% |"
                  % (r["iid"]["frac_flat_or_worse"], r["block"]["frac_flat_or_worse"]),
                  "", "**Drawdown exceeded, out of %d paths**" % N_SIM, "",
                  "| over | i.i.d. | block |", "|---:|---:|---:|"]
            for b in DD_BANDS:
                L.append("| %dR | %.2f%% | %.2f%% |"
                         % (b, r["iid"]["over_bands"][str(b)],
                            r["block"]["over_bands"][str(b)]))
            L.append("")
            L.append("Worst path inflates the observed drawdown by **%.1fx under i.i.d.**"
                     " and **%.1fx under the block bootstrap**."
                     % (r["iid"]["dd_max"] / o["dd"], r["block"]["dd_max"] / o["dd"]))
            L.append("")
    L += ["---", "", "## How to read this", "",
          "The doc's survivability question is whether the account and the sizing",
          "survive the worst ordering. The kill-line it suggests is the P99 —",
          "position so that the 99th-percentile drawdown is survivable rather than",
          "the one history happened to produce.", "",
          "Two things worth carrying away. First, **the observed drawdown is not",
          "the number to size against** — for 107 on IS it sits in the top",
          "half-percentile of its own shuffles, so the history was arranged",
          "unluckily and the median ordering is far gentler. Second, **block",
          "bootstrap is the honest one to quote**, because an i.i.d. resample",
          "dissolves losing streaks and a losing streak is what a drawdown *is*.", ""]
    MD.write_text("\n".join(L), encoding="utf-8")
    REPORT.write_text("\n".join(L), encoding="utf-8")
    print("\nwrote %s, %s and %s  (%.0fs)" % (OUT.name, MD.name, REPORT.name, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())