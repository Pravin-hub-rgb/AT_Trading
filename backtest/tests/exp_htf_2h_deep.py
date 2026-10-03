"""HTF PLANE - 5-arm deep experiment. Duration vs resolution, separated.

WHY THIS EXISTS
===============
`exp_htf_2h.py` moved the parent plane 1h -> 2h but held every bar-count
constant in BARS. On 2h bars that silently doubled six lookbacks at once:

  constant          bars   1h clock   2h clock (what that run actually did)
  sw20 min_bars      20      20h          40h
  sw10 min_bars      10      10h          20h
  chop lb            14      14h          28h
  garch regime lb    96       4d           8d
  entry stat lb      96       4d           8d
  detect lb          48       2d           4d
  16-day cap          -      16d          16d   (time-based, correctly unchanged)

So "2h lost 6/6" conflated two very different claims:
  (a) 2h RESOLUTION is too coarse, and
  (b) doubled LOOKBACK duration is what actually did the damage.
Those have opposite implications and this experiment separates them.

THE ARMS (pre-registered before the run)
========================================
  C0  1h  full      control - must reproduce the published books EXACTLY
  A1  1h  half      the duration lever ON THE 1H PLANE. If halving hurts here,
                    the original 0/6 was never about 2h at all.
  B0  2h  full      the earlier 0/6 result, re-run through this same code path
  A2  2h  half      DURATION-MATCHED 2h - halves every bar-count, restoring
                    the 1h clock durations. This is the real question.
  A3  2h  half swings only, features full - isolates whether swing duration or
                    the chop/garch feature lookbacks is the dominant term.

Halving restores the 1h clock duration AND preserves the HTF:LTF swing-duration
ratio (1h sw20 20h vs LTF 12.5h = 1.6x), which is presumably what makes the
shipped system coherent. Note A1 breaks that ratio deliberately: 10h vs 12.5h
= 0.8x, i.e. the parent swing becomes SHORTER than the LTF swing. That
inversion is itself one of the things being measured.

CAUSALITY (unchanged and still mandatory)
========================================
v18:269 `candle_ts_htf_close=[t+3600 ...]` is the gate deciding which parent bar
has CLOSED. A 2h plane without moving it to 7200 reads every 2h bar one hour
early - a lookahead leak. `htf_bar_secs` carries that fix.

PRE-REGISTERED READING (fixed now, before running)
=================================================
  A2 ~ C0  -> resolution incidental, lookback DURATION is the driver. 1h still
              ships; the belief and the wording of the 0/6 claim both change.
  A2 << C0 -> resolution genuinely load-bearing. 1h confirmed more strongly.
  A1 << C0 -> the duration lever alone is destructive; 0/6 is re-attributed.
  A3 ~ A2 >> A1 -> swings dominate; chop/garch are incidental.

ADOPTION: none, in any arm. The shipped engine stays 1h / min_bars 20. This is
diagnostic only. age10 is reported separately per house convention.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_htf_2h_deep.py
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

OUT = ROOT / "backtest/tests/_htf_2h_deep.json"
H1, H2 = 3600, 7200
LTF_SWING_H = 50 * 15 / 60.0           # min_bars_15m=50 -> 750 min -> 12.5 clock hours

# arm -> plane_secs, (sw20, sw10, chop, garch, ent, detect)
ARMS = {
    "C0_1h_full": (H1, (20, 10, 14, 96, 96, 48)),
    "A1_1h_half": (H1, (10, 5, 7, 48, 48, 24)),
    "B0_2h_full": (H2, (20, 10, 14, 96, 96, 48)),
    "A2_2h_half": (H2, (10, 5, 7, 48, 48, 24)),
    "A3_2h_swhalf_featfull": (H2, (10, 5, 14, 96, 96, 48)),
}

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


def build_deep_module():
    """Engine with all five HTF lookbacks exposed as parameters.

    Patch surface (anchor counts asserted at build time, never assumed):
      candle_ts_htf_close=[t+3600 ...]  -> t+htf_bar_secs   (2 occurrences:
                                               one is live code, one is the
                                               comment stating the rule; both
                                               must move or code and docs
                                               disagree)
      _chop_series_1h(candles_htf, lb=14) -> lb=chop_lb
      _garch_regime_1h(candles_htf)       -> , garch_lb=garch_lb
      _ent_lb=96                          -> _ent_lb=ent_lb
      _fd_lb=48                           -> _fd_lb=fd_lb
    The 16-day cap is time-based and deliberately untouched.
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
    s = s.replace(t1, t1 + "    htf_bar_secs=3600, garch_lb=96, ent_lb=96, fd_lb=48,\n")

    # chop needs NO patch: the engine already exposes exp31_lb and calls
    #   _chop_series_1h(candles_htf, lb=(exp31_lb or 14))
    # so the default 14 is the `exp31_lb or 14` fallback, and passing
    # exp31_lb=7 genuinely moves it. Reusing the shipped knob is safer than
    # inventing a parallel one.
    for anchor, repl, want in (
            ("candle_ts_htf_close=[t+3600 for t in candle_ts_htf]",
             "candle_ts_htf_close=[t+htf_bar_secs for t in candle_ts_htf]", 2),
            ("_garch_regime_1h(candles_htf)",
             "_garch_regime_1h(candles_htf, lb=garch_lb)", 1),
            ("    _ent_lb=96", "    _ent_lb=ent_lb", 1),
            ("    _fd_lb=48", "    _fd_lb=fd_lb", 1)):
        assert s.count(anchor) == want, f"anchor {anchor!r}: {s.count(anchor)} != {want}"
        s = s.replace(anchor, repl)

    p = ROOT / "backtest/tests/_htf2hdeep_tmp.py"
    p.write_text(s, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("v18_htf2h_deep", str(p))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert callable(m.simulate_htf_ltf_streak_halt), "patched entrypoint missing"
    return m.simulate_htf_ltf_streak_halt


def load_scope(scope):
    """15m + fine 1m (shared, never varied) and the 1h parent candles."""
    from run_experiment import get_data
    from test_4_new_concepts import load_unseen, load_fine_1m
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        fine = load_fine_1m(c15[0]["ts"], c15[-1]["ts"])
    else:
        d = get_data()
        c15, f15, c1h, f1h, fine = d["c15"], d["f15"], d["c1h"], d["f1h"], d["fine"]
    return {"c15": c15, "f15": f15, "fine": fine, "c1h": c1h, "f1h": f1h}


def parent(raw, plane_secs, sw20, sw10):
    """Parent candles + swings for one arm (swings computed per arm min_bars)."""
    from src.btc.btc_routes import _compute_swings
    from exp_htf_2h import resample_2h, flow_2h
    if plane_secs == H1:
        candles, flow = raw["c1h"], raw["f1h"]
    else:
        candles = resample_2h(raw["c1h"])
        flow = flow_2h(candles)
    return {"c1h": candles,
            "sw20": _compute_swings(flow, "continuous", min_bars=sw20),
            "sw10": _compute_swings(flow, "continuous", min_bars=sw10)}



def main():
    t0 = time.time()
    print("=" * 104, flush=True)
    print("  HTF deep - 5 arms: duration vs resolution, separated", flush=True)
    print("=" * 104, flush=True)

    from exp_sizing_combo import run as sim_fn
    from exp_equity_quality import equity_quality
    from experiment_registry import BP, EXPERIMENTS

    sim = build_deep_module()
    payload = {"stage": "htf_2h_deep",
               "question": "is the 1h edge lost to bar RESOLUTION or to doubled lookback DURATION?",
               "ltf_unchanged": "15m candles, 1m fine data, min_bars_15m=50 - never varied",
               "cache": {}, "arms": {}, "controls": {}}

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] ===", flush=True)
        raw = load_scope(scope)
        from engine.v18_params import SWING
        from src.btc.btc_routes import _compute_swings
        sw15 = _compute_swings(raw["f15"], "continuous", min_bars=SWING["min_bars_15m"])
        ltf = {"c15": raw["c15"], "sw15": sw15, "fine": raw["fine"]}

        for arm, (plane, kb) in ARMS.items():
            sw20, sw10, chop, garch, ent, fd = kb
            htf = parent(raw, plane, sw20, sw10)
            bar_h = plane / 3600.0
            cells = {}
            for name, key in LANES:
                params = {**BP, **EXPERIMENTS[key]["params"]}
                book = sim_fn(sim, {**htf, **ltf}, params, htf_bar_secs=plane,
                              exp31_lb=chop, garch_lb=garch, ent_lb=ent, fd_lb=fd)
                m = equity_quality(book, YEARS[scope])
                cells[name] = {"n": m["n"], "net": round(m["net"], 1),
                               "max_dd": m["max_dd"], "pf": m["pf"], "wr": m["wr"]}
            ratio = round((sw20 * bar_h) / LTF_SWING_H, 2)
            payload["arms"].setdefault(arm, {})[scope] = {
                "plane_h": bar_h, "bars": {"sw20": sw20, "sw10": sw10, "chop": chop,
                                           "garch": garch, "ent": ent, "detect": fd},
                "htf_swing_h": sw20 * bar_h, "htf_ltf_ratio": ratio, "cells": cells}
            if arm == "C0_1h_full":                       # identity gate
                for name, _ in LANES:
                    en, ev = BYBIT_BASE[name][scope]
                    got = cells[name]
                    assert got["n"] == en and abs(got["net"] - ev) < 0.5, (
                        f"CONTROL FAIL {scope}/{name}: {got['n']}/{got['net']} != {en}/{ev}")
                payload["controls"][scope] = "EXACT - all 3 lanes reproduced"
            cc = cells
            print(f"  {arm:<24} ratio={ratio:<5} "
                  f"champ {cc['champion']['net']:>+7.1f} (PF {cc['champion']['pf']:.2f}) | "
                  f"utcsat {cc['utcsat']['net']:>+7.1f} (PF {cc['utcsat']['pf']:.2f}) | "
                  f"age10 {cc['age10']['net']:>+7.1f}", flush=True)
        print(f"  {'':<24} (C0 identity gate: {payload['controls'][scope]})", flush=True)

    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print("\n" + "=" * 104, flush=True)
    print("  arms:", ", ".join(ARMS), flush=True)
    print("  controls:", payload["controls"], flush=True)
    print(f"wrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()

