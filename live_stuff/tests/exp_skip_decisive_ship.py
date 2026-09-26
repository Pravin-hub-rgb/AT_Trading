"""Skip-decisive comparison: ON vs OFF on champion/utcsat/age10, IS+OOS.

Arms: OFF baseline | ON (exp_skip_decisive=1) | ON stacked onto age10 best.
Research lens: report raw P&L and equity effects; no fixed ship threshold.
Identity gate: patched defaults == shipped before any variant.
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

OUT = ROOT / "live_stuff/tests/_skip_decisive_ship_results.json"
CONFIGS = (
    "champion_multi_sw10",
    "utcsat_multi_sw10",
    "age10_dirmatch_swingpause_single_sw10",
)
YEARS = {"is": 3.67, "oos": 2.0}


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
    py = defaultdict(float)
    for t, g in zip(trades, gross):
        py[str(t.get("exit_date") or "")[:4]] += g
    peak = cum = dd = 0.0
    for x in net:
        cum += x
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    wr = 100.0 * sum(1 for x in gross if x > 0) / len(gross) if gross else 0.0
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
    result = {
        "stage": "skip_decisive_comparison",
        "scope": scope,
        "research_policy": "No fixed R/year ship threshold; report raw deltas and equity effects separately.",
        "configs": {},
    }
    print(f"\n=== skip_decisive comparison [{scope.upper()}] years={years} ===", flush=True)
    for key in CONFIGS:
        cfg = EXPERIMENTS[key]
        params = {**BP, **cfg["params"]}
        params.setdefault("exp_partial_r", 0.0)
        arms = [
            ("OFF", {}),
            ("ON", dict(exp_skip_decisive=1)),
        ]
        if key == "age10_dirmatch_swingpause_single_sw10":
            arms.append(("ON_stack_age10", dict(exp_skip_decisive=1)))

        rows = {}
        base_net = None
        print(f"\n  {key}", flush=True)
        print(
            f"    {'arm':<16} {'n':>4} {'gross':>9} {'net':>9} {'dNet':>8} "
            f"{'dNet/yr':>8} {'WR%':>6}",
            flush=True,
        )
        for name, flags in arms:
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
    print("  SKIP_DECISIVE RESEARCH COMPARISON — full path IS + true OOS", flush=True)
    print("=" * 100, flush=True)

    data_is = load_scope("is")
    data_oos = load_scope("oos")
    sim = build_module()

    out = {
        "instrument": "BTCUSDT_BYBIT",
        "research_policy": "No fixed R/year ship threshold; report raw deltas and equity effects separately.",
        "years": YEARS,
        "is": run_scope("is", sim, data_is),
        "oos": run_scope("oos", sim, data_oos),
        "elapsed_sec": round(time.time() - t0, 2),
    }

    print("\n=== VERDICT (research comparison: report P&L and equity effects; no fixed ship gate) ===", flush=True)
    verdicts = {}
    for key in CONFIGS:
        r_is = out["is"]["configs"][key].get("ON") or out["is"]["configs"][key].get("ON_stack_age10")
        r_oos = out["oos"]["configs"][key].get("ON") or out["oos"]["configs"][key].get("ON_stack_age10")
        # prefer plain ON for multi/utcsat; for age10 report both
        on_is = out["is"]["configs"][key]["ON"]
        on_oos = out["oos"]["configs"][key]["ON"]
        both_ok = on_is["dNet_yr"] >= 0 and on_oos["dNet_yr"] >= 0
        verdicts[key] = {
            "dNet_yr_is": on_is["dNet_yr"],
            "dNet_yr_oos": on_oos["dNet_yr"],
            "reason": (
                "POSITIVE BOTH" if both_ok
                else ("IS HURT" if on_is["dNet_yr"] < 0 else "OOS HURT")
            ),
        }
        print(
            f"  {key}: dIS/yr {on_is['dNet_yr']:+.1f}  dOOS/yr {on_oos['dNet_yr']:+.1f}  "
            f"-> {verdicts[key]['reason']}",
            flush=True,
        )
        if "ON_stack_age10" in out["is"]["configs"][key]:
            s_is = out["is"]["configs"][key]["ON_stack_age10"]
            s_oos = out["oos"]["configs"][key]["ON_stack_age10"]
            print(
                f"    stack: dIS/yr {s_is['dNet_yr']:+.1f}  dOOS/yr {s_oos['dNet_yr']:+.1f}",
                flush=True,
            )

    out["verdicts"] = verdicts
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT} ({out['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
