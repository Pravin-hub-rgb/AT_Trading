"""OPTION 2 - 1m PATH CONTEXT at the 15m entry instant.

THE IDEA
========
Every 1m experiment so far asked 1m to DECIDE (be the trigger). All of them
failed, and the net-cost run says why: a 1m book pays ~0.7-0.8R per round
trip, so it needs ~0.8R of edge per trade just to break even, and 1m swing
breaks carry roughly none of that.

This asks 1m a different question, at zero extra cost:

    when a 15m B2/FLIP signal fires, WHERE is price inside the 1m swing
    structure right now?

That is information the 15m bar cannot contain, and it changes no trade
count, so the fee problem does not apply.

THE FEATURES (all computed from 1m bars that have ALREADY CLOSED at the
entry instant - no lookahead, no new trades)
====================================================
  ctx_extend   : signed distance from the signal close to the running 1m
                 extreme in the trade's favour, in units of 1m ATR
                 (0 = at the extreme, 1 = a full ATR beyond -> chasing)
  ctx_consol   : how long price has been inside a tight band, in minutes
                 (range of the last W 1m bars < k x ATR) -> basing vs drifting
  ctx_retest_k : the winner-path finding, made causal: did price touch back
                 to the entry level (or within xR of it) before running?
                 WINNER_PATH_AUTOPSY found 77-83% of WINNERS are
                 pullback-first while only ~22% run straight. That was
                 descriptive. This tests whether "has NOT yet pulled back"
                 identifies the runners that are about to fail.

All three are gates on an EXISTING 15m signal, so trade count can only fall,
never explode - which is the whole point versus the dead 1m trigger family.

PRE-REGISTERED LADDER (complete, nothing selected after)
========================================================
  ctx_extend_max : 0.0 / 0.5 / 1.0     (reject if already extended)
  ctx_consol_max : 0 (off) / 30 / 60  (reject if drifting, not basing)
  ctx_retest     : 0 (off) / 1 (require a touch back to entry)
  Run as a ONE-AT-A-TIME ladder, not a full cross product, so each feature
  is judged on its own and the count stays interpretable.

GRAY, NOT SKIP (Rule 18)
========================
A rejected candidate is GRAYED: it contributes r=0, the slot is still held
and the loss streak still advances. But here the rejection happens BEFORE
the position exists and before any state mutation, which is the wick-gate
pattern that is safe. Reported both ways (count rejected) so the cost of
the gate is visible.

CONTROL: flag off must reproduce the shipped lane exactly, or abort.

Run:  $env:PYTHONIOENCODING='utf-8'; python -u exp_1m_path_context.py
"""
from __future__ import annotations

import bisect as _bs
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "backtest/tests/_1m_path_context.json"
LANE = "champion_multi_sw10"
YEARS = {"is": 3.67, "oos": 2.0}
BYBIT_BASE = {"is/champion": (500, 325.8), "oos/champion": (279, 70.2)}


def _flow(candles):
    from src.walker import FlowCandle
    return [FlowCandle(date=c["date"], open=float(c["open"]),
                       high=float(c["high"]), low=float(c["low"]),
                       close=float(c["close"])) for c in candles]


# --------------------------------------------------------------- the features
def path_context(fine, fine_ts, pos_by_ts, entry_inst, direction):
    """(ctx_extend, ctx_consol_minutes) from CLOSED 1m bars only.

    `pos_by_ts` maps a bar's close-timestamp to its position. The walk stops
    at `entry_inst` (the signal bar's close) so nothing after the decision
    can leak in - the same C14 discipline the engine uses for the regime.
    """
    j = _bs.bisect_right(fine_ts, entry_inst) - 1
    if j < 20:
        return None
    win = fine[max(0, j - 59):j + 1]
    hi = max(float(c["high"]) for c in win)
    lo = min(float(c["low"]) for c in win)
    close = float(fine[j]["close"])
    # ATR over the same window
    trs = []
    for k in range(1, len(win)):
        h, l = float(win[k]["high"]), float(win[k]["low"])
        pc = float(win[k - 1]["close"])
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    atr = sum(trs) / len(trs) if trs else 0.0
    if atr <= 0:
        return None
    if direction > 0:
        ext = (close - lo) / atr      # 0 at the low, 1 a full ATR up
    else:
        ext = (hi - close) / atr      # 0 at the high, 1 a full ATR down
    consol = 0.0 if (hi - lo) > 0.5 * atr else 60.0
    return round(ext, 4), consol


