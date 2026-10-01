"""Phase B — retest limit-below-entry fill (fill-price improvement), path-true IS + OOS.

Pre-registered in WINNER_PATH_AUTOPSY.md (no post-hoc changes):
  arms     : baseline / limit@(entry-0.10R) / limit@(entry-0.25R)
  wait     : 240 min (4h) from signal close, then CANCEL (no trade)
  configs  : champion_multi_sw10 + age10_dirmatch_swingpause_single_sw10
  report   : n, filled, timeouts (miss), monsters >=10R captured/missed, gross/net, dd
  verdict  : arm survives only if net improves on BOTH IS and OOS; else DEAD

Mechanics (exp_retest_fill, craze kwarg, default-off identity-safe):
  limit sits exp_retest_fill*risk below (long) / above (short) the signal-close
  entry; first 1m touch within the wait window fills at min(limit, open) long /
  max(limit, open) short; SL price UNCHANGED; risk/target recomputed at fill
  (better entry = smaller risk = more R per same move, but fees/funding are
  % of notional => cost-in-R RISES as risk shrinks — reported honestly).

Run: $env:PYTHONIOENCODING='utf-8'; python -u backtest/tests/exp_retest_fill.py
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
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

OUT = ROOT / "backtest/tests/_retest_fill_results.json"
CONFIGS = (
    "champion_multi_sw10",
    "age10_dirmatch_swingpause_single_sw10",
)
YEARS = {"is": 3.67, "oos": 2.0}
MONSTER_R = 10.0

# Pre-frozen arm grid
ARMS = (
    ("baseline", {}),
    ("limit_0.10R", dict(exp_retest_fill=0.10, exp_retest_wait=240)),
    ("limit_0.25R", dict(exp_retest_fill=0.25, exp_retest_wait=240)),
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
    return out["ltf_trades"], out.get("retest_stats") or {"filled": 0, "timeout": 0}


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
    monsters = [t for t, g in zip(trades, gross) if g >= MONSTER_R]
    return {
        "n": len(trades),
        "gross": round(sum(gross), 4),
        "net": round(sum(net), 4),
        "wr": round(wr, 2),
        "dd_net": round(dd, 4),
        "monsters": len(monsters),
        "yearly_gross": {k: round(v, 4) for k, v in sorted(py.items())},
    }


def mkey(t):
    """Signal identity for cross-arm matching: swing + direction."""
    return (t.get("swing_no"), t.get("dir"))


def run_scope(scope, sim, data):
    years = YEARS[scope]
    result = {"scope": scope, "configs": {}}
    print(f"\n=== retest limit fill [{scope.upper()}] years={years} ===", flush=True)
    for key in CONFIGS:
        cfg = EXPERIMENTS[key]
        params = {**BP, **cfg["params"]}
        params.setdefault("exp_partial_r", 0.0)
        base_net = None
        base_monsters = set()
        rows = {}
        print(f"\n  {key}", flush=True)
        print(
            f"    {'arm':<14} {'n':>4} {'fill':>5} {'miss':>5} {'gross':>9} {'net':>9} "
            f"{'dNet':>8} {'dNet/yr':>8} {'WR%':>6} {'mono':>5} {'mCap':>5} {'mMiss':>6}",
            flush=True,
        )
        for name, flags in ARMS:
            tr, stats = run(sim, data, params, **flags)
            m = metrics(tr)
            if base_net is None:
                base_net = m["net"]
                base_monsters = {mkey(t) for t in tr
                                 if float(t.get("r_multiple") or 0) >= MONSTER_R}
            d = m["net"] - base_net
            d_yr = d / years
            arm_keys = {mkey(t) for t in tr}
            m_cap = len(base_monsters & arm_keys)
            m_miss = len(base_monsters - arm_keys)
            rows[name] = {**m, "dNet": round(d, 4), "dNet_yr": round(d_yr, 4),
                          "filled": stats.get("filled", 0),
                          "miss": stats.get("timeout", 0),
                          "monsters_captured": m_cap, "monsters_missed": m_miss,
                          "flags": flags}
            print(
                f"    {name:<14} {m['n']:>4} {stats.get('filled', 0):>5} "
                f"{stats.get('timeout', 0):>5} {m['gross']:>+9.1f} {m['net']:>+9.1f} "
                f"{d:>+8.1f} {d_yr:>+8.1f} {m['wr']:>6.1f} {m['monsters']:>5} "
                f"{m_cap:>5} {m_miss:>6}",
                flush=True,
            )
        result["configs"][key] = rows
    return result


def main():
    t0 = time.time()
    print("=" * 104, flush=True)
    print("  PHASE B — RETEST LIMIT-BELOW-ENTRY FILL (pre-registered) — path-true IS + OOS", flush=True)
    print("=" * 104, flush=True)

    sim = build_module()
    data_is = load_scope("is")
    data_oos = load_scope("oos")

    is_res = run_scope("is", sim, data_is)
    oos_res = run_scope("oos", sim, data_oos)

    print("\n=== VERDICT (pre-registered: net must improve BOTH eras; else DEAD) ===", flush=True)
    verdicts = {}
    for key in CONFIGS:
        verdicts[key] = {}
        for name, _ in ARMS:
            if name == "baseline":
                continue
            d_is = is_res["configs"][key][name]["dNet_yr"]
            d_oos = oos_res["configs"][key][name]["dNet_yr"]
            both_pos = d_is > 0 and d_oos > 0
            verdicts[key][name] = {
                "dNet_yr_is": d_is,
                "dNet_yr_oos": d_oos,
                "reason": "POSITIVE BOTH" if both_pos else (
                    "IS HURT" if d_is <= 0 and d_oos > 0 else
                    "OOS HURT" if d_oos <= 0 and d_is > 0 else "BOTH HURT"),
            }
            print(f"  {key:38} {name:<14} dIS/yr {d_is:+7.1f}  dOOS/yr {d_oos:+7.1f}"
                  f"  -> {verdicts[key][name]['reason']}", flush=True)

    payload = {
        "instrument": "BTCUSDT_BYBIT",
        "arms": [{"name": n, "flags": f} for n, f in ARMS],
        "monster_r": MONSTER_R,
        "research_policy": "No fixed R/year ship threshold; report raw deltas, coverage and equity separately.",
        "years": YEARS,
        "verdicts": verdicts,
        "elapsed_sec": round(time.time() - t0, 2),
    }
    OUT.write_text(json.dumps({"is": is_res, "oos": oos_res, **payload}, indent=2),
                   encoding="utf-8")
    print(f"\nWrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
