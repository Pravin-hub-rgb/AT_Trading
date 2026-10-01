"""1m path context, SCALE-MATCHED - the corrected version of a failed run.

WHY THIS FILE EXISTS
====================
`ONE_MIN_PATH_CONTEXT.md` recorded a -325.8R "result" that was really the
whole book deleted: the gate grayed 658 of 660 signals. The probe showed
why - ctx_extend had a MEDIAN of 8.7 while the thresholds were 0.5/1.0:

    IS  ctx_extend: min 0.131  p25 6.529  MED 8.691  p95 16.271

The bug was MINE and it was a units error. I measured a 15m-scale distance
(distance from the running low, AFTER a 15m signal bar has already moved)
and divided it by 1m-scale volatility:

    ctx_extend = (close - low_60min) / ATR_1m

BTC's 15m range is several 1m ATRs wide, so that ratio is ~9 BY
CONSTRUCTION. The number carried no information; the arms were miscalibrated,
not refuted.

THE FIX - two scale-matched features
====================================
  ctx_pos_15m  : where the 1m close sits inside the SIGNAL 15m bar's own
                 range, 0..1. Scale-free by construction - 0 = at the bar's
                 low, 1 = at its high. Answers "how far through its own bar
                 is price", which is the question a 15m entry should ask.

  ctx_ext_15m  : (close - low_60min) / ATR_15 - the same numerator as the
                 failed version but over FIFTEEN-minute volatility, so
                 numerator and denominator share a scale.

THRESHOLDS ARE ROUND NUMBERS, FROZEN BEFORE OOS IS SCORED
==========================================================
The failure mode of the last run was hand-picked absolutes with no relation
to the feature's own distribution. Here the cut points are round, the IS
distribution is printed so the reader can see they land sensibly, and the
SAME cuts go to OOS untouched. Not a licence to fish: nothing is re-tuned
after seeing OOS.

GRAY, NOT SKIP: rejection is r=0 with the loss streak still advancing, taken
before any state mutation, so the wick-gate cascade cannot apply. Rejected
counts are reported.

CONTROL: flag off must reproduce 500t +325.8R / 279t +70.2R exactly.

Run:  $env:PYTHONIOENCODING='utf-8'; python -u exp_1m_ctx_scaled.py
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

OUT = ROOT / "backtest/tests/_1m_ctx_scaled.json"
LANE = "champion_multi_sw10"
YEARS = {"is": 3.67, "oos": 2.0}
BYBIT_BASE = {"is": (500, 325.8), "oos": (279, 70.2)}
POS_CUTS = (0.25, 0.75)
EXT_CUTS = (2.0, 4.0)

def build():
    """Craze super-set + the two scale-matched features, grayed not skipped."""
    import importlib.util
    import test_experiments_craze as tc
    cap: dict = {}
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
    assert s.count(t1) == 1
    s = s.replace(t1, t1 + "    exp_ctx_pos_lo=0.0,\n"
                          "    exp_ctx_pos_hi=0.0,\n"
                          "    exp_ctx_ext_lo=0.0,\n"
                          "    exp_ctx_ext_hi=0.0,\n"
                          "    exp_ctx_stats=None,\n")

    gate = ('        if (not exp_mltf) and busy_until and bar_time <= busy_until:\n'
            '            if exp_shadow_book: _sr["reason"]="busy"\n'
            '            continue\n')
    assert s.count(gate) == 1, f"gate count {s.count(gate)}"

    # atr15 already exists at this point in the engine (built for the SL
    # buffer), so the 15m-scale denominator costs nothing extra.
    body = (
        '        if (exp_ctx_pos_lo>0.0 or exp_ctx_pos_hi>0.0 or '
        'exp_ctx_ext_lo>0.0 or exp_ctx_ext_hi>0.0) and fine_ltf:\n'
        '            _cx=int(sig["dir"])\n'
        '            _cxnow=int(candles_ltf[i]["ts"])+900\n'
        '            _cxf=bisect.bisect_right(fine_ts,_cxnow)-1\n'
        '            if _cxf>=0:\n'
        '                # feature 1: position inside the SIGNAL 15m bar\n'
        '                _bx=float(candles_ltf[i]["high"])-float(candles_ltf[i]["low"])\n'
        '                _cpx=(float(fine_ltf[_cxf]["close"])-float(candles_ltf[i]["low"]))/_bx if _bx>0 else 0.5\n'
        '                # feature 2: 60m distance over 15m ATR\n'
        '                _cxs=fine_ltf[max(0,_cxf-59):_cxf+1]\n'
        '                _cxlo=min(float(_c["low"]) for _c in _cxs)\n'
        '                _cxa=atr15[i] if i<len(atr15) else 0.0\n'
        '                _ce=0.0\n'
        '                if _cxa>0:\n'
        '                    _ce=(((float(fine_ltf[_cxf]["close"])-_cxlo) if _cx>0 else (_cxlo-float(fine_ltf[_cxf]["close"])))/_cxa)\n'
        '                exp_ctx_stats["considered"]=exp_ctx_stats.get("considered",0)+1\n'
        '                exp_ctx_stats.setdefault("pos",[]).append(round(_cpx,4))\n'
        '                exp_ctx_stats.setdefault("ext",[]).append(round(_ce,4))\n'
        '                _cxbad=False\n'
        '                if exp_ctx_pos_lo>0.0 and _cpx<exp_ctx_pos_lo: _cxbad=True\n'
        '                if exp_ctx_pos_hi>0.0 and _cpx>exp_ctx_pos_hi: _cxbad=True\n'
        '                if exp_ctx_ext_lo>0.0 and _ce<exp_ctx_ext_lo: _cxbad=True\n'
        '                if exp_ctx_ext_hi>0.0 and _ce>exp_ctx_ext_hi: _cxbad=True\n'
        '                if _cxbad:\n'
        '                    exp_ctx_stats["grayed"]=exp_ctx_stats.get("grayed",0)+1\n'
        '                    continue\n'
        '                exp_ctx_stats["passed"]=exp_ctx_stats.get("passed",0)+1\n'
    )
    s = s.replace(gate, body + gate)
    p = ROOT / "backtest/tests/_v18_ctxscaled_tmp.py"
    p.write_text(s, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("v18_ctxscaled", str(p))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.simulate_htf_ltf_streak_halt


ARMS = (
    ("baseline", {}),
    ("pos_0.25-0.75", dict(exp_ctx_pos_lo=0.25, exp_ctx_pos_hi=0.75)),
    ("pos_hi_0.75", dict(exp_ctx_pos_hi=0.75)),
    ("pos_lo_0.25", dict(exp_ctx_pos_lo=0.25)),
    ("ext_2-4", dict(exp_ctx_ext_lo=2.0, exp_ctx_ext_hi=4.0)),
    ("ext_hi_4", dict(exp_ctx_ext_hi=4.0)),
)


def _pct(v, p):
    s = sorted(v)
    return s[int(p * (len(s) - 1))]


def main():
    from exp_5m_confirm import load_book
    from exp_sizing_combo import run as sim_fn
    from experiment_registry import BP, EXPERIMENTS
    from exp_equity_quality import equity_quality

    t0 = time.time()
    sim = build()
    params = {**BP, **EXPERIMENTS[LANE]["params"]}
    payload = {"lane": LANE, "pos_cuts": list(POS_CUTS),
               "ext_cuts": list(EXT_CUTS), "cells": {}, "probe": {}}
    print("=" * 104, flush=True)
    print("  1m PATH CONTEXT - scale-matched (the corrected run)", flush=True)
    print("=" * 104, flush=True)

    for scope in ("is", "oos"):
        data, _ = load_book(scope)
        ctl = equity_quality(sim_fn(sim, data, dict(params)), YEARS[scope])
        exp_n, exp_net = BYBIT_BASE[scope]
        ok = ctl["n"] == exp_n and abs(ctl["net"] - exp_net) < 0.6
        print(f"\n  [{scope}] CONTROL {ctl['n']}t {ctl['net']:+.1f}R "
              f"{'OK' if ok else 'MISMATCH'}", flush=True)
        if not ok:
            payload.setdefault("errors", []).append(scope)
            continue
        payload["cells"][f"{scope}/baseline"] = {"n": ctl["n"], "net": ctl["net"]}

        # Probe first, so the reader can see the cuts land in the bulk and
        # not in the tail like the failed run did.
        probe: dict = {}
        sim_fn(sim, data, {**params, "exp_ctx_pos_hi": 99.0,
                           "exp_ctx_stats": probe})
        for feat in ("pos", "ext"):
            v = probe.get(feat, [])
            if v:
                print(f"    probe {feat:>3}: n={len(v):,}  p10 {_pct(v,.1):.3f} "
                      f"p25 {_pct(v,.25):.3f} MED {_pct(v,.5):.3f} "
                      f"p75 {_pct(v,.75):.3f} p90 {_pct(v,.9):.3f} "
                      f"max {max(v):.3f}", flush=True)
                payload["probe"].setdefault(scope, {})[feat] = {
                    "n": len(v), "p25": _pct(v, .25), "median": _pct(v, .5),
                    "p75": _pct(v, .75), "p90": _pct(v, .9), "max": max(v)}

        for name, flags in ARMS[1:]:
            st: dict = {}
            m = equity_quality(sim_fn(sim, data, {**params, **flags,
                                                  "exp_ctx_stats": st}),
                               YEARS[scope])
            d = round(m.get("net", 0) - ctl["net"], 1)
            payload["cells"][f"{scope}/{name}"] = {
                "n": m.get("n"), "net": m.get("net"), "d_net": d,
                "wr": m.get("wr"), "pf": m.get("pf"), "max_dd": m.get("max_dd"),
                "gate": {k: v for k, v in st.items()
                         if k in ("considered", "grayed", "passed")}}
            print(f"    {name:<16} {m.get('n', 0):>4}t "
                  f"{m.get('net', 0):>+8.1f}R ({d:+7.1f})  "
                  f"WR {str(m.get('wr')):>5}%  PF {str(m.get('pf')):>6}  "
                  f"DD {str(m.get('max_dd')):>6}  "
                  f"| grayed {st.get('grayed', 0)} / {st.get('considered', 0)}",
                  flush=True)

    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()