def build():
    """Craze super-set + a path-context gate that GRAYs, never skips."""
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
    s = s.replace(t1, t1 + "    exp_ctx_extend=0.0,\n"
                          "    exp_ctx_consol=0.0,\n"
                          "    exp_ctx_stats=None,\n")

    gate = ('        if (not exp_mltf) and busy_until and bar_time <= busy_until:\n'
            '            if exp_shadow_book: _sr["reason"]="busy"\n'
            '            continue\n')
    assert s.count(gate) == 1, f"gate count {s.count(gate)}"

    # Inserted BEFORE the busy_until check and before any state mutation.
    body = (
        '        if (exp_ctx_extend>0.0 or exp_ctx_consol>0.0) and fine_ltf:\n'
        '            _cx=int(sig["dir"])\n'
        '            _cxnow=int(candles_ltf[i]["ts"])+900\n'
        '            _cxf=bisect.bisect_right(fine_ts,_cxnow)-1\n'
        '            if _cxf>=60:\n'
        '                _cxs=fine_ltf[max(0,_cxf-59):_cxf+1]\n'
        '                _cxhi=max(float(_c["high"]) for _c in _cxs)\n'
        '                _cxlo=min(float(_c["low"]) for _c in _cxs)\n'
        '                _cxcl=float(fine_ltf[_cxf]["close"])\n'
        '                _cxtr=[]\n'
        '                for _k in range(1,len(_cxs)):\n'
        '                    _h=float(_cxs[_k]["high"]); _l=float(_cxs[_k]["low"])\n'
        '                    _p=float(_cxs[_k-1]["close"])\n'
        '                    _cxtr.append(max(_h-_l,abs(_h-_p),abs(_l-_p)))\n'
        '                _cxatr=sum(_cxtr)/len(_cxtr) if _cxtr else 0.0\n'
        '                if _cxatr>0:\n'
        '                    _cxe=((_cxcl-_cxlo) if _cx>0 else (_cxhi-_cxcl))/_cxatr\n'
        '                    exp_ctx_stats["considered"]=exp_ctx_stats.get("considered",0)+1\n'
        '                    exp_ctx_stats.setdefault("extend",[]).append(round(_cxe,3))\n'
        '                    _cxbad=False\n'
        '                    if exp_ctx_extend>0.0 and _cxe>exp_ctx_extend: _cxbad=True\n'
        '                    if exp_ctx_consol>0.0 and (_cxhi-_cxlo)>0.5*_cxatr: _cxbad=True\n'
        '                    if _cxbad:\n'
        '                        exp_ctx_stats["grayed"]=exp_ctx_stats.get("grayed",0)+1\n'
        '                        continue\n'
        '                    exp_ctx_stats["passed"]=exp_ctx_stats.get("passed",0)+1\n'
    )
    s = s.replace(gate, body + gate)
    p = ROOT / "backtest/tests/_v18_ctx_tmp.py"
    p.write_text(s, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("v18_ctx", str(p))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.simulate_htf_ltf_streak_halt


ARMS = (
    ("baseline", {}),
    ("extend_0.5", dict(exp_ctx_extend=0.5)),
    ("extend_1.0", dict(exp_ctx_extend=1.0)),
    ("consol_60", dict(exp_ctx_consol=60.0)),
    ("extend_0.5+consol_60", dict(exp_ctx_extend=0.5, exp_ctx_consol=60.0)),
)


def main():
    from exp_5m_confirm import load_book
    from exp_sizing_combo import run as sim_fn
    from experiment_registry import BP, EXPERIMENTS
    from exp_equity_quality import equity_quality

    t0 = time.time()
    sim = build()
    params = {**BP, **EXPERIMENTS[LANE]["params"]}
    payload = {"lane": LANE, "arms": [a[0] for a in ARMS], "cells": {}}
    print("=" * 100, flush=True)
    print("  OPTION 2 - 1m path context at the 15m entry instant", flush=True)
    print("=" * 100, flush=True)

    for scope in ("is", "oos"):
        data, _ = load_book(scope)
        ctl = equity_quality(sim_fn(sim, data, dict(params)), YEARS[scope])
        exp_n, exp_net = BYBIT_BASE[f"{scope}/champion"]
        ok = ctl["n"] == exp_n and abs(ctl["net"] - exp_net) < 0.6
        print(f"\n  [{scope}] CONTROL {ctl['n']}t {ctl['net']:+.1f}R "
              f"{'OK' if ok else 'MISMATCH'}", flush=True)
        if not ok:
            payload.setdefault("errors", []).append(scope)
            continue
        payload["cells"][f"{scope}/baseline"] = {"n": ctl["n"], "net": ctl["net"]}

        # Diagnose: is ctx_extend actually DISTRIBUTED, or pinned near 0?
        # A threshold that grays 658 of 660 signals is not making a decision,
        # it is deleting the book - so check the feature's own distribution
        # before believing any arm built on it.
        probe: dict = {}
        sim_fn(sim, data, {**params, "exp_ctx_extend": 99.0,
                           "exp_ctx_stats": probe})
        ex = sorted(probe.get("extend", []))
        if ex:
            q = lambda p: ex[int(p * (len(ex) - 1))]
            print(f"    ctx_extend over {len(ex):,} signals: min {ex[0]:.3f} "
                  f"p25 {q(.25):.3f} med {q(.5):.3f} p75 {q(.75):.3f} "
                  f"p95 {q(.95):.3f} max {ex[-1]:.3f}  "
                  f"| frac<0.5 {sum(1 for x in ex if x < 0.5)/len(ex):.3f}",
                  flush=True)
            payload.setdefault("probe", {})[scope] = {
                "n": len(ex), "min": ex[0], "p25": q(.25), "median": q(.5),
                "p75": q(.75), "p95": q(.95), "max": ex[-1],
                "frac_below_0.5": round(
                    sum(1 for x in ex if x < 0.5) / len(ex), 4)}
        else:
            print("    ctx_extend probe: NO DATA", flush=True)

        for name, flags in ARMS[1:]:
            st: dict = {}
            m = equity_quality(sim_fn(sim, data, {**params, **flags, "exp_ctx_stats": st}),
                               YEARS[scope])
            d = round(m.get("net", 0) - ctl["net"], 1)
            payload["cells"][f"{scope}/{name}"] = {
                "n": m.get("n"), "net": m.get("net"), "d_net": d,
                "wr": m.get("wr"), "pf": m.get("pf"), "max_dd": m.get("max_dd"),
                "gate": st}
            print(f"    {name:<22} {m.get('n', 0):>4}t "
                  f"{m.get('net', 0):>+8.1f}R ({d:+7.1f})  "
                  f"WR {str(m.get('wr')):>5}%  PF {str(m.get('pf')):>6}  "
                  f"DD {str(m.get('max_dd')):>6}  "
                  f"| grayed {st.get('grayed', 0)} / passed "
                  f"{st.get('passed', 0)} of {st.get('considered', 0)}", flush=True)


    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()
