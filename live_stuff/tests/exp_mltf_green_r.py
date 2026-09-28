"""PHASE 3 - `exp_mltf_green_r`: does an R-threshold beat a time-threshold
on the 1m add-on?

THE USER'S OTHER 1m IDEA, AND WHY IT IS THE ONE TO RUN NOW
==========================================================
"1-minute scalping" is TWO different things in this repo, in different states:

  (A) a 1m SETUP/ENTRY LAYER - detect and enter on 1m. That is Phase 1/2 of
      HANDOVER section 7. It is BLOCKED, and Phase 0 proved why: the naive
      patch drops 91% of signals and rescales every bar-counted param 15x.
      See PHASE0_1M_SWING_BLOCKER.md, "Phase 1 as written".

  (B) the 1m ADD-ON / SCALING that ALREADY SHIPS as `exp_mltf=True`. It
      needs no 1m swing layer at all and is live in the champion today.

This file is (B). It is unblocked, and Stage 44 already says the cohort is
profitable, so the only open question is the SHAPE of the gate.

WHAT exp_mltf ACTUALLY DOES (read, not assumed)
===============================================
`exp_mltf` does NOT create 1m signals. It makes the slot gate inert:

    v18 line 577:  if busy_until and bar_time <= busy_until: continue
    v18 line 743:  busy_until = candles_ltf[exit_idx]["date"]

and the craze super-set rewrites 577 to

    if (not exp_mltf) and busy_until and bar_time <= busy_until: continue

So under exp_mltf the slot is never held: a 15m signal can open a second
position while the first is live. That IS the "1m scaling" behaviour - more
entries, overlapping - on 15m signals with 1m fills. The 1m data supplies
the EXIT path, not the trigger. So (B) is a CONCURRENCY policy, not a
timeframe change, which is exactly why it is immune to the Phase 1
re-parameterisation problem.

THE EXPERIMENT
==============
`exp_mltf_green_r = k` : a new add-on is allowed only when the already-open
SAME-DIRECTION cohort is at least kR green at the decision instant.
k = 0.25 / 0.5 / 1.0 / 1.5. Pre-registered ladder, every rung reported, no
rung selected after the fact.

This is the R-threshold. The shipped alternative is `exp_persist=7`, a
TIME-threshold on the regime channel. The run answers a real question: does
"add only when green" beat "add any time" and "add after 7 bars"?

WHY THIS IS THE RIGHT FIRST MOVE
================================
Stage 44 (MARGINAL_PREENTRY_ATLAS.md) already measured this cohort: when the
HTF trade is in profit the add-on is profitable in all six cells - champion
+109.6R IS / +42.2R OOS, with higher WR and PF than first trades. The user's
instinct was right and it is VALIDATED. What was never run is the path-true
GATE, because red add-ons were ALSO positive on tiny samples (2-7 per cell),
which left a descriptive block-red rule unjustifiable. An R-threshold is a
different rule from block-red: it keeps the marginal add-on when the cohort
is meaningfully green, not merely non-red. That is the untested variant.

CAUSALITY (this repo has shipped this leak once)
================================================
The gate reads MARKED R of positions open AT the decision instant:
    px_now = the 1m close at the decision bar (already closed)
    r_mark = (px_now - entry) * d / |entry - sl|
Only closed 1m bars are used, and only trades that entered before the
candidate. No trade's FINAL r is ever read - AGENT_COORDINATION.md line 155
records that doing so shipped a false 4/4 once. A position that has already
exited is not open and does not vote.

R DENOMINATOR (HANDOVER section 5, trap 1)
==========================================
r_mark divides by each trade's OWN |entry - sl|, held per trade, never pooled
across trades. Nothing averages R across a bucket with a shared denominator
and nothing compares buckets, so the stop-distance confound does not apply.

GRAY, NOT SKIP (Rule 18)
========================
The gate REJECTS a new add-on. It does not cancel or resize anything already
open, frees no slot and resets no cooldown, and it runs before any state
mutation. So the wick-gate failure mode (skip frees the slot and admits a
worse replacement: -39.0R vs gray +28.1R) does not apply - this is an
entry-side decision, not a book mutation.

Run:  $env:PYTHONIOENCODING='utf-8'; python -u exp_mltf_green_r.py
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

OUT = ROOT / "live_stuff/tests/_mltf_green_r.json"

# Pre-registered ladder. Every rung is run and reported; none is selected.
K_LADDER = (0.25, 0.5, 1.0, 1.5)

LANES = (("champion", "champion_multi_sw10"),
         ("utcsat", "utcsat_multi_sw10"))
YEARS = {"is": 3.67, "oos": 2.0}

# Reference ledgers from HANDOVER section 1. Abort on mismatch.
BYBIT_BASE = {
    "is/champion": (500, 325.8), "is/utcsat": (454, 358.9),
    "oos/champion": (279, 70.2), "oos/utcsat": (253, 60.2),
}

# The craze gate, exactly as test_experiments_craze.py:955 writes it.
_GATE = ('        if (not exp_mltf) and busy_until and bar_time <= busy_until:\n'
         '            if exp_shadow_book: _sr["reason"]="busy"\n'
         '            continue\n')

_KWARG = "    exp_mltf_green_r=0.0,\n"
_STATS = "    exp_mltf_green_stats=None,\n"

# The gate body. Inserted immediately BEFORE the busy_until check, so the
# R-threshold is evaluated first and can `continue` past the whole entry.
# Marked R uses only closed 1m bars at the decision instant and each open
# trade's own risk; the final r of any trade is never read.
_GATE_BODY = (
    '        if exp_mltf_green_r>0.0 and exp_mltf_green_stats is not None:\n'
    '            _gd=int(sig["dir"])\n'
    '            _now=int(candles_ltf[i]["ts"])+900\n'
    '            _fi=bs.bisect_right(fine_ts,_now)-1\n'
    '            if _fi>=0:\n'
    '                _gpx=float(fine_ltf[_fi]["close"])\n'
    '                _mark=0.0; _nopen=0\n'
    '                _gdir="long" if _gd>0 else "short"\n'
    '                for _t in ltf_trades:\n'
    '                    if _t.get("dir")!=_gdir: continue\n'
    '                    if int(_t.get("entry_ts") or 0)>=_now: continue\n'
    '                    if int(_t.get("exit_ts") or 0)<=_now: continue\n'
    '                    _rk=abs(float(_t["entry_price"])-float(_t["sl"]))\n'
    '                    if _rk<=0: continue\n'
    '                    _mark+=((_gpx-float(_t["entry_price"]))*_gd)/_rk\n'
    '                    _nopen+=1\n'
    '                _S=exp_mltf_green_stats\n'
    '                _S["considered"]=_S.get("considered",0)+1\n'
    '                if _nopen==0:\n'
    '                    _S["no_open_cohort"]=_S.get("no_open_cohort",0)+1\n'
    '                elif _mark<exp_mltf_green_r:\n'
    '                    _S["blocked"]=_S.get("blocked",0)+1\n'
    '                    _S.setdefault("blocked_mark_r",[]).append(round(_mark,4))\n'
    '                    _S.setdefault("blocked_open_n",[]).append(_nopen)\n'
    '                    continue\n'
    '                else:\n'
    '                    _S["allowed"]=_S.get("allowed",0)+1\n'
)


def build():
    """Craze super-set + the exp_mltf_green_r gate. No shared file is edited.

    The craze text is captured by spying on its loader rather than
    re-implementing it, so this rides the SAME super-set every other
    experiment here rides - exp_mltf included.
    """
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
    assert s.count(t1) == 1, f"sig star count {s.count(t1)}"
    s = s.replace(t1, t1 + _KWARG + _STATS)

    assert s.count(_GATE) == 1, f"craze gate count {s.count(_GATE)}"
    s = s.replace(_GATE, _GATE_BODY + _GATE)

    p = ROOT / "live_stuff/tests/_v18_green_r_tmp.py"
    p.write_text(s, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("v18_green_r", str(p))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.simulate_htf_ltf_streak_halt


def summarise(tr, years):
    """equity_quality plus the ex-best-3/5 tail check (Rule 14)."""
    from exp_equity_quality import equity_quality
    m = equity_quality(tr, years)
    rs = sorted((float(t["r_multiple"]) for t in tr), reverse=True)
    m["ex_best3"] = round(sum(rs[3:]), 1)
    m["ex_best5"] = round(sum(rs[5:]), 1)
    m["top3_share"] = (round(100.0 * sum(rs[:3]) / sum(rs), 1)
                       if rs and sum(rs) > 0 else None)
    return m


def main():
    t0 = time.time()
    sim = build()
    print("  craze super-set + exp_mltf_green_r gate built "
          "(shared file NOT edited)", flush=True)
    from exp_sizing_combo import run as sim_fn
    from exp_5m_confirm import load_book
    from experiment_registry import BP, EXPERIMENTS

    payload = {"stage": "mltf_green_r", "k_ladder": list(K_LADDER), "cells": {}}
    print("\n" + "=" * 104, flush=True)
    print("  PHASE 3 - exp_mltf_green_r : R-threshold on the 1m add-on",
          flush=True)
    print("=" * 104, flush=True)

    for scope in ("is", "oos"):
        data, _ = load_book(scope)
        for name, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            ctl = summarise(sim_fn(sim, data, dict(params)), YEARS[scope])
            exp_n, exp_net = BYBIT_BASE[f"{scope}/{name}"]
            ok = ctl["n"] == exp_n and abs(ctl["net"] - exp_net) < 0.6
            print(f"\n  [{scope}/{name}] CONTROL {ctl['n']}t {ctl['net']:+.1f}R"
                  f" (expect {exp_n}t {exp_net:+.1f}) "
                  f"{'OK' if ok else 'MISMATCH - ABORT'}", flush=True)
            if not ok:
                payload.setdefault("errors", []).append(f"{scope}/{name}")
                continue
            for k in K_LADDER:
                st: dict = {}
                m = summarise(sim_fn(sim, data, {
                    **params, "exp_mltf_green_r": k,
                    "exp_mltf_green_stats": st}), YEARS[scope])
                d = round(m["net"] - ctl["net"], 1)
                payload["cells"][f"{scope}/{name}/k{k}"] = {
                    "n": m["n"], "net": m["net"], "d_net": d, "wr": m["wr"],
                    "pf": m["pf"], "max_dd": m["max_dd"], "calmar": m["calmar"],
                    "ex_best3": m["ex_best3"], "ex_best5": m["ex_best5"],
                    "top3_share": m["top3_share"],
                    "gate": {kk: vv for kk, vv in st.items()
                             if not kk.startswith("blocked_")},
                }
                print(f"    k={k:<5} {m['n']:>4}t {m['net']:>+8.1f}R ({d:+7.1f})"
                      f"  WR {m['wr']:>5}%  PF {m['pf']:>6}  DD {m['max_dd']:>6.1f}"
                      f"  ex-b3 {m['ex_best3']:>+7.1f}  ex-b5 {m['ex_best5']:>+7.1f}"
                      f"  | {st.get('blocked', 0)} blocked /"
                      f" {st.get('allowed', 0)} allowed", flush=True)

    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()
