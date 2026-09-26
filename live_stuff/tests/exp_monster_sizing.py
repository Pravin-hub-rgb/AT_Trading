"""Stage M — monster anatomy + sizing-UP maps (descriptive Phase 1, IS + OOS).

Question: do PRE-ENTRY era-consistent features identify trades worth
sizing UP (graded alternative to filtering)? Prior cohort sizing tested
only LOSS-side maps (streak poison) and hurt OOS multi; quality-side
sizing-up was never tested.

Pre-frozen flags (entry-causal, from prior findings — no peeking):
  M1 freshB1 : cur_start_to_b1_bars <= 1     (Stage F era-consistent cell)
  M2 bigleg  : cur_mag_atr >= 3.0            (large current leg at entry)
  M3 union   : M1 or M2
  M4 b2only  : signal_kind == "B2"           (era-split: B2 era-stable)
Sizing maps (flagged trades x1.5 r_multiple, others x1.0; costs/funding
unchanged - correct in R units since both P&L and risk scale together).

Anatomy: flag rate in monsters (>=4R) vs rest, avgR flagged/unflagged.
Lanes: champion/utcsat/age10 candidate arms. Descriptive; no gate.

Run: $env:PYTHONIOENCODING='utf-8'; python -u live_stuff/tests/exp_monster_sizing.py
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
from run_experiment import get_data, identity_gate, net_r
from test_experiments_craze import build_module
from test_4_new_concepts import load_fine_1m, load_unseen
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING
from exp_thesis_swing_geometry_deep import trade_rows

OUT = ROOT / "live_stuff/tests/_monster_sizing_results.json"
YEARS = {"is": 3.67, "oos": 2.0}
SIZE = 1.5
MONSTER_R = 4.0

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


def flags_of(r):
    m1 = r.get("cur_start_to_b1_bars") is not None and r["cur_start_to_b1_bars"] <= 1
    m2 = (r.get("cur_mag_atr") or 0) >= 3.0
    m4 = r.get("signal_kind") == "B2"
    return {"M1_freshB1": bool(m1), "M2_bigleg": bool(m2),
            "M3_union": bool(m1 or m2), "M4_b2only": bool(m4)}


def anatomy(rows):
    monsters = [r for r in rows if float(r["r_multiple"]) >= MONSTER_R]
    out = {}
    for f in ("M1_freshB1", "M2_bigleg", "M3_union", "M4_b2only"):
        fl = [r for r in rows if flags_of(r)[f]]
        un = [r for r in rows if not flags_of(r)[f]]
        fm = [r for r in monsters if flags_of(r)[f]]
        def avg(a):
            return round(sum(float(r["r_multiple"]) for r in a) / len(a), 3) if a else None
        out[f] = {
            "n_flag": len(fl), "pct_of_trades": round(100.0 * len(fl) / len(rows), 1) if rows else 0,
            "avgR_flag": avg(fl), "avgR_unflag": avg(un),
            "monster_n": len(monsters),
            "monster_flagged": len(fm),
            "flag_rate_in_monsters_pct": round(100.0 * len(fm) / len(monsters), 1) if monsters else None,
            "flag_rate_in_others_pct": round(
                100.0 * (len(fl) - len(fm)) / max(1, len(rows) - len(monsters)), 1),
        }
    return out


def weighted_net(rows, flag):
    """Scale flagged trades' r to SIZE; costs unchanged (R-unit correct)."""
    tot = 0.0
    for r in rows:
        t = dict(r)
        if flags_of(r)[flag]:
            t["r_multiple"] = float(r["r_multiple"]) * SIZE
        tot += net_r([t])
    return round(tot, 1)


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  STAGE M — MONSTER ANATOMY + SIZING-UP MAPS (descriptive, IS + OOS)", flush=True)
    print(f"  maps: M1 freshB1 | M2 bigleg(>=3 ATR) | M3 union | M4 b2only | size x{SIZE}", flush=True)
    print("=" * 100, flush=True)

    sim = build_module()
    payload = {
        "instrument": "BTCUSDT_BYBIT",
        "stage": "monster_sizing",
        "lens": "descriptive; sizing post-process, no engine change",
        "size": SIZE, "monster_r": MONSTER_R,
        "years": YEARS, "scopes": {},
    }

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] years={YEARS[scope]} ===", flush=True)
        data = load_scope(scope)
        sc = {}
        for name, key, flags in LANES:
            cfg = EXPERIMENTS[key]
            params = {**BP, **cfg["params"]}
            params.setdefault("exp_partial_r", 0.0)
            trades = run(sim, data, params, **flags)
            rows = trade_rows(trades, data)
            if not rows:
                print(f"  {name}: no rows - skip", flush=True)
                continue
            anat = anatomy(rows)
            flat = round(sum(net_r([r]) for r in rows), 1)
            maps = {f: weighted_net(rows, f) for f in
                    ("M1_freshB1", "M2_bigleg", "M3_union", "M4_b2only")}
            sc[name] = {
                "n_trades": len(trades), "n_rows": len(rows),
                "flat_net_rows": flat, "maps": maps,
                "deltas": {f: round(v - flat, 1) for f, v in maps.items()},
                "anatomy": anat,
            }
            print(f"\n  {name} (rows {len(rows)}/{len(trades)}) flat={flat:+.1f}", flush=True)
            print(f"    {'flag':<12} {'n%':>5} {'avgR_f':>7} {'avgR_u':>7} "
                  f"{'mon%':>6} {'oth%':>6} | {'wNet':>8} {'dNet':>7}", flush=True)
            for f, a in anat.items():
                print(f"    {f:<12} {a['pct_of_trades']:>5.1f} "
                      f"{(a['avgR_flag'] if a['avgR_flag'] is not None else 0):>+7.2f} "
                      f"{(a['avgR_unflag'] if a['avgR_unflag'] is not None else 0):>+7.2f} "
                      f"{(a['flag_rate_in_monsters_pct'] or 0):>6.1f} "
                      f"{(a['flag_rate_in_others_pct'] or 0):>6.1f} | "
                      f"{maps[f]:>+8.1f} {maps[f] - flat:>+7.1f}", flush=True)
        payload["scopes"][scope] = sc

    print("\n=== CROSS-ERA dNET (weighted - flat, rows subset) ===", flush=True)
    verdicts = {}
    for name, _, _ in LANES:
        verdicts[name] = {}
        for f in ("M1_freshB1", "M2_bigleg", "M3_union", "M4_b2only"):
            d_is = payload["scopes"]["is"].get(name, {}).get("deltas", {}).get(f)
            d_oos = payload["scopes"]["oos"].get(name, {}).get("deltas", {}).get(f)
            verdicts[name][f] = {
                "d_is": d_is, "d_oos": d_oos,
                "both_positive": (d_is or 0) > 0 and (d_oos or 0) > 0,
            }
            print(f"  {name:<10} {f:<12} dNet {d_is:+7.1f}/{d_oos:+6.1f} "
                  f"both+ {(d_is or 0) > 0 and (d_oos or 0) > 0}", flush=True)
    payload["verdicts"] = verdicts
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
