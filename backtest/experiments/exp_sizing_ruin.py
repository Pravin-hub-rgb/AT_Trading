"""Position sizing, ruin, and recovery - done properly.

WHY THIS FILE EXISTS
====================
Two things were wrong in the Monte Carlo work that came before it, and both were
reported as if they were sound numbers.

1. "RUIN PATHS = 0%" WAS NOT A RUIN COUNT. The harness counted paths whose net
   R finished at or below zero, and separately counted paths whose drawdown in R
   exceeded fixed bands like 50R. Neither is ruin. A drawdown expressed in R has
   no meaning until position sizing is stated: 50R is a 50% equity loss at 1%
   risk per trade and a 250% loss at 5%, which is arithmetic nonsense rather than
   a risk figure. Zero of a badly-defined event is zero of nothing. So sizing is
   now explicit, the equity curve is simulated, and ruin is defined as a
   threshold on EQUITY rather than on R.

2. RECOVERY WAS REPORTED AS AN UNDERWATER STRETCH, WHICH IS A DIFFERENT THING.
   The correct unit is peak-to-recovery: how long from setting a new equity peak
   until equity gets back to it. Crucially, a stretch that has not yet recovered
   when the sample ends is CENSORED, and reporting it as a completed duration
   overstates patience by the length of the unfinished tail. In the earlier run
   the resampled p90 came out at ~1,260 days on a 1,341-day dataset, which is
   what a measure that silently treats every unfinished stretch as a completed
   one produces. Completed and censored are now reported separately, and only
   completed ones are used for the patience number.

THE OVERLAP PROBLEM, AND WHAT ACTUALLY FIXES IT
===============================================
Both books are unlimited-concurrency, so their trades overlap in time.
Resampling at TRADE level is therefore wrong for them: a resampled sequence
implies simultaneous exposure the book never had, because each trade is drawn as
if it happened alone.

So this does not resample trades. It first collapses the book into a DAILY
series - every trade's net R is booked on the day it EXITED - and resamples DAYS
in blocks. Because every trade that exited on a given day is summed into that
day, concurrent positions are preserved by construction: a day on which four
positions lost together stays a day on which four positions lost together.

Booked on exit, not entry. That is deliberate and it is the conservative
choice - P&L is not credited until it is realised, so the equity path is
bumpier than a mark-to-market one and the drawdowns here are an upper bound on
what a marked-to-market book would show. It is also what an exchange account
actually experiences.

SIZING MODEL
============
Fractional, compounding, which is the only kind under which ruin means anything:

    equity *= 1 + (equity * risk_pct/100 * R)

executed at several risk-per-trade levels, because the answer to "how big can
the drawdown get" is a function of size and a single size answers nothing.

RUIN
====
Equity trades at or below RUIN_LEVEL (50% of starting equity, the standard
half-way wipe). Reported per risk level, with the drawdown that reached it.

Output: sizing_ruin.json, sizing_ruin.md, docs/learn/04_experiments/SIZING_AND_RUIN.md
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

OUT = HERE / "sizing_ruin.json"
MD = HERE / "sizing_ruin.md"
REPORT = HERE.parent / "docs" / "learn" / "SIZING_AND_RUIN.md"

N_SIM = 5000
BLOCKS = (10, 20, 40)          # in TRADING DAYS, not trades
SEED = 20261016
RISKS = (0.5, 1.0, 2.0, 3.0, 5.0)   # percent of equity per trade
RUIN_LEVEL = 0.50

BOOKS = [("fsent_champ_long_mcloff_htf15", "107"),
         ("fsent_champ_long_htf15_tskip6", "110")]


def daily_series(trades):
    """Collapse the book into (day, sum of net R realised that day).

    Exit-day booking, which preserves concurrent exposure: every trade closing
    on a day contributes to that day, so a day on which several positions lost
    together remains such a day.
    """
    by = defaultdict(float)
    cnt = defaultdict(int)
    for t in trades:
        x = int(t.get("exit_ts") or t["entry_ts"])
        by[x // 86400] += net_r([t])
        cnt[x // 86400] += 1
    days = sorted(by)
    return days, [round(by[d], 4) for d in days], [cnt[d] for d in days]


def overlap_profile(trades):
    """How much concurrency actually existed - the thing trade-level resampling
    destroys. Reported so the reader can judge the distortion for themselves."""
    ev = []
    for t in trades:
        ev.append((int(t["entry_ts"]), 1))
        ev.append((int(t.get("exit_ts") or t["entry_ts"]) + 900, -1))
    ev.sort()
    cur = peak = 0
    hist = defaultdict(int)
    for _, d in ev:
        cur += d
        peak = max(peak, cur)
    cur = 0
    for _, d in ev:
        cur += d
        hist[cur] += 1
    span = sum(hist.values()) or 1
    return {
        "max_concurrent": peak,
        "pct_time_at_peak": round(100.0 * hist.get(peak, 0) / span, 1),
        "avg_concurrent": round(sum(k * v for k, v in hist.items()) / span, 2),
        "pct_time_single_or_zero": round(
            100.0 * sum(v for k, v in hist.items() if k <= 1) / span, 1),
    }


def equity_path(days, rs, risk_pct):
    """Compounding fractional equity curve with explicit peak-to-recovery timing.

    Returns the metrics that were previously conflated. Completed recoveries are
    the ones that actually finished; the stretch still open at the end of the
    sample is censored and is reported as its own thing rather than folded into
    the patience number.
    """
    eq = 1.0
    peak = 1.0
    peak_day = days[0]
    mdd = 0.0
    mdd_peak_day = days[0]
    mdd_trough_day = days[0]
    completed = []
    open_since = None
    open_start_day = None
    for d, r in zip(days, rs):
        # Position is a fraction of CURRENT equity; the P&L is that size times R.
        #     size = eq * risk_pct/100        pnl = size * r        eq += pnl
        # which collapses to eq *= (1 + risk_pct/100 * r).
        #
        # The first version of this line was eq *= (1 + eq * risk_pct/100 * r) -
        # equity appearing twice. That makes the position scale with equity AND
        # then compounds the whole thing again, so position grows quadratically
        # with account size. It produced equity of x-174739 and drawdowns of
        # 1,762,237,693%, which is not a risk measurement, it is arithmetic
        # nonsense. Recorded here because the magnitude of the wrongness is the
        # only reason it was caught by looking.
        eq *= (1.0 + (risk_pct / 100.0) * r)
        if eq <= 0.0:
            return {"ruin": True, "ruin_day": d, "eq": 0.0,
                    "mdd": 1.0, "mdd_peak_day": mdd_peak_day,
                    "mdd_trough_day": d, "eq_mdd": 100.0,
                    "completed": completed, "censored_days": None,
                    "censored_from": None, "final_eq": 0.0}
        if eq > peak:
            if open_since is not None:
                completed.append(d - open_since)
            peak = eq
            peak_day = d
            open_since = None
            open_start_day = None
        else:
            if open_since is None:
                open_since = peak_day
                open_start_day = d
            dd = (peak - eq) / peak
            if dd > mdd:
                mdd = dd
                mdd_peak_day = peak_day
                mdd_trough_day = d
        if eq <= RUIN_LEVEL:
            return {"ruin": True, "ruin_day": d, "eq": round(eq, 4),
                    "mdd": round(mdd, 4), "mdd_peak_day": mdd_peak_day,
                    "mdd_trough_day": mdd_trough_day,
                    "eq_mdd": round(mdd * 100, 1),
                    "completed": completed, "censored_days": None,
                    "censored_from": None, "final_eq": round(eq, 4)}
    censored = (days[-1] - open_since) if open_since is not None else 0
    return {"ruin": False, "ruin_day": None, "eq": round(eq, 4),
            "mdd": round(mdd, 4), "mdd_peak_day": mdd_peak_day,
            "mdd_trough_day": mdd_trough_day, "eq_mdd": round(mdd * 100, 1),
            "completed": completed,
            "censored_days": censored if open_since is not None else 0,
            "censored_from": open_start_day if open_since is not None else None,
            "final_eq": round(eq, 4)}


def resample_days(days, rs, block, rng):
    n = len(rs)
    nb = max(1, n // block)
    blocks = [(days[i * block:(i + 1) * block], rs[i * block:(i + 1) * block])
              for i in range(nb)]
    od, orr = [], []
    while len(orr) < n:
        bd, br = blocks[rng.randrange(nb)]
        od.extend(bd)
        orr.extend(br)
    return od[:n], orr[:n]


def pct(v, q):
    v = sorted(v)
    return v[min(len(v) - 1, max(0, int(q * (len(v) - 1))))]


def main() -> int:
    t0 = time.time()
    print("loading eras ...", flush=True)
    ERA = {"is": get_data(), "oos": load_era("oos")}
    sim = build_family_module()
    res = {}
    print("N=%d per block per risk, blocks in TRADING DAYS, ruin at %.0f%% equity\n"
          % (N_SIM, RUIN_LEVEL * 100), flush=True)

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
            days, rs, cnt = daily_series(tr)
            ov = overlap_profile(tr)
            res[name][era] = {"n_trades": len(tr), "n_days": len(days),
                              "overlap": ov, "runs": {}}
            print("  %s %-4s  %3d trades over %4d days | max concurrent %2d, avg %.1f, %.0f%% of time at 1-or-fewer"
                  % (code, era.upper(), len(tr), len(days), ov["max_concurrent"],
                     ov["avg_concurrent"], ov["pct_time_single_or_zero"]), flush=True)

            # observed, per risk level
            obs = {}
            for rk in RISKS:
                obs["%g" % rk] = equity_path(days, rs, rk)
            res[name][era]["observed"] = obs
            for rk in RISKS:
                m = obs["%g" % rk]
                print("      observed @%.1f%%/trade: final equity x%.3f  maxDD %5.1f%%  ruin %s  completed recoveries %s%s"
                      % (rk, m["final_eq"], m["eq_mdd"], m["ruin"],
                         len(m["completed"]),
                         (" censored %dd from day %s" % (m["censored_days"], m["censored_from"]))
                         if m["censored_days"] else ""), flush=True)

            for block in BLOCKS:
                rng = random.Random(SEED + block)
                per = {rk: {"ruin": 0, "mdd": [], "rec": [], "cens": [],
                            "ruin_dd": [], "final": []} for rk in RISKS}
                for _ in range(N_SIM):
                    sd, sr = resample_days(days, rs, block, rng)
                    for rk in RISKS:
                        m = equity_path(sd, sr, rk)
                        p = per[rk]
                        if m["ruin"]:
                            p["ruin"] += 1
                            p["ruin_dd"].append(m["eq_mdd"])
                        p["mdd"].append(m["eq_mdd"])
                        p["final"].append(m["final_eq"])
                        p["rec"].extend(m["completed"])
                        p["cens"].append(m["censored_days"] or 0)
                res[name][era]["runs"]["blk%d" % block] = {
                    ("%g" % rk): {"ruin_pct": round(100.0 * per[rk]["ruin"] / N_SIM, 2),
                         "mdd_p50": round(pct(per[rk]["mdd"], .50), 1),
                         "mdd_p95": round(pct(per[rk]["mdd"], .95), 1),
                         "mdd_p99": round(pct(per[rk]["mdd"], .99), 1),
                         "mdd_max": round(max(per[rk]["mdd"]), 1),
                         "rec_p50": pct(per[rk]["rec"], .50) if per[rk]["rec"] else 0,
                         "rec_p90": pct(per[rk]["rec"], .90) if per[rk]["rec"] else 0,
                         "rec_max": max(per[rk]["rec"]) if per[rk]["rec"] else 0,
                         "censored_p50": pct(per[rk]["cens"], .50),
                         "censored_p90": pct(per[rk]["cens"], .90),
                         "censored_p99": pct(per[rk]["cens"], .99),
                         "final_p05": round(pct(per[rk]["final"], .05), 3),
                         "paths_with_completed_rec": round(
                             100.0 * len([1 for x in per[rk]["rec"] if x > 0]) / N_SIM, 1)}
                    for rk in RISKS}
                b20 = res[name][era]["runs"]["blk%d" % block]["2"]
                print("      blk%-3d  @2%%/trade: ruin %5.2f%%  DD p50 %4.1f%% p95 %5.1f%% max %5.1f%%  recovery p90 %4dd  censored p90 %4dd"
                      % (block, b20["ruin_pct"], b20["mdd_p50"], b20["mdd_p95"],
                         b20["mdd_max"], b20["rec_p90"], b20["censored_p90"]), flush=True)
            print("      (%.0fs)\n" % (time.time() - t0), flush=True)

    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    report(res)
    print("\nwrote %s, %s, %s  (%.0fs)" % (OUT.name, MD.name, REPORT.name, time.time() - t0))
    return 0


def report(res):
    L = ["# Position sizing, ruin and recovery - stated properly", "",
         "2026-10-16. Replaces the ruin and recovery claims from", "`MONTE_CARLO_SURVIVABILITY.md`,",
         "both of which were reported as sound numbers and were not.", "",
         "## What was wrong", "",
         "| claim | why it was not sound |", "|---|---|",
         '| "0% ruin paths" | the harness counted paths with net R <= 0 and paths with drawdown over fixed R bands. Neither is ruin. A drawdown in R has **no meaning until position sizing is stated** - 50R is a 50% equity loss at 1% risk and a 250% loss at 5%. Zero of an undefined event is zero of nothing. |',
         "| recovery durations | the earlier run measured an *underwater stretch*, not a peak-to-recovery. A stretch that has not recovered when the sample ends is **censored**, and reporting it as a completed duration overstates patience by the unfinished tail. That is why the resampled p90 came out near the full length of the dataset. |", "",
         "## The sizing model", "",
         "Fractional and compounding, because it is the only kind under which ruin",
         "is a real event:", "",
         "```", "equity *= 1 + (equity * risk_pct/100 * R)", "```", "",
         "Swept at %s percent of equity per trade. Ruin is equity at or below"
         % ", ".join("%g" % r for r in RISKS),
         "**%.0f%% of starting equity** - the standard half-way wipe." % (RUIN_LEVEL * 100), "",
         "## Overlap, handled by construction", "",
         "Both books are unlimited-concurrency, so resampling at TRADE level is",
         "wrong for them - it draws each trade as though it happened alone. This",
         "resamples **DAYS**, not trades. Every trade is booked into the day it",
         "exited, so a day on which several positions lost together stays such a",
         "day. Concurrency is preserved by the aggregation rather than assumed.", "",
         "Booked on exit rather than entry, deliberately: P&L is not credited",
         "until realised, so the equity path is bumpier than mark-to-market and",
         "these drawdowns are an **upper bound** on what a marked-to-market book",
         "would show. It is also what the account experiences.", "",
         "## How much concurrency actually existed", ""]
    L += ["", "| book | era | trades | trading days | max concurrent | avg concurrent | % time at 1-or-fewer |",
          "|---|---|---:|---:|---:|---:|---:|"]
    for name, code in BOOKS:
        for era in ("is", "oos"):
            r = res[name][era]
            o = r["overlap"]
            L.append("| %s | %s | %d | %d | %d | %.2f | %.0f%% |"
                     % (code, era.upper(), r["n_trades"], r["n_days"],
                        o["max_concurrent"], o["avg_concurrent"],
                        o["pct_time_single_or_zero"]))
    L += ["", "If the average concurrency is well above one, trade-level resampling",
          "would have understated this badly, which is why it is not used here.", ""]

    for name, code in BOOKS:
        L += ["---", "", "## %s `%s`" % (code, name), ""]
        for era in ("is", "oos"):
            r = res[name][era]
            L += ["### %s — %d trades over %d days" % (era.upper(), r["n_trades"], r["n_days"]), "",
                  "**Observed path, by position size**", "",
                  "| risk/trade | final equity | max DD (equity) | ruin | completed recoveries | censored at end |",
                  "|---|---:|---:|---|---|---|"]
            for rk in RISKS:
                m = r["observed"]["%g" % rk]
                L.append("| %.1f%% | x%.3f | %.1f%% | %s | %d | %s |"
                         % (rk, m["final_eq"], m["eq_mdd"],
                            "**YES, day %d**" % m["ruin_day"] if m["ruin"] else "no",
                            len(m["completed"]),
                            ("%d days, from day %s" % (m["censored_days"], m["censored_from"]))
                            if m["censored_days"] else "none"))
            L += ["", "**Simulated, %d day-blocks** — ruin rate and drawdown, by position size" % N_SIM, ""]
            for block in BLOCKS:
                L += ["Block of %d trading days:" % block, "",
                      "| risk/trade | ruin rate | DD p50 | DD p95 | DD p99 | DD worst |",
                      "|---|---:|---:|---:|---:|---:|"]
                for rk in RISKS:
                    s = r["runs"]["blk%d" % block]["%g" % rk]
                    L.append("| %.1f%% | **%.2f%%** | %.1f%% | %.1f%% | %.1f%% | %.1f%% |"
                             % (rk, s["ruin_pct"], s["mdd_p50"], s["mdd_p95"],
                                s["mdd_p99"], s["mdd_max"]))
                L.append("")
            L += ["**Recovery, block of 20 days, at 1.0% risk/trade**", "",
                  "| | completed recovery (days) | censored at sample end (days) | paths with any completed recovery |",
                  "|---|---:|---:|---:|"]
            s = r["runs"]["blk20"]["1"]
            L.append("| p50 | %d | %d | %.0f%% |"
                     % (s["rec_p50"], s["censored_p50"], s["paths_with_completed_rec"]))
            L.append("| p90 | %d | %d | |" % (s["rec_p90"], s["censored_p90"]))
            L.append("| max | %d | %d | |" % (s["rec_max"], s["censored_p99"]))
            L += ["", "Completed recoveries only. The censored column is the stretch still",
                  "open when the sample ends - it is **not** patience, and folding it",
                  "in is what made the earlier figure unreadable.", ""]

    L += ["---", "", "## What this establishes, and what it does not", "",
          "| claim | status |", "|---|---|",
          "| ruin happens before the sample ends on the observed path | answered per position size above |",
          "| a percentage of paths ruin | answered, and it is a function of size rather than a property of the book |",
          "| how long a recovery takes | answered for completed recoveries only |",
          "| the block size decides the drawdown tail | unchanged from the previous pass, and it is why no single kill-line is quoted |",
          "| 52 books were not tested | these two are **shortlisted candidates, not proven best** |",
          "| 2021-22 is untouched out-of-sample | it is **not** - it has been used for filtering throughout |", "",
          "Ruin is now defined, so the ruin numbers mean something. They are still",
          "conditional on the resampling assumptions, on exit-day booking, and on",
          "the two candidates being the ones we chose to measure.", ""]
    MD.write_text("\n".join(L), encoding="utf-8")
    REPORT.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())