"""Stage N3Stack - completed-win N3 policy on the Stage-B candidate stack books (2026-09-26).

Gap: Stage 64/65 (CHECKLIST 24.64) endorsed lane-specific N3 policies on the
SHIPPED DEFAULT books (champion global_soft_n3, king/utcsat window_soft_n3)
and explicitly left the next interaction - N3 on the Stage-B candidate stack
(half+delay1+skipD, 24.41) - untested. This is that run.

PRE-REGISTERED BEFORE THE RUN (2026-09-26):
  N3 flags (engine policy, path-true - trade lists change, NO sizing
  exemption; identity gate = flag-off == shipped):
    global_soft_n3 = exp_window_win_kill_n=3, action=soft, scope=global
    window_soft_n3  = same, scope=window
    (exact Stage-65 flag sets; built-in loss halt preserved as shipped)
  Books: stack flags EXACTLY as 24.60 - champion/utcsat = exp_trail_half=1 +
    exp_trail_delay_r=1.0 + exp_skip_decisive=1; age10 = exp_retest_fill=0.25
    + exp_retest_wait=240.
  Arms (ALL reported, per lane):
    stack             stack flags only        (asserted vs 24.60 refs)
    stack_global_n3   stack + global_soft_n3
    stack_window_n3   stack + window_soft_n3
    flat              no flags                (asserted vs flat refs)
    flat_global_n3    flat + global_soft_n3   (CONTROL vs Stage 65)
    flat_window_n3    flat + window_soft_n3   (CONTROL vs Stage 65)
  TESTED pairs (chosen by Stage 64, NO new search here):
    champion + global_soft_n3 vs champion STACK;
    utcsat   + window_soft_n3 vs utcsat STACK.
    PASS per pair = dNet > 0 AND curve_better TRUE in BOTH eras (IS+OOS).
    Aggregate = both pairs pass (ALL / NOT ALL printed).
  EXPLORATORY (reported, NO gate): age10 with both policies; cross-pairs
    (champion+window, utcsat+global); all flat+n3 marginals are controls/
    context only.
  Controls (abort on mismatch > 1.0):
    stack ledgers vs 24.60 (champion 466/+429.6 IS, 217/+110.5 OOS; utcsat
    428/+411.2, 194/+94.6; age10 94/+489.3, 50/+65.8);
    flat ledgers vs flat refs (500/+325.8, 279/+70.2; 454/+358.9, 253/+60.2;
    130/+435.7, 76/+43.2);
    flat+global_n3 champion net IS +331.7 / OOS +90.0 (Stage 65);
    flat+global_n3 utcsat net IS +360.5 / OOS +60.8 (Stage 65);
    flat+window_n3 champion net IS +328.9 / OOS +70.2 (Stage 65);
    flat+window_n3 utcsat net IS +362.2 / OOS +60.2 (Stage 65).
  Note: Stage-65 IS JSON was missing from the repo and was regenerated with
    the unchanged harness before this run (identity IDENTICAL, docs numbers
    reproduced exactly).
RESEARCH_POLICY: report raw P&L + equity + caveats; no automatic gate.

Run: $env:PYTHONIOENCODING='utf-8'; python -u backtest/tests/exp_n3_stack.py
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

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate
from test_experiments_craze import build_module
from test_4_new_concepts import load_fine_1m, load_unseen
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING

from exp_equity_quality import equity_quality, arm_scores, curve_better

OUT = ROOT / "backtest/tests/_n3_stack_results.json"
YEARS = {"is": 3.67, "oos": 2.0}

HALF = dict(exp_trail_half=1, exp_trail_delay_r=1.0)
SKIPD = dict(exp_skip_decisive=1)
RETEST = dict(exp_retest_fill=0.25, exp_retest_wait=240)
G3 = dict(exp_window_win_kill_n=3, exp_window_win_kill_action="soft",
          exp_window_win_kill_scope="global")
W3 = dict(exp_window_win_kill_n=3, exp_window_win_kill_action="soft",
          exp_window_win_kill_scope="window")

EXPECT_STACK = {
    "champion": {"is": (466, 429.6), "oos": (217, 110.5)},
    "utcsat": {"is": (428, 411.2), "oos": (194, 94.6)},
    "age10": {"is": (94, 489.3), "oos": (50, 65.8)},
}
EXPECT_FLAT = {
    "champion": {"is": (500, 325.8), "oos": (279, 70.2)},
    "utcsat": {"is": (454, 358.9), "oos": (253, 60.2)},
    "age10": {"is": (130, 435.7), "oos": (76, 43.2)},
}
# Stage-65 flat+n3 net book totals (abort on mismatch > 1.0)
EXPECT_N3_CONTROL = {
    ("champion", "flat_global_n3"): {"is": 331.7, "oos": 90.0},
    ("champion", "flat_window_n3"): {"is": 328.9, "oos": 70.2},
    ("utcsat", "flat_global_n3"): {"is": 360.5, "oos": 60.8},
    ("utcsat", "flat_window_n3"): {"is": 362.2, "oos": 60.2},
}

LANES = (
    ("champion", "champion_multi_sw10", dict(HALF, **SKIPD)),
    ("utcsat", "utcsat_multi_sw10", dict(HALF, **SKIPD)),
    ("age10", "age10_dirmatch_swingpause_single_sw10", dict(RETEST)),
)

ARMS = ("flat", "flat_global_n3", "flat_window_n3",
        "stack", "stack_global_n3", "stack_window_n3")
ARM_DESC = {
    "flat": "1x reference (flat book)",
    "flat_global_n3": "flat + global_soft_n3 (Stage-65 control)",
    "flat_window_n3": "flat + window_soft_n3 (Stage-65 control)",
    "stack": "1x reference (stack book)",
    "stack_global_n3": "stack + global_soft_n3 (TESTED on champion)",
    "stack_window_n3": "stack + window_soft_n3 (TESTED on utcsat)",
}

# pre-registered tested pairs: (lane, arm)
TESTED_PAIRS = (("champion", "stack_global_n3"), ("utcsat", "stack_window_n3"))


def arm_flags(stack_flags, arm):
    if arm == "flat":
        return {}
    if arm == "flat_global_n3":
        return dict(G3)
    if arm == "flat_window_n3":
        return dict(W3)
    if arm == "stack":
        return dict(stack_flags)
    if arm == "stack_global_n3":
        return {**stack_flags, **G3}
    if arm == "stack_window_n3":
        return {**stack_flags, **W3}
    raise ValueError(arm)


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
    return out


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  STAGE N3STACK - completed-win N3 policy on the Stage-B candidate stack books",
          flush=True)
    print("=" * 100, flush=True)

    sim = build_module()
    payload = {
        "instrument": "BTCUSDT_BYBIT",
        "stage": "n3_stack",
        "lens": "path-true engine policy (trade lists change); no automatic gate",
        "arms": ARM_DESC,
        "n3_flags": {"global": G3, "window": W3},
        "stack_flags": {"champion_utcsat": HALF | SKIPD, "age10": RETEST},
        "years": YEARS, "scopes": {},
        "pre_registered": "PASS per tested pair (champion stack+global_n3, utcsat stack+window_n3) = dNet>0 AND curve_better TRUE in BOTH eras vs the stack book; age10 + cross-pairs exploratory, no gate",
        "controls": "identity gate; stack ledgers vs 24.60 x6; flat ledgers x6; flat+n3 nets vs Stage 65 (tol 1.0) x8 - abort on mismatch",
    }

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] years={YEARS[scope]} ===", flush=True)
        data = load_scope(scope)
        yrs = YEARS[scope]
        sc = {}
        for name, key, stack_flags in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            params.setdefault("exp_partial_r", 0.0)
            print(f"\n  {name}", flush=True)
            print(f"    {'arm':<17} {'n':>4} {'net':>8} {'DD':>6} {'ulcer':>7} "
                  f"{'sort':>7} {'calmar':>7} {'streak':>6} {'PF':>6} {'dNet':>8} "
                  f"curve trig block", flush=True)
            arms_out = {}
            base_metric = {}
            for arm in ARMS:
                out = run(sim, data, params, **arm_flags(stack_flags, arm))
                trades = out["ltf_trades"]
                m = equity_quality(trades, yrs)
                st = out.get("win_window_kill_stats", {}) or {}
                base = "stack" if arm.startswith("stack") else "flat"
                arms_out[arm] = {"metric": m, "n": m["n"],
                                 "trig": st.get("triggered", 0),
                                 "block": st.get("blocked_entries", 0)}
                if arm in ("flat", "stack"):
                    base_metric[base] = m

            # ledger asserts
            for base, refs in (("flat", EXPECT_FLAT), ("stack", EXPECT_STACK)):
                m = base_metric[base]
                exp_n, exp_net = refs[name][scope]
                assert m["n"] == exp_n, (
                    f"{base} ledger n mismatch {name}/{scope}: {m['n']} != {exp_n}")
                assert abs(m["net"] - exp_net) < 0.5, (
                    f"{base} ledger net mismatch {name}/{scope}: {m['net']} != {exp_net}")
                print(f"    [ledger-ok] {base}: n={m['n']} net={m['net']:+.1f} "
                      f"matches reference", flush=True)

            # n3 control asserts
            for arm in ("flat_global_n3", "flat_window_n3"):
                keyc = (name, arm)
                if keyc in EXPECT_N3_CONTROL:
                    exp_net = EXPECT_N3_CONTROL[keyc][scope]
                    got = arms_out[arm]["metric"]["net"]
                    assert abs(got - exp_net) <= 1.0, (
                        f"n3 control mismatch {name}/{arm}/{scope}: "
                        f"{got} != {exp_net} (Stage 65)")
                    print(f"    [n3-ctrl-ok] {arm}: net={got:+.1f} "
                          f"== Stage 65 {exp_net:+.1f}", flush=True)

            # scores vs the matching base
            for arm in ARMS:
                base = "stack" if arm.startswith("stack") else "flat"
                d = arm_scores(arms_out[arm]["metric"], base_metric[base])
                cb = curve_better(d)
                arms_out[arm]["delta"] = d
                arms_out[arm]["curve_better"] = cb
                arms_out[arm]["base"] = base
                print(f"    {arm:<17} {arms_out[arm]['n']:>4} "
                      f"{arms_out[arm]['metric'].get('net', 0):>+8.1f} "
                      f"{arms_out[arm]['metric'].get('max_dd', 0):>6.1f} "
                      f"{arms_out[arm]['metric'].get('ulcer', 0):>7.2f} "
                      f"{arms_out[arm]['metric'].get('sortino', 0):>7.2f} "
                      f"{arms_out[arm]['metric'].get('calmar', 0):>7.3f} "
                      f"{arms_out[arm]['metric'].get('max_streak', 0):>6} "
                      f"{arms_out[arm]['metric'].get('pf', 0):>6.2f} "
                      f"{d.get('d_net', 0):>+8.1f} {cb!s:<5} "
                      f"{arms_out[arm]['trig']:>3} {arms_out[arm]['block']:>3}",
                      flush=True)
            sc[name] = arms_out
        payload["scopes"][scope] = sc

    print("\n=== CROSS-ERA VERDICT (stack arms vs their stack book) ===", flush=True)
    verdicts = {}
    for name, _, _ in LANES:
        for arm in ("stack_global_n3", "stack_window_n3"):
            d_is = payload["scopes"]["is"][name][arm]["delta"]
            d_oos = payload["scopes"]["oos"][name][arm]["delta"]
            v = {"d_net_is": d_is.get("d_net"), "d_net_oos": d_oos.get("d_net"),
                 "d_dd_is": d_is.get("d_max_dd"), "d_dd_oos": d_oos.get("d_max_dd"),
                 "curve_is": curve_better(d_is), "curve_oos": curve_better(d_oos),
                 "cell_is_pass": (d_is.get("d_net") or 0) > 0 and curve_better(d_is),
                 "cell_oos_pass": (d_oos.get("d_net") or 0) > 0 and curve_better(d_oos)}
            v["pair_pass"] = v["cell_is_pass"] and v["cell_oos_pass"]
            verdicts[f"{name}_{arm}"] = v
            tested = (name, arm) in TESTED_PAIRS
            print(f"  {'TESTED    ' if tested else 'exploratory'} {name:<10} {arm:<17} "
                  f"dNet {v['d_net_is']:+7.1f}/{v['d_net_oos']:+7.1f} "
                  f"dDD {v['d_dd_is']:+6.1f}/{v['d_dd_oos']:+6.1f} "
                  f"curve {int(v['curve_is'])}/{int(v['curve_oos'])} "
                  f"pair={v['pair_pass']}", flush=True)
    payload["verdicts"] = verdicts
    tested_results = {f"{n}_{a}": verdicts[f"{n}_{a}"]["pair_pass"]
                      for n, a in TESTED_PAIRS}
    payload["pass_tested_pairs"] = tested_results
    payload["pass_all_tested"] = all(tested_results.values())
    print(f"  PASS tested pairs (champion+global, utcsat+window): "
          f"{'ALL PASS' if payload['pass_all_tested'] else 'NOT ALL PASS'}",
          flush=True)

    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
