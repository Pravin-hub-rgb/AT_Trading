"""OPTION 1 - REPLICATE `exp_retest_fill=0.25` on the age10 lane, on
INDEPENDENT data.

WHY THIS IS WORTH DOING
=======================
`exp_retest_fill` is the single surviving 1m idea in the repo, and the only
one that uses 1m as an EXECUTOR rather than a trigger:

    is/champion   IS 435.7 -> 489.3 net  (+14.6R/yr)  dd 8.7 -> 8.4
    oos/champion  OOS 43.2 ->  65.8 net  (+11.3R/yr)  dd 8.6 -> 6.5
                  WR 39.5% -> 44.0%, curve_better BOTH eras

It works because it does NOT add trades. The 15m signal is unchanged; the
1m series is used to get a better fill price on a trade we were already
going to take. That is the opposite of a 1m trigger book, and it is why it
is not dead while the 1m trigger family is (0/196 cells).

THE GAP THIS FILLS
==================
Those numbers are Bybit, and Bybit IS/OOS are the most inspected data in
this repo (HANDOVER section 8: "Forward gate / independent data"). A
candidate that only reproduces on the data that found it is not a
candidate. This runs it on **data/btc** - a different venue's file, same
instrument, never used to select this arm.

The age10 lane is the ONLY lane it survived on; champion died at both
depths (-7.1R/yr, -35.7R/yr). So the lane is fixed, not chosen: if the
arm also dies on champion here, that is a replication of the kill, not a
selective omission.

PRE-REGISTERED (frozen before the run)
=====================================
  dataset   : data/btc only (independent of the Bybit run)
  lane      : age10_dirmatch_swingpause_single_sw10  (the surviving lane)
  arms      : baseline / limit_0.25R   (0.10R is dead on this lane; not
               re-run, because re-running a dead rung to fish for a pass is
               exactly the multiplicity this repo forbids)
  wait      : 240 min
  verdict   : survives only if net improves on BOTH halves of data/btc
               split on the same calendar the Bybit run used

HONEST LIMITS, STATED UP FRONT
==============================
  * age10 is a THIN lane (n=137 IS / 107 OOS on Bybit). A replication on
    ~the same sample size cannot manufacture power it does not have. This
    tests TRANSFER, not significance, and a pass here means "not refuted on
    a second venue", not "proven".
  * The monster-miss cost (11/14 IS monsters captured on Bybit) is
    re-measured here and reported whether it helps or hurts.

Run:  $env:PYTHONIOENCODING='utf-8'; python -u exp_retest_replicate.py
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

OUT = ROOT / "backtest/tests/_retest_replicate.json"

LANE = "age10_dirmatch_swingpause_single_sw10"
YEARS = {"btc_is": 3.67, "btc_oos": 2.0}
MONSTER_R = 10.0
ARMS = (
    ("baseline", {}),
    ("limit_0.25R", dict(exp_retest_fill=0.25, exp_retest_wait=240)),
)
# data/btc covers 2023-01-01 onward for 15m/1h. Split it the way the Bybit
# run did so the two are comparable: early = IS-like, late = OOS-like.
SPLIT_TS = None  # resolved at load time to the 64% mark


def _read(path):
    from exp_s3_forensic import _read_tf
    return _read_tf(path)


def load_btc():
    """data/btc 15m + 1h + 1m, split into two halves ON TIME.

    The first attempt sliced by INDEX and crashed: data/btc's 1h file is
    shorter than its 15m file, so an index cut left the second half empty
    (`IndexError`). Splitting on the 15m TIMESTAMP and then selecting every
    candle whose ts falls on the correct side is robust to the two files
    having different lengths, which they do.
    """
    from exp_s3_forensic import _candles
    from src.btc.btc_routes import _compute_swings
    from engine.v18_params import SWING
    d = ROOT / "data/btc"
    c15, f15 = _candles(_read(d / "BTCUSDT_15m.csv"))
    c1h, f1h = _candles(_read(d / "BTCUSDT_1h.csv"))
    cut = int(c15[int(len(c15) * 0.64)]["ts"])
    print(f"  split at ts={cut} (64% of 15m bars)", flush=True)
    out = {}
    for name, sel in (("btc_is", lambda t: t < cut),
                      ("btc_oos", lambda t: t >= cut)):
        s15 = [c for c in c15 if sel(int(c["ts"]))]
        s1h = [c for c in c1h if sel(int(c["ts"]))]
        if not s15 or not s1h:
            print(f"  {name}: EMPTY (15m={len(s15)} 1h={len(s1h)})", flush=True)
            continue
        t0 = min(s15[0]["ts"], s1h[0]["ts"])
        t1 = max(s15[-1]["ts"], s1h[-1]["ts"])
        out[name] = {
            "c15": s15, "c1h": s1h,
            "sw15": _compute_swings(_flow(s15), "continuous",
                                    min_bars=SWING["min_bars_15m"]),
            "sw10": _compute_swings(_flow(s1h), "continuous", min_bars=10),
            "fine": _load_1m(d / "BTCUSDT_1m.csv", t0, t1),
        }
        print(f"  {name}: 15m {len(s15):,}  1h {len(s1h):,}  "
              f"1m {len(out[name]['fine']):,}  "
              f"{s15[0]['date']} -> {s15[-1]['date']}", flush=True)
    return out



def _flow(candles):
    from src.walker import FlowCandle
    return [FlowCandle(date=c["date"], open=float(c["open"]),
                       high=float(c["high"]), low=float(c["low"]),
                       close=float(c["close"])) for c in candles]


def _load_1m(path, t0, t1):
    from exp_s3_forensic import load_1m
    return load_1m(path, t0, t1)


def main():
    from experiment_registry import BP, EXPERIMENTS
    from run_experiment import net_r
    from test_experiments_craze import build_module

    t0 = time.time()
    print("=" * 100, flush=True)
    print("  OPTION 1 - replicate exp_retest_fill=0.25 (age10) on data/btc",
          flush=True)
    print("=" * 100, flush=True)
    print("\nloading data/btc ...", flush=True)
    books = load_btc()

    sim = build_module()
    params = {**BP, **EXPERIMENTS[LANE]["params"]}
    payload = {"lane": LANE, "dataset": "data/btc", "arms": [a[0] for a in ARMS],
               "cells": {}}

    for scope, data in books.items():
        # Control first: the flag OFF must reproduce the shipped lane.
        base_tr = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                      fine_ltf=data["fine"], **params)
        base_n = len(base_tr["ltf_trades"] if isinstance(base_tr, dict) else base_tr)
        base_net = net_r(base_tr["ltf_trades"] if isinstance(base_tr, dict)
                         else base_tr)
        print(f"\n  [{scope}] BASELINE {base_n}t {base_net:+.1f}R net", flush=True)
        base = {"n": base_n, "net": round(base_net, 1)}
        payload["cells"][f"{scope}/baseline"] = base

        for name, flags in ARMS:
            if not flags:
                continue
            tr = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                     fine_ltf=data["fine"], **params, **flags)
            trades = tr["ltf_trades"] if isinstance(tr, dict) else tr
            n_ = net_r(trades)
            rs = [float(t["r_multiple"]) for t in trades]
            monsters = sum(1 for x in rs if x >= MONSTER_R)
            d_yr = (n_ - base_net) / YEARS[scope]
            row = {"n": len(trades), "net": round(n_, 1),
                   "d_net_yr": round(d_yr, 2),
                   "d_net_total": round(n_ - base_net, 1),
                   "monsters": monsters,
                   "wr": round(100.0 * sum(1 for x in rs if x > 0) / len(rs), 1)
                   if rs else None}
            payload["cells"][f"{scope}/{name}"] = row
            print(f"  [{scope}] {name:<12} {row['n']:>4}t {n_:>+8.1f}R net  "
                  f"({d_yr:+.2f}/yr)  WR {row['wr']}%  "
                  f"monsters {monsters}", flush=True)
        # monster delta
        for name, _f in ARMS[1:]:
            k = f"{scope}/{name}"
            if k in payload["cells"]:
                payload["cells"][k]["monster_delta"] = (
                    payload["cells"][k]["monsters"]
                    - payload.get(f"{scope}/baseline_monsters", 0))
        base_m = payload["cells"][f"{scope}/baseline"].get("monsters")
        for name, _f in ARMS[1:]:
            k = f"{scope}/{name}"
            if k in payload["cells"] and base_m is not None:
                payload["cells"][k]["monster_delta"] = (
                    payload["cells"][k]["monsters"] - base_m)

    # Verdict
    print("\n" + "=" * 100, flush=True)
    print("  VERDICT - survives only if BOTH halves improve on net R/yr")
    print("=" * 100, flush=True)
    deltas = {}
    for scope in books:
        for name, _f in ARMS[1:]:
            c = payload["cells"].get(f"{scope}/{name}")
            if c:
                deltas[(scope, name)] = c["d_net_yr"]
    survives = all(v > 0 for v in deltas.values()) and deltas
    for (scope, name), v in sorted(deltas.items()):
        print(f"  {scope:<8} {name:<12} {v:+.2f}R/yr")
    print(f"\n  REPLICATION: {'SURVIVES on independent data' if survives else 'FAILS to replicate'}")
    payload["verdict"] = ("survives_independent" if survives
                          else "fails_to_replicate")
    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()
