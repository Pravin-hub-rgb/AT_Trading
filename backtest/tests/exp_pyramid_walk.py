"""Stage D — Pyramid/scale-in Phase 1 (descriptive gate, offline 1m walk).

Pre-frozen design (2026-09-25):
  - Baseline trades: champion_multi_sw10 + age10_dirmatch_swingpause_single_sw10,
    IS + OOS (identity-gated).
  - For every baseline trade, walk the 1m fine path entry -> base exit.
  - ADD TRIGGER (arm): favorable move reaches milestone M in {0.5R, 1R, 2R}
    measured from base entry (base risk = |entry - sl|).
  - Conservative same-bar rule: milestone bar must be strictly BEFORE the base
    exit bar (if base SL/exit happens in the milestone bar, no add).
  - Conservative fill: long fill = max(level, bar open) if bar opens beyond
    level (gap), else level; short mirrored (min(level, open)).
  - Add size: 50% of base risk (notional 0.5x base).
  - Add SL: add-price -/+ 1R (base R distance), fixed once entered.
  - Add exit: first of (add-SL hit on 1m) or (base exit at base exit price).
  - Incremental net R = 0.5 * (dir*(exit-add)/risk) - costs, costs = same
    convention as net_r: 0.125% fee+slip of add notional in R + proportional
    funding for bars held.
  - Phase 1 gate: incremental net R > 0 on BOTH IS and OOS for at least one
    config => Phase 2 (path-true engine kwargs) may be designed. Else DEAD,
    no engine changes.

Run: $env:PYTHONIOENCODING='utf-8'; python -u backtest/tests/exp_pyramid_walk.py
"""
from __future__ import annotations

import bisect
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
from test_4_new_concepts import load_fine_1m, load_unseen
from test_experiments_craze import build_module
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING

OUT = ROOT / "backtest/tests/_pyramid_walk_results.json"
CONFIGS = (
    "champion_multi_sw10",
    "age10_dirmatch_swingpause_single_sw10",
)
MILESTONES = (0.5, 1.0, 2.0)
SIZE = 0.5
ADD_SL_R = 1.0
FEE = 0.00055          # per side
ENTRY_SLIP = 0.00005
EXIT_SLIP = 0.00010
FUND_RATE = 0.0001     # per 8h


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


