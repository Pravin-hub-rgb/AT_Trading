"""IS THE +0.498 ACF A TAIL ARTEFACT? Rank-based and binary re-test.

THE QUESTION
============
`exp_quant_autopsy.py` measured OOS trade-R ACF(lag1) = +0.4981 against a
+/-0.1173 band - four times outside, and it is the largest unexplained
structure found in this session. `exp_halt_firing_rate.py` then refuted my
own first explanation (the halt) by showing it fires at the same rate in
both eras (10.20 IS vs 10.39 OOS per 100 trades).

The one candidate left is the most embarrassing one: **this book is
tail-concentrated.** ACF is computed on R VALUES, so a handful of large R
in adjacent trades can push lag-1 correlation to +0.5 with no clustering of
wins or losses at all. If so, "+0.498" is three trades in a statistics
costume.

THE DECISIVE TEST
=================
The SAME lag-1 statistic, three ways, on the same trades:

  raw     : ACF of R                        (what was reported, +0.4981)
  wins    : ACF of the WIN/LOSS 0-1 series  (immune to any single R)
  ranked  : ACF of the RANKS of R            (monotone-transform invariant:
                                             only ORDER matters)

If the tail is the cause, `raw` is high and `wins` is ~0. If losses really
cluster, `wins` is high too. `ranked` is the tie-breaker: invariant to ANY
monotone transform of R, so it can only differ from `raw` if magnitude
carries the signal.

Where the monsters sit is also printed, since looking at whether big R
values are adjacent settles it without any statistics at all.

Run:  $env:PYTHONIOENCODING='utf-8'; python -u exp_acf_tail_check.py
"""
from __future__ import annotations

import json
import math
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "live_stuff/tests/_acf_tail_check.json"
LANE = "champion_multi_sw10"
BYBIT_BASE = {"is": (500, 325.8), "oos": (279, 70.2)}
MONSTER_R = 5.0


def acf(x, lag=1):
    n = len(x)
    if n <= lag + 2:
        return None
    d = [v - statistics.fmean(x) for v in x]
    den = sum(v * v for v in d)
    if den <= 0:
        return None
    return sum(d[i] * d[i + lag] for i in range(n - lag)) / den


def ranks(x):
    """Average-tie ranks, 1..n. Invariant to any monotone transform."""
    order = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and x[order[j + 1]] == x[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def main():
    from test_experiments_craze import build_module
    from exp_5m_confirm import load_book
    from exp_sizing_combo import run as sim_fn
    from experiment_registry import BP, EXPERIMENTS
    from exp_equity_quality import equity_quality

    t0 = time.time()
    sim = build_module()
    params = {**BP, **EXPERIMENTS[LANE]["params"]}
    payload = {"lane": LANE, "monster_r": MONSTER_R, "eras": {}}
    print("=" * 96, flush=True)
    print("  IS THE +0.498 ACF A TAIL ARTEFACT?  raw vs wins vs ranked",
          flush=True)
    print("=" * 96, flush=True)

    for scope in ("is", "oos"):
        data, _ = load_book(scope)
        tr = sim_fn(sim, data, dict(params))
        trades = tr["ltf_trades"] if isinstance(tr, dict) else tr
        rs = [float(t["r_multiple"]) for t in trades]
        n = len(rs)
        band = 1.96 / math.sqrt(n)
        m = equity_quality(tr, 3.67 if scope == "is" else 2.0)
        exp_n, exp_net = BYBIT_BASE[scope]
        ok = m["n"] == exp_n and abs(m["net"] - exp_net) < 0.6
        print(f"\n  [{scope}] CONTROL {m['n']}t {m['net']:+.1f}R "
              f"{'OK' if ok else 'MISMATCH'}", flush=True)
        if not ok:
            payload.setdefault("errors", []).append(scope)
            continue

        raw = acf(rs)
        acw = acf([1.0 if r > 0 else 0.0 for r in rs])
        acr = acf(ranks(rs))
        flag = lambda v: "OUTSIDE" if abs(v) > band else "inside"  # noqa: E731
        print(f"    n={n}   band +/-{band:.4f}", flush=True)
        print(f"      raw R       ACF1 {raw:+.4f}  {flag(raw)}", flush=True)
        print(f"      win/loss    ACF1 {acw:+.4f}  {flag(acw)}"
              f"   (immune to R magnitude)", flush=True)
        print(f"      ranks of R  ACF1 {acr:+.4f}  {flag(acr)}"
              f"   (monotone-invariant)", flush=True)

        mon = [i for i, r in enumerate(rs) if r >= MONSTER_R]
        gaps = [mon[i + 1] - mon[i] for i in range(len(mon) - 1)]
        adj = sum(1 for g in gaps if g == 1)
        print(f"    trades >= {MONSTER_R}R: {len(mon)}   adjacent pairs: {adj}"
              f"{'   <-- CLUSTERED' if adj >= 2 else ''}", flush=True)
        if mon:
            print(f"      R values:   {[round(rs[i], 1) for i in mon[:12]]}",
                  flush=True)
            print(f"      positions:  {mon[:12]}", flush=True)

        payload["eras"][scope] = {
            "n": n, "band": round(band, 4),
            "acf_raw": round(raw, 4), "acf_wins": round(acw, 4),
            "acf_ranked": round(acr, 4),
            "raw_outside": abs(raw) > band, "wins_outside": abs(acw) > band,
            "ranked_outside": abs(acr) > band,
            "monsters": len(mon), "monster_adjacent_pairs": adj,
            "monster_positions": mon[:20],
        }

    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()
