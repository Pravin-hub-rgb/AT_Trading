"""1m SCALP — the axes the first two runs left FIXED.

WHY A THIRD RUN
===============
Run 1 (`exp_1m_scalp.py`) fixed target_r=2.0 + swing trail.
Run 2 (`exp_1m_scalp_sweep.py`) swept the reward and exit sides:
target_r 0.5-4.0 x target/trail/half_be. Result: no cell with a positive
trimmed mean; half_be was catastrophic (BE turns the stop into a
noise-catcher at 1m).

But two axes were held CONSTANT through both runs, and both are exactly
the "grind level" the user keeps pointing at:

  1. `min_bars` - only 10 and 40 were tried. The 1m swing grind level is
     the single most obvious knob for "scalping" and it is unexplored.
     min_bars IS the 1m swing's minimum leg length, so it sets both how
     noisy a break is and how long a scalp is expected to run.
  2. `max_concurrent` - fixed at 1 in every run, i.e. scalps never stack.
     Stacking is the whole point of scalping inside a window, and it was
     never varied. It is also the knob most likely to interact with the
     cascade findings (AGENT_COORDINATION.md: slot effects are 3-5x the
     direct effect), so it must be reported with ex-best and DD, not net.

PRE-REGISTERED
==============
  min_bars        : 3, 5, 8, 10, 15, 20, 30, 40, 60, 80
  max_concurrent  : 1, 2, 3
  target_r        : 1.0, 2.0          (the sweep showed 0.5/4.0 are worse;
                                        keep 2 rungs so concurrency is the
                                        only thing moving)
  exit_mode       : trail             (best of run 2's three, every time)
  entry_break     : decisive, b1      (b1 was the OOS-trimmed-mean leader)

= 10 x 3 x 2 x 2 = 120 cells per era. All run. None selected after.

THE JUDGING RULE IS UNCHANGED AND DELIBERATE
============================================
Trimmed mean, positive in BOTH eras, plus ex-best-3/5 positive. Run 2
showed why this matters: at r=3/4 the NET goes positive (+178R) while the
trimmed mean is -0.155. That is not an edge, it is three trades. A grid
this size WILL produce net-positive cells by chance; the trimmed mean and
the both-eras requirement are what stop those from being mistaken for a
result.

Run:  $env:PYTHONIOENCODING='utf-8'; python -u exp_1m_scalp_grid.py
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

OUT = ROOT / "backtest/tests/_1m_scalp_grid.json"

MIN_BARS = (3, 5, 8, 10, 15, 20, 30, 40, 60, 80)
MAX_CONCURRENT = (1, 2, 3)
TARGET_R = (1.0, 2.0)
ENTRY_KINDS = ("decisive", "b1")

SL_BUF_ATR = 0.01
MAX_HOLD_MIN = 240.0
MIN_RISK_ATR = 0.25
YEARS = {"is": 3.67, "oos": 2.0}
LANES = (("champion", "champion_multi_sw10"),)
BYBIT_BASE = {"is/champion": (500, 325.8), "oos/champion": (279, 70.2)}


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
    payload = {"min_bars": list(MIN_BARS), "max_concurrent": list(MAX_CONCURRENT),
               "target_r": list(TARGET_R), "entry_kinds": list(ENTRY_KINDS),
               "exit_mode": "trail", "cells": {}}
    print("=" * 104, flush=True)
    print("  1m SCALP GRID - min_bars x max_concurrent (the fixed axes)",
          flush=True)
    print("=" * 104, flush=True)

    for scope in ("is", "oos"):
        print(f"\nloading {scope} ...", flush=True)
        data, _ = load_book(scope)
        c1m = data["fine"]
        f1m = _flow(c1m)
        wins = E.htf_windows(data["c1h"], data["sw10"], fine_ltf=data["fine"])
        print(f"  1m bars {len(c1m):,}   HTF windows {len(wins):,}", flush=True)

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
                # One swing set at a time: 1.95M bars x 10 settings does not
                # fit in memory all at once.
                sw = _compute_swings(f1m, "continuous", min_bars=mb)
                print(f"\n    -- min_bars={mb}: {len(sw):,} 1m swings", flush=True)
                for kind in ENTRY_KINDS:
                    for r in TARGET_R:
                        for mc in MAX_CONCURRENT:
                            st: dict = {}
                            tr = E.simulate_1m_scalp(
                                c1m, sw, wins, entry_break=kind, target_r=r,
                                sl_buf_atr=SL_BUF_ATR, max_concurrent=mc,
                                max_hold_min=MAX_HOLD_MIN, exit_mode="trail",
                                min_risk_atr=MIN_RISK_ATR, stats=st)
                            E.assert_hold_cap(tr, MAX_HOLD_MIN,
                                              f"{scope}/mb{mb}/{kind}/r{r}/mc{mc}")
                            m = E.book_metrics(tr, YEARS[scope])
                            k = f"{scope}/{name}/mb{mb}/{kind}/r{r}/mc{mc}"
                            payload["cells"][k] = {**m, "gate": st}
                            n_run += 1
                            print(f"    mb{mb:<3} {kind:<8} r={r:<4} mc={mc}  "
                                  f"{m['n']:>6}t net {m['net']:>+8.1f}  "
                                  f"trim {str(m.get('trimmed_mean')):>7}  "
                                  f"PF {str(m.get('pf')):>6}  "
                                  f"WR {m.get('wr', 0):>5}%  "
                                  f"DD {m.get('max_dd', 0):>7.1f}  "
                                  f"exB5 {str(m.get('ex_best5')):>8}", flush=True)
                del sw
            print(f"  [{scope}/{name}] {n_run} cells", flush=True)

    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


def report():
    j = json.loads(OUT.read_text(encoding="utf-8"))
    cells = j["cells"]
    by: dict = {}
    for k, c in cells.items():
        p = k.split("/")
        by.setdefault((p[2], p[3], p[4], p[5]), {})[p[0]] = c
    both = {s: e for s, e in by.items() if set(e) == {"is", "oos"}}
    print("\n" + "=" * 104)
    print("  PASSING THE CONJUNCTIVE BAR IN BOTH ERAS")
    print("=" * 104)
    win = []
    for s, e in sorted(both.items()):
        a, b = e["is"], e["oos"]
        if (a["trimmed_mean"] > 0 and b["trimmed_mean"] > 0 and a["net"] > 0
                and b["net"] > 0 and a["ex_best5"] > 0 and b["ex_best5"] > 0):
            win.append(s)
            print(f"  PASS  mb{s[0]:<3} {s[1]:<8} r={s[2]:<4} mc={s[3]}  "
                  f"IS {a['net']:+.1f}R trim {a['trimmed_mean']:+.3f} | "
                  f"OOS {b['net']:+.1f}R trim {b['trimmed_mean']:+.3f}")
    print(f"\n  {len(win)}/{len(both)} cells pass.")
    best = sorted(((min(v["is"]["trimmed_mean"], v["oos"]["trimmed_mean"]), s)
                   for s, v in both.items()), reverse=True)[:8]
    print("\n  top 8 by WORST-ERA trimmed mean:")
    for v, s in best:
        print(f"    {v:+.4f}  mb{s[0]:<3} {s[1]:<8} r={s[2]:<4} mc={s[3]}")
    return win


if __name__ == "__main__":
    if "--report" in sys.argv:
        report()
    else:
        main()
        report()
