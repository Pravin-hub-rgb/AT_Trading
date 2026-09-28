"""B1 ENTRY - the last open direction, done properly (path-true engine run).

THE GAP THIS CLOSES
===================
`CLOSED_DO_NOT_REPEAT.md` lists "B1 entry" as genuinely untested. Every B1
number produced so far was an artefact: it reused the B2-era exit, mixed risk
denominators, and had a degenerate-stop bug. This is the real thing.

HOW THE PATCH WORKS
===================
The LTF entry trigger is
    ltf_sigs=_collect_signals(swings_ltf, "decisive", ...)
and inside `_collect_signals` the mark kinds come from
    {"b2": ("B2",), "flip": ("FLIP",)}.get(entry_break, ("B2","FLIP"))
There is NO "b1" key, so B1 entry has never been reachable, and
`exp_b1_b2_mode` cannot help - it blocks the B2 trigger, it does not change
it.

Rather than edit the shared engine file, this rebuilds that one module in
memory with a `"b1": ("B1",)` key added and installs it in sys.modules BEFORE
the craze loader imports it. Everything downstream (SL, trail, cooldown, loss
streak, window caps) then runs untouched. Same pattern the repo already uses
for `no_shared_file_edit` runtime patches. B1 marks do exist -
`exp_thesis_swing_geometry_deep.first_mark(s,"B1",...)` finds them.

The user also asked for a stop above the swing low. Both are swept together,
because a B1 fill with a swing-low stop is the degenerate case: the fill sits
near the extreme, so the stop must come up. Whether B1 can be made to work at
all is only visible in the combined grid.

Arms: entry {b1, decisive=B2/flip} x SL pull {0, 0.5, 1.0, 1.5, 2.0} x ATR15.
decisive + 0.0 is the shipped book and must reproduce the reference ledgers
exactly or the run aborts.
"""
from __future__ import annotations

import json
import sys
import time
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "live_stuff/tests/_b1_entry.json"
ENGINE_SRC = ROOT / "backend/src/btc/btc_engine.py"
LANES = (("champion", "champion_multi_sw10"),
         ("utcsat", "utcsat_multi_sw10"))
YEARS = {"is": 3.67, "oos": 2.0}
SL_K = (0.0, 0.5, 1.0, 1.5, 2.0)
BYBIT_BASE = {
    "is/champion": (500, 325.8), "is/utcsat": (454, 358.9),
    "oos/champion": (279, 70.2), "oos/utcsat": (253, 60.2),
}
_LONG_SL = ('            sl=sl_pivot - sl_buf_atr*atr15[i] '
           'if sl_buf_atr>0 else sl_pivot')
_SHORT_SL = ('            sl=sl_pivot + sl_buf_atr*atr15[i] '
            'if sl_buf_atr>0 else sl_pivot')
_TIGHT = ('            if exp_sl_tight>0.0:\n'
          '                sl_pivot = sl_pivot + exp_sl_tight*atr15[i]*'
          '(1.0 if entry>sl_pivot else -1.0)\n')
_TRIG = 'ltf_sigs=_collect_signals(swings_ltf, "decisive",'

def install_b1():
    """Rebuild btc_engine in memory with a B1 mark kind. No file is edited."""
    src = ENGINE_SRC.read_text(encoding="utf-8")
    anchor = '        "b2": ("B2",),'
    if '"b1": ("B1",)' not in src:
        assert src.count(anchor) == 1, f"b2 key count {src.count(anchor)}"
        src = src.replace(anchor, anchor + '\n        "b1": ("B1",),')
    mod = types.ModuleType("src.btc.btc_engine")
    mod.__file__ = str(ENGINE_SRC)
    mod.__package__ = "src.btc"
    exec(compile(src, str(ENGINE_SRC), "exec"), mod.__dict__)
    sys.modules["src.btc.btc_engine"] = mod
    return mod


def build():
    """Craze super-set + B1 entry switch + SL-pull patch."""
    import importlib.util
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
    assert s.count(t1) == 1
    s = s.replace(t1, t1 + "    exp_sl_tight=0.0,\n    exp_b1_entry=\"decisive\",\n")
    for a in (_LONG_SL, _SHORT_SL):
        assert s.count("\n" + a) == 1, f"sl anchor {a[:30]}"
        s = s.replace("\n" + a, "\n" + _TIGHT + a)
    assert s.count(_TRIG) == 1, f"trigger count {s.count(_TRIG)}"
    s = s.replace(_TRIG, 'ltf_sigs=_collect_signals(swings_ltf, exp_b1_entry,')
    p = ROOT / "live_stuff/tests/_v18_b1_tmp.py"
    p.write_text(s, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("v18_b1", str(p))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.simulate_htf_ltf_streak_halt


def main():
    t0 = time.time()
    install_b1()
    print("  btc_engine rebuilt in memory with a B1 mark kind "
          "(shared file NOT edited)", flush=True)
    sim = build()
    print("  craze module built: B1 entry switch + SL-pull patch", flush=True)
    from exp_sizing_combo import run as sim_fn
    from exp_5m_confirm import load_book
    from experiment_registry import BP, EXPERIMENTS
    from exp_equity_quality import equity_quality

    payload = {"stage": "b1_entry", "cells": {}}
    print("\n" + "=" * 100, flush=True)
    print("  B1 ENTRY x SL VARIANT - full path-true grid", flush=True)
    print("=" * 100, flush=True)
    for scope in ("is", "oos"):
        data, _ = load_book(scope)
        for name, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            ctl = equity_quality(sim_fn(sim, data, {
                **params, "exp_b1_entry": "decisive",
                "exp_sl_tight": 0.0}), YEARS[scope])
            exp_n, exp_net = BYBIT_BASE[f"{scope}/{name}"]
            ok = ctl["n"] == exp_n and abs(ctl["net"] - exp_net) < 0.6
            print(f"\n  [{scope}/{name}] CONTROL {ctl['n']}t {ctl['net']:+.1f}R"
                  f" (expect {exp_n}t {exp_net:+.1f}) "
                  f"{'OK' if ok else 'MISMATCH - ABORT'}", flush=True)
            if not ok:
                payload.setdefault("errors", []).append(f"{scope}/{name}")
                continue
            for entry in ("b1", "decisive"):
                for k in SL_K:
                    tr = sim_fn(sim, data, {
                        **params, "exp_b1_entry": entry, "exp_sl_tight": k})
                    m = equity_quality(tr, YEARS[scope])
                    d = round(m["net"] - ctl["net"], 1)
                    lbl = "B1    " if entry == "b1" else "B2flip"
                    payload["cells"][
                        f"{scope}/{name}/{lbl}/k{k}"] = {
                        "n": m["n"], "net": m["net"], "wr": m["wr"],
                        "pf": m["pf"], "max_dd": m["max_dd"],
                        "calmar": m["calmar"], "d_net": d,
                        "d_dd": round(ctl["max_dd"] - m["max_dd"], 1)}
                    print(f"    {lbl} SL+{k:<4} {m['n']:>4}t {m['net']:>+8.1f}R"
                          f" ({d:+7.1f})  WR {m['wr']:>5}%  PF {m['pf']:>6}  "
                          f"DD {m['max_dd']:>6.1f}  cal {m['calmar']:>7.3f}",
                          flush=True)
    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()
