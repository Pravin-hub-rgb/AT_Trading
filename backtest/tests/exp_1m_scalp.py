"""RUN THE 1-MINUTE SCALPING BOOK - the experiment the user asked for.

THE ASK
=======
  "1h tf bias open, 15min normal trade open, now this is also a window,
   now 1min decides to trade" ... "1:2 fixed trading wager" ...
   "1min mai bhi b1, b2, flip wagera karo" ... "sab engine banao joh
   1min mai b1, b2, flip fs kare 1min ke grind level pe"

So: keep the 1h window and the 15m book exactly as they are, and add a 1m
SCALPING book inside the same window. Fixed 1:2 target, swing-pivot stop,
1m trail. The mark kinds on 1m (decisive/B2/FLIP, plus B1 which the shipped
engine cannot even express) are the arms.

PRE-REGISTERED LADDER - every cell run, no cell selected afterwards
===================================================================
  entry_break : decisive (B2+FLIP), b2, flip, b1
  min_bars_1m : 10, 20, 40          (1m swing grind level)
  target_r    : 2.0                 (the user's fixed 1:2, NOT swept)
  sl_buf_atr  : 0.01                (the shipped champion's constant)
  max_conc    : 1                   (no stacked scalps)
  eras        : is + oos; lanes : champion, utcsat

target_r is FIXED at 2.0 on purpose. It is the user's stated wager, not a
knob to tune; sweeping it would be exactly the multiplicity this repo
forbids. min_bars and entry_break are the real questions.

HIT BAR (all required, per the repo's standing rules)
=====================================================
  1. net R POSITIVE in BOTH eras, and
  2. same sign on BOTH lanes in BOTH eras, and
  3. trimmed mean positive (Rule 13 - these books are tail-concentrated), and
  4. ex-best-3 AND ex-best-5 still positive (Rule 14), and
  5. ADDITIVE: 15m book + 1m book beats the 15m book alone.

CONTROL GATE
============
The 15m book is untouched by construction (separate engine, separate state).
But the HTF WINDOWS the 1m book depends on are rebuilt here, so the run
asserts the champion's reference ledger before any 1m number is shown. If
the window replication were wrong, every 1m number would be meaningless.

Run:  $env:PYTHONIOENCODING='utf-8'; python -u exp_1m_scalp.py
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

OUT = ROOT / "backtest/tests/_1m_scalp.json"

ENTRY_KINDS = ("decisive", "b2", "flip", "b1")
MIN_BARS = (10, 20, 40)
TARGET_R = 2.0
SL_BUF_ATR = 0.01
MAX_CONCURRENT = 1
MAX_HOLD_MIN = 240.0
YEARS = {"is": 3.67, "oos": 2.0}
LANES = (("champion", "champion_multi_sw10"),
         ("utcsat", "utcsat_multi_sw10"))
BYBIT_BASE = {
    "is/champion": (500, 325.8), "is/utcsat": (454, 358.9),
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
    payload = {"entry_kinds": list(ENTRY_KINDS), "min_bars": list(MIN_BARS),
               "target_r": TARGET_R, "sl_buf_atr": SL_BUF_ATR,
               "max_concurrent": MAX_CONCURRENT, "cells": {}}
    print("=" * 108, flush=True)
    print("  1-MINUTE SCALPING BOOK - parallel to the 15m book, inside the "
          "1h window", flush=True)
    print("=" * 108, flush=True)
    sim = build_module()

    for scope in ("is", "oos"):
        print(f"\nloading {scope} ...", flush=True)
        data, _ = load_book(scope)
        c1m = data["fine"]
        print(f"  1m bars: {len(c1m):,}  {c1m[0]['date']} -> "
              f"{c1m[-1]['date']}", flush=True)
        f1m = _flow(c1m)
        sw_cache = {}
        for mb in MIN_BARS:
            sw_cache[mb] = _compute_swings(f1m, "continuous", min_bars=mb)
            print(f"  1m swings min_bars={mb}: {len(sw_cache[mb]):,}", flush=True)

        for name, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            ctl = equity_quality(sim_fn(sim, data, dict(params)), YEARS[scope])
            exp_n, exp_net = BYBIT_BASE[f"{scope}/{name}"]
            ok = ctl["n"] == exp_n and abs(ctl["net"] - exp_net) < 0.6
            print(f"\n  [{scope}/{name}] 15m CONTROL {ctl['n']}t "
                  f"{ctl['net']:+.1f}R (expect {exp_n}t {exp_net:+.1f}) "
                  f"{'OK' if ok else 'MISMATCH'}", flush=True)
            if not ok:
                payload.setdefault("errors", []).append(f"{scope}/{name}")
                continue

            wins = E.htf_windows(data["c1h"], data["sw10"],
                                 fine_ltf=data["fine"])
            print(f"  [{scope}/{name}] HTF windows: {len(wins):,}", flush=True)
            payload.setdefault("windows", {})[f"{scope}/{name}"] = len(wins)

            for mb in MIN_BARS:
                for kind in ENTRY_KINDS:
                    st: dict = {}
                    tr = E.simulate_1m_scalp(
                        c1m, sw_cache[mb], wins, entry_break=kind,
                        target_r=TARGET_R, sl_buf_atr=SL_BUF_ATR,
                        max_concurrent=MAX_CONCURRENT, stats=st)
                    m = E.book_metrics(tr, YEARS[scope])
                    E.assert_hold_cap(tr, MAX_HOLD_MIN,
                                      f"{scope}/{name}/mb{mb}/{kind}")
                    payload["cells"][f"{scope}/{name}/mb{mb}/{kind}"] = {
                        **m, "gate": st,
                        "net_per_yr": round(m.get("net", 0) / YEARS[scope], 2)}
                    print(f"    mb={mb:<3} {kind:<9} {m['n']:>5}t "
                          f"net {m['net']:>+8.1f}R  WR {m.get('wr', 0):>5}%  "
                          f"PF {str(m.get('pf')):>6}  DD {m.get('max_dd', 0):>6.1f}"
                          f"  trim {str(m.get('trimmed_mean')):>7}  "
                          f"exB3 {str(m.get('ex_best3')):>7}  "
                          f"exB5 {str(m.get('ex_best5')):>7}  "
                          f"| sig {st.get('signals', 0)} win "
                          f"{st.get('window_hits', 0)}", flush=True)

    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()
