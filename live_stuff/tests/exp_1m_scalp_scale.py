"""1m SCALP at the CORRECT grind level - the user's correction, and it matters.

THE ERROR IN MY EARLIER GRIDS
==============================
The user caught it:

    "15min mai mb50 hai toh uppar level mai karo nah 9000+ trades are too
     much yaar kam karna hai"

`v18_params.SWING` has **min_bars_15m = 50**. On 15m bars that is a swing
leg of 50 x 15min = **12.5 hours**. That is what "structure" means in this
system.

My grids ran 1m at min_bars 3..40. At 1m, min_bars=10 is a **10-minute**
leg - 75x shorter than the 15m book's. That is not a finer swing, it is
noise, and it is why the books came out at 20,000+ trades with a win rate
near a coin flip. Every conclusion drawn at that scale was about noise.

The fix is not a bigger grid, it is the right SCALE:

    15m book : 50 bars x 15 min = 750 min = 12.5 h
    1m  book : mb x 1 min         ->  mb=50 is 50 min, mb=100 is 100 min

So the meaningful 1m range is 50..400, not 3..40. At mb=50 the 1m leg is
still shorter than the 15m leg (that is what "scalp" means), but it is
long enough to be a swing rather than a tick.

PRE-REGISTERED
==============
  min_bars        : 50, 75, 100, 150, 200, 300, 400
  max_concurrent  : 1
  entry_break     : decisive, b1
  target_r        : 1.0, 2.0
  exit_mode       : trail
= 7 x 2 x 2 = 28 cells per era. All run.

TRADE COUNT IS A REPORTED DIAGNOSTIC, NOT A TUNED KNOB
======================================================
The user wants FEWER trades. So trade count is printed next to every cell
and compared against the 15m book's 500 (IS) / 279 (OOS). A cell that
still produces thousands of trades at mb=400 is telling us something about
the window density, and that is worth seeing rather than hiding by
throwing more filters at it.

Run:  $env:PYTHONIOENCODING='utf-8'; python -u exp_1m_scalp_scale.py
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

OUT = ROOT / "live_stuff/tests/_1m_scalp_scale.json"

# 15m book: 50 bars x 15 min = 12.5h.  1m book: mb x 1 min.
MIN_BARS = (50, 75, 100, 150, 200, 300, 400)
MAX_CONCURRENT = 1
TARGET_R = (1.0, 2.0)
ENTRY_KINDS = ("decisive", "b1")
SL_BUF_ATR = 0.01
MAX_HOLD_MIN = 240.0
MIN_RISK_ATR = 0.25
YEARS = {"is": 3.67, "oos": 2.0}
BYBIT_BASE = {"is/champion": (500, 325.8), "oos/champion": (279, 70.2)}
LANE_KEY = "champion_multi_sw10"
REF_15M_N = {"is": 500, "oos": 279}


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
    payload = {"min_bars": list(MIN_BARS), "target_r": list(TARGET_R),
               "entry_kinds": list(ENTRY_KINDS), "ref_15m_n": REF_15M_N,
               "cells": {}}
    print("=" * 108, flush=True)
    print("  1m SCALP AT THE RIGHT SCALE - min_bars 50..400 "
          "(15m book uses 50 x 15min = 12.5h)", flush=True)
    print("=" * 108, flush=True)

    for scope in ("is", "oos"):
        print(f"\nloading {scope} ...", flush=True)
        data, _ = load_book(scope)
        c1m = data["fine"]
        f1m = _flow(c1m)
        wins = E.htf_windows(data["c1h"], data["sw10"], fine_ltf=data["fine"])
        params = {**BP, **EXPERIMENTS[LANE_KEY]["params"]}
        ctl = equity_quality(sim_fn(sim, data, dict(params)), YEARS[scope])
        exp_n, exp_net = BYBIT_BASE[f"{scope}/champion"]
        ok = ctl["n"] == exp_n and abs(ctl["net"] - exp_net) < 0.6
        print(f"  [{scope}] 1m bars {len(c1m):,}  HTF windows {len(wins):,}", flush=True)
        print(f"  [{scope}] 15m CONTROL {ctl['n']}t {ctl['net']:+.1f}R "
              f"{'OK' if ok else 'MISMATCH'}   (1m book is judged against "
              f"n={REF_15M_N[scope]})", flush=True)
        if not ok:
            payload.setdefault("errors", []).append(scope)
            continue

        n_run = 0
        for mb in MIN_BARS:
            sw = _compute_swings(f1m, "continuous", min_bars=mb)
            leg_min = mb  # 1m bars
            print(f"\n    -- min_bars={mb} (leg ~{leg_min} min): "
                  f"{len(sw):,} 1m swings", flush=True)
            for kind in ENTRY_KINDS:
                for r in TARGET_R:
                    st: dict = {}
                    tr = E.simulate_1m_scalp(
                        c1m, sw, wins, entry_break=kind, target_r=r,
                        sl_buf_atr=SL_BUF_ATR, max_concurrent=MAX_CONCURRENT,
                        max_hold_min=MAX_HOLD_MIN, exit_mode="trail",
                        min_risk_atr=MIN_RISK_ATR, stats=st)
                    E.assert_hold_cap(tr, MAX_HOLD_MIN, f"{scope}/mb{mb}/{kind}/r{r}")
                    m = E.book_metrics(tr, YEARS[scope])
                    k = f"{scope}/champion/mb{mb}/{kind}/r{r}"
                    payload["cells"][k] = {**m, "gate": st}
                    n_run += 1
                    print(f"    mb{mb:<4} {kind:<8} r={r:<4} {m['n']:>5}t "
                          f"(vs {REF_15M_N[scope]})  net {m['net']:>+8.1f}  "
                          f"trim {str(m.get('trimmed_mean')):>7}  "
                          f"PF {str(m.get('pf')):>6}  WR {m.get('wr', 0):>5}%  "
                          f"DD {m.get('max_dd', 0):>7.1f}  "
                          f"exB5 {str(m.get('ex_best5')):>8}  "
                          f"| sig {st.get('signals', 0)} "
                          f"win {st.get('window_hits', 0)}", flush=True)
            del sw
        print(f"  [{scope}] {n_run} cells", flush=True)

    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


def report():
    j = json.loads(OUT.read_text(encoding="utf-8"))
    cells = j["cells"]
    by: dict = {}
    for k, c in cells.items():
        p = k.split("/")
        by.setdefault((p[2], p[3], p[4]), {})[p[0]] = c
    both = {s: e for s, e in by.items() if set(e) == {"is", "oos"}}
    print("\n" + "=" * 108)
    print("  BOTH-ERA VERDICT (trimmed mean is the judge)")
    print("=" * 108)
    win = []
    for s, e in sorted(both.items()):
        a, b = e["is"], e["oos"]
        ok = (a["trimmed_mean"] > 0 and b["trimmed_mean"] > 0 and a["net"] > 0
              and b["net"] > 0 and a["ex_best5"] > 0 and b["ex_best5"] > 0)
        if ok:
            win.append(s)
        print(f"  {'PASS' if ok else 'fail'}  {s[0]:<8} {s[1]:<8} r={s[2]:<4} "
              f"n {a['n']:>4}/{b['n']:>4}  IS {a['net']:+8.1f}R "
              f"trim {a['trimmed_mean']:+.4f} | OOS {b['net']:+8.1f}R "
              f"trim {b['trimmed_mean']:+.4f}")
    print(f"\n  {len(win)}/{len(both)} pass.")
    best = sorted(((min(v["is"]["trimmed_mean"], v["oos"]["trimmed_mean"]), s)
                   for s, v in both.items()), reverse=True)[:6]
    print("\n  top 6 by WORST-ERA trimmed mean:")
    for v, s in best:
        print(f"    {v:+.4f}  {s[0]:<8} {s[1]:<8} r={s[2]}")
    return win


if __name__ == "__main__":
    if "--report" in sys.argv:
        report()
    else:
        main()
        report()
