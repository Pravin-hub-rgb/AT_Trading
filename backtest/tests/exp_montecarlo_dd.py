"""Stage T — Monte Carlo drawdown distribution + kill-line (video Step 2).

NEW (prior art: Stage 4/24.4 did month-block bootstrap for TOTAL RETURN only;
DD distribution never computed). Pre-registered:

  Series: 4 lanes (baseline=champion default, champion/utcsat/age10 cand arms)
  Scopes: pooled 2021-26 (PRIMARY - the live line), IS-only, OOS-only (sanity)
  Methods: A = i.i.d. permutation, N=10000 (video's exact resampling)
           B = moving-block bootstrap, block=20 trades, N=10000 (secondary;
               preserves loss clustering - i.i.d. understates DD tail)
  Per sim: maxDD_R (sum curve), maxDD_pct (per-trade compounding 1+r*1%,
           1R=1% equity), longest underwater (trades), max loss streak,
           total return%.
  Observed metrics always on entry-time order; MC ignores order (multiset).
  Outputs: P50/P95/P99/max per metric, historical percentile, kill-line =
           P99 under BOTH methods (conservative). Risk scaling: lines are at
           1R=1% equity - scale linearly with risk-per-trade.
  Milestones (Stage U input): n in {50,100,200,300} without-replacement
           samples from POOLED series, N=5000: P5/P50/P95 bands for
           avgR/trade, WR%, PF, maxDD%.
  Seed 42 (reproducibility). Descriptive only - no gate authored.

Run: $env:PYTHONIOENCODING='utf-8'; python -u backtest/tests/exp_montecarlo_dd.py
"""
from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
from test_experiments_craze import build_module
from test_4_new_concepts import load_fine_1m, load_unseen
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING

OUT = ROOT / "backtest/tests/_montecarlo_dd_results.json"
N_SIM = 10000
N_MILE = 5000
BLOCK = 20
RISK_PCT = 1.0  # 1R = 1% equity
SEED = 42
MILESTONES = (50, 100, 200, 300)
PCTS = (5, 50, 95, 99)

HALF = dict(exp_trail_half=1, exp_trail_delay_r=1.0)
SKIPD = dict(exp_skip_decisive=1)
RETEST = dict(exp_retest_fill=0.25, exp_retest_wait=240)

LANES = (
    ("baseline", "champion_multi_sw10", {}),
    ("champion", "champion_multi_sw10", dict(HALF, **SKIPD)),
    ("utcsat", "utcsat_multi_sw10", dict(HALF, **SKIPD)),
    ("age10", "age10_dirmatch_swingpause_single_sw10", dict(RETEST)),
)


def run(sim, data, params, **flags):
    out = sim(
        data["c1h"], data["sw10"], data["c15"], data["sw15"],
        fine_ltf=data["fine"], **{**params, **flags},
    )
    trades = out["ltf_trades"] if isinstance(out, dict) else out
    return sorted(trades, key=lambda t: int(t["entry_ts"]))


def sim_metrics(rs):
    cum = 0.0
    peak = 0.0
    maxdd = 0.0
    uw = 0
    maxuw = 0
    streak = 0
    maxstreak = 0
    eq = 1.0
    peakeq = 1.0
    maxddpct = 0.0
    wins = 0
    pf_num = 0.0
    pf_den = 0.0
    for r in rs:
        if r > 0:
            wins += 1
            pf_num += r
            streak = 0
        else:
            streak += 1
            if streak > maxstreak:
                maxstreak = streak
            pf_den -= r
        cum += r
        if cum > peak:
            peak = cum
            uw = 0
        else:
            uw += 1
            if uw > maxuw:
                maxuw = uw
            d = peak - cum
            if d > maxdd:
                maxdd = d
        eq *= (1.0 + r * RISK_PCT / 100.0)
        if eq > peakeq:
            peakeq = eq
        else:
            d = (peakeq - eq) / peakeq * 100.0
            if d > maxddpct:
                maxddpct = d
    n = len(rs)
    pf = (pf_num / pf_den) if pf_den > 0 else 999.0
    return {
        "maxdd_r": maxdd, "maxdd_pct": maxddpct, "maxuw": maxuw,
        "maxstreak": maxstreak, "total_pct": (eq - 1.0) * 100.0,
        "avg_r": sum(rs) / n, "wr": 100.0 * wins / n, "pf": pf,
    }


