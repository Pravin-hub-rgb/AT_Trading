"""Is the age10 OOS 2.18x transfer a real effect or a handful of trades?

THE QUESTION
------------
Cross-instrument Slice 4 moved age10 OOS from +43.2R (bybit) to +94.2R
(binance perp) - 2.18x - while every other lane/era DECLINED:

  champion   IS 0.78x   OOS 0.25x
  utcsat     IS 0.58x   OOS 0.13x
  age10      IS 0.42x   OOS 2.18x   <-- one lane doubled while all others fell

A single lane inverting direction while the rest decay is more likely noise
than a venue property. This measures WHERE the +94.2R comes from: is it spread
across the book, or carried by a couple of outliers?

PRE-REGISTERED (fixed before the run)
--------------------------------------
The transfer is called CONCENTRATED - i.e. luck-shaped rather than structural -
if ANY of these hold on the age10 OOS binance book:

  1. Top 5 trades contribute more than 50% of total net R.
  2. Removing the single best trade leaves net R below +20R (less than half of
     the bybit reference).
  3. Fewer than 10 trades carry a positive R of 3R or more.

If NONE hold, the lift is broad-based and the 2.18x is a real venue effect.

This is DIAGNOSTIC ONLY. It cannot promote age10 into the queue and cannot
demote M2; it only characterizes one number already recorded in
method/CAPITAL_STAGE_PLAN.md section 4c.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "backtest/tests/_age10_anomaly.json"
AGE10 = "age10_dirmatch_swingpause_single_sw10"
BYBIT_OOS_REF = 43.2          # the +43.2R being compared against
TOP_N = 5
BIG_R = 3.0
HALF_OF_REF = 20.0


def _trades(sim, data, params):
    out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
              fine_ltf=data["fine"], **params)
    tr = out["ltf_trades"] if isinstance(out, dict) else out
    return sorted(tr, key=lambda t: int(t["entry_ts"]))


def main():
    t0 = time.time()
    from experiment_registry import BP, EXPERIMENTS
    from run_experiment import net_r
    from test_experiments_craze import build_module
    import exp_cross_instrument_transfer as T

    sim = T.build_module() if hasattr(T, "build_module") else None
    if sim is None:
        from test_experiments_craze import build_module as _bm
        sim = _bm()

    params = {**BP, **EXPERIMENTS[AGE10]["params"]}
    params.setdefault("exp_partial_r", 0.0)

    payload = {
        "stage": "age10_anomaly",
        "question": "is the age10 OOS 2.18x transfer luck-shaped or structural?",
        "lane": AGE10,
        "bybit_oos_ref_net": BYBIT_OOS_REF,
        "pre_registered": {
            "concentrated_if_any": [
                f"top {TOP_N} trades > 50% of total net R",
                f"best trade removed leaves net < {HALF_OF_REF}R",
                f"fewer than 10 trades with R >= +{BIG_R}R",
            ],
        },
        "books": {},
    }

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] ===", flush=True)
        bybit = T.load_bybit(scope, sim)
        tr_b = _trades(sim, bybit, params)
        bounds = T.bybit_bounds(bybit, scope)
        bn = T.load_binance(scope, bounds)
        tr_n = _trades(sim, bn, params)

        for venue, tr in (("bybit", tr_b), ("binance", tr_n)):
            rs = sorted((float(t["r_multiple"]) for t in tr), reverse=True)
            total = sum(rs)
            net = net_r(tr)
            top5 = sum(rs[:TOP_N])
            without_best = net - (rs[0] if rs else 0.0)
            n_big = sum(1 for r in rs if r >= BIG_R)
            rec = {
                "n": len(tr),
                "net": round(net, 2),
                "gross_pos": round(sum(r for r in rs if r > 0), 2),
                "gross_neg": round(sum(r for r in rs if r < 0), 2),
                "best": round(rs[0], 2) if rs else None,
                "worst": round(rs[-1], 2) if rs else None,
                "top5_net": round(top5, 2),
                "top5_share_pct": round(100.0 * top5 / net, 1) if net else None,
                "net_without_best": round(without_best, 2),
                "n_R_ge_3": n_big,
                "win_rate_pct": round(100.0 * sum(1 for r in rs if r > 0) / len(rs), 1)
                if rs else None,
                "n_r_ge_5": sum(1 for r in rs if r >= 5.0),
            }
            payload["books"][f"{scope}|{venue}"] = rec
            print(f"  {scope:4s} {venue:8s} n={rec['n']:4d} net={rec['net']:+8.1f} "
                  f"best={rec['best']} worst={rec['worst']} "
                  f"top5={rec['top5_share_pct']}% nR>=3:{rec['n_R_ge_3']} "
                  f"WR={rec['win_rate_pct']}%", flush=True)

    # apply the rule to the cell under investigation
    a = payload["books"]["oos|binance"]
    triggers = []
    if a["top5_share_pct"] is not None and a["top5_share_pct"] > 50:
        triggers.append(f"top{TOP_N} carry {a['top5_share_pct']}% of net")
    if a["net_without_best"] < HALF_OF_REF:
        triggers.append(f"without best trade net={a['net_without_best']} "
                        f"< {HALF_OF_REF}")
    if a["n_R_ge_3"] < 10:
        triggers.append(f"only {a['n_R_ge_3']} trades with R>=+{BIG_R}")
    payload["result"] = {
        "triggers": triggers,
        "concentration_max_of": "any trigger fires",
        "verdict": "CONCENTRATED (luck-shaped)" if triggers
                   else "BROAD-BASED (structural)",
        "interpretation": (
            "If CONCENTRATED, the 2.18x is carried by few trades and should not "
            "be quoted as a venue property. It is a property of one sample, and "
            "it says nothing about M2 or the rest of the queue."
        ),
    }
    print("\n" + "=" * 78, flush=True)
    print("  age10 OOS TRANSFER CONCENTRATION", flush=True)
    print("=" * 78, flush=True)
    for t in triggers:
        print("   TRIGGER:", t, flush=True)
    if not triggers:
        print("   no trigger fired - lift is broad-based", flush=True)
    print(f"   VERDICT: {payload['result']['verdict']}", flush=True)
    print("=" * 78, flush=True)
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n",
                   encoding="utf-8")
    print(f"wrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()