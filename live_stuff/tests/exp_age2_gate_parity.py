"""Stage C — age-2 B1->B2 gate: live-feasibility / prefix PARITY audit.

Stage 28's open caveat: "prefix audit fails for baseline AND candidate due to
the shared full-history swing-chain boundary; gate-level mark lookup is causal,
but live replay equivalence still needs dedicated validation."

This audit isolates the GATE from the chain noise:
  - run full-history and truncated-prefix replays with exp_b1_b2_mode on,
    collecting exp_b1_b2_stats rows (entry_idx, b1_b2_bars, allowed);
  - join rows by entry_idx (same candle indexing in both runs);
  - report, on COMMON signal bars: how often the gate's measured age and its
    allow/block decision are identical.

If gate parity is ~100% on common bars, the age-2 decision is live-computable;
residual trade differences belong to the shared chain caveat (which hits
baseline equally). If parity itself fails, the gate is not live-safe.

Controls: literal_v18_single/multi (Stage 28 headline cells) + champion/utcsat
+ fullstack single (production references).

Run: $env:PYTHONIOENCODING='utf-8'; python -u live_stuff/tests/exp_age2_gate_parity.py
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
from exp_geom_pure_v18_sweep import load_data, params_for
from test_experiments_craze import build_module
from src.btc.btc_routes import _compute_swings
from src.walker import FlowCandle
from engine.v18_params import SWING

OUT = {"is": ROOT / "live_stuff/tests/_age2_gate_parity_is.json",
       "oos": ROOT / "live_stuff/tests/_age2_gate_parity_oos.json"}
REGISTRY_CONFIGS = ("champion_multi_sw10", "utcsat_multi_sw10",
                    "fullstack_wage10_cd0_single_sw10")
ALL_CONFIGS = ("literal_v18_single", "literal_v18_multi") + REGISTRY_CONFIGS
FRACTIONS = (0.70, 0.85)
MODE = "block_immediate"


def params_for_cfg(control):
    if control in REGISTRY_CONFIGS:
        p = {**BP, **EXPERIMENTS[control]["params"]}
        p.setdefault("exp_partial_r", 0.0)
        return p
    return params_for(control)


def flow(candles):
    return [FlowCandle(date=c["date"], open=float(c["open"]),
                       high=float(c["high"]), low=float(c["low"]),
                       close=float(c["close"])) for c in candles]


def prefix_data(data, cut):
    c1h = [c for c in data[0] if int(c["ts"]) <= cut]
    c15 = [c for c in data[2] if int(c["ts"]) <= cut]
    fine = [c for c in data[4] if int(c["ts"]) <= cut]
    sw10 = _compute_swings(flow(c1h), "continuous", min_bars=10)
    sw15 = _compute_swings(flow(c15), "continuous", min_bars=50)
    return c1h, sw10, c15, sw15, fine


def gate_run(sim, five, params, stats_out):
    out = sim(*five,
              **{**params, "exp_b1_b2_mode": MODE, "exp_b1_b2_stats": stats_out})
    return out["ltf_trades"] if isinstance(out, dict) else out


def rows_by_bar(rows):
    d = {}
    for r in rows:
        d.setdefault(int(r["entry_idx"]), []).append(r)
    return d


def compare(full_rows, pre_rows, cut_idx):
    f = {k: v[-1] for k, v in rows_by_bar(full_rows).items() if k <= cut_idx}
    p = {k: v[-1] for k, v in rows_by_bar(pre_rows).items() if k <= cut_idx}
    common = sorted(set(f) & set(p))
    only_f = sorted(set(f) - set(p))
    only_p = sorted(set(p) - set(f))
    age_mismatch = [k for k in common
                    if f[k].get("b1_b2_bars") != p[k].get("b1_b2_bars")]
    dec_mismatch = [k for k in common if int(f[k]["allowed"]) != int(p[k]["allowed"])]
    # blocked-by-age2 counts (decision materiality)
    blk_f = sum(1 for k in common if not int(f[k]["allowed"]))
    return {
        "full_bars": len(f), "prefix_bars": len(p), "common_bars": len(common),
        "full_only": len(only_f), "prefix_only": len(only_p),
        "age_mismatch": len(age_mismatch), "dec_mismatch": len(dec_mismatch),
        "dec_mismatch_bars": dec_mismatch[:20],
        "age_mismatch_bars": age_mismatch[:20],
        "blocked_in_full": blk_f,
        "parity_pass": len(age_mismatch) == 0 and len(dec_mismatch) == 0,
    }


def run_scope(scope, sim):
    t0 = time.time()
    data = load_data(scope)
    result = {"scope": scope, "mode": MODE, "fractions": list(FRACTIONS),
              "configs": {}}
    print(f"\n=== [{scope.upper()}] gate parity ===", flush=True)
    for cfg in ALL_CONFIGS:
        params = params_for_cfg(cfg)
        full_rows: list = []
        full = gate_run(sim, data, params, full_rows)
        row = {"full_trades": len(full)}
        for frac in FRACTIONS:
            cut = int(data[2][int((len(data[2]) - 1) * frac)]["ts"])
            pdata = prefix_data(data, cut)
            pre_rows: list = []
            gate_run(sim, pdata, params, pre_rows)
            cut_idx = len(pdata[2]) - 1
            cmp_ = compare(full_rows, pre_rows, cut_idx)
            row[str(frac)] = cmp_
            print(f"  {cfg:38} {frac:.2f} common={cmp_['common_bars']:4d} "
                  f"age_mm={cmp_['age_mismatch']:3d} dec_mm={cmp_['dec_mismatch']:3d} "
                  f"onlyF={cmp_['full_only']:3d} onlyP={cmp_['prefix_only']:3d} "
                  f"blocked={cmp_['blocked_in_full']:3d} "
                  f"{'PASS' if cmp_['parity_pass'] else 'FAIL'}", flush=True)
        result["configs"][cfg] = row
    result["elapsed_sec"] = round(time.time() - t0, 1)
    return result


def main():
    print("=" * 100, flush=True)
    print("  STAGE C — AGE-2 B1->B2 GATE PREFIX PARITY (live-feasibility)", flush=True)
    print("=" * 100, flush=True)
    sim = build_module()
    import inspect
    if "exp_b1_b2_mode" not in inspect.signature(sim).parameters:
        raise SystemExit("missing exp_b1_b2_mode kwarg")
    combined = {"instrument": "BTCUSDT_BYBIT", "stage": "C_age2_gate_parity"}
    for scope in ("is", "oos"):
        r = run_scope(scope, sim)
        OUT[scope].write_text(json.dumps(r, indent=2), encoding="utf-8")
        print(f"wrote {OUT[scope]}", flush=True)
        combined[scope] = r
    # summary
    print("\n=== SUMMARY (dec_mismatch on common bars) ===", flush=True)
    total_c = total_m = 0
    for scope in ("is", "oos"):
        for cfg, row in combined[scope]["configs"].items():
            for frac in FRACTIONS:
                c = row[str(frac)]
                total_c += c["common_bars"]
                total_m += c["dec_mismatch"]
    print(f"  common bars {total_c}, decision mismatches {total_m} "
          f"({(100.0*total_m/total_c) if total_c else 0:.2f}%)", flush=True)
    OUT.setdefault("is", None)
    print("done", flush=True)


if __name__ == "__main__":
    main()
