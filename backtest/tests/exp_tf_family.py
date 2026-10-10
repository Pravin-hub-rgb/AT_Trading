"""HTF/LTF TIMEFRAME FAMILY - 2x2 factorial, with a causality bug fixed first.

THE USER'S HYPOTHESIS (and it is a good one)
===========================================
Shipped is LTF 15m / HTF 1h - a clean 4:1 ladder, since 15m x 4 = 1h. If that
self-consistency is what matters, then LTF 30m / HTF 2h (30m x 4 = 2h) should
be an equally valid family. Every prior 2h run held the LTF at 15m, so it moved
the ratio to 8:1 and confounded "is 2h bad" with "is 8:1 bad". This separates
the two.

THE BUG THIS EXPERIMENT ALSO FIXES
==================================
v18:537-539 says, in the engine's own comment:

    C15: the window is knowable from the flip candle CLOSE (entry_ts + 3600);
    the LTF entry instant is bar_ts + 900. Gate in knowable-instant space.
    if not (s + 2700 < bar_ts <= e + 2700): continue

`s` is an HTF entry_ts (v18:239 `iv.append([int(t["entry_ts"]), ...])`), so the
gate is comparing an HTF-space instant against an LTF-space instant, and
2700 = 3600 - 900 exactly = htf_bar_secs - ltf_bar_secs.

The earlier 2h runs (logs 104/105) patched the bisect close list to 7200 but LEFT
THIS 2700 ALONE. So they gated on 1h math while reading 2h bars, admitting LTF
entries up to an hour before the 2h flip candle had closed - a lookahead leak.
The "2h loses 6/6" direction is unaffected (a leak flatters 2h, and 2h still
lost), so the verdict stands and is conservative - but the published NUMBERS
were wrong and every 2h figure is recomputed here with the correct gate.

The gate is therefore derived, never hard-coded: (htf_bar_secs - ltf_bar_secs).

PATCH SURFACE (every site asserted unique at build time)
  candle_ts_htf_close=[t+3600 ...]  -> t+htf_bar_secs      (2: code + comment)
  ts+900                            -> ts+ltf_bar_secs     (LTF close instant)
  +2700<bar_ts / e+2700             -> +(htf_bar_secs-ltf_bar_secs)
The 16-day cap is time-based and untouched. _atr_pct_15m is a bar-window, not a
time constant, so it needs nothing.

THE GRID (pre-registered)
========================
  cell          LTF   HTF   ladder   gate
  F0_control   15m    1h     4:1     2700   <- must reproduce the books EXACTLY
  F1_ltf_only  30m    1h     2:1     1800   <- LTF change in isolation
  F2_htf_only  15m    2h     8:1     6300   <- HTF change alone, CORRECTED gate
  F3_family    30m    2h     4:1     5400   <- the hypothesis: matched ladder
run at min_bars_15m = 50 (count-preserved) and 25 (duration-preserved, since
50 x 30m = 25h would double the LTF swing while 25 x 30m = 12.5h matches
shipped).

ADOPTION: none. Diagnostic only. Engine stays 15m / 1h / min_bars 20.
age10 reported separately.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_tf_family.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "backtest/tests/_tf_family.json"
M15, M30, H1, H2 = 900, 1800, 3600, 7200
LTF_SWING_H_SHIPPED = 50 * 15 / 60.0          # 12.5 clock hours

# cell -> (ltf_secs, htf_secs)
CELLS = {
    "F0_control_15m_1h": (M15, H1),
    "F1_ltf_only_30m_1h": (M30, H1),
    "F2_htf_only_15m_2h": (M15, H2),
    "F3_family_30m_2h": (M30, H2),
}
# min_bars_15m variants: (label, mb15m)
MB_VARIANTS = (("mb50_count", 50), ("mb25_duration", 25))

BYBIT_BASE = {
    "champion": {"is": (500, 325.8), "oos": (279, 70.2)},
    "utcsat": {"is": (453, 279.5), "oos": (254, 66.9)},
    "age10": {"is": (130, 435.7), "oos": (76, 43.2)},
}
YEARS = {"is": 3.67, "oos": 2.0}
LANES = (
    ("champion", "champion_multi_sw10"),
    ("utcsat", "utcsat_multi_sw10"),
    ("age10", "age10_dirmatch_swingpause_single_sw10"),
)


def build_family_module():
    """Engine with htf_bar_secs AND ltf_bar_secs exposed, and the window gate derived.

    The gate is computed once as _win = htf_bar_secs - ltf_bar_secs, which
    reproduces the shipped 2700 for 1h/15m by construction rather than by
    coincidence. Hard-coding 2700 for every plane is exactly the bug this
    harness exists to correct.
    """
    import importlib.util
    import test_experiments_craze as tc
    cap = {}
    orig = tc._load_module

    def spy(text, name):
        cap["text"] = text
        return orig(text, name)

    tc._load_module = spy
    try:
        tc.build_module()
    finally:
        tc._load_module = orig
    s = cap["text"]

    t1 = "    *,\n"
    assert s.count(t1) == 1, f"sig anchor: {s.count(t1)}"
    s = s.replace(t1, t1 + "    htf_bar_secs=3600, ltf_bar_secs=900,\n")

    # htf bar close instant: 2 sites (the live line + the comment stating the rule)
    a = "candle_ts_htf_close=[t+3600 for t in candle_ts_htf]"
    assert s.count(a) == 2, f"htf close anchor: {s.count(a)}"
    s = s.replace(a, "candle_ts_htf_close=[t+htf_bar_secs for t in candle_ts_htf]")

    # LTF bar close instant: 8 live bisect gates plus their comments.
    n900 = s.count("ts+900")
    assert n900 >= 8, f"ts+900 sites: {n900} (expected >= 8)"
    s = s.replace("ts+900", "ts+ltf_bar_secs")

    # NAME COLLISION, found the hard way. v18 already has a LOCAL `_win` holding a
    # list slice (`_win=_vol15[_lo:_vi]`) in its rolling-percentile loop. Naming the
    # window gate `_win` reassigns that list's name, and the gate then evaluates
    # `e + <list>` -> "unsupported operand type(s) for +: int and list". Use a name
    # that cannot collide, and ASSERT it is unused.
    assert "_knowwin" not in s, "patch variable _knowwin already exists in the engine"

    # SWEEP the C15 window gate; do not trust a grep. build_module() applies extra
    # patches on top of v18 and two more gate sites appear ONLY in that text:
    #     candle_ts_ltf[_k]<=e+2700
    #     int(_wb[0]) + 2700 < candle_ts[i] <= int(_wb[1]) + 2700
    # A line-based search of v18 alone misses them, which is how the earlier 2h runs
    # shipped a leak while looking carefully inspected. They also differ in SPACING
    # ("+2700" vs "+ 2700"), so sweeping on the operator alone catches only half -
    # sweep the bare literal.
    #
    # 2026-10-07 (C17): this count was 7 and is now 3. The window END no longer
    # carries a shift at all - it is stored knowable by _wend_settle in unified.py,
    # because the old end-side shift was reusing the START's offset and admitting
    # LTF entries on windows that were already closed (4 IS / 3 OOS on
    # fsent_champ_long). The four removed literals were end-side only: the two
    # engine gates plus the two gates test_experiments_craze.py injects, all
    # fixed the same way. Every literal that remains is a window START and must
    # move: the union gate, the main gate, and the injected window-budget gate.
    # 2026-10-10: the hardcoded gate moved into a parameter, `exp_window_floor_s`.
    # Its default is written 2_700 rather than 2700 so this count still sees only
    # the 3 live gate sites. That is not cosmetic: the count asserts there are
    # exactly 3 places to sweep for a 2h plane, and the signature is not one of
    # them - the default has to stay 2700 so every pinned 1h/15m book reproduces
    # byte-identically. Same value, different spelling, so the two jobs do not
    # fight.
    swept = s.count("2700")
    s = s.replace("2700", "_knowwin")
    assert s.count("2700") == 0, f"stray 2700 remains: {s.count('2700')}"
    assert swept == 3, f"expected 3 C15 window-START offsets, got {swept}"

    # define the gate once, immediately before its first use
    anchor = "    candle_ts_ltf=[int(c[\"ts\"]) for c in candles_ltf]"
    assert s.count(anchor) == 1, f"gate-definition anchor: {s.count(anchor)}"
    s = s.replace(anchor,
                  "    _knowwin = htf_bar_secs - ltf_bar_secs  # C15: HTF close - LTF close\n"
                  + anchor)

    # Per-process file name: exp_signal_metrics.py and exp_multi_metrics.py
    # were launched together once and both wrote this fixed path - the second
    # truncation landed mid-import of the first, which got a module with no
    # entrypoint (AttributeError: simulate_htf_ltf_streak_halt) and died. The
    # _*_tmp.py ignore rule covers _tffam_<pid>_tmp.py by shape, on purpose.
    p = ROOT / ("backtest/tests/_tffam_%d_tmp.py" % os.getpid())
    p.write_text(s, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("v18_tf_family", str(p))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert callable(m.simulate_htf_ltf_streak_halt), "patched entrypoint missing"
    return m.simulate_htf_ltf_streak_halt


def resample_30m(candles):
    """15m candle dicts -> 30m. Same convention as resample_2h; both legs required."""
    out = []
    for i in range(0, len(candles) - 1, 2):
        a, b = candles[i], candles[i + 1]
        if int(b["ts"]) - int(a["ts"]) != M15:      # not an adjacent pair
            continue
        out.append({"date": a["date"], "ts": int(a["ts"]),
                    "open": float(a["open"]),
                    "high": max(float(a["high"]), float(b["high"])),
                    "low": min(float(a["low"]), float(b["low"])),
                    "close": float(b["close"]),
                    "volume": float(a.get("volume") or 0.0) + float(b.get("volume") or 0.0)})
    return out


def load_scope(scope):
    from run_experiment import get_data
    from test_4_new_concepts import load_unseen, load_fine_1m
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        fine = load_fine_1m(c15[0]["ts"], c15[-1]["ts"])
    else:
        d = get_data()
        c15, f15, c1h, f1h, fine = d["c15"], d["f15"], d["c1h"], d["f1h"], d["fine"]
    return {"c15": c15, "f15": f15, "fine": fine, "c1h": c1h, "f1h": f1h}


def build_planes(raw):
    """Every (LTF candles, LTF swings-input, HTF candles, HTF swings-input) needed."""
    from exp_htf_2h import resample_2h, flow_2h
    from src.walker import FlowCandle
    c30 = resample_30m(raw["c15"])
    f30 = [FlowCandle(date=c["date"], open=c["open"], high=c["high"],
                       low=c["low"], close=c["close"]) for c in c30]
    c2h = resample_2h(raw["c1h"])
    f2h = flow_2h(c2h)
    return {"c15": raw["c15"], "f15": raw["f15"], "c30": c30, "f30": f30,
            "c1h": raw["c1h"], "f1h": raw["f1h"], "c2h": c2h, "f2h": f2h,
            "fine": raw["fine"], "n30": len(c30), "n2h": len(c2h)}


def main():
    t0 = time.time()
    print("=" * 108, flush=True)
    print("  TF family 2x2 - is 4:1 the ladder, or is the 15m/1h PAIR special?", flush=True)
    print("  window gate corrected to (htf_bar_secs - ltf_bar_secs); earlier 2h runs leaked", flush=True)
    print("=" * 108, flush=True)

    from exp_sizing_combo import run as sim_fn
    from exp_equity_quality import equity_quality
    from experiment_registry import BP, EXPERIMENTS
    from src.btc.btc_routes import _compute_swings

    sim = build_family_module()
    payload = {"stage": "tf_family",
               "question": "is the 4:1 ladder what matters, or the specific 15m/1h pair?",
               "bug_fixed": "C15 window gate was hard-coded 2700 (=3600-900); on 2h it must be "
                            "6300. Earlier 2h numbers ran with a 1h gate and are recomputed here.",
               "gate_formula": "htf_bar_secs - ltf_bar_secs",
               "cells": {}, "controls": {}}

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] ===", flush=True)
        pl = build_planes(load_scope(scope))
        print(f"  30m bars {pl['n30']} | 2h bars {pl['n2h']}", flush=True)
        for mblabel, mb15 in MB_VARIANTS:
            sw15 = _compute_swings(pl["f15"], "continuous", min_bars=mb15)
            sw30 = _compute_swings(pl["f30"], "continuous", min_bars=mb15)
            for cell, (ltf_s, htf_s) in CELLS.items():
                if ltf_s == M15:
                    ltf = {"c15": pl["c15"], "sw15": sw15}
                else:
                    ltf = {"c15": pl["c30"], "sw15": sw30}
                if htf_s == H1:
                    htf = {"c1h": pl["c1h"], "sw20": _compute_swings(
                        pl["f1h"], "continuous", min_bars=20),
                        "sw10": _compute_swings(pl["f1h"], "continuous", min_bars=10)}
                else:
                    htf = {"c1h": pl["c2h"], "sw20": _compute_swings(
                        pl["f2h"], "continuous", min_bars=20),
                        "sw10": _compute_swings(pl["f2h"], "continuous", min_bars=10)}
                books = {}
                for name, key in LANES:
                    params = {**BP, **EXPERIMENTS[key]["params"]}
                    # chop/garch/ent/detect are deliberately NOT passed. Their
                    # defaults (exp31_lb->14, garch 96, ent 96, detect 48) are
                    # the shipped values, and log 105 proved all four are
                    # NON-BINDING on trade selection: driving them to absurd
                    # values left the book at n=490 net=+53.8630 unchanged. So
                    # passing them would add no information and this harness
                    # stays focused on the one axis under test.
                    bk = sim_fn(sim, {**htf, **ltf, "fine": pl["fine"]}, params,
                                htf_bar_secs=htf_s, ltf_bar_secs=ltf_s)
                    m = equity_quality(bk, YEARS[scope])
                    books[name] = {"n": m["n"], "net": round(m["net"], 1),
                                    "max_dd": m["max_dd"], "pf": m["pf"]}
                key2 = f"{scope}/{mblabel}/{cell}"
                payload["cells"][key2] = {
                    "ltf_secs": ltf_s, "htf_secs": htf_s, "ladder": round(htf_s / ltf_s, 1),
                    "gate": htf_s - ltf_s, "mb15": mb15, "books": books}
                if cell == "F0_control_15m_1h" and mblabel == "mb50_count":
                    for name, _ in LANES:
                        en, ev = BYBIT_BASE[name][scope]
                        g = books[name]
                        assert g["n"] == en and abs(g["net"] - ev) < 0.5, (
                            f"CONTROL FAIL {scope}/{name}: {g['n']}/{g['net']} != {en}/{ev}")
                    payload["controls"][scope] = "EXACT - all 3 lanes reproduced"
                b = books
                print(f"  {mblabel:<12} {cell:<22} ladder={htf_s/ltf_s:>4.1f}:1 "
                      f"gate={htf_s-ltf_s:<5} champ {b['champion']['net']:>+7.1f} "
                      f"PF {b['champion']['pf']:>4.2f} | utcsat {b['utcsat']['net']:>+7.1f} "
                      f"PF {b['utcsat']['pf']:>4.2f} | age10 {b['age10']['net']:>+7.1f}", flush=True)
        print(f"  {'':<12} {'':<22} CONTROL: {payload['controls'][scope]}", flush=True)

    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print("\n" + "=" * 108)
    print("  controls:", payload["controls"], flush=True)
    print(f"wrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
