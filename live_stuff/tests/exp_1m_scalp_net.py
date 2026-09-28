"""THE DECISIVE 1m RUN - NET R, honest scale, visible trade count.

THREE CORRECTIONS THIS RUN MAKES
================================
1. NET, NOT GROSS. Every 1m number so far was gross. The 15m baseline
   (+325.8 / +358.9) is net, so a gross 1m number cannot be added to it.
   Cost is charged PER ROUND TRIP, and a 1m book does 10-50x more round
   trips than a 500-trade swing book - so this correction works AGAINST
   the 1m book, which is exactly why it had to be made before a verdict.

2. THE SCALE. The user caught it: 15m uses min_bars=50, a 12.5-hour leg.
   1m at min_bars=10 is a 10-MINUTE leg - noise, not structure. So min_bars
   is swept where a leg is tens of minutes, and the trade count is printed
   next to the 15m book's 500/279 so "too many trades" is visible as a
   number instead of being assumed away.

3. NO FILTER PILE-ON. The user wants fewer trades, but every filter tried
   so far (concurrency, half_be) either did not reduce count or destroyed
   the book. `min_risk_atr=0.25` (the HANDOVER 5.1 noise floor) is the only
   exclusion, and its count is reported so it is visible, not silent.

THE ARMS (pre-registered, complete)
===================================
  min_bars  : 20, 50, 100, 150     (leg = 20..150 minutes on 1m)
  entry     : decisive, b1
  target_r  : 1.0, 2.0
  exit_mode : trail
  = 16 cells per era, both eras, champion lane.

Run:  $env:PYTHONIOENCODING='utf-8'; python -u exp_1m_scalp_net.py
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

OUT = ROOT / "live_stuff/tests/_1m_scalp_net.json"

MIN_BARS = (20, 50, 100, 150)
TARGET_R = (1.0, 2.0)
ENTRY_KINDS = ("decisive", "b1")
SL_BUF_ATR = 0.01
MAX_HOLD_MIN = 240.0
MIN_RISK_ATR = 0.25
YEARS = {"is": 3.67, "oos": 2.0}
BYBIT_BASE = {"is": (500, 325.8), "oos": (279, 70.2)}
LANE_KEY = "champion_multi_sw10"


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
    payload = {"scoring": "NET R (fees+slip+funding per round trip)",
               "min_bars": list(MIN_BARS), "target_r": list(TARGET_R),
               "entry_kinds": list(ENTRY_KINDS), "cells": {}}
    print("=" * 112, flush=True)
    print("  1m SCALP - NET R at the right scale (15m book: 50 bars = 12.5h)",
          flush=True)
    print("=" * 112, flush=True)

    for scope in ("is", "oos"):
        print(f"\nloading {scope} ...", flush=True)
        data, _ = load_book(scope)
        c1m = data["fine"]
        f1m = _flow(c1m)
        wins = E.htf_windows(data["c1h"], data["sw10"], fine_ltf=data["fine"])
        params = {**BP, **EXPERIMENTS[LANE_KEY]["params"]}
        ctl = equity_quality(sim_fn(sim, data, dict(params)), YEARS[scope])
        exp_n, exp_net = BYBIT_BASE[scope]
        ok = ctl["n"] == exp_n and abs(ctl["net"] - exp_net) < 0.6
        print(f"  [{scope}] 15m CONTROL {ctl['n']}t {ctl['net']:+.1f}R NET "
              f"{'OK' if ok else 'MISMATCH'}", flush=True)
        if not ok:
            payload.setdefault("errors", []).append(scope)
            continue

        for mb in MIN_BARS:
            sw = _compute_swings(f1m, "continuous", min_bars=mb)
            print(f"\n    -- min_bars={mb} (~{mb} min leg): {len(sw):,} swings",
                  flush=True)
            for kind in ENTRY_KINDS:
                for r in TARGET_R:
                    st: dict = {}
                    tr = E.simulate_1m_scalp(
                        c1m, sw, wins, entry_break=kind, target_r=r,
                        sl_buf_atr=SL_BUF_ATR, max_concurrent=1,
                        max_hold_min=MAX_HOLD_MIN, exit_mode="trail",
                        min_risk_atr=MIN_RISK_ATR, stats=st)
                    E.assert_hold_cap(tr, MAX_HOLD_MIN, f"{scope}/mb{mb}/{kind}/r{r}")
                    m = E.book_metrics(tr, YEARS[scope], net=True)
                    payload["cells"][f"{scope}/mb{mb}/{kind}/r{r}"] = {**m, "gate": st}
                    print(f"    mb{mb:<4} {kind:<8} r={r:<4} {m['n']:>5}t  "
                          f"GROSS {m['gross']:>+8.1f}  cost {m['cost_r']:>7.1f}  "
                          f"NET {m['net']:>+8.1f}  "
                          f"({str(m.get('cost_per_trade'))}/t)  "
                          f"trim {str(m.get('trimmed_mean')):>7}  "
                          f"PF {str(m.get('pf')):>6}  WR {m.get('wr', 0):>5}%  "
                          f"DD {m.get('max_dd', 0):>7.1f}", flush=True)
            del sw

    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


def report():
    j = json.loads(OUT.read_text(encoding="utf-8"))
    by: dict = {}
    for k, c in j["cells"].items():
        p = k.split("/")
        by.setdefault((p[1], p[2], p[3]), {})[p[0]] = c
    both = {s: e for s, e in by.items() if set(e) == {"is", "oos"}}
    print("\n" + "=" * 112)
    print("  NET-R VERDICT - both eras required")
    print("=" * 112)
    win = []
    for s, e in sorted(both.items()):
        a, b = e["is"], e["oos"]
        ok = (a["net"] > 0 and b["net"] > 0 and a["trimmed_mean"] > 0
              and b["trimmed_mean"] > 0 and a["ex_best5"] > 0 and b["ex_best5"] > 0)
        if ok:
            win.append(s)
        print(f"  {'PASS' if ok else 'fail'}  {s[0]:<8} {s[1]:<8} r={s[2]:<4} "
              f"n {a['n']:>4}/{b['n']:>4}  "
              f"IS gross {a['gross']:>+7.1f} cost {a['cost_r']:>6.1f} "
              f"NET {a['net']:>+8.1f} trim {a['trimmed_mean']:+.3f} | "
              f"OOS NET {b['net']:>+8.1f} trim {b['trimmed_mean']:+.3f}")
    print(f"\n  {len(win)}/{len(both)} pass on NET in both eras.")
    if not win:
        best = sorted(((min(v["is"]["net"], v["oos"]["net"]), s)
                       for s, v in both.items()), reverse=True)[:5]
        print("  best by WORST-ERA net R:")
        for v, s in best:
            print(f"    {v:+9.1f}  {s[0]:<8} {s[1]:<8} r={s[2]}")
    return win


if __name__ == "__main__":
    if "--report" in sys.argv:
        report()
    else:
        main()
        report()
