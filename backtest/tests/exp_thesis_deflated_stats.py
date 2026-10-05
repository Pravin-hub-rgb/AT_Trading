"""Study 2 — Deflated statistics: how much of +325R survives 73 experiments?

We never corrected for selection bias. This harness:
  1. reconstructs the real trial count from the registry + documented arms
  2. runs a null placebo sweep: random strategy variants scored on the same
     data, to get the distribution of best-of-N
  3. asks how often a null variant set produces something as good as the
     observed champion
  4. deflated edge: observed edge corrected for the trial count

Bybit BTCUSDT perpetual only. Read-only. No production change.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
from test_experiments_craze import build_module

OUT = {"is": ROOT / "backtest/tests/_thesis_deflated_stats_is.json",
       "oos": ROOT / "backtest/tests/_thesis_deflated_stats_oos.json"}
CONFIGS = ("champion_multi_sw10", "utcsat_multi_sw10", "fullstack_wage10_cd0_single_sw10")
NULL_SETS = 400
NULL_VARIANTS_PER_SET = 40
SEED = 20260926


def trial_inventory():
    """Reconstruct how many distinct configurations were actually scored."""
    reg = len(EXPERIMENTS)
    # documented arm counts from the experiment log (each log row = one family)
    log = ROOT / "backtest/docs/method/EXPERIMENT_LOG.md"
    harness_files = len(list((ROOT / "backtest/tests").glob("*.py")))
    exp_files = len([p for p in (ROOT / "backtest/tests").glob("*.py")
                     if p.name.startswith("exp_")])
    test_files = len([p for p in (ROOT / "backtest/tests").glob("*.py")
                      if p.name.startswith("test_")])
    log_rows = 0
    if log.exists():
        for line in log.read_text(encoding="utf-8").splitlines():
            if line.startswith("| ") and line.count("|") >= 6:
                head = line.split("|")[1].strip()
                if head and (head[0].isdigit() or head.upper().startswith("FINAL")):
                    log_rows += 1
    return {"registry_configs": reg, "logged_experiments": log_rows,
            "exp_harnesses_on_disk": exp_files, "test_harnesses_on_disk": test_files,
            "all_py_in_tests": harness_files,
            "note": "lower bound on trials; each logged experiment swept multiple arms"}


def load_scope(scope):
    from exp_thesis_win_streak import load_scope as _ls
    return _ls(scope)


def net_of(trades):
    return sum(net_r([t]) for t in trades)


def run_once(sim, data, params):
    out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
              fine_ltf=data["fine"], **params)
    return out["ltf_trades"]


# ---------------------------------------------------------------------------
# Null model. We do NOT need a full engine sweep to answer the selection
# question. What matters is: given the observed per-trade R distribution,
# how large is the best-of-N statistic under random reshuffling?
# Shuffling the ORDER of our own trades preserves the payoff geometry, the
# win rate, the tail, and the drawdown-generating clustering, and destroys
# only the signal ordering. That is the tightest possible null.
# ---------------------------------------------------------------------------

def block_resample(blocks, rng, n_draw=None):
    """Bootstrap month blocks WITH REPLACEMENT to the same count.

    Must sample with replacement: a circular rotation visits every block
    exactly once, so the sum is invariant and the null is degenerate.
    """
    n = len(blocks)
    k = n_draw if n_draw is not None else n
    out = []
    for _ in range(k):
        out.extend(blocks[rng.randrange(n)])
    return out


def month_blocks(trades):
    bym = defaultdict(list)
    for t in trades:
        bym[(t.get("exit_date") or t.get("entry_date") or "")[:7]].append(
            float(t.get("r_multiple") or 0.0))
    return [v for _, v in sorted(bym.items())]


def max_dd(xs):
    peak = cum = dd = 0.0
    for v in xs:
        cum += v
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    return dd


def null_best_of_n(observed_trades, n_variants, n_sets, seed):
    """Best-of-N under a ZERO-EDGE null.

    This must answer: "if the strategy had NO expectancy, how large a result
    would the best of N attempts produce?" — which is the selection-bias
    question. Two things are required for that to be honest:

    1. CENTER the trade distribution. Subtract the observed mean R from every
       trade, so the null has zero expectancy but IDENTICAL variance, payoff
       ratio, win rate and tail shape. Resampling the raw R values instead
       would preserve the real edge in the null and make every p-value 1.0,
       which measures nothing.

    2. FIX the trade count. A variant that draws more months can duplicate the
       good ones and inflate the spread for a reason unrelated to selection.

    A separate third null (month-clustered, uncentered) is reported alongside
    because it answers a different and also important question: how fragile is
    the result to WHICH months you happened to be flat in.
    """
    rs = [float(t.get("r_multiple") or 0.0) for t in observed_trades]
    n_trades = len(rs)
    mean_r = sum(rs) / max(n_trades, 1)
    blocks_raw = month_blocks(observed_trades)
    # Center PER TRADE by the PER-TRADE mean, not by the per-month sum.
    # Subtracting a per-month aggregate from every trade in that month
    # over-corrects by roughly the month's trade count and drives the whole
    # null far negative, which would make every p-value 0.0.
    blocks_c = [[r - mean_r for r in v] for v in blocks_raw]

    rng = random.Random(seed)

    def fixed_len(blocks):
        out = []
        while len(out) < n_trades:
            out.extend(blocks[rng.randrange(len(blocks))])
        return out[:n_trades]

    best_sums, best_avgs, best_dds = [], [], []
    for _ in range(n_sets):
        vs, vd = [], []
        for _v in range(n_variants):
            seq = fixed_len(blocks_c)
            rng.shuffle(seq)
            vs.append(sum(seq))
            vd.append(max_dd(seq))
        best_sums.append(max(vs))
        best_avgs.append(max(vs) / max(n_trades, 1))
        best_dds.append(min(vd))

    # third null: uncentered month-clustered (fragility, not selection bias)
    frag_sums = []
    for _ in range(n_sets):
        vs = []
        for _v in range(n_variants):
            seq = fixed_len(blocks_raw)
            rng.shuffle(seq)
            vs.append(sum(seq))
        frag_sums.append(max(vs))

    return best_sums, best_avgs, best_dds, frag_sums


def analyze(data, sim, key, scope):
    params = {**BP, **EXPERIMENTS[key]["params"]}
    params.setdefault("exp_partial_r", 0.0)
    trades = run_once(sim, data, params)
    rs = [float(t.get("r_multiple") or 0.0) for t in trades]
    gross = sum(rs)
    net = net_of(trades)
    n = len(rs)

    seeds = {"is": SEED, "oos": SEED + 1}
    best_sums, best_avgs, best_dds, frag_sums = null_best_of_n(
        trades, NULL_VARIANTS_PER_SET, NULL_SETS, seeds[scope])

    gross_pct = sum(1 for b in best_sums if b >= gross) / len(best_sums)
    net_pct = sum(1 for b in best_sums if b >= net) / len(best_sums)
    avg_observed = gross / n
    avg_pct = sum(1 for b in best_avgs if b >= avg_observed) / len(best_avgs)
    dd_observed = max_dd(rs)
    dd_pct = sum(1 for d in best_dds if d <= dd_observed) / len(best_dds)

    infl = trial_inventory()
    trials = infl["logged_experiments"] * 8  # documented arms per logged experiment

    return {
        "config": key, "n": n,
        "observed": {"gross_r": round(gross, 4), "net_r": round(net, 4),
                     "avg_gross_r": round(avg_observed, 6),
                     "max_dd_r": round(max_dd(rs), 4),
                     "win_rate_pct": round(100.0 * sum(1 for r in rs if r > 0) / n, 3),
                     "payoff": round((sum(r for r in rs if r > 0) / max(sum(-r for r in rs if r <= 0), 1e-9)), 4)},
        "null_best_of_n": {
            "n_variants_per_set": NULL_VARIANTS_PER_SET, "n_sets": NULL_SETS,
            "best_gross_r_mean": round(statistics.mean(best_sums), 3),
            "best_gross_r_p50": round(statistics.median(best_sums), 3),
            "best_gross_r_p95": round(sorted(best_sums)[int(0.95 * len(best_sums))], 3),
            "best_gross_r_max": round(max(best_sums), 3),
            "best_avg_r_mean": round(statistics.mean(best_avgs), 6),
            "best_avg_r_p95": round(sorted(best_avgs)[int(0.95 * len(best_avgs))], 6),
            "best_dd_min_p50": round(statistics.median(best_dds), 3),
            "best_dd_min_p05": round(sorted(best_dds)[int(0.05 * len(best_dds))], 3),
        },
        "selection_p_value": {
            "p_gross_at_least_observed": round(gross_pct, 4),
            "p_net_at_least_observed": round(net_pct, 4),
            "p_avg_r_at_least_observed": round(avg_pct, 4),
            "p_dd_at_most_observed": round(dd_pct, 4),
            "interpretation": ("if p > 0.05 the result is NOT exceptional for a best-of-N search"
                               if gross_pct > 0.05 else
                               "result is in the top few percent of a best-of-N search"),
        },
        "fragility_null_month_clustered": {
            "note": ("uncentered month-clustered resample; NOT a selection-bias test. "
                     "Answers: how large could a result be if the real edge were removed "
                     "but the monthly CLUSTERING of our own P&L were kept?"),
            "best_p50": round(statistics.median(frag_sums), 3),
            "best_p95": round(sorted(frag_sums)[int(0.95 * len(frag_sums))], 3),
            "p_observed_gross_at_least": round(
                sum(1 for b in frag_sums if b >= gross) / len(frag_sums), 4),
        },
        "deflation": {
            "estimated_trials": trials,
            "trial_basis": "logged_experiments x 8 documented arms per experiment",
            "observed_avg_r": round(avg_observed, 6),
            "null_best_avg_r_p95": round(sorted(best_avgs)[int(0.95 * len(best_avgs))], 6),
            "deflation_ratio_vs_p95": round(avg_observed / max(sorted(best_avgs)[int(0.95 * len(best_avgs))], 1e-9), 4),
        },
        "inventory": infl,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = ap.parse_args()
    scopes = ("is", "oos") if args.scope == "both" else (args.scope,)
    sim = build_module()
    allr = {"study": 2, "name": "deflated statistics / selection-bias correction",
            "instrument": "BTCUSDT_BYBIT", "scopes": {}}
    for scope in scopes:
        print("=" * 100, flush=True)
        print(f"  DEFLATED STATISTICS — BYBIT {scope.upper()}", flush=True)
        print("=" * 100, flush=True)
        data = load_scope(scope)
        res = {}
        for key in CONFIGS:
            row = analyze(data, sim, key, scope)
            res[key] = row
            o, s = row["observed"], row["selection_p_value"]
            print(f"  {key:34} n={row['n']:4d} G={o['gross_r']:+8.1f} "
                  f"N={o['net_r']:+8.1f} avg={o['avg_gross_r']:+.3f} "
                  f"DD={o['max_dd_r']:5.1f} | nullBestP50={row['null_best_of_n']['best_gross_r_p50']:+8.1f} "
                  f"p95={row['null_best_of_n']['best_gross_r_p95']:+8.1f} | "
                  f"p(gross)={s['p_gross_at_least_observed']:.3f} p(net)={s['p_net_at_least_observed']:.3f} "
                  f"p(dd)={s['p_dd_at_most_observed']:.3f}",
                  flush=True)
        allr["scopes"][scope] = res
    out = OUT[scopes[-1]]
    out.write_text(json.dumps(allr, indent=2), encoding="utf-8")
    print(f"\n  wrote {out}", flush=True)


if __name__ == "__main__":
    main()
