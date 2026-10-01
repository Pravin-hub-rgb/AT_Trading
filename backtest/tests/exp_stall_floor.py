"""Stage Q — stall-gated giveback floor (descriptive fine-path replay, IS+OOS).

LOSS_AUTOPSY: 224.8R MFE giveback (39 trades gave back 50-75% of peak).
Trail-tighten family (Stage 21, 13 variants) + partials/BE all DEAD because
they cut runners. This tests a DISTINCT mechanism: floor only arms AFTER
the trade has stalled — a live runner keeps making new highs, so the stall
condition should spare it.

Pre-registered arms (stall fixed 48h, no post-hoc extras):
  Q1: MFE>=2R + no new peak >=48h -> floor = peak - 2R
  Q2: MFE>=2R + no new peak >=48h -> floor = +0.5R
  Q3: MFE>=4R + no new peak >=48h -> floor = peak - 2R
Replay (causal, fine 1m): track running peak; floor activates only when
peak>=trig AND ts-last_new_peak>=48h; after activation exit at first fine
close <= floor. Floor fixed at activation (no ratchet). Trades whose
floor-touch occurs AFTER the original exit are untouched (structural trail
would have exited first anyway). Original SL/window exits that would have
fired before floor-touch remain untouched by construction.

Reported: n_affected, n monsters (orig>=4R) among affected, orig vs new net
of affected, book delta, both eras, cand lanes. Monster-safe gate: report
monster leakage explicitly.
Run: $env:PYTHONIOENCODING='utf-8'; python -u backtest/tests/exp_stall_floor.py
"""
from __future__ import annotations

import json
import sys
import time
from bisect import bisect_right
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
from test_experiments_craze import build_module
from test_4_new_concepts import load_fine_1m, load_unseen
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING

from exp_equity_quality import equity_quality

OUT = ROOT / "backtest/tests/_stall_floor_results.json"
YEARS = {"is": 3.67, "oos": 2.0}
STALL_S = 48 * 3600

ARMS = (
    ("Q1_2R_peak-2", 2.0, "peak-2"),
    ("Q2_2R_0.5", 2.0, "0.5"),
    ("Q3_4R_peak-2", 4.0, "peak-2"),
)

HALF = dict(exp_trail_half=1, exp_trail_delay_r=1.0)
SKIPD = dict(exp_skip_decisive=1)
RETEST = dict(exp_retest_fill=0.25, exp_retest_wait=240)

