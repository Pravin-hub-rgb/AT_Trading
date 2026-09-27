"""NULL CONTROL for 24.88 ETH-ledness: is the flag better than picking at random?

WHY
---
24.88 found three ETH-ledness arms at 6/6 on the Bybit gate. Before treating
that as a result, two things in its own JSON look wrong:

1. `d_max_dd` is NEGATIVE in 22 of 24 cells. The drawdown gets DEEPER almost
   everywhere. Every pass rode the `d_ulcer>0.5 OR d_calmar>0.05` branches of
   `curve_better`, never the `d_max_dd>0.5` branch. E_lag in particular passes
   6/6 with ulcer as low as -9.21 and d_max_dd -19.68, carried entirely by a
   calmar ratio.

2. The flag is NOT picking winners. `mean_r_flagged / book_mean` is 0.76 / 0.79
   / 0.65 / 0.72 / 0.97 / 1.43 - below 1.0 in five of six cells. The flagged
   cohort averages WORSE than the book it is drawn from, and it is ~45% of the
   book.

Together those two facts suggest dNet>0 here may be close to automatic: take any
~45% subset of a profitable book, multiply by 1.5, and the dNet is positive as
long as the subset's R sum is positive - which it usually is when the whole book
is profitable. Under that reading the ETH feature is not doing the work.

WHAT THIS RUNS
--------------
  Null arms: x1.5 on a RANDOM subset, matched to each real arm's flagged COUNT
  (not its share), so the null has the same sizing footprint by construction.
  Seeds: 200 per cell. This gives the NULL DISTRIBUTION of dNet and of
  curve_better, so a real arm can be placed in it instead of being eyeballed.

  REALITY CHECK = the real arm's dNet percentile against its own matched null.
    - if the real arm sits at ~50th percentile, the ETH feature adds nothing and
      the 6/6 is a property of the base book, not of ETH.
    - only a high percentile with a null that mostly FAILS curve_better would
      justify calling the arm real.

  Same ledgers, same equity_quality, same sizing exemption. No engine rerun.
  Control: bybit base ledgers must reproduce the 24.85 references, or abort.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_eth_ledness_null.py
"""
from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "live_stuff/tests/_eth_ledness_null.json"
SIZE = 1.5
SEEDS = 200
RNG = 0xE7  # fixed so the run is reproducible

BYBIT_BASE = {
    "champion": {"is": (500, 325.8), "oos": (279, 70.2)},
    "utcsat": {"is": (454, 358.9), "oos": (253, 60.2)},
    "age10": {"is": (130, 435.7), "oos": (76, 43.2)},
}

LANES = (
    ("champion", "champion_multi_sw10"),
    ("utcsat", "utcsat_multi_sw10"),
    ("age10", "age10_dirmatch_swingpause_single_sw10"),
)
ARMS = ("E_lead", "E_lag", "E_lead_w", "E_lag_w")
# END_PART