def pct(sorted_arr, p):
    k = min(len(sorted_arr) - 1,
            max(0, int(round((p / 100.0) * (len(sorted_arr) - 1)))))
    return sorted_arr[k]


def summarize(vals, observed=None):
    s = sorted(vals)
    out = {f"P{p}": round(pct(s, p), 2) for p in PCTS}
    out["max"] = round(s[-1], 2)
    out["mean"] = round(sum(s) / len(s), 2)
    if observed is not None:
        out["observed"] = round(observed, 2)
        out["obs_pctile"] = round(100.0 * sum(1 for v in s if v <= observed)
                                  / len(s), 2)
    return out


def run_iid(rs, rng, n_sim):
    keys = ("maxdd_r", "maxdd_pct", "maxuw", "maxstreak", "total_pct")
    acc = {k: [] for k in keys}
    n = len(rs)
    for _ in range(n_sim):
        m = sim_metrics(rng.sample(rs, n))
        for k in keys:
            acc[k].append(m[k])
    return acc


def run_block(rs, rng, n_sim, block):
    keys = ("maxdd_r", "maxdd_pct", "maxuw", "maxstreak", "total_pct")
    acc = {k: [] for k in keys}
    n = len(rs)
    for _ in range(n_sim):
        seq = []
        while len(seq) < n:
            st = rng.randrange(n)
            seq.extend(rs[st:st + block])
        m = sim_metrics(seq[:n])
        for k in keys:
            acc[k].append(m[k])
    return acc


