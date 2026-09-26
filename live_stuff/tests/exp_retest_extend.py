"""Stage J — retest_fill extension to champion/utcsat lanes (path-true IS+OOS).

Question: age10's Stage-B survivor (retest_fill 0.25 + wait 240) — does it
also help the multi lanes, stacked on top of THEIR Stage-B winner?

Pre-frozen arms (x champion, utcsat, IS+OOS):
  1 baseline
  2 retest_0.25                      (age10's mechanism alone)
  3 cand             = half+delay1+skipD   (Stage B lane winner, ref)
  4 cand+retest                       (does retest ADD on top?)

Scoring: equity_quality + delta vs baseline; cross-era both-positive check.
RESEARCH_POLICY: report raw P&L + equity + caveats; no automatic gate.
Run: $env:PYTHONIOENCODING='utf-8'; python -u live_stuff/tests/exp_retest_extend.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate
from test_experiments_craze import build_module
from test_4_new_concepts import load_fine_1m, load_unseen
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING

from exp_equity_quality import equity_quality, arm_scores, curve_better

OUT = ROOT / "live_stuff/tests/_retest_extend_results.json"
YEARS = {"is": 3.67, "oos": 2.0}

HALF = dict(exp_trail_half=1, exp_trail_delay_r=1.0)
SKIPD = dict(exp_skip_decisive=1)
RETEST = dict(exp_retest_fill=0.25, exp_retest_wait=240)

ARMS = (
    ("baseline", {}),
    ("retest_0.25", dict(RETEST)),
    ("cand", dict(HALF, **SKIPD)),
    ("cand+retest", {**HALF, **SKIPD, **RETEST}),
)

LANES = ("champion_multi_sw10", "utcsat_multi_sw10")


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


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  STAGE J — retest_fill EXTENSION to champion/utcsat (path-true IS+OOS)", flush=True)
    print("=" * 100, flush=True)

    sim = build_module()
    payload = {
        "instrument": "BTCUSDT_BYBIT",
        "stage": "retest_extend",
        "lens": "raw net + equity quality; no automatic ship gate",
        "years": YEARS,
        "arms": [{"name": n, "flags": f} for n, f in ARMS],
        "lanes": list(LANES),
        "scopes": {},
    }

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] years={YEARS[scope]} ===", flush=True)
        data = load_scope(scope)
        yrs = YEARS[scope]
        sc = {}
        for key in LANES:
            cfg = EXPERIMENTS[key]
            params = {**BP, **cfg["params"]}
            params.setdefault("exp_partial_r", 0.0)
            rows = {}
            base_m = None
            print(f"\n  {key}", flush=True)
            print(f"    {'arm':<16} {'n':>4} {'net':>8} {'DD':>6} {'ulcer':>7} "
                  f"{'calmar':>7} {'streak':>6} {'PF':>6} {'dNet':>7}", flush=True)
            for name, flags in ARMS:
                tr = run(sim, data, params, **flags)
                m = equity_quality(tr, yrs)
                if base_m is None:
                    base_m = m
                d = arm_scores(m, base_m)
                rows[name] = {**m, "delta_vs_base": d, "flags": flags}
                print(f"    {name:<16} {m['n']:>4} {m.get('net', 0):>+8.1f} "
                      f"{m.get('max_dd', 0):>6.1f} {m.get('ulcer', 0):>7.2f} "
                      f"{m.get('calmar', 0):>7.3f} {m.get('max_streak', 0):>6} "
                      f"{m.get('pf', 0):>6.2f} {d.get('d_net', 0):>+7.1f}", flush=True)
            sc[key] = rows
        payload["scopes"][scope] = sc

    print("\n=== CROSS-ERA DELTAS (vs own baseline) ===", flush=True)
    verdicts = {}
    for key in LANES:
        verdicts[key] = {}
        for name, _ in ARMS:
            if name == "baseline":
                continue
            d_is = payload["scopes"]["is"][key][name]["delta_vs_base"]
            d_oos = payload["scopes"]["oos"][key][name]["delta_vs_base"]
            v = {
                "d_net_is": d_is.get("d_net"), "d_net_oos": d_oos.get("d_net"),
                "curve_better_is": curve_better(d_is),
                "curve_better_oos": curve_better(d_oos),
            }
            v["net_positive_both"] = (v["d_net_is"] or 0) > 0 and (v["d_net_oos"] or 0) > 0
            v["curve_pass_both"] = v["curve_better_is"] and v["curve_better_oos"]
            verdicts[key][name] = v
            print(f"  {key:34} {name:<16} dNet {v['d_net_is']:+8.1f}/{v['d_net_oos']:+7.1f} "
                  f"curve {v['curve_pass_both']} net+ {v['net_positive_both']}", flush=True)
    payload["verdicts"] = verdicts
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