LANES = (
    ("champion", "champion_multi_sw10", dict(HALF, **SKIPD)),
    ("utcsat", "utcsat_multi_sw10", dict(HALF, **SKIPD)),
    ("age10", "age10_dirmatch_swingpause_single_sw10", dict(RETEST)),
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


def replay(trades, fine, trig_r, floor_kind):
    if not fine:
        return list(trades), []
    fts = [int(f["ts"]) for f in fine]
    out, affected = [], []
    for t in trades:
        e_ts, x_ts = int(t["entry_ts"]), int(t["exit_ts"])
        i0 = bisect_right(fts, e_ts)
        i1 = bisect_right(fts, x_ts)
        if i1 - i0 < 2:
            out.append(t)
            continue
        e = float(t["entry_price"])
        sl = float(t["sl"])
        rk = abs(e - sl)
        if rk <= 0 or e <= 0:
            out.append(t)
            continue
        sgn = 1.0 if t.get("dir") == "long" else -1.0
        peak = -1e9
        peak_ts = None
        floor = None
        exit_i = None
        for i in range(i0, i1):
            r = sgn * (float(fine[i]["close"]) - e) / rk
            ts = int(fine[i]["ts"])
            if r > peak:
                peak = r
                peak_ts = ts
            if floor is None and peak >= trig_r and peak_ts is not None \
                    and (ts - peak_ts) >= STALL_S:
                floor = (peak - 2.0) if floor_kind == "peak-2" else 0.5
            if floor is not None and r <= floor:
                exit_i = i
                break
        if exit_i is None:
            out.append(t)
            continue
        r_new = sgn * (float(fine[exit_i]["close"]) - e) / rk
        t2 = dict(t)
        t2["r_multiple"] = round(r_new, 3)
        t2["exit_ts"] = int(fine[exit_i]["ts"])
        t2["exit_date"] = fine[exit_i]["date"]
        t2["bars_held"] = max(1, (t2["exit_ts"] - e_ts) // (15 * 60))
        out.append(t2)
        affected.append({
            "entry_date": t.get("entry_date"),
            "orig_r": float(t["r_multiple"]),
            "new_r": round(r_new, 3),
            "orig_monster": float(t["r_multiple"]) >= 4.0,
            "floor": round(floor, 3),
            "peak_at_stall": round(peak, 3),
        })
    return out, affected


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  STAGE Q — STALL-GATED GIVEBACK FLOOR (descriptive fine replay, IS+OOS)", flush=True)
    print("  arms: Q1 MFE2R+48h stall -> peak-2 | Q2 -> +0.5 | Q3 MFE4R -> peak-2", flush=True)
    print("=" * 100, flush=True)

    sim = build_module()
    payload = {
        "instrument": "BTCUSDT_BYBIT",
        "stage": "stall_floor",
        "lens": "descriptive fine-path replay; floor as ADDITIONAL exit trigger",
        "stall_hours": 48,
        "arms": [{"name": n, "trig_r": tr, "floor": fk} for n, tr, fk in ARMS],
        "years": YEARS, "scopes": {},
    }

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] years={YEARS[scope]} ===", flush=True)
        data = load_scope(scope)
        fine = data["fine"]
        yrs = YEARS[scope]
        sc = {}
        for name, key, flags in LANES:
            cfg = EXPERIMENTS[key]
            params = {**BP, **cfg["params"]}
            params.setdefault("exp_partial_r", 0.0)
            base = run(sim, data, params, **flags)
            bm = equity_quality(base, yrs)
            sc[name] = {"baseline": {"n": bm["n"], "net": bm.get("net"),
                                     "max_dd": bm.get("max_dd")}}
            print(f"\n  {name}: base n={bm['n']} net={bm.get('net'):+.1f} "
                  f"DD={bm.get('max_dd'):.1f}", flush=True)
            for arm, trig, fk in ARMS:
                new, aff = replay(base, fine, trig, fk)
                m = equity_quality(new, yrs)
                lost_m = [a for a in aff if a["orig_monster"]]
                aff_orig = sum(a["orig_r"] for a in aff)
                aff_new = sum(a["new_r"] for a in aff)
                d_net = round(m.get("net", 0) - bm.get("net", 0), 1)
                sc[name][arm] = {
                    **{k: m.get(k) for k in ("n", "net", "max_dd", "ulcer",
                                             "sortino", "calmar", "pf")},
                    "n_affected": len(aff),
                    "n_monsters_affected": len(lost_m),
                    "monster_orig_r": round(sum(a["orig_r"] for a in lost_m), 1),
                    "aff_orig_net": round(aff_orig, 1),
                    "aff_new_net": round(aff_new, 1),
                    "d_net_vs_base": d_net,
                    "d_dd_vs_base": round(m.get("max_dd", 0) - bm.get("max_dd", 0), 1),
                }
                print(f"    {arm:<14} aff={len(aff):>3} monsters={len(lost_m):>2} "
                      f"(origR {sum(a['orig_r'] for a in lost_m):+6.1f}) "
                      f"aff {aff_orig:+6.1f}->{aff_new:+6.1f} | "
                      f"net {bm.get('net'):+7.1f}->{m.get('net'):+7.1f} ({d_net:+6.1f}) "
                      f"DD {bm.get('max_dd'):.1f}->{m.get('max_dd'):.1f}", flush=True)
        payload["scopes"][scope] = sc

    print("\n=== CROSS-ERA dNET (vs own baseline) ===", flush=True)
    verdicts = {}
    for name, _, _ in LANES:
        verdicts[name] = {}
        for arm, _, _ in ARMS:
            d_is = payload["scopes"]["is"][name][arm]["d_net_vs_base"]
            d_oos = payload["scopes"]["oos"][name][arm]["d_net_vs_base"]
            mm_is = payload["scopes"]["is"][name][arm]["n_monsters_affected"]
            mm_oos = payload["scopes"]["oos"][name][arm]["n_monsters_affected"]
            verdicts[name][arm] = {
                "d_is": d_is, "d_oos": d_oos,
                "monsters_is": mm_is, "monsters_oos": mm_oos,
                "both_positive": d_is > 0 and d_oos > 0,
            }
            print(f"  {name:<10} {arm:<14} dNet {d_is:+7.1f}/{d_oos:+6.1f} "
                  f"monsters {mm_is}/{mm_oos} both+ {d_is > 0 and d_oos > 0}", flush=True)
    payload["verdicts"] = verdicts
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
