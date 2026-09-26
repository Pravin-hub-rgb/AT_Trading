"""Stage B — open-candidate consolidation stack (path-true, IS + OOS).

Question: do the individually-surviving default-off candidates COMPOSE?

Survivors so far (all default-off, not adopted):
  champion/utcsat: exp_trail_half=1 + exp_trail_delay_r=1.0 (curve pass both,
      equity_quality 2026-09-25); exp_skip_decisive=1 (OOS up, IS ~0);
      exp_regime_skip=10 (champion dIS +30.9 / dOOS +2.3 per exp_stack_marginals).
  age10 single: exp_retest_fill=0.25 + exp_retest_wait=240 (Phase B survivor).

Pre-frozen arms (no post-hoc extras):
  multi (champion, utcsat):
    1 baseline
    2 half+delay1
    3 skip_decisive
    4 regime10
    5 half+delay1 + skip_decisive
    6 half+delay1 + regime10
    7 skip_decisive + regime10
    8 all three
  age10 single:
    1 baseline
    2 retest_0.25
    3 regime10
    4 retest_0.25 + regime10

Scoring: raw net + full equity-lens (reuse exp_equity_quality.equity_quality).
RESEARCH_POLICY: raw P&L + equity + coverage + caveats; NO automatic ship gate.

Run: $env:PYTHONIOENCODING='utf-8'; python -u live_stuff/tests/exp_candidate_stack.py
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

OUT = ROOT / "live_stuff/tests/_candidate_stack_results.json"
YEARS = {"is": 3.67, "oos": 2.0}

HALF = dict(exp_trail_half=1, exp_trail_delay_r=1.0)
SKIPD = dict(exp_skip_decisive=1)
REG10 = dict(exp_regime_skip=10.0)
RETEST = dict(exp_retest_fill=0.25, exp_retest_wait=240)

MULTI_ARMS = (
    ("baseline", {}),
    ("half+delay1", dict(HALF)),
    ("skip_decisive", dict(SKIPD)),
    ("regime10", dict(REG10)),
    ("half+delay1+skipD", {**HALF, **SKIPD}),
    ("half+delay1+reg10", {**HALF, **REG10}),
    ("skipD+reg10", {**SKIPD, **REG10}),
    ("all_three", {**HALF, **SKIPD, **REG10}),
)

AGE10_ARMS = (
    ("baseline", {}),
    ("retest_0.25", dict(RETEST)),
    ("regime10", dict(REG10)),
    ("retest_0.25+reg10", {**RETEST, **REG10}),
)

MULTI_CFGS = ("champion_multi_sw10", "utcsat_multi_sw10")
AGE10_CFG = "age10_dirmatch_swingpause_single_sw10"


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


def run_cfg(sim, data, key, arms, years):
    cfg = EXPERIMENTS[key]
    params = {**BP, **cfg["params"]}
    params.setdefault("exp_partial_r", 0.0)
    rows = {}
    base_m = None
    print(f"\n  {key}", flush=True)
    print(f"    {'arm':<20} {'n':>4} {'net':>8} {'DD':>6} {'ulcer':>7} "
          f"{'sort':>7} {'calmar':>7} {'m+%':>5} {'streak':>6} {'PF':>6}",
          flush=True)
    for name, flags in arms:
        tr = run(sim, data, params, **flags)
        m = equity_quality(tr, years)
        if base_m is None:
            base_m = m
        delta = arm_scores(m, base_m)
        rows[name] = {**m, "delta_vs_base": delta, "flags": flags}
        print(f"    {name:<20} {m['n']:>4} {m['net']:>+8.1f} {m['max_dd']:>6.1f} "
              f"{m['ulcer']:>7.2f} {m['sortino']:>7.2f} {m['calmar']:>7.3f} "
              f"{m['pos_month_pct']:>5.1f} {m['max_streak']:>6} {m['pf']:>6.2f}",
              flush=True)
    return rows


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  STAGE B — OPEN-CANDIDATE CONSOLIDATION STACK (IS + OOS, Bybit BTCUSDT)", flush=True)
    print("=" * 100, flush=True)

    sim = build_module()
    import inspect
    sig = inspect.signature(sim)
    for kw in ("exp_trail_half", "exp_trail_delay_r", "exp_skip_decisive",
               "exp_regime_skip", "exp_retest_fill", "exp_retest_wait"):
        if kw not in sig.parameters:
            raise SystemExit(f"missing kwarg {kw}")

    data_is = load_scope("is")
    data_oos = load_scope("oos")

    payload = {
        "instrument": "BTCUSDT_BYBIT",
        "stage": "B_candidate_stack",
        "lens": "raw net + equity quality; no automatic ship gate",
        "years": YEARS,
        "multi_arms": [{"name": n, "flags": f} for n, f in MULTI_ARMS],
        "age10_arms": [{"name": n, "flags": f} for n, f in AGE10_ARMS],
        "scopes": {},
    }

    for scope, data in (("is", data_is), ("oos", data_oos)):
        print(f"\n=== [{scope.upper()}] years={YEARS[scope]} ===", flush=True)
        yrs = YEARS[scope]
        sc = {}
        for key in MULTI_CFGS:
            sc[key] = run_cfg(sim, data, key, MULTI_ARMS, yrs)
        sc[AGE10_CFG] = run_cfg(sim, data, AGE10_CFG, AGE10_ARMS, yrs)
        payload["scopes"][scope] = sc

    # cross-era verdict per arm (delta net both sides + curve pass both)
    print("\n=== CROSS-ERA DELTAS (vs own baseline) ===", flush=True)
    verdicts = {}
    for key in list(MULTI_CFGS) + [AGE10_CFG]:
        arms = MULTI_ARMS if key in MULTI_CFGS else AGE10_ARMS
        verdicts[key] = {}
        for name, _ in arms:
            if name == "baseline":
                continue
            d_is = payload["scopes"]["is"][key][name]["delta_vs_base"]
            d_oos = payload["scopes"]["oos"][key][name]["delta_vs_base"]
            v = {
                "d_net_is": d_is.get("d_net"),
                "d_net_oos": d_oos.get("d_net"),
                "d_net_yr_is": d_is.get("d_net_yr"),
                "d_net_yr_oos": d_oos.get("d_net_yr"),
                "d_dd_is": d_is.get("d_max_dd"),
                "d_dd_oos": d_oos.get("d_max_dd"),
                "d_ulcer_is": d_is.get("d_ulcer"),
                "d_ulcer_oos": d_oos.get("d_ulcer"),
                "curve_better_is": curve_better(d_is),
                "curve_better_oos": curve_better(d_oos),
            }
            v["net_positive_both"] = (v["d_net_is"] or 0) > 0 and (v["d_net_oos"] or 0) > 0
            v["curve_pass_both"] = v["curve_better_is"] and v["curve_better_oos"]
            verdicts[key][name] = v
            print(f"  {key:36} {name:<20} dNet {v['d_net_is']:+8.1f}/{v['d_net_oos']:+7.1f} "
                  f"dDD {v['d_dd_is']:+6.1f}/{v['d_dd_oos']:+6.1f} "
                  f"curve {v['curve_pass_both']} net+ {v['net_positive_both']}",
                  flush=True)
    payload["verdicts"] = verdicts
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
