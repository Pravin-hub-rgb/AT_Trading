"""Stage 1 — Multi-config portfolio book (descriptive Phase 1, IS + OOS).

Question: do the surviving lanes COMBINE into a better book than any single lane?

Pre-frozen portfolio members (Stage B winners, no post-hoc arms):
  champion   -> half+delay1+skipD   (curve pass both, Stage B 24.41)
  utcsat     -> half+delay1+skipD
  age10      -> retest_0.25         (retest_fill 0.25 + retest_wait 240)
Plus baseline portfolio control (all three lanes, default params).

Per portfolio k lanes:
  full  -> every trade still 1R risk (capital: up to k concurrent R)
  scaled-> each lane at 1/k size (total risk ~= single lane; fair vs single)

Reported per arm: n, net, net/yr, PF, maxDD, ulcer, sortino, calmar,
  max_streak, pos-month%, yearly. Pairwise daily-R Pearson correlation,
  interval overlap %, max concurrent cross-lane positions.

RESEARCH_POLICY: descriptive only; no automatic ship gate.
Run: $env:PYTHONIOENCODING='utf-8'; python -u live_stuff/tests/exp_portfolio_book.py
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
from test_experiments_craze import build_module
from test_4_new_concepts import load_fine_1m, load_unseen
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING

from exp_equity_quality import equity_quality

OUT = ROOT / "live_stuff/tests/_portfolio_book_results.json"
YEARS = {"is": 3.67, "oos": 2.0}

HALF = dict(exp_trail_half=1, exp_trail_delay_r=1.0)
SKIPD = dict(exp_skip_decisive=1)
RETEST = dict(exp_retest_fill=0.25, exp_retest_wait=240)

LANES = (
    ("champion", "champion_multi_sw10", dict(HALF, **SKIPD)),
    ("utcsat", "utcsat_multi_sw10", dict(HALF, **SKIPD)),
    ("age10", "age10_dirmatch_swingpause_single_sw10", dict(RETEST)),
)

PAIRS = (("champion", "utcsat"), ("champion", "age10"), ("utcsat", "age10"))
TRIO = ("champion", "utcsat", "age10")


def load_scope(scope):
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
        sw10 = _compute_swings(f1h, "continuous", min_bars=10)
        return {
            "c15": c15, "sw15": sw15, "c1h": c1h, "sw10": sw10,
            "fine": load_fine_1m(c15[0]["ts"], c15[-1]["ts"]),
        }
    data = get_data()
    identity_gate(data, build_module())
    return data


def run(sim, data, params, **flags):
    out = sim(
        data["c1h"], data["sw10"], data["c15"], data["sw15"],
        fine_ltf=data["fine"], **{**params, **flags},
    )
    return out["ltf_trades"] if isinstance(out, dict) else out


def scaled_trades(trades, w):
    out = []
    for t in trades:
        t2 = dict(t)
        t2["r_multiple"] = round(float(t["r_multiple"]) * w, 6)
        out.append(t2)
    return out


def daily_r(trades):
    by_day = defaultdict(float)
    for t in trades:
        d = str(t.get("exit_date") or t.get("entry_date") or "")[:10]
        by_day[d] += net_r([t])
    return by_day


def pearson(a, b):
    ks = sorted(set(a) | set(b))
    if len(ks) < 3:
        return None
    xs = [a.get(k, 0.0) for k in ks]
    ys = [b.get(k, 0.0) for k in ks]
    n = len(ks)
    mx = sum(xs) / n
    my = sum(ys) / n
    sx = sum((x - mx) ** 2 for x in xs) ** 0.5
    sy = sum((y - my) ** 2 for y in ys) ** 0.5
    if sx < 1e-12 or sy < 1e-12:
        return None
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return round(cov / (sx * sy), 4)


def overlap_stats(trades_by_lane, names):
    ivs = {n: [(int(t["entry_ts"]), int(t["exit_ts"])) for t in trades_by_lane[n]]
           for n in names}
    pairs = {}
    for a, b in combinations(names, 2):
        hits_a = sum(1 for s, e in ivs[a]
                     if any(s < e2 and e > s2 for s2, e2 in ivs[b]))
        hits_b = sum(1 for s, e in ivs[b]
                     if any(s < e2 and e > s2 for s2, e2 in ivs[a]))
        pairs[f"{a}|{b}"] = {
            "a_overlapping": hits_a, "a_n": len(ivs[a]),
            "b_overlapping": hits_b, "b_n": len(ivs[b]),
            "pct_a": round(100.0 * hits_a / len(ivs[a]), 1) if ivs[a] else 0.0,
            "pct_b": round(100.0 * hits_b / len(ivs[b]), 1) if ivs[b] else 0.0,
        }
    events = []
    for n in names:
        for s, e in ivs[n]:
            events.append((s, 1))
            events.append((e, -1))
    events.sort()
    cur = mx = 0
    for _, d in events:
        cur += d
        mx = max(mx, cur)
    return {"pairs": pairs, "max_concurrent": mx}


def corr_matrix(trades_by_lane, names):
    dr = {n: daily_r(trades_by_lane[n]) for n in names}
    m = {}
    for a, b in combinations(names, 2):
        m[f"{a}|{b}"] = pearson(dr[a], dr[b])
    return m


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  STAGE 1 — MULTI-CONFIG PORTFOLIO BOOK (descriptive Phase 1, IS + OOS)", flush=True)
    print("=" * 100, flush=True)

    sim = build_module()

    payload = {
        "instrument": "BTCUSDT_BYBIT",
        "stage": "portfolio_book",
        "lens": "descriptive; no automatic ship gate",
        "years": YEARS,
        "lanes": [{"name": n, "cfg": c, "flags": f} for n, c, f in LANES],
        "scopes": {},
    }

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] years={YEARS[scope]} ===", flush=True)
        data = load_scope(scope)
        yrs = YEARS[scope]

        trades = {"base": {}, "cand": {}}
        for name, key, flags in LANES:
            cfg = EXPERIMENTS[key]
            params = {**BP, **cfg["params"]}
            params.setdefault("exp_partial_r", 0.0)
            trades["base"][name] = run(sim, data, params)
            trades["cand"][name] = run(sim, data, params, **flags)

        sc = {}

        print(f"\n  {'arm':<34} {'n':>4} {'net':>8} {'/yr':>7} {'DD':>6} "
              f"{'ulcer':>7} {'sort':>7} {'calmar':>7} {'streak':>6} {'PF':>6}",
              flush=True)

        def emit(label, m):
            print(f"  {label:<34} {m['n']:>4} {m.get('net', 0):>+8.1f} "
                  f"{m.get('net_per_yr', 0):>+7.1f} {m.get('max_dd', 0):>6.1f} "
                  f"{m.get('ulcer', 0):>7.2f} {m.get('sortino', 0):>7.2f} "
                  f"{m.get('calmar', 0):>7.3f} {m.get('max_streak', 0):>6} "
                  f"{m.get('pf', 0):>6.2f}", flush=True)

        for arm in ("base", "cand"):
            for name, _, _ in LANES:
                m = equity_quality(trades[arm][name], yrs)
                sc[f"single_{arm}_{name}"] = m
                emit(f"single {arm}/{name}", m)

            groups = list(PAIRS) + [TRIO]
            for grp in groups:
                merged = sorted(
                    (t for n in grp for t in trades[arm][n]),
                    key=lambda t: int(t["entry_ts"]),
                )
                k = len(grp)
                for mode, tt in (("full", merged),
                                 ("scaled", scaled_trades(merged, 1.0 / k))):
                    lbl = "+".join(grp)
                    m = equity_quality(tt, yrs)
                    sc[f"port_{arm}_{lbl}_{mode}"] = m
                    emit(f"port {arm}/{lbl} {mode}", m)

        # overlap + correlation (candidate lanes)
        ov = overlap_stats(trades["cand"], [n for n, _, _ in LANES])
        cm = corr_matrix(trades["cand"], [n for n, _, _ in LANES])
        cm_b = corr_matrix(trades["base"], [n for n, _, _ in LANES])
        print(f"\n  overlap (candidate): {json.dumps(ov)}", flush=True)
        print(f"  corr daily-R (candidate): {cm}", flush=True)
        print(f"  corr daily-R (baseline): {cm_b}", flush=True)
        sc["_overlap_candidate"] = ov
        sc["_corr_candidate"] = cm
        sc["_corr_baseline"] = cm_b

        payload["scopes"][scope] = sc

    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
