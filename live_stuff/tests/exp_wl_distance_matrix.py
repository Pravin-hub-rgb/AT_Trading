"""Stage F — W/L × distance matrix (documentation only, no gate).

Re-cuts Stage 25 geometry distances (exp_thesis_swing_geometry_deep feature
rows) into explicit winner/loser x distance-bucket cells. The Stage 25 report
gave winners/losses distribution stats per field; this gives per-bucket
n / win-rate / net R so the W/L asymmetry across distance is readable as a
matrix.

Fields (pre-frozen): prev_fs_to_signal, prev_final_to_signal, b1_to_signal,
cur_start_to_b1 — bars + ATR variants where present.
Configs: fullstack_wage10_cd0_single_sw10, champion_multi_sw10,
utcsat_multi_sw10. Scopes: IS + OOS.

Verdict slot: documentation only — NO gate, no production change.

Run: $env:PYTHONIOENCODING='utf-8'; python -u live_stuff/tests/exp_wl_distance_matrix.py
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
from test_experiments_craze import build_module
from exp_thesis_structure_volume import load_scope, CONFIGS
from exp_thesis_swing_geometry_deep import trade_rows, bar_bucket

OUT = ROOT / "live_stuff/tests/_wl_distance_matrix_results.json"
FIELDS = (
    ("prev_fs_to_signal_bars", bar_bucket),
    ("prev_final_to_signal_bars", bar_bucket),
    ("b1_to_signal_bars", bar_bucket),
    ("cur_start_to_b1_bars", bar_bucket),
    ("prev_fs_to_signal_atr", lambda v: "none" if v is None else
     "neg" if v < 0 else "0-1" if v < 1 else "1-2" if v < 2 else
     "2-4" if v < 4 else "4-8" if v < 8 else "8+"),
    ("prev_final_to_signal_atr", lambda v: "none" if v is None else
     "neg" if v < 0 else "0-1" if v < 1 else "1-2" if v < 2 else
     "2-4" if v < 4 else "4-8" if v < 8 else "8+"),
    ("b1_to_signal_atr", lambda v: "none" if v is None else
     "neg" if v < 0 else "0-1" if v < 1 else "1-2" if v < 2 else
     "2-4" if v < 4 else "4-8" if v < 8 else "8+"),
)


def cell(rows):
    n = len(rows)
    if not n:
        return None
    wins = [r for r in rows if r["r_multiple"] > 0]
    gross = sum(float(r.get("r_multiple") or 0) for r in rows)
    return {
        "n": n, "wins": len(wins),
        "win_rate_pct": round(100.0 * len(wins) / n, 1),
        "gross_r": round(gross, 2),
        "net_per_r": round(gross / n, 3),
        "runner_n": sum(1 for r in rows if float(r.get("r_multiple") or 0) >= 3.0),
    }


def matrix(rows, field, bucket_fn):
    groups = {}
    for r in rows:
        v = r.get(field)
        groups.setdefault(bucket_fn(v), []).append(r)
    ordered = sorted(groups.items(), key=lambda kv: str(kv[0]))
    return {str(k): cell(v) for k, v in ordered if cell(v) is not None}


def main():
    t0 = time.time()
    print("=" * 104, flush=True)
    print("  STAGE F — W/L × DISTANCE MATRIX (documentation only, no gate)", flush=True)
    print("=" * 104, flush=True)
    sim = build_module()
    payload = {"instrument": "BTCUSDT_BYBIT",
               "study": "W/L x distance matrix (Stage 25 re-cut, descriptive)",
               "configs": list(CONFIGS)}
    for scope in ("is", "oos"):
        data = load_scope(scope)
        payload[scope] = {}
        print(f"\n=== [{scope.upper()}] ===", flush=True)
        for key in CONFIGS:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            params.setdefault("exp_partial_r", 0.0)
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                      fine_ltf=data["fine"], **params)
            trades = out["ltf_trades"] if isinstance(out, dict) else out
            rows = trade_rows(trades, data)
            block = {}
            print(f"\n  {key} (n={len(rows)})", flush=True)
            for field, bfn in FIELDS:
                m = matrix(rows, field, bfn)
                block[field] = m
                print(f"    {field}", flush=True)
                print(f"      {'bucket':>8} {'n':>4} {'win%':>6} {'grossR':>8} "
                      f"{'R/n':>7} {'3R+':>4}", flush=True)
                for b, c in m.items():
                    print(f"      {b:>8} {c['n']:>4} {c['win_rate_pct']:>6.1f} "
                          f"{c['gross_r']:>+8.1f} {c['net_per_r']:>+7.3f} "
                          f"{c['runner_n']:>4}", flush=True)
            payload[scope][key] = block
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)", flush=True)
    print("documentation only — no gate, no production change", flush=True)


if __name__ == "__main__":
    main()