def milestone_bands(rs, rng):
    out = {}
    n_all = len(rs)
    for m in MILESTONES:
        if m > n_all:
            out[m] = None
            continue
        avgs, wrs, pfs, dds = [], [], [], []
        for _ in range(N_MILE):
            s = rng.sample(rs, m)
            mm = sim_metrics(s)
            avgs.append(mm["avg_r"])
            wrs.append(mm["wr"])
            pfs.append(mm["pf"] if mm["pf"] < 999 else 100.0)
            dds.append(mm["maxdd_pct"])
        out[m] = {
            "avg_r": summarize(avgs), "wr": summarize(wrs),
            "pf": summarize(pfs), "maxdd_pct": summarize(dds),
        }
    return out


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print(f"  STAGE T — MONTE CARLO DD DISTRIBUTION + KILL-LINE "
          f"(N={N_SIM} iid + {N_SIM} block{BLOCK}, seed {SEED}, 1R={RISK_PCT}%)",
          flush=True)
    print("=" * 100, flush=True)

    sim = build_module()

    print("loading OOS...", flush=True)
    (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
    oos_data = {
        "c15": c15, "sw15": _compute_swings(f15, "continuous",
                                            min_bars=SWING["min_bars_15m"]),
        "c1h": c1h, "sw10": _compute_swings(f1h, "continuous", min_bars=10),
        "fine": load_fine_1m(c15[0]["ts"], c15[-1]["ts"]),
    }
    print("loading IS...", flush=True)
    is_data = get_data()
    identity_gate(is_data, build_module())

    series = {}  # lane -> scope -> net-R list (entry-time order)
    for name, key, flags in LANES:
        cfg = EXPERIMENTS[key]
        params = {**BP, **cfg["params"]}
        params.setdefault("exp_partial_r", 0.0)
        t_is = run(sim, is_data, params, **flags)
        t_oos = run(sim, oos_data, params, **flags)
        series[name] = {
            "is": [net_r([t]) for t in t_is],
            "oos": [net_r([t]) for t in t_oos],
            "pooled": [net_r([t]) for t in
                       sorted(t_oos + t_is, key=lambda t: int(t["entry_ts"]))],
        }
        print(f"  {name}: IS {len(t_is)}t OOS {len(t_oos)}t "
              f"pooled {len(t_is) + len(t_oos)}t", flush=True)

    payload = {
        "stage": "montecarlo_dd",
        "lens": "descriptive; kill-line proposal = P99 both methods",
        "n_sim": N_SIM, "block": BLOCK, "seed": SEED, "risk_pct": RISK_PCT,
        "methods": ["iid_permutation", f"moving_block_bootstrap_b{BLOCK}"],
        "series": {},
    }

    for name, _, _ in LANES:
        payload["series"][name] = {}
        for scope in ("pooled", "is", "oos"):
            rs = series[name][scope]
            obs = sim_metrics(rs)
            print(f"\n  --- {name} / {scope} (n={len(rs)}) "
                  f"obs maxDD {obs['maxdd_r']:.1f}R / {obs['maxdd_pct']:.1f}% "
                  f"uw {obs['maxuw']} streak {obs['maxstreak']} "
                  f"total {obs['total_pct']:.0f}% ---", flush=True)
            iid = run_iid(rs, random.Random(SEED + 1), N_SIM)
            blk = run_block(rs, random.Random(SEED + 2), N_SIM, BLOCK)
            entry = {"observed": {k: round(obs[k], 2)
                                  for k in ("maxdd_r", "maxdd_pct", "maxuw",
                                            "maxstreak", "total_pct")},
                     "iid": {}, "block": {}}
            for k in ("maxdd_r", "maxdd_pct", "maxuw", "maxstreak", "total_pct"):
                entry["iid"][k] = summarize(iid[k], obs[k])
                entry["block"][k] = summarize(blk[k], obs[k])
            dd_iid = entry["iid"]["maxdd_pct"]["P99"]
            dd_blk = entry["block"]["maxdd_pct"]["P99"]
            entry["kill_line_pct"] = {
                "iid_p99": dd_iid, "block_p99": dd_blk,
                "line_pct": max(dd_iid, dd_blk),
                "obs_pctile_iid": entry["iid"]["maxdd_pct"]["obs_pctile"],
                "obs_pctile_block": entry["block"]["maxdd_pct"]["obs_pctile"],
            }
            print(f"    maxDD% obs {obs['maxdd_pct']:.1f} | iid "
                  f"P50/P95/P99 {entry['iid']['maxdd_pct']['P50']}/"
                  f"{entry['iid']['maxdd_pct']['P95']}/"
                  f"{entry['iid']['maxdd_pct']['P99']} "
                  f"(obs pctile {entry['kill_line_pct']['obs_pctile_iid']}) | "
                  f"block P50/P95/P99 {entry['block']['maxdd_pct']['P50']}/"
                  f"{entry['block']['maxdd_pct']['P95']}/"
                  f"{entry['block']['maxdd_pct']['P99']} "
                  f"(obs pctile {entry['kill_line_pct']['obs_pctile_block']})",
                  flush=True)
            print(f"    KILL-LINE (max of P99s): "
                  f"{entry['kill_line_pct']['line_pct']}% | uw P99 "
                  f"{entry['iid']['maxuw']['P99']}/{entry['block']['maxuw']['P99']} "
                  f"trades | streak P99 "
                  f"{entry['iid']['maxstreak']['P99']}/"
                  f"{entry['block']['maxstreak']['P99']}", flush=True)
            payload["series"][name][scope] = entry
        payload["series"][name]["milestones_pooled"] = milestone_bands(
            series[name]["pooled"], random.Random(SEED + 3))
        mp = payload["series"][name]["milestones_pooled"]
        print(f"    milestones {name}: " + " | ".join(
            f"n={m}: avgR {v['avg_r']['P5']:+.2f}..{v['avg_r']['P95']:+.2f} "
            f"WR {v['wr']['P5']:.0f}..{v['wr']['P95']:.0f}% "
            f"DD {v['maxdd_pct']['P5']:.1f}..{v['maxdd_pct']['P95']:.1f}%"
            for m, v in mp.items() if v), flush=True)

    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
