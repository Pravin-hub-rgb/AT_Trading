"""Slower/wider swing-trail experiment — path-true IS + OOS.

Craze kwargs (defaults off, identity-safe):
  exp_trail_delay_r  : apply trail only after unrealized R >= this (slower)
  exp_trail_skip_n   : skip first N post-entry trail events (slower)
  exp_trail_half     : ratchet half-way to candidate (wider)

Research lens: report raw IS/OOS net-R deltas and equity effects; no fixed ship threshold.
Configs: champion, utcsat, age10.
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
from run_experiment import get_data, identity_gate, net_r
from test_4_new_concepts import load_fine_1m, load_unseen
from test_experiments_craze import build_module
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING

OUT = {
    "is": ROOT / "live_stuff/tests/_trail_slower_results_is.json",
    "oos": ROOT / "live_stuff/tests/_trail_slower_results_oos.json",
}
CONFIGS = (
    "champion_multi_sw10",
    "utcsat_multi_sw10",
    "age10_dirmatch_swingpause_single_sw10",
)
YEARS = {"is": 3.67, "oos": 2.0}

# Pre-frozen arm grid (no tuning after seeing results)
ARMS = (
    ("baseline", {}),
    ("delay_r_0.5", dict(exp_trail_delay_r=0.5)),
    ("delay_r_1.0", dict(exp_trail_delay_r=1.0)),
    ("delay_r_1.5", dict(exp_trail_delay_r=1.5)),
    ("delay_r_2.0", dict(exp_trail_delay_r=2.0)),
    ("skip_n_1", dict(exp_trail_skip_n=1)),
    ("skip_n_2", dict(exp_trail_skip_n=2)),
    ("skip_n_3", dict(exp_trail_skip_n=3)),
    ("half", dict(exp_trail_half=1)),
    ("half+delay1", dict(exp_trail_half=1, exp_trail_delay_r=1.0)),
)


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


def metrics(trades):
    gross = [float(t.get("r_multiple") or 0.0) for t in trades]
    net = [net_r([t]) for t in trades]
    peak = cum = dd = 0.0
    for x in net:
        cum += x
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    wr = 100.0 * sum(1 for x in gross if x > 0) / len(gross) if gross else 0.0
    py = defaultdict(float)
    for t, g in zip(trades, gross):
        py[str(t.get("exit_date") or "")[:4]] += g
    return {
        "n": len(trades),
        "gross": round(sum(gross), 4),
        "net": round(sum(net), 4),
        "wr": round(wr, 2),
        "dd_net": round(dd, 4),
        "yearly_gross": {k: round(v, 4) for k, v in sorted(py.items())},
    }


def run_scope(scope, sim, data):
    years = YEARS[scope]
    result = {"scope": scope, "configs": {}}
    print(f"\n=== slower/wider trail [{scope.upper()}] years={years} ===", flush=True)
    for key in CONFIGS:
        cfg = EXPERIMENTS[key]
        params = {**BP, **cfg["params"]}
        params.setdefault("exp_partial_r", 0.0)
        base_net = None
        rows = {}
        print(f"\n  {key}", flush=True)
        print(
            f"    {'arm':<16} {'n':>4} {'gross':>9} {'net':>9} {'dNet':>8} "
            f"{'dNet/yr':>8} {'WR%':>6}",
            flush=True,
        )
        for name, flags in ARMS:
            tr = run(sim, data, params, **flags)
            m = metrics(tr)
            if base_net is None:
                base_net = m["net"]
            d = m["net"] - base_net
            d_yr = d / years
            rows[name] = {**m, "dNet": round(d, 4), "dNet_yr": round(d_yr, 4), "flags": flags}
            print(
                f"    {name:<16} {m['n']:>4} {m['gross']:>+9.1f} {m['net']:>+9.1f} "
                f"{d:>+8.1f} {d_yr:>+8.1f} {m['wr']:>6.1f}",
                flush=True,
            )
        result["configs"][key] = rows
    return result


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  SLOWER/WIDER TRAIL — path-true IS + true OOS", flush=True)
    print("=" * 100, flush=True)

    # Confirm new kwargs exist on built module (build fails if patch missing)
    sim = build_module()
    data_is = load_scope("is")
    data_oos = load_scope("oos")

    is_res = run_scope("is", sim, data_is)
    oos_res = run_scope("oos", sim, data_oos)

    print("\n=== VERDICT (research comparison: report dNet/yr and equity evidence; no fixed ship gate) ===", flush=True)
    verdicts = {}
    for key in CONFIGS:
        verdicts[key] = {}
        base_is = is_res["configs"][key]["baseline"]["net"]
        base_oos = oos_res["configs"][key]["baseline"]["net"]
        for name, _ in ARMS:
            if name == "baseline":
                continue
            d_is = is_res["configs"][key][name]["dNet_yr"]
            d_oos = oos_res["configs"][key][name]["dNet_yr"]
            both_pos = d_is >= 0 and d_oos >= 0
            verdicts[key][name] = {
                "dNet_yr_is": d_is,
                "dNet_yr_oos": d_oos,
                "reason": "POSITIVE BOTH" if both_pos else (
                    "IS HURT" if d_is < 0 and d_oos >= 0 else
                    "OOS HURT" if d_oos < 0 and d_is >= 0 else "BOTH HURT"
                ),
            }
        best = max(
            verdicts[key].items(),
            key=lambda kv: kv[1]["dNet_yr_is"] + kv[1]["dNet_yr_oos"],
        )
        b = best[1]
        print(
            f"  {key:34} best={best[0]:<14} dIS/yr {b['dNet_yr_is']:+.1f}  "
            f"dOOS/yr {b['dNet_yr_oos']:+.1f}  -> {b['reason']}",
            flush=True,
        )

    payload = {
        "instrument": "BTCUSDT_BYBIT",
        "arms": [{"name": n, "flags": f} for n, f in ARMS],
        "research_policy": "No fixed R/year ship threshold; report raw deltas and equity effects separately.",
        "years": YEARS,
        "verdicts": verdicts,
        "elapsed_sec": round(time.time() - t0, 2),
    }
    OUT["is"].write_text(
        json.dumps({"is": is_res, "oos": oos_res, **payload}, indent=2),
        encoding="utf-8",
    )
    OUT["oos"].write_text(
        json.dumps({"is": is_res, "oos": oos_res, **payload}, indent=2),
        encoding="utf-8",
    )
    print(f"\nWrote {OUT['is']} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
