"""SL-WIDTH BUCKET AUTOPSY - a standalone descriptive pass (no gray gate).

Why separate: the gray-gate harness (exp_sl_width_gate.py) produced valid gate
numbers but its identity/bucket sections came out EMPTY, because the reference
book is produced by exp_sizing_combo.run, which does not carry the patched
`sl_width_pct` field into the harness in a way this audit could rely on. Rather
than debug that plumbing, this recomputes sl_width_pct directly from the SHIPPED
trade records (entry_price + sl, v18:732-733) - the identical formula the gate
uses - so the bucket table is trustworthy and independent of any patch.

This answers the USER'S ACTUAL QUESTION first: is there a healthy SL-width
range? The gate only matters if some band is genuinely better.

Descriptive only. It proposes a band; it does not gate anything and it does
not look at outcomes it did not pre-declare.
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

OUT = ROOT / "backtest/tests/_sl_width_buckets.json"
BUCKETS = ((0.0, 0.25), (0.25, 0.4), (0.4, 0.55), (0.55, 0.7),
           (0.7, 0.9), (0.9, 1.2), (1.2, 1.6), (1.6, 99.0))

BYBIT_BASE = {
    "champion": {"is": (500, 325.8), "oos": (279, 70.2)},
    "utcsat": {"is": (453, 279.5), "oos": (254, 66.9)},
    "age10": {"is": (130, 435.7), "oos": (76, 43.2)},
}
LANES = (
    ("champion", "champion_multi_sw10"),
    ("utcsat", "utcsat_multi_sw10"),
    ("age10", "age10_dirmatch_swingpause_single_sw10"),
)


def slw(t):
    e = float(t["entry_price"]); s = float(t["sl"])
    return abs(e - s) / e * 100.0 if e else None


def main():
    t0 = time.time()
    from test_experiments_craze import build_module
    from exp_sizing_combo import run as sim_fn
    from exp_cross_instrument_transfer import load_bybit
    from experiment_registry import BP, EXPERIMENTS
    from run_experiment import net_r

    sim = build_module()
    years = {"is": 3.67, "oos": 2.0}
    payload = {"stage": "sl_width_buckets", "buckets":
               [f"{lo:.2f}-{hi:.2f}" for lo, hi in BUCKETS], "cells": {}}
    agg = {}

    for scope in ("is", "oos"):
        data = load_bybit(scope, sim)
        for name, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            trades = sim_fn(sim, data, params)
            n = len(trades)
            net = net_r(trades)
            exp_n, exp_net = BYBIT_BASE[name][scope]
            print(f"   [control] n={n} vs {exp_n}  net={net:.3f} vs {exp_net}",
                  flush=True)
            assert n == exp_n, f"CONTROL n {scope}/{name}: {n} != {exp_n}"
            assert abs(net - exp_net) < 0.5, (
                f"CONTROL net {scope}/{name}: {net} != {exp_net}")
            rows = []
            print(f"\n{scope}/{name}  n={n} net={net:+.1f}", flush=True)
            for lo, hi in BUCKETS:
                sel_t = [t for t in trades
                         if (w := slw(t)) is not None and lo <= w < hi]
                sel = [net_r([t]) for t in sel_t]
                m = len(sel)
                a = round(sum(sel) / m, 4) if m else None
                wr = round(sum(1 for x in sel if x > 0) / m, 4) if m else None
                rows.append({"band": f"{lo:.2f}-{hi:.2f}", "n": m, "avg_r": a,
                             "wr": wr, "net": round(sum(sel), 2)})
                g = agg.setdefault(f"{lo:.2f}-{hi:.2f}", {"n": 0, "net": 0.0, "sum": 0.0, "wr": 0.0})
                g["n"] += m; g["net"] += sum(sel)
                if m:
                    g["sum"] += sum(sel); g["wr"] += sum(1 for x in sel if x > 0)
                print(f"   {rows[-1]['band']:>10}  n={m:>4}  avgR={str(a):>8}  "
                      f"wr={str(wr):>7}  net={rows[-1]['net']:>+9.1f}", flush=True)
            payload["cells"][f"{scope}/{name}"] = rows

    print("\n=== AGGREGATE (all 6 cells) ===", flush=True)
    for b, g in agg.items():
        if not g["n"]:
            continue
        print(f"  {b:>10}  n={g['n']:>5}  avgR={g['sum']/g['n']:>7.3f}  "
              f"WR={g['wr']/g['n']*100:>5.1f}%  net={g['net']:>+10.1f}", flush=True)
        payload.setdefault("agg", {})[b] = {
            "n": g["n"], "avg_r": round(g["sum"]/g["n"], 4),
            "wr": round(g["wr"]/g["n"], 4), "net": round(g["net"], 2)}
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
