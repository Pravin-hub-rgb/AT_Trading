"""INDEPENDENT AUDIT of the 1h wick gate - does NOT reuse the other agent's flags.

WHY THIS EXISTS
---------------
`exp_gray_wick1h.py` (other agent) reports Stage B's real 1h-plane wick gate at
4/4 PASS under gray mode, and I verified its parity is exact. But three questions
were left open, and this harness answers them by RECOMPUTING the feature from the
engine rather than reading `_gray_wick1h.json`:

  Q1 ROBUSTNESS - is the cohort negative because of a genuine edge, or because
     of one or two runners? Drop the single best trade from the cohort and see
     whether it stays negative.
  Q2 THRESHOLD OVERFIT - 6.026 is a value Stage B found by mining. If the cohort
     is only negative at exactly that number, it is a fitted point. A real
     effect shows as a PLATEAU across a range, in BOTH eras independently.
  Q3 AGE10 - the flagged cohort is -28.1R on champion but **+2.0R** on age10
     (20 trades). Is that a structural difference or noise at n=20?

CAUSALITY
----------
`wick_atr12` comes from exp_regime_structure_autopsy.compute_features, which
resolves `j = bisect_right(ts, cutoff-3600)-1` over `build_arrays(data["c1h"])`
- the last 1h bar CLOSED before the cutoff, ATR14 of 1h, 12 bars ending at j.
Short-only, exactly as Stage B. Nothing here is recomputed from a later bar.

PRE-REGISTERED BEFORE THE RUN (2026-09-27)
------------------------------------------
  Threshold sweep: 4.0 / 4.5 / 5.0 / 5.5 / 6.0 / 6.026 / 6.5 / 7.0 / 8.0.
  PASS (edge is real) requires: cohort sum_net < 0 in BOTH eras at 6.026, AND
  still < 0 in both eras across at least the 5.0-7.0 span (a plateau), AND
  still < 0 after dropping the cohort's single best trade in at least 4 of 6
  cells (not outlier-driven).
  Controls: bybit base ledgers must reproduce the 24.85 references; Stage B
  parity (counts + sum_net) must reproduce to 1e-3 at 6.026.
  No retune after the run.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_wick1h_audit.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from run_experiment import net_r  # module-level: cohort() needs it

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "backtest/tests/_wick1h_audit.json"
STAGEB_THR = 6.026
SWEEP = (4.0, 4.5, 5.0, 5.5, 6.0, 6.026, 6.5, 7.0, 8.0)
STAGEB_REF = {          # counts + sum_net from the other agent's parity block
    "is/champion": (74, -28.056935), "is/utcsat": (62, -25.673556),
    "oos/champion": (35, -19.780510), "oos/utcsat": (36, -23.774610),
}

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
# END_MARKER



def build_ctx(data):
    """The 1h-plane context compute_features() expects (same as the Z1 autopsy)."""
    from exp_regime_structure_autopsy import build_arrays
    from exp_regime_structure_autopsy import _chop_series_1h
    arr = build_arrays(data["c1h"])
    conf = []
    for s in data["sw10"]:
        ci = s.get("confirmed_at_idx")
        if ci is None or not (0 <= ci < arr["n"]):
            continue
        dur = max(1, (s["seg"]["end_idx"] - s["seg"]["start_idx"]))
        conf.append((arr["ts"][ci], s["dir"], float(dur)))
    conf.sort(key=lambda x: x[0])
    return {"arr": arr, "chop": _chop_series_1h(data["c1h"], lb=14),
            "conf_ts": [x[0] for x in conf], "conf_dir": [x[1] for x in conf],
            "conf_dur": [x[2] for x in conf]}


def cohort(trades, feats, thr):
    """Short trades with 1h wick_atr12 <= thr, as (net, key, wick) tuples."""
    out = []
    for t, f in zip(trades, feats):
        if t.get("dir") == "long":
            continue
        w = f.get("wick_atr12")
        if w is None or w > thr:
            continue
        out.append((net_r([t]), (int(t["entry_ts"]), int(t["exit_ts"])), float(w)))
    return out


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  WICK 1H AUDIT - robustness, threshold overfit, age10", flush=True)
    print("=" * 100, flush=True)

    from test_experiments_craze import build_module
    from exp_sizing_combo import run as sim_fn
    from exp_cross_instrument_transfer import load_bybit
    from exp_regime_structure_autopsy import compute_features
    from experiment_registry import BP, EXPERIMENTS
    from run_experiment import net_r

    sim = build_module()
    payload = {
        "stage": "wick1h_audit", "plane": "1h", "window": 12,
        "stageb_thr": STAGEB_THR, "sweep": list(SWEEP),
        "pre_registered": {
            "real_edge": ("cohort sum_net<0 in BOTH eras at 6.026 AND across the "
                          "5.0-7.0 span (plateau) AND survives dropping the "
                          "cohort's best trade in >=4 of 6 cells"),
            "control": "base ledgers reproduce 24.85; Stage B parity to 1e-3",
        },
        "cells": {}, "sweep_tbl": {}, "parity": {},
    }

    for scope in ("is", "oos"):
        data = load_bybit(scope, sim)
        ctx = build_ctx(data)
        for name, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            trades = sim_fn(sim, data, params)
            n, net = len(trades), net_r(trades)
            exp_n, exp_net = BYBIT_BASE[name][scope]
            assert n == exp_n and abs(net - exp_net) < 0.5, (
                f"CONTROL {scope}/{name}: {n}/{net:.2f}")
            feats = [compute_features(t, ctx) for t in trades]
            book_avg = net / n
            payload["cells"][f"{scope}/{name}"] = {
                "n": n, "net": round(net, 3),
                "book_avg_r": round(book_avg, 4)}
            print(f"\n{scope}/{name}  n={n} net={net:+.1f} "
                  f"bookAvgR={book_avg:+.3f}", flush=True)

            for thr in SWEEP:
                c = cohort(trades, feats, thr)
                s = sum(x[0] for x in c)
                row = {"thr": thr, "n_cohort": len(c), "sum_net": round(s, 3),
                       "avg_r": round(s / len(c), 4) if c else None,
                       "vs_book_avg": (round(s / len(c) - book_avg, 4) if c
                                       else None),
                       "positive": s > 0}
                if c:
                    best = max(c, key=lambda x: x[0])
                    rest = s - best[0]
                    row["sum_net_ex_best"] = round(rest, 3)
                    row["still_neg_ex_best"] = rest < 0
                    row["top3_contrib"] = round(
                        sum(sorted((x[0] for x in c), reverse=True)[:3]), 3)
                payload["sweep_tbl"][f"{scope}/{name}/{thr}"] = row
                mark = "*" if abs(thr - STAGEB_THR) < 1e-9 else " "
                print(f"   thr{thr:>6.2f}{mark} n={row['n_cohort']:>4} "
                      f"sum={row['sum_net']:>+9.2f} avgR={str(row['avg_r']):>8} "
                      f"vsBook={str(row['vs_book_avg']):>8}", flush=True)

            c = cohort(trades, feats, STAGEB_THR)
            kk = f"{scope}/{name}"
            if kk in STAGEB_REF:
                en, es = STAGEB_REF[kk]
                payload["parity"][kk] = {
                    "n": len(c), "n_expected": en,
                    "sum_net": round(sum(x[0] for x in c), 6),
                    "sum_expected": es,
                    "match": (len(c) == en
                              and abs(sum(x[0] for x in c) - es) < 1e-3)}

    # ---- verdicts -------------------------------------------------------
    par = payload["parity"]
    payload["verdicts"] = {"stageb_parity_all": all(p["match"] for p in par.values()),
                          "parity_cells": len(par)}

    for thr in SWEEP:
        rows = [v for k, v in payload["sweep_tbl"].items()
                if abs(v["thr"] - thr) < 1e-9]
        neg_cells = sum(1 for r in rows if r["sum_net"] < 0)
        ex_best_neg = sum(1 for r in rows if r.get("still_neg_ex_best"))
        eras = {s: all(payload["sweep_tbl"][f"{s}/{n}/{thr}"]["sum_net"] < 0
                       for n, _ in LANES)
                for s in ("is", "oos")}
        payload["verdicts"][f"thr_{thr}"] = {
            "neg_cells": neg_cells, "of": len(rows),
            "ex_best_neg_cells": ex_best_neg,
            "both_eras_all_lanes_negative": all(eras.values()),
            "era_detail": {k: v for k, v in eras.items()},
        }
        print(f"  thr {thr:>6.3f}  cohort negative in {neg_cells}/{len(rows)} "
              f"cells | ex-best {ex_best_neg}/{len(rows)} | "
              f"both eras {all(eras.values())}", flush=True)

    pl = [5.0, 5.5, 6.0, 6.026, 6.5, 7.0]
    plateau = all(payload["verdicts"][f"thr_{t}"]["both_eras_all_lanes_negative"]
                  for t in pl)
    at_thr = payload["verdicts"]["thr_6.026"]
    payload["verdicts"]["plateau_5_to_7"] = plateau
    payload["verdicts"]["edge_is_real"] = bool(
        payload["verdicts"]["stageb_parity_all"]
        and at_thr["both_eras_all_lanes_negative"]
        and at_thr["ex_best_neg_cells"] >= 4
        and plateau)
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print("\n" + "=" * 100, flush=True)
    print(f"  STAGE B PARITY (independent recompute): "
          f"{payload['verdicts']['stageb_parity_all']}", flush=True)
    for k, v in payload["parity"].items():
        print(f"    {k:16} n={v['n']}/{v['n_expected']} "
              f"sum={v['sum_net']:+.6f} vs {v['sum_expected']:+.6f} "
              f"-> {v['match']}", flush=True)
    print(f"  PLATEAU 5.0-7.0: {plateau}", flush=True)
    print(f"  EDGE IS REAL: {payload['verdicts']['edge_is_real']}", flush=True)
    print("=" * 100, flush=True)
    print(f"wrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
