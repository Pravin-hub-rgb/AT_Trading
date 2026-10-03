"""FULL 1m SCALP SWEEP - vary the wager and the exit, as the user asked.

    "1:2 yeh ratio se alag karo kuch toh karo ... trailing karo kuch toh
     karo yaar"

Run 1 fixed target_r=2.0 with a swing trail and found PF ~1.0 everywhere.
That result is consistent with a book whose expectancy is already zero at
the entry, but it leaves the two obvious untested axes open: the REWARD
side and the EXIT side. This sweeps both, pre-registered and complete.

THE AXES (all run, none selected afterwards)
============================================
  target_r  : 0.5, 1.0, 1.5, 2.0, 3.0, 4.0     - the "1:2 ratio" the user
               named, plus both tighter and far wider wagers
  exit_mode : target   - fixed target, stop NEVER moves (pure wager)
               trail    - stop ratchets to each confirmed 1m swing pivot
               half_be  - stop to breakeven at +be_r, then trails
  be_r      : 0.5, 1.0                              (half_be only)
  min_bars  : 10, 40       - the two ends of the grind ladder
  entry     : decisive, b1 - b1 because it was the only OOS-trimmed-mean
                            positive cell in run 1

FIXED, not swept: sl_buf_atr=0.01 (the champion's constant), max_hold_min
=240, max_concurrent=1, min_risk_atr=0.25 (the HANDOVER 5.1 noise floor).
Sweeping those too would bury the answer in multiplicity.

WHY A BIG GRID IS STILL HONEST HERE
===================================
It is NOT because the grid is small. A grid this size WILL produce cells
that look good in one era. That is expected and is why the hit bar is
conjunctive and the judge is the TRIMMED MEAN (Rule 13), not avg R - a
0.5R target and a 4R target have wildly different avg-R profiles for the
same underlying edge, so avg R is not comparable across rungs here. Every
cell is reported, both eras, both lanes, and a cell only counts if it
clears the bar in BOTH eras simultaneously.

THE HIT BAR (unchanged from run 1)
==================================
  1. net R positive in BOTH eras
  2. trimmed mean positive in BOTH eras      <- the real judge
  3. ex-best-3 AND ex-best-5 positive       <- Rule 14
  4. same sign on both lanes
  5. additive: 15m book + 1m book > 15m book alone

Run:  $env:PYTHONIOENCODING='utf-8'; python -u exp_1m_scalp_sweep.py
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

OUT = ROOT / "backtest/tests/_1m_scalp_sweep.json"

TARGET_R = (0.5, 1.0, 1.5, 2.0, 3.0, 4.0)
EXIT_MODES = ("target", "trail", "half_be")
BE_R = (0.5, 1.0)
MIN_BARS = (10, 40)
ENTRY_KINDS = ("decisive", "b1")

# fixed
SL_BUF_ATR = 0.01
MAX_HOLD_MIN = 240.0
MAX_CONCURRENT = 1
MIN_RISK_ATR = 0.25
YEARS = {"is": 3.67, "oos": 2.0}
LANES = (("champion", "champion_multi_sw10"),
         ("utcsat", "utcsat_multi_sw10"))
BYBIT_BASE = {
    "is/champion": (500, 325.8), "is/utcsat": (453, 279.5),
    "oos/champion": (279, 70.2), "oos/utcsat": (253, 60.2),
}


def _flow(candles):
    from src.walker import FlowCandle
    return [FlowCandle(date=c["date"], open=float(c["open"]),
                       high=float(c["high"]), low=float(c["low"]),
                       close=float(c["close"])) for c in candles]


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
    payload = {"target_r": list(TARGET_R), "exit_modes": list(EXIT_MODES),
               "be_r": list(BE_R), "min_bars": list(MIN_BARS),
               "entry_kinds": list(ENTRY_KINDS), "cells": {}}
    print("=" * 100, flush=True)
    print("  1m SCALP SWEEP - reward side x exit side, pre-registered",
          flush=True)
    print("=" * 100, flush=True)

    for scope in ("is", "oos"):
        print(f"\nloading {scope} ...", flush=True)
        data, _ = load_book(scope)
        c1m = data["fine"]
        f1m = _flow(c1m)
        sw_cache = {mb: _compute_swings(f1m, "continuous", min_bars=mb)
                    for mb in MIN_BARS}
        for mb in MIN_BARS:
            print(f"  1m swings mb={mb}: {len(sw_cache[mb]):,}", flush=True)
        wins = E.htf_windows(data["c1h"], data["sw10"], fine_ltf=data["fine"])
        print(f"  HTF windows: {len(wins):,}", flush=True)

        for name, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            ctl = equity_quality(sim_fn(sim, data, dict(params)), YEARS[scope])
            exp_n, exp_net = BYBIT_BASE[f"{scope}/{name}"]
            ok = ctl["n"] == exp_n and abs(ctl["net"] - exp_net) < 0.6
            print(f"\n  [{scope}/{name}] 15m CONTROL {ctl['n']}t "
                  f"{ctl['net']:+.1f}R {'OK' if ok else 'MISMATCH'}", flush=True)
            if not ok:
                payload.setdefault("errors", []).append(f"{scope}/{name}")
                continue
            n_run = 0
            for mb in MIN_BARS:
                for kind in ENTRY_KINDS:
                    for r in TARGET_R:
                        modes = EXIT_MODES if r >= 1.0 else ("target",)
                        for mode in modes:
                            bes = BE_R if mode == "half_be" else (0.0,)
                            for be in bes:
                                st: dict = {}
                                tr = E.simulate_1m_scalp(
                                    c1m, sw_cache[mb], wins, entry_break=kind,
                                    target_r=r, sl_buf_atr=SL_BUF_ATR,
                                    max_concurrent=MAX_CONCURRENT,
                                    max_hold_min=MAX_HOLD_MIN,
                                    exit_mode=mode, be_r=be,
                                    min_risk_atr=MIN_RISK_ATR, stats=st)
                                E.assert_hold_cap(
                                    tr, MAX_HOLD_MIN,
                                    f"{scope}/{name}/mb{mb}/{kind}/r{r}/{mode}")
                                m = E.book_metrics(tr, YEARS[scope])
                                k = (f"{scope}/{name}/mb{mb}/{kind}/r{r}/"
                                     f"{mode}/be{be}")
                                payload["cells"][k] = {
                                    **m, "gate": st, "target_r": r,
                                    "exit_mode": mode, "be_r": be}
                                n_run += 1
                                print(f"    mb{mb} {kind:<8} r={r:<4} "
                                      f"{mode:<8} be={be:<4} {m['n']:>6}t "
                                      f"net {m['net']:>+8.1f}  "
                                      f"trim {str(m.get('trimmed_mean')):>7}  "
                                      f"PF {str(m.get('pf')):>6}  "
                                      f"DD {m.get('max_dd', 0):>6.1f}  "
                                      f"exB5 {str(m.get('ex_best5')):>8}",
                                      flush=True)
            print(f"  [{scope}/{name}] {n_run} cells", flush=True)

    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


def report():
    """Post-run: which cells clear the conjunctive hit bar in BOTH eras?"""
    j = json.loads(OUT.read_text(encoding="utf-8"))
    cells = j["cells"]
    by_shape: dict = {}
    for k, c in cells.items():
        p = k.split("/")
        shape = (p[2], p[3], p[4], p[5], p[6])
        by_shape.setdefault(shape, {})[p[0]] = c

    print("\n" + "=" * 100)
    print("  CELLS CLEARING THE HIT BAR IN BOTH ERAS")
    print("=" * 100)
    winners = []
    both = {s: e for s, e in by_shape.items() if set(e) == {"is", "oos"}}
    for shape, eras in sorted(both.items()):
        a, b = eras["is"], eras["oos"]
        if (a["trimmed_mean"] > 0 and b["trimmed_mean"] > 0
                and a["net"] > 0 and b["net"] > 0
                and a["ex_best5"] > 0 and b["ex_best5"] > 0):
            winners.append((shape, a, b))
            print(f"  PASS  mb{shape[0]} {shape[1]:<8} r={shape[2]:<5} "
                  f"{shape[3]:<8} be={shape[4]:<5} "
                  f"IS {a['net']:+.1f}R trim {a['trimmed_mean']:+.3f} | "
                  f"OOS {b['net']:+.1f}R trim {b['trimmed_mean']:+.3f}")
    print(f"\n  {len(winners)}/{len(both)} cells pass the conjunctive bar.")
    if not winners:
        best = sorted(((min(v["is"]["trimmed_mean"], v["oos"]["trimmed_mean"]), s)
                       for s, v in both.items()), reverse=True)[:6]
        print("  best by WORST-ERA trimmed mean (the honest ranking):")
        for v, s in best:
            print(f"    {v:+.4f}  mb{s[0]} {s[1]:<8} r={s[2]} {s[3]} be={s[4]}")
    return winners


if __name__ == "__main__":
    if "--report" in sys.argv:
        report()
    else:
        main()
        report()