def walk_add(trade, fine, fine_ts, milestone):
    """Returns add-outcome dict or None (no add)."""
    entry = float(trade["entry_price"])
    sl = float(trade["sl"])
    d = 1 if trade["dir"] == "long" else -1
    risk = abs(entry - sl)
    exit_ts = int(trade.get("exit_ts") or 0)
    if risk <= 0 or exit_ts <= 0:
        return None
    start = bisect.bisect_left(fine_ts, int(trade["entry_ts"]) + 900)
    end = bisect.bisect_right(fine_ts, exit_ts)
    if start >= end:
        return None

    level = entry + d * milestone * risk
    mbar = None
    for k in range(start, end):
        c = fine[k]
        fav = (float(c["high"]) - entry) / risk if d > 0 else (entry - float(c["low"])) / risk
        if fav >= milestone:
            mbar = k
            break
    if mbar is None or mbar >= end - 1:
        # never reached, or reached only in the base-exit bar (no room) -> no add
        return None

    op = float(fine[mbar]["open"])
    add_px = max(level, op) if d > 0 else min(level, op)
    if add_px <= 0:
        return None

    # walk add: SL or base exit
    add_exit_px = None
    add_exit_ts = None
    exit_reason = "base_exit"
    add_sl = add_px - d * ADD_SL_R * risk
    for k in range(mbar + 1, end):
        c = fine[k]
        lo, hi = float(c["low"]), float(c["high"])
        hit_sl = lo <= add_sl if d > 0 else hi >= add_sl
        if hit_sl:
            add_exit_px = add_sl
            add_exit_ts = int(c["ts"])
            exit_reason = "add_sl"
            break
    if add_exit_px is None:
        add_exit_px = float(trade["exit_price"])
        add_exit_ts = exit_ts
        exit_reason = "base_exit"

    gross_r = SIZE * d * (add_exit_px - add_px) / risk
    bars = max(1, (add_exit_ts - int(fine[mbar]["ts"])) // 60)
    cost_notional = FEE * 2 + ENTRY_SLIP + EXIT_SLIP
    cost_r = SIZE * cost_notional * add_px / risk
    fund_r = SIZE * (bars * 0.25 / 8.0) * FUND_RATE * (add_px / risk)
    net = gross_r - cost_r - fund_r
    return {
        "milestone": milestone,
        "add_px": add_px, "add_sl": add_sl,
        "exit_px": add_exit_px, "exit_reason": exit_reason,
        "gross_r": gross_r, "net_r": net,
        "bars": bars,
        "base_r": float(trade.get("r_multiple") or 0.0),
        "add_bar_offset": mbar - start,
    }


def analyze_scope(scope, sim, data):
    fine = data["fine"]
    fine_ts = [int(c["ts"]) for c in fine]
    result = {"scope": scope, "configs": {}}
    print(f"\n=== pyramid Phase 1 [{scope.upper()}] ===", flush=True)
    for key in CONFIGS:
        params = {**BP, **EXPERIMENTS[key]["params"]}
        params.setdefault("exp_partial_r", 0.0)
        out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                  fine_ltf=fine, **params)
        trades = out["ltf_trades"] if isinstance(out, dict) else out
        base_net = sum(net_r([t]) for t in trades)
        cfg = {"n_base": len(trades), "base_net": round(base_net, 3), "arms": {}}
        print(f"\n  {key}: n={len(trades)} base_net={base_net:+.1f}", flush=True)
        for m in MILESTONES:
            rows = [walk_add(t, fine, fine_ts, m) for t in trades]
            adds = [r for r in rows if r is not None]
            if not adds:
                cfg["arms"][str(m)] = {"n_add": 0}
                print(f"    M={m}R: no adds", flush=True)
                continue
            tot_net = sum(r["net_r"] for r in adds)
            tot_gross = sum(r["gross_r"] for r in adds)
            sl_hits = sum(1 for r in adds if r["exit_reason"] == "add_sl")
            pos = sum(1 for r in adds if r["net_r"] > 0)
            med_off = sorted(r["add_bar_offset"] for r in adds)[len(adds) // 2]
            cov = 100.0 * len(adds) / len(trades)
            # incremental series stats
            series = [r["net_r"] for r in adds]
            peak = cum = dd = 0.0
            for x in series:
                cum += x
                peak = max(peak, cum)
                dd = max(dd, peak - cum)
            cfg["arms"][str(m)] = {
                "n_add": len(adds), "coverage_pct": round(cov, 1),
                "gross_r": round(tot_gross, 3), "net_r": round(tot_net, 3),
                "add_sl_hits": sl_hits, "win_pct": round(100.0 * pos / len(adds), 1),
                "max_dd_r": round(dd, 3),
                "med_offset_1m": med_off,
                "combined_net": round(base_net + tot_net, 3),
            }
            print(f"    M={m}R: adds={len(adds)} ({cov:.0f}%) net={tot_net:+.1f} "
                  f"gross={tot_gross:+.1f} sl_hits={sl_hits} win={100.0*pos/len(adds):.0f}% "
                  f"dd={dd:.1f} combined={base_net+tot_net:+.1f}", flush=True)
        result["configs"][key] = cfg
    return result


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  STAGE D — PYRAMID / SCALE-IN PHASE 1 (offline 1m walk, descriptive)", flush=True)
    print(f"  milestones={MILESTONES} size={SIZE} addSL={ADD_SL_R}R conservative pre-exit rule", flush=True)
    print("=" * 100, flush=True)
    sim = build_module()
    res = {}
    for scope in ("is", "oos"):
        res[scope] = analyze_scope(scope, sim, load_scope(scope))

    payload = {
        "instrument": "BTCUSDT_BYBIT",
        "study": "pyramid/scale-in Phase 1 (descriptive; engine untouched)",
        "design": {"milestones": list(MILESTONES), "size": SIZE,
                   "add_sl_r": ADD_SL_R, "cost_pct_roundtrip": 0.00125},
        "is": res["is"], "oos": res["oos"],
        "elapsed_sec": round(time.time() - t0, 2),
    }
    OUT.write_text(json.dumps(payload, indent=1), encoding="utf-8")

    print("\n=== PHASE 1 GATE (net_r > 0 both sides, per config x milestone) ===", flush=True)
    verdict = []
    for key in CONFIGS:
        for m in MILESTONES:
            a_is = res["is"]["configs"][key]["arms"].get(str(m), {})
            a_oos = res["oos"]["configs"][key]["arms"].get(str(m), {})
            if not a_is.get("n_add") or not a_oos.get("n_add"):
                continue
            ok = a_is["net_r"] > 0 and a_oos["net_r"] > 0
            verdict.append((key, m, a_is["net_r"], a_oos["net_r"], ok))
            print(f"  {key:46} M={m} IS {a_is['net_r']:+8.1f} OOS {a_oos['net_r']:+8.1f} "
                  f"{'PASS' if ok else 'FAIL'}", flush=True)
    gate_pass = any(v[4] for v in verdict)
    print(f"\n  GATE: {'PASS -> Phase 2 design may proceed' if gate_pass else 'FAIL -> DEAD, no engine changes'}",
          flush=True)
    print(f"wrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
