"""B1/B2 ENTRY + a TIGHTENED STOP (the user's variant), path-true.

WHAT THE USER ASKED
===================
Not the half-swing stop (that was tested and is degenerate - for a small
swing the midpoint sits inside the noise and is hit 84-93% of the time).
The variant is: keep entry at B1 or B2, but put the SL ABOVE the swing low
so the risk is tighter and usable.

WHY THIS IS A SMALL, CLEAN PATCH
================================
The engine's stop is anchored on `sl_pivot` (the swing extreme):
    long :  sl = sl_pivot - sl_buf_atr*atr15[i]
    short:  sl = sl_pivot + sl_buf_atr*atr15[i]
So the ONLY change needed is to move `sl_pivot` toward the entry by a
controlled number of ATRs before those lines run. Moving it TOWARD the entry
is direction-agnostic (`sign(entry - sl_pivot)`), so one injected line covers
both branches and cannot get the short case backwards.

    exp_sl_tight = 0.0  -> current behaviour, byte-identical
    exp_sl_tight = 0.5  -> SL pulled 0.5 x ATR15 toward the entry
    exp_sl_tight = 1.0 / 1.5 / 2.0

This is a real engine run, not arithmetic on a finished book: the stop change
alters which trades survive, so exits, cooldown and streak all re-simulate.
It is the path-true version of what the last run could only describe badly.

ENTRY MARK
==========
There is no kwarg to fire the entry on B1 instead of B2 - `exp_b1_b2_mode` is
a blocking filter on the B2 trigger, not a different trigger. This run
therefore varies the STOP only, at the engine's real B2/flip entry, and says
so plainly rather than pretending the B1 leg is covered.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "live_stuff/tests/_sl_tighten.json"
TMP = ROOT / "live_stuff/tests/_v18_sltight_tmp.py"
LANES = (("champion", "champion_multi_sw10"),
         ("utcsat", "utcsat_multi_sw10"))
YEARS = {"is": 3.67, "oos": 2.0}
ARMS = (("baseline (tight=0)", 0.0), ("tight 0.5 ATR", 0.5),
        ("tight 1.0 ATR", 1.0), ("tight 1.5 ATR", 1.5),
        ("tight 2.0 ATR", 2.0))
_LONG_SL = ('            sl=sl_pivot - sl_buf_atr*atr15[i] '
           'if sl_buf_atr>0 else sl_pivot')
_SHORT_SL = ('            sl=sl_pivot + sl_buf_atr*atr15[i] '
            'if sl_buf_atr>0 else sl_pivot')
# Injected at the SAME 12-space indent as the SL lines it precedes.
_TIGHT = ('            if exp_sl_tight>0.0:\n'
          '                sl_pivot = sl_pivot + exp_sl_tight*atr15[i]*'
          '(1.0 if entry>sl_pivot else -1.0)\n')


def build():
    import test_experiments_craze as tc
    cap = {}
    orig = tc._load_module

    def spy(t, n):
        cap["text"] = t
        return orig(t, n)
    tc._load_module = spy
    try:
        tc.build_module()
    finally:
        tc._load_module = orig
    s = cap["text"]
    t1 = "    *,\n"
    assert s.count(t1) == 1, "sig star"
    s = s.replace(t1, t1 + "    exp_sl_tight=0.0,\n")
    for anchor in (_LONG_SL, _SHORT_SL):
        c = s.count("\n" + anchor)
        print(f"  sl anchor count = {c}")
        assert c == 1, f"anchor missing/ambiguous: {anchor[:40]}"
        s = s.replace("\n" + anchor, "\n" + _TIGHT + anchor)
    TMP.write_text(s, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("v18_sltight", str(TMP))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.simulate_htf_ltf_streak_halt


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  TIGHTENED STOP (path-true) - SL pulled toward entry by k x ATR",
          flush=True)
    print("=" * 100, flush=True)
    from exp_sizing_combo import run as sim_fn
    from exp_5m_confirm import load_book
    from experiment_registry import BP, EXPERIMENTS
    from exp_equity_quality import equity_quality
    sim = build()
    payload = {"stage": "sl_tighten", "cells": {}}
    for scope in ("is", "oos"):
        data, _ = load_book(scope)
        for name, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            m0 = equity_quality(sim_fn(sim, data, params), YEARS[scope])
            print(f"\n  [{scope}/{name}] BASE {m0['n']}t {m0['net']:+.1f}R "
                  f"WR {m0['wr']}% PF {m0['pf']} DD {m0['max_dd']} "
                  f"cal {m0['calmar']}", flush=True)
            for lbl, k in ARMS:
                tr = sim_fn(sim, data, {**params, "exp_sl_tight": k})
                m = equity_quality(tr, YEARS[scope])
                d = round(m["net"] - m0["net"], 1)
                payload["cells"][f"{scope}/{name}/{lbl}"] = {
                    "k": k, "n": m["n"], "net": m["net"], "wr": m["wr"],
                    "pf": m["pf"], "max_dd": m["max_dd"],
                    "calmar": m["calmar"], "d_net": d,
                    "d_dd": round(m0["max_dd"] - m["max_dd"], 1)}
                print(f"    {lbl:<18} {m['n']:>4}t {m['net']:>+8.1f}R "
                      f"({d:+7.1f})  WR {m['wr']:>5}%  PF {m['pf']:>6}  "
                      f"DD {m['max_dd']:>5.1f} ({m0['max_dd']-m['max_dd']:+.1f})"
                      f"  cal {m['calmar']:>6.3f}", flush=True)
    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()