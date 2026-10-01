"""PATH-TRUE rerun of the Stage B standing candidate: wick_atr12@short <= 6.03.

WHY THIS EXISTS
---------------
Stage B (exp_bleed_autopsy.py) reported this removal as PASS 4/4 with OOS dNet
+19.8/+23.8 and OOS maxDD 53.2->36.7 / 29.4->19.8. But that was a POST-PROCESS
skip: the trade was deleted from the finished ledger, so every downstream piece
of engine state still believed the trade had been taken.

With exp_mltf=True the engine holds CONCURRENT positions, so removing a trade
frees a busy_until slot, changes the cooldown/last_loss_bar timeline, and can
shift the max_consecutive_losses streak. Study 1 (exp_thesis_chain_decomposition)
showed exactly this cascade term is what flips sign in OOS. So the post-process
+19.8R is an UPPER BOUND.

WHAT THIS DOES
--------------
Patches the shipped engine so the same predicate rejects the entry BEFORE any
state is mutated - placed immediately after `i=ltf_store.pos(bar_time)`, before
busy_until / cooldown / streak-halt / book mutation. That makes the removal
path-true: state evolves as if the trade never existed.

PREDICATE (identical to Stage B section 5.3, not retuned here)
  short AND wick_atr12 <= 6.03
  where wick_atr12 = (sum(up_wick) + sum(low_wick)) / ATR over the 12 closed 15m
  bars ending at the entry bar - pure market structure, no trade state.
  Masked to SHORT only; both surviving Stage B removals are short-side.

GATES
  identity gate: patched-with-filter-off must reproduce the shipped trade list
  exactly (same n, same R list) in all 4 cells before any filtered result shows.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_wick_short_pathtrue.py
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

from experiment_registry import BP, EXPERIMENTS
from run_experiment import net_r
from test_experiments_craze import build_module
from exp_boundary_state_autopsy import load_scope
from exp_equity_quality import equity_quality, arm_scores, curve_better

OUT = ROOT / "backtest/tests/_wick_short_pathtrue.json"
YEARS = {"is": 3.67, "oos": 2.0}
LANES = (("champion", "champion_multi_sw10"), ("utcsat", "utcsat_multi_sw10"))
WICK_MAX = 6.03          # threshold fixed by Stage B - NOT fitted here
LB = 12                  # 15m bars in the wick window

ANCHOR = "        if i < 0 or i>=n-1: continue\n"
INJECT = ANCHOR + (
    "        if _WICK_MAX>0 and direction_of(sig)!=1:\n"
    "            _j=i\n"
    "            if _j>=_LB:\n"
    "                _lo=_j-_LB+1\n"
    "                _us=0.0; _ls=0.0\n"
    "                for _k in range(_lo,_j+1):\n"
    "                    _c=candles_ltf[_k]\n"
    "                    _o=float(_c[\"open\"]); _h=float(_c[\"high\"])\n"
    "                    _l=float(_c[\"low\"]); _cc=float(_c[\"close\"])\n"
    "                    _us+=_h-max(_o,_cc)\n"
    "                    _ls+=min(_o,_cc)-_l\n"
    "                _a=atr15[_j]\n"
    "                if _a>0 and (_us+_ls)/_a<=_WICK_MAX:\n"
    "                    continue\n"
)


def build_patched():
    """Craze super-set + one asserted, default-off patch.

    Patches the SAME source text build_module() builds (the super-set that
    accepts the registry kwargs), so exp_partial_r / exp_mltf pass through.
    The identity gate still compares against the shipped engine's trade list,
    so any deviation from the baseline shows up immediately.
    """
    import test_experiments_craze as T

    # build_module() writes its patched text to a temp file, execs it, then
    # deletes it. We intercept that text by re-running the chain ourselves:
    # grab the super-set the same way, then add our one patch on top.
    s = T.SRC
    orig_load = T._load_module
    captured = {}

    def spy(text, name):
        captured["text"] = text
        raise SystemExit(0)          # stop build_module right after it patches

    T._load_module = spy
    try:
        T.build_module()
    except SystemExit:
        pass
    finally:
        T._load_module = orig_load
    assert "text" in captured, "failed to capture craze super-set source"
    s = captured["text"]

    t_loop = "    for sig, use in filtered:\n"
    assert s.count(t_loop) == 1, "filtered loop anchor"
    s = s.replace(t_loop, "    def direction_of(sig):\n"
                           "        return 1 if int(sig[\"dir\"])==1 else -1\n"
                        + t_loop)

    assert s.count(ANCHOR) == 1, f"LTF entry anchor count={s.count(ANCHOR)}"
    s = s.replace(ANCHOR, INJECT)

    # module-level tunables, settable from outside before each run.
    # Must come AFTER any "from __future__ import" line, so anchor on it.
    fut = "from __future__ import annotations\n"
    if fut in s:
        assert s.count(fut) == 1, "future import anchor"
        s = s.replace(fut, fut + "\n_WICK_MAX = 0.0\n_LB = 12\n")
    else:
        s = "_WICK_MAX = 0.0\n_LB = 12\n" + s

    import importlib.util
    p = ROOT / "backtest/tests/_wick_tmp.py"
    p.write_text(s, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("wick_patched", str(p))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def run(fn, data, params):
    out = fn(data["c1h"], data["sw10"], data["c15"], data["sw15"],
             fine_ltf=data["fine"], **params)
    trades = out["ltf_trades"] if isinstance(out, dict) else out
    return sorted(trades, key=lambda t: int(t["entry_ts"]))


def line(tag, base, filt, yrs):
    qb, qf = equity_quality(base, yrs), equity_quality(filt, yrs)
    nb, nf = net_r(base), net_r(filt)
    d = arm_scores(qf, qb)
    cf = curve_better(d)
    ok = (qf["net"] > qb["net"] and len(filt) < len(base)
          and nf / len(filt) > nb / len(base) and cf)
    return (f"  {tag:24s} n {len(base):4d}->{len(filt):4d}  "
            f"net {qb['net']:+8.1f}->{qf['net']:+8.1f} (d{qf['net']-qb['net']:+7.1f})  "
            f"avg {nb/len(base):+.3f}->{nf/len(filt):+.3f}  "
            f"DD {qb['max_dd']:5.1f}->{qf['max_dd']:5.1f}  "
            f"calmar {qb['calmar']:.3f}->{qf['calmar']:.3f}  "
            f"curve {cf}  {'ok' if ok else 'FAIL'}")


def main():
    t0 = time.time()
    print("=" * 112, flush=True)
    print("  PATH-TRUE RERUN: remove wick_atr12@short <= %.2f" % WICK_MAX, flush=True)
    print("=" * 112, flush=True)
    ship = build_module()
    pmod = build_patched()
    patched = pmod.simulate_htf_ltf_streak_halt
    gate_ok = True
    payload = {
        "filter": f"short and wick_atr12<={WICK_MAX}", "lb": LB,
        "postprocess_stageB_dNet": {"oos|champion": 19.8, "oos|utcsat": 23.8},
        "years": YEARS, "cells": {}}

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] ===", flush=True)
        data = load_scope(scope)
        for lane, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            params.setdefault("exp_partial_r", 0.0)
            base = run(ship, data, params)
            pmod._WICK_MAX = 0.0
            off = run(patched, data, params)   # filter OFF = identity
            same = (len(off) == len(base)
                    and round(net_r(off), 6) == round(net_r(base), 6)
                    and [t["entry_ts"] for t in off] == [t["entry_ts"] for t in base])
            gate_ok &= same
            print(f"  [{scope}|{lane}] identity gate: {len(off)}t vs shipped "
                  f"{len(base)}t -> {'IDENTICAL' if same else 'MISMATCH'}",
                  flush=True)
            if not same:
                continue
            pmod._WICK_MAX = WICK_MAX
            filt = run(patched, data, params)
            years = YEARS[scope]
            print(line(f"{scope}|{lane} PATH-TRUE", base, filt, years), flush=True)
            payload["cells"][f"{scope}|{lane}"] = {
                "identical": same,
                "base_n": len(base), "filt_n": len(filt),
                "base_net": round(net_r(base), 2),
                "filt_net": round(net_r(filt), 2),
                "dNet": round(net_r(filt) - net_r(base), 2),
                "base_eq": equity_quality(base, years),
                "filt_eq": equity_quality(filt, years),
                "delta": arm_scores(equity_quality(filt, years),
                                    equity_quality(base, years)),
                "curve_better": curve_better(
                    arm_scores(equity_quality(filt, years),
                               equity_quality(base, years))),
            }

    print("\n" + "=" * 112, flush=True)
    print("  IDENTITY GATE: " + ("ALL IDENTICAL - results valid"
                                 if gate_ok else "FAILED - results void"),
          flush=True)
    print("  Stage B post-process comparison: OOS champion +19.8, OOS utcsat +23.8",
          flush=True)
    print("=" * 112, flush=True)
    payload["gate_ok"] = gate_ok
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"wrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
