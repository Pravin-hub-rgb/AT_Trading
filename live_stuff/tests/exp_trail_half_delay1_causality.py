"""Causality audit for the half+delay1 trail variant.

The original experiment used the current 1m bar high/low before evaluating
whether a structural event was eligible for the delayed ratchet. This harness
compares it with a strict-prevbar arm that uses only the previous completed
1m bar for that eligibility decision. Structural event ordering and the
half-ratchet arithmetic are otherwise unchanged.
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import identity_gate, net_r
from test_experiments_craze import build_module
from exp_trail_slower import load_scope, run

OUT = {
    "is": ROOT / "live_stuff/tests/_trail_half_delay1_causality_results_is.json",
    "oos": ROOT / "live_stuff/tests/_trail_half_delay1_causality_results_oos.json",
}
CONFIGS = ("champion_multi_sw10", "utcsat_multi_sw10", "age10_dirmatch_swingpause_single_sw10")
ARMS = (
    ("baseline", {}),
    ("half_delay1_original", {"exp_trail_half": 1, "exp_trail_delay_r": 1.0}),
    ("half_delay1_strict_prevbar", {"exp_trail_half": 1, "exp_trail_delay_r": 1.0,
                                    "exp_trail_delay_prevbar": 1}),
)


def stats(values):
    xs = [float(x) for x in values]
    wins = [x for x in xs if x > 0]
    losses = [x for x in xs if x <= 0]
    return {
        "n": len(xs), "sum": round(sum(xs), 6),
        "avg": round(sum(xs) / len(xs), 6) if xs else 0.0,
        "wins": len(wins), "losses": len(losses),
        "wr": round(100.0 * len(wins) / len(xs), 4) if xs else 0.0,
        "avg_win": round(sum(wins) / len(wins), 6) if wins else 0.0,
        "avg_loss": round(sum(losses) / len(losses), 6) if losses else 0.0,
        "pf": round(sum(wins) / abs(sum(losses)), 6) if losses and sum(losses) else 0.0,
        "runners_2": sum(x >= 2 for x in xs), "runners_3": sum(x >= 3 for x in xs),
        "runners_5": sum(x >= 5 for x in xs), "runners_10": sum(x >= 10 for x in xs),
    }


def metrics(trades):
    gross = [float(t.get("r_multiple") or 0.0) for t in trades]
    net = [net_r([t]) for t in trades]
    peak = cum = dd = 0.0
    for x in net:
        cum += x
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    years = defaultdict(float)
    for t, x in zip(trades, gross):
        years[str(t.get("exit_date") or t.get("entry_date") or "")[:4]] += x
    return {"gross": stats(gross), "net": stats(net), "net_dd": round(dd, 6),
            "yearly_gross": dict(sorted(years.items())),
            "outcomes": {k: sum(str(t.get("outcome") or "") == k for t in trades)
                         for k in sorted(set(str(t.get("outcome") or "") for t in trades))}}


def run_scope(scope):
    started = time.time()
    data = load_scope(scope)
    sim = build_module()
    result = {"scope": scope, "instrument": "BTCUSDT_BYBIT",
              "audit": "same-bar MFE eligibility vs previous-completed-bar MFE",
              "configs": {}}
    for key in CONFIGS:
        params = {**BP, **EXPERIMENTS[key]["params"]}
        params.setdefault("exp_partial_r", 0.0)
        result["configs"][key] = {}
        for name, flags in ARMS:
            trades = run(sim, data, params, **flags)
            row = {"flags": flags, "metrics": metrics(trades)}
            if name != "baseline":
                b = result["configs"][key]["baseline"]["metrics"]
                m = row["metrics"]
                row["delta_vs_baseline"] = {
                    "gross": round(m["gross"]["sum"] - b["gross"]["sum"], 6),
                    "net": round(m["net"]["sum"] - b["net"]["sum"], 6),
                    "n": m["gross"]["n"] - b["gross"]["n"],
                }
            result["configs"][key][name] = row
            g = row["metrics"]["gross"]; n = row["metrics"]["net"]
            print(f"{scope.upper():3} {key:34} {name:27} n={g['n']:3d} gross={g['sum']:+8.2f} net={n['sum']:+8.2f} DD={n['sum']-n['sum']+row['metrics']['net_dd']:5.1f} runners3={g['runners_3']:3d}", flush=True)
    result["elapsed_sec"] = round(time.time() - started, 3)
    return result


def main():
    for scope in ("is", "oos"):
        data = run_scope(scope)
        OUT[scope].write_text(json.dumps(data, indent=2), encoding="utf-8")
        print("wrote", OUT[scope], flush=True)


if __name__ == "__main__":
    main()
