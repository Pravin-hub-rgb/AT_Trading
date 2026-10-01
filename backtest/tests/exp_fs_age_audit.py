"""Stage A — fs_age degeneracy audit (read-only).

Stage 24's by_fs_age put EVERY trade in the "0-4" bucket across all six
reference/era cells. Possible causes:
  1. bucket-chain bug: lambda uses `<= 4` with no lower bound, so NEGATIVE
     fs_age (FS stamped after entry) silently lands in "0-4";
  2. fs_at_idx genuinely within 0-4 bars of entry for all trades;
  3. fs_at_idx missing -> -1 -> fs_age None -> would show as "none" bucket
     (not observed, but verify raw).
  4. fallback path (sig mark missing at entry bar) skewing ages.

Run: python -u backtest/tests/exp_fs_age_audit.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate
from test_experiments_craze import build_module
from test_4_new_concepts import load_unseen, load_fine_1m
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING

import exp_thesis_structure_volume as tsv

OUT = ROOT / "backtest/tests/_fs_age_audit_results.json"


def collect(scope):
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
        sw10 = _compute_swings(f1h, "continuous", min_bars=10)
        fine = load_fine_1m(c15[0]["ts"], c15[-1]["ts"])
        data = {"c15": c15, "f15": f15, "c1h": c1h, "f1h": f1h,
                "sw15": sw15, "sw10": sw10, "fine": fine}
    else:
        data = get_data()
        identity_gate(data, build_module())
    sim = build_module()
    cfg = EXPERIMENTS["champion_multi_sw10"]
    params = {**BP, **cfg["params"]}
    params.setdefault("exp_partial_r", 0.0)
    out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
              fine_ltf=data["fine"], **params)
    trades = out["ltf_trades"] if isinstance(out, dict) else out
    rows = tsv.trade_features(trades, data, scope)
    return data, rows


def audit_rows(rows, label):
    ages = [r["fs_age_bars"] for r in rows]
    none_n = sum(a is None for a in ages)
    vals = [a for a in ages if a is not None]
    neg = [a for a in vals if a < 0]
    res = {
        "label": label,
        "n": len(rows),
        "none": none_n,
        "min": min(vals) if vals else None,
        "max": max(vals) if vals else None,
        "negatives": len(neg),
        "hist": dict(sorted(Counter(
            "neg" if a < 0 else "0-4" if a <= 4 else "5-12" if a <= 12
            else "13-48" if a <= 48 else "49+" for a in vals).items())),
        "sample": [],
    }
    for r in rows[:5] + rows[len(rows) // 2:len(rows) // 2 + 3]:
        sw = None
        i15 = r["i15"]
        res["sample"].append({
            "entry": str(r.get("entry_date", ""))[:16],
            "i15": i15,
            "fs_age": r["fs_age_bars"],
            "swing_no": r.get("swing_no"),
            "mark_at_entry": r.get("mark_sequence"),
        })
    return res


def stage25_check():
    """Dump raw bucket structure for prev-fs distances in Stage 25 JSONs."""
    out = {}
    for era in ("is", "oos"):
        p = ROOT / f"backtest/tests/_thesis_swing_geometry_deep_results_{era}.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        found = {}

        def walk(o, path=""):
            if isinstance(o, dict):
                for key in ("prev_fs_to_signal_bars", "prev_fs_to_cur_start_bars",
                            "prev_final_to_signal_bars"):
                    if key in o and isinstance(o[key], dict):
                        found.setdefault(path + "/" + key, {
                            k: (v.get("n"), v.get("net_r")) if isinstance(v, dict) else v
                            for k, v in o[key].items()})
                for k, v in o.items():
                    walk(v, path + "/" + k)
            elif isinstance(o, list):
                for i, v in enumerate(o):
                    walk(v, path + f"[{i}]")
        walk(d)
        out[era] = found
    return out


def main():
    print("=" * 90, flush=True)
    print("  STAGE A — fs_age DEGENERACY AUDIT (read-only)", flush=True)
    print("=" * 90, flush=True)
    result = {"stage": "A_fs_age_audit"}
    for scope in ("is", "oos"):
        print(f"\n--- {scope.upper()} ---", flush=True)
        data, rows = collect(scope)
        a = audit_rows(rows, f"champion_{scope}")
        result[scope] = a
        print(f"  n={a['n']} none={a['none']} min={a['min']} max={a['max']} "
              f"negatives={a['negatives']}", flush=True)
        print(f"  hist: {a['hist']}", flush=True)
        for s in a["sample"]:
            print(f"    {s}", flush=True)
    print("\n--- Stage 25 prev-fs bucket structures (raw) ---", flush=True)
    result["stage25_prev_fs"] = stage25_check()
    for era, found in result["stage25_prev_fs"].items():
        for path, buckets in found.items():
            print(f"  [{era}] {path}: {buckets}", flush=True)
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
