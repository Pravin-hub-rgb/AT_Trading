"""MIN_BARS on 1m - BINARY SEARCH for the plateau edge, not a blind ladder.

THE PROBLEM WITH THE LINEAR LADDER
==================================
The grid ran min_bars 3, 5, 8, 10, 15, 20, 30, 40, 60, 80. The check showed
min_bars 2, 3, 4, 5, 6 ALL return byte-identical swing chains (91,559), and
the first change is at 8 (91,463). So four of the ten rungs were the same
cell repeated - a ladder that looks thorough and is not, which understates
the real search while appearing to cover it.

The shape is monotone non-increasing in min_bars (a longer minimum leg can
only remove swings, never add them), so the plateau edge is a single
boundary and BINARY SEARCH finds it in O(log n) instead of sweeping it.
That is what this does: locate the exact smallest min_bars at which the
chain first changes, then price the book at the few points that matter.

Monotonicity is ASSUMED, then VERIFIED: if the search ever sees a value
whose fingerprint equals an earlier one, the assumption is recorded as
violated rather than silently trusted.

WHAT IS PRICED (only these, because only these can differ)
=========================================================
  mb_plateau  - the 2..6 plateau value; the true 1m floor
  mb_edge     - the first min_bars whose chain differs from the plateau
  2x edge     - one step of real headroom above it
  plus two coarse anchors (a fine and a very coarse one) for context

Each is run on both eras with the champion lane, entry decisive, trail
exit, and BOTH max_concurrent values - because concurrency was the other
axis the earlier runs held fixed, and it is the one most likely to
interact (AGENT_COORDINATION.md: slot effects run 3-5x the direct effect).

Run:  $env:PYTHONIOENCODING='utf-8'; python -u exp_1m_minbars_bsearch.py
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

OUT = ROOT / "backtest/tests/_1m_minbars_bsearch.json"

LO, HI = 2, 400            # search bounds for the plateau edge
PLATEAU_PROBE = 2          # the floor value everything is compared against
TARGET_R = 2.0
MAX_CONCURRENT = (1, 2)
ENTRY_KIND = "decisive"
SL_BUF_ATR = 0.01
MAX_HOLD_MIN = 240.0
MIN_RISK_ATR = 0.25
YEARS = {"is": 3.67, "oos": 2.0}
BYBIT_BASE = {"is/champion": (500, 325.8), "oos/champion": (279, 70.2)}
LANE_KEY = "champion_multi_sw10"


def _flow(candles):
    from src.walker import FlowCandle
    return [FlowCandle(date=c["date"], open=float(c["open"]),
                       high=float(c["high"]), low=float(c["low"]),
                       close=float(c["close"])) for c in candles]


def fingerprint(sw):
    """Cheap but decisive identity for a swing chain.

    Count alone can coincide across different chains, so this mixes the
    count with the first/middle/last swing's geometry. Two chains with the
    same fingerprint are treated as the same cell.
    """
    if not sw:
        return (0,)
    n = len(sw)
    picks = (sw[0], sw[n // 2], sw[-1])
    return (n,) + tuple(
        (s.get("swing_index"), s.get("dir"),
         s.get("seg", {}).get("start_idx"), s.get("seg", {}).get("end_idx"),
         round(float(s.get("seg", {}).get("end_px", 0.0)), 2))
        for s in picks)


def bsearch_edge(compute, lo, hi, base_fp):
    """Smallest min_bars in (lo, hi] whose chain differs from base_fp.

    Returns (edge, trace, monotonicity_violations).
    """
    trace = []
    violations = []
    seen = {}
    while lo < hi:
        mid = (lo + hi) // 2
        fp = fingerprint(compute(mid))
        trace.append({"min_bars": mid, "n": fp[0]})
        if fp in seen:
            violations.append({"min_bars": mid, "also_equals": seen[fp]})
        else:
            seen[fp] = mid
        if fp == base_fp:
            lo = mid + 1          # still on the plateau, go higher
        else:
            hi = mid               # diverged, the edge is at or below mid
    return lo, trace, violations


def main():
    import scalp_1m_engine as E
    E.install_b1_key()
    from src.btc.btc_routes import _compute_swings
    from exp_5m_confirm import load_book
    from exp_sizing_combo import run as sim_fn
    from experiment_registry import BP, EXPERIMENTS
    from exp_equity_quality import equity_quality
    from test_experiments_craze import build_module

    t0 = time.time()
    sim = build_module()
    payload = {"lo": LO, "hi": HI, "cells": {}, "edges": {}}
    print("=" * 104, flush=True)
    print("  1m MIN_BARS - binary search for the plateau edge, then price it",
          flush=True)
    print("=" * 104, flush=True)

    for scope in ("is", "oos"):
        print(f"\nloading {scope} ...", flush=True)
        data, _ = load_book(scope)
        c1m = data["fine"]
        f1m = _flow(c1m)
        wins = E.htf_windows(data["c1h"], data["sw10"], fine_ltf=data["fine"])
        print(f"  1m bars {len(c1m):,}  HTF windows {len(wins):,}", flush=True)

        params = {**BP, **EXPERIMENTS[LANE_KEY]["params"]}
        ctl = equity_quality(sim_fn(sim, data, dict(params)), YEARS[scope])
        exp_n, exp_net = BYBIT_BASE[f"{scope}/champion"]
        ok = ctl["n"] == exp_n and abs(ctl["net"] - exp_net) < 0.6
        print(f"  [{scope}] 15m CONTROL {ctl['n']}t {ctl['net']:+.1f}R "
              f"{'OK' if ok else 'MISMATCH'}", flush=True)
        if not ok:
            payload.setdefault("errors", []).append(scope)
            continue

        cache: dict = {}

        def compute(mb, _f=f1m, _c=cache):
            if mb not in _c:
                _c[mb] = _compute_swings(_f, "continuous", min_bars=mb)
            return _c[mb]

        base_fp = fingerprint(compute(PLATEAU_PROBE))
        print(f"\n  plateau probe min_bars={PLATEAU_PROBE}: "
              f"{base_fp[0]:,} swings", flush=True)

        edge, trace, viol = bsearch_edge(compute, LO, HI, base_fp)
        print(f"  BINARY SEARCH trace: " +
              " -> ".join(f"{t['min_bars']}({t['n']:,})" for t in trace),
              flush=True)
        print(f"  PLATEAU EDGE = min_bars {edge}  "
              f"(chain {fingerprint(compute(edge))[0]:,})", flush=True)
        if viol:
            print(f"  !! monotonicity violated: {viol}", flush=True)
        payload["edges"][scope] = {
            "edge": edge, "trace": trace, "violations": viol,
            "plateau_n": base_fp[0],
            "edge_n": fingerprint(compute(edge))[0],
        }

        # Price only the points that can actually differ.
        priced = sorted({PLATEAU_PROBE, edge, edge * 2, 40, 120})
        for mb in priced:
            sw = compute(mb)
            for mc in MAX_CONCURRENT:
                st: dict = {}
                tr = E.simulate_1m_scalp(
                    c1m, sw, wins, entry_break=ENTRY_KIND, target_r=TARGET_R,
                    sl_buf_atr=SL_BUF_ATR, max_concurrent=mc,
                    max_hold_min=MAX_HOLD_MIN, exit_mode="trail",
                    min_risk_atr=MIN_RISK_ATR, stats=st)
                E.assert_hold_cap(tr, MAX_HOLD_MIN, f"{scope}/mb{mb}/mc{mc}")
                m = E.book_metrics(tr, YEARS[scope])
                payload["cells"][f"{scope}/champion/mb{mb}/mc{mc}"] = {
                    **m, "gate": st, "min_bars": mb, "max_concurrent": mc}
                print(f"    mb{mb:<5} mc={mc}  sw {len(sw):>7,}  {m['n']:>6}t "
                      f"net {m['net']:>+8.1f}  trim "
                      f"{str(m.get('trimmed_mean')):>7}  "
                      f"PF {str(m.get('pf')):>6}  WR {m.get('wr', 0):>5}%  "
                      f"DD {m.get('max_dd', 0):>7.1f}  "
                      f"exB5 {str(m.get('ex_best5')):>8}", flush=True)
        cache.clear()

    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


def report():
    j = json.loads(OUT.read_text(encoding="utf-8"))
    print("\n" + "=" * 104)
    print("  EDGE + BOTH-ERA VERDICT")
    print("=" * 104)
    for scope, e in j.get("edges", {}).items():
        print(f"  {scope}: plateau n={e['plateau_n']:,} -> edge min_bars="
              f"{e['edge']} n={e['edge_n']:,}"
              + ("  [MONOTONICITY VIOLATED]" if e["violations"] else ""))
    cells = j["cells"]
    by: dict = {}
    for k, c in cells.items():
        p = k.split("/")
        by.setdefault((p[2], p[3]), {})[p[0]] = c
    both = {s: e for s, e in by.items() if set(e) == {"is", "oos"}}
    print(f"\n  {len(both)} shapes priced in both eras")
    win = []
    for s, e in sorted(both.items()):
        a, b = e["is"], e["oos"]
        tag = "PASS" if (a["trimmed_mean"] > 0 and b["trimmed_mean"] > 0
                         and a["net"] > 0 and b["net"] > 0
                         and a["ex_best5"] > 0 and b["ex_best5"] > 0) else "fail"
        if tag == "PASS":
            win.append(s)
        print(f"  {tag}  {s[0]:<10} mc={s[1]}  IS {a['net']:+8.1f}R "
              f"trim {a['trimmed_mean']:+.4f} | OOS {b['net']:+8.1f}R "
              f"trim {b['trimmed_mean']:+.4f}")
    print(f"\n  {len(win)}/{len(both)} pass the conjunctive bar.")
    return win


if __name__ == "__main__":
    if "--report" in sys.argv:
        report()
    else:
        main()
        report()
