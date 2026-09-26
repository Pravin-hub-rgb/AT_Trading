"""Cohort variable sizing — post-process weighted R on baseline trade lists.

Pre-frozen maps (no tuning):
  flat           : all 1.0
  elite_poison   : streak>=3 -> 1.5, streak==2 -> 0.5, else 1.0
  full_map       : elite/poison + in-window prior_loss>=2 -> 1.5 (if not poison)

Identity: entry/exit/ts sequence identical to baseline (sizing does not change path).
Configs: champion, utcsat, age10; scopes IS + OOS.
Research lens: report weighted NET deltas and equity effects; no fixed ship threshold.
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
    "is": ROOT / "live_stuff/tests/_cohort_sizing_results_is.json",
    "oos": ROOT / "live_stuff/tests/_cohort_sizing_results_oos.json",
}
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


def trade_key(t):
    return (
        int(t.get("entry_ts") or 0),
        int(t.get("exit_ts") or 0),
        str(t.get("dir") or ""),
        round(float(t.get("r_multiple") or 0.0), 6),
    )


def annotate(trades):
    """Causal in-window prior-loss count via window_key; attach streak."""
    rows = sorted(trades, key=lambda t: int(t.get("entry_ts") or 0))
    prior_loss = defaultdict(int)
    out = []
    for t in rows:
        wk = t.get("window_key")
        n_pl = int(prior_loss[wk]) if wk is not None else 0
        streak = int(t.get("loss_streak_at_entry") or 0)
        r = float(t.get("r_multiple") or 0.0)
        if wk is not None:
            if r <= 0:
                prior_loss[wk] += 1
        out.append((t, streak, n_pl))
    return out


def weight_flat(t, streak, n_pl):
    return 1.0


def weight_elite_poison(t, streak, n_pl):
    if streak >= 3:
        return 1.5
    if streak == 2:
        return 0.5
    return 1.0


def weight_full(t, streak, n_pl):
    if streak >= 3:
        return 1.5
    if streak == 2:
        return 0.5
    if n_pl >= 2:
        return 1.5
    return 1.0


MAPS = (
    ("flat", weight_flat),
    ("elite_poison", weight_elite_poison),
    ("full_map", weight_full),
)


def summarize(rows):
    """rows: list of (t, weight). weighted net = sum(net_r * w)."""
    w_net = 0.0
    b_net = 0.0
    w_gross = 0.0
    b_gross = 0.0
    for t, w in rows:
        g = float(t.get("r_multiple") or 0.0)
        n = net_r([t])
        b_gross += g
        b_net += n
        w_gross += g * w
        w_net += n * w
    return {
        "n": len(rows),
        "baseline_net": round(b_net, 4),
        "weighted_net": round(w_net, 4),
        "delta_net": round(w_net - b_net, 4),
        "baseline_gross": round(b_gross, 4),
        "weighted_gross": round(w_gross, 4),
    }


def run_scope(scope, sim, data):
    years = YEARS[scope]
    result = {"scope": scope, "configs": {}}
    print(f"\n=== cohort sizing [{scope.upper()}] years={years} ===", flush=True)
    for key in CONFIGS:
        cfg = EXPERIMENTS[key]
        params = {**BP, **cfg["params"]}
        params.setdefault("exp_partial_r", 0.0)
        out = sim(
            data["c1h"], data["sw10"], data["c15"], data["sw15"],
            fine_ltf=data["fine"], **params,
        )
        trades = out["ltf_trades"] if isinstance(out, dict) else out
        base_keys = [trade_key(t) for t in trades]
        annotated = annotate(trades)
        print(f"\n  {key}  n={len(trades)}", flush=True)
        print(
            f"    {'map':<16} {'weighted':>10} {'base':>9} {'dNet':>8} "
            f"{'dNet/yr':>8}  identity",
            flush=True,
        )
        cfg_rows = {}
        for name, fn in MAPS:
            rows = [(t, fn(t, s, p)) for t, s, p in annotated]
            keys = [trade_key(t) for t, _ in rows]
            ident = keys == base_keys
            s = summarize(rows)
            d = s["delta_net"]
            d_yr = d / years
            cfg_rows[name] = {
                **s,
                "dNet_yr": round(d_yr, 4),
                "identity_ok": ident,
                "weights_hist": dict(
                    sorted(
                        {
                            w: sum(1 for _, ww in rows if ww == w)
                            for w in sorted({ww for _, ww in rows})
                        }.items()
                    )
                ),
            }
            print(
                f"    {name:<16} {s['weighted_net']:>+10.1f} {s['baseline_net']:>+9.1f} "
                f"{d:>+8.1f} {d_yr:>+8.1f}  {'OK' if ident else 'FAIL'}",
                flush=True,
            )
            if not ident:
                raise SystemExit(f"IDENTITY FAILED {key}/{name} {scope}")
        result["configs"][key] = cfg_rows
    return result


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  COHORT VARIABLE SIZING — post-process on baseline lists, IS + OOS", flush=True)
    print("=" * 100, flush=True)

    data_is = load_scope("is")
    data_oos = load_scope("oos")
    sim = build_module()

    is_res = run_scope("is", sim, data_is)
    oos_res = run_scope("oos", sim, data_oos)

    print("\n=== VERDICT (research comparison: report dNet/yr; no fixed ship gate) ===", flush=True)
    verdicts = {}
    for key in CONFIGS:
        verdicts[key] = {}
        for mname, _ in MAPS:
            d_is = is_res["configs"][key][mname]["dNet_yr"]
            d_oos = oos_res["configs"][key][mname]["dNet_yr"]
            verdicts[key][mname] = {
                "dNet_yr_is": d_is,
                "dNet_yr_oos": d_oos,
                "reason": "POSITIVE BOTH" if d_is >= 0 and d_oos >= 0 else (
                    "IS HURT" if d_is < 0 else "OOS HURT"
                ),
            }
            print(
                f"  {key:34} {mname:<16} dIS/yr {d_is:+.1f}  dOOS/yr {d_oos:+.1f}  "
                f"-> {verdicts[key][mname]['reason']}",
                flush=True,
            )

    payload = {
        "instrument": "BTCUSDT_BYBIT",
        "maps": [m for m, _ in MAPS],
        "identity": "entry/exit/ts/r sequence identical to baseline",
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