def apply_size(trades, keys, mult=SIZE):
    out = []
    for t in trades:
        t2 = dict(t)
        if (int(t["entry_ts"]), int(t["exit_ts"])) in keys:
            t2["r_multiple"] = round(float(t["r_multiple"]) * mult, 6)
        out.append(t2)
    assert [(t["entry_ts"], t["exit_ts"]) for t in out] == \
           [(t["entry_ts"], t["exit_ts"]) for t in trades], "key sequence changed"
    return out


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  ETH-LEDNESS NULL CONTROL - is the flag better than random?", flush=True)
    print("=" * 100, flush=True)

    from test_experiments_craze import build_module
    from exp_sizing_combo import run as sim_fn
    from exp_cross_instrument_transfer import load_bybit
    from exp_equity_quality import equity_quality, arm_scores, curve_better
    from exp_eth_ledness import (
        load_eth_1h, btc_closes, flag_keys, ARMS as ETH_ARMS)
    from experiment_registry import BP, EXPERIMENTS

    sim = build_module()
    ets, ecl = load_eth_1h()
    years = {"is": 3.67, "oos": 2.0}
    payload = {
        "stage": "eth_ledness_null",
        "lens": "random-subset null, matched flagged COUNT, 200 seeds per cell",
        "seeds": SEEDS, "size": SIZE,
        "pre_registered": {
            "purpose": ("place each 24.88 arm in its own matched null distribution "
                        "instead of eyeballing it"),
            "null": "x1.5 on a random subset of the same size as the real flag",
            "reading": ("~50th percentile => ETH adds nothing and 6/6 is a "
                        "property of the base book; only a high percentile with a "
                        "null that mostly FAILS curve_better justifies 'real'"),
            "control": "bybit base ledgers reproduce the 24.85 references",
        },
        "scopes": {}, "verdicts": {},
    }

    for scope in ("is", "oos"):
        data = load_bybit(scope, sim)
        bts, bcl = btc_closes(data)
        for name, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            trades = sim_fn(sim, data, params)
            m_base = equity_quality(trades, years[scope])
            exp_n, exp_net = BYBIT_BASE[name][scope]
            assert trades and m_base["n"] == exp_n, "CONTROL FAIL n"
            assert abs(m_base["net"] - exp_net) < 0.5, "CONTROL FAIL net"

            all_keys = [(int(t["entry_ts"]), int(t["exit_ts"])) for t in trades]
            n = len(all_keys)
            out = {}
            for arm, L, direction in ETH_ARMS:
                if arm not in ARMS:
                    continue
                keys = flag_keys(trades, ets, ecl, bts, bcl, L, direction)
                k = len(keys)
                if k == 0:
                    continue
                m_real = equity_quality(apply_size(trades, keys), years[scope])
                d_real = arm_scores(m_real, m_base)
                real_net, real_cb = d_real.get("d_net"), curve_better(d_real)

                rng = random.Random(RNG)
                null_nets, null_cbs = [], 0
                for _ in range(SEEDS):
                    rk = set(rng.sample(all_keys, k))
                    m_n = equity_quality(apply_size(trades, rk), years[scope])
                    d_n = arm_scores(m_n, m_base)
                    null_nets.append(d_n.get("d_net") or 0.0)
                    if curve_better(d_n):
                        null_cbs += 1
                null_nets.sort()

                def pct(v, _nn=null_nets):
                    below = sum(1 for x in _nn if x < v)
                    return round(100.0 * below / len(_nn), 1)

                out[arm] = {
                    "n_flagged": k, "share": round(k / n, 4),
                    "real_d_net": real_net, "real_curve_better": real_cb,
                    "null_mean_d_net": round(sum(null_nets) / len(null_nets), 4),
                    "null_median_d_net": round(null_nets[len(null_nets) // 2], 4),
                    "null_p5": round(null_nets[int(0.05 * len(null_nets))], 4),
                    "null_p95": round(null_nets[int(0.95 * len(null_nets))], 4),
                    "real_percentile": pct(real_net),
                    "null_curve_pass_rate": round(100.0 * null_cbs / SEEDS, 1),
                    "beats_null_p50": real_net > null_nets[len(null_nets) // 2],
                }
                print(f"  {scope}/{name:<9} {arm:<9} k={k:>3} "
                      f"real={real_net:>+8.1f} "
                      f"null_p50={null_nets[len(null_nets)//2]:>+8.1f} "
                      f"pct={pct(real_net):>5} "
                      f"nullCB={100.0*null_cbs/SEEDS:>5.1f}%", flush=True)
            payload["scopes"][f"{scope}/{name}"] = out


    # ---- verdicts -------------------------------------------------------
    arm_agrees, arm_cells, arm_nullfail = {}, {}, {}
    for arm in ARMS:
        cells = [v[arm] for v in payload["scopes"].values() if arm in v]
        arm_cells[arm] = len(cells)
        arm_agrees[arm] = sum(1 for c in cells if c["real_percentile"] >= 90.0)
        arm_nullfail[arm] = sum(1 for c in cells
                                if c["null_curve_pass_rate"] < 50.0)
    payload["verdicts"] = {
        "arm_cells": arm_cells,
        "arm_cells_real_pct_ge_90": arm_agrees,
        "arm_cells_null_curve_pass_under_50pct": arm_nullfail,
        "arm_is_real": {a: (arm_agrees[a] == arm_cells[a] and arm_nullfail[a] == arm_cells[a])
                        for a in ARMS},
    }
    payload["any_arm_real"] = any(payload["verdicts"]["arm_is_real"].values())
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print("\n" + "=" * 100, flush=True)
    print("  NULL-CONTROL VERDICT (real = beats its own matched null, 6/6 cells):",
          flush=True)
    for arm in ARMS:
        v = payload["verdicts"]
        print(f"    {arm:<9} pct>=90 in {v['arm_cells_real_pct_ge_90'][arm]}/6 | "
              f"null-curve-fails in {v['arm_cells_null_curve_pass_under_50pct'][arm]}/6 "
              f"| REAL={v['arm_is_real'][arm]}", flush=True)
    print("=" * 100, flush=True)
    print(f"  ANY ARM SURVIVES THE NULL: "
          f"{'YES' if payload['any_arm_real'] else 'NO'}", flush=True)
    print(f"wrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
