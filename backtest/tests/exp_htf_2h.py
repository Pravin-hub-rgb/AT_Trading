"""HTF PLANE 1h -> 2h - structural test of the timeframe, not a sizing flag.

WHY THIS IS A DIFFERENT KIND OF EXPERIMENT
==========================================
Everything so far in this programme varied WHAT is traded (a flag) or HOW MUCH
(position size). Nothing has varied the *plane* the strategy reasons on. The
whole engine reasons on a 1h parent chain: regime, chop, the sw10 window chain,
the 16-day window, the htf trails. Shifting that plane to 2h is a structural
question - "is 1h the right parent timeframe at all" - and it has never been
tested.

DATA (checked on disk, not assumed)
----------------------------------
There is no 2h CSV anywhere in data/. bybit ships 15m/1h/1m/4h/5m. But 2h is
exactly 2 x 1h, so it resamples losslessly:
  bybit 1h = 32,434 rows (2023-01-01 00:30 -> 2026-09-13 09:30)
  -> 16,217 complete 2h buckets, ZERO partial.
No fetching, no interpolation, no approximation.

THE CRITICAL FINDING BEFORE WRITING ANY OF IT
============================================
The shipped engine hard-codes 1h arithmetic in SEVEN places, and one of them
is load-bearing for causality:

  v18:269  candle_ts_htf_close=[t+3600 for t in candle_ts_htf]
  v18:272  j=bisect_right(candle_ts_htf_close, ts+900)-1     (and 5 more)

`candle_ts_htf_close` is how the engine decides "this 1h bar has CLOSED, so I
may read its regime/chop". If we feed 2h candles while that list still says
t+3600, every 2h bar would be treated as closed 3600s early - i.e. the engine
would read a 2h bar's high/low/close one hour before it actually closed. That
is a LOOKAHEAD LEAK, not a subtle bias. So the plane shift is only valid if
this constant moves to 7200, and the run is void otherwise.

This is why the plane shift cannot be done as a data swap in a harness: it
requires patching the engine's time arithmetic, not just its inputs.

PRE-REGISTERED BEFORE THE RUN (2026-09-27)
------------------------------------------
  ARMS: htf_1h (control, must reproduce 24.85 exactly) and htf_2h.
  Lanes: champion / utcsat / age10, IS + OOS. LTF 15m and fine 1m UNCHANGED -
  only the parent plane moves.
  Engine patch: 3600 -> 7200 in the htf close-time list ONLY. The `ts+900`
  (LTF 15m close) and the 2700 (window bounds) constants are LTF-side and stay.
  Identity gate: the patched engine with 2h input OFF (i.e. 1h input) must
  reproduce the shipped 1h books exactly. If the patch leaks or breaks, abort.
  The 2h arm is measured, not gated: the question is "is 2h better or worse",
  so there is no 6/6 rule. Reported per cell: n, net, maxDD, PF, WR, and the
  OOS/IS retention the MASTER_LEADERBOARD already scores on.
  Nothing adopted. No production file edited - runtime patch only.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_htf_2h.py
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

OUT = ROOT / "backtest/tests/_htf_2h.json"
H1 = 3600
H2 = 7200

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


def resample_2h(candles):
    """Exact 2h resample of 1h candles -> a parallel list of 2h candle dicts.

    o = first 1h open, h = max high, l = min low, c = last 1h close,
    volume = sum. Bucket boundaries are on the epoch grid so they line up with
    the 15m LTF grid; a bucket is kept only if it has both 1h legs, otherwise
    the last bar would be a half-formed 2h candle.

    NOTE: this returns DICTS. The engine wants candle dicts (with "date"/"ts"),
    but _compute_swings wants FlowCandle objects - see flow_2h() for that.
    """
    if not candles:
        return []
    out = []
    cur = None
    for c in candles:
        bucket = (int(c["ts"]) // H2) * H2
        if cur is None or cur["_b"] != bucket:
            if cur is not None and cur["_n"] == 2:
                out.append(cur)
            cur = {"_b": bucket, "_n": 0, "date": c["date"],
                   "ts": bucket, "open": float(c["open"]), "high": float(c["high"]),
                   "low": float(c["low"]), "close": float(c["close"]),
                   "volume": 0.0}
        else:
            cur["high"] = max(cur["high"], float(c["high"]))
            cur["low"] = min(cur["low"], float(c["low"]))
            cur["close"] = float(c["close"])
        cur["_n"] += 1
        cur["volume"] += float(c.get("volume") or 0.0)
    if cur is not None and cur["_n"] == 2:
        out.append(cur)
    for c in out:
        c.pop("_b", None)
        c.pop("_n", None)
    return out


def flow_2h(candles_2h):
    """2h candle dicts -> FlowCandle objects, which _compute_swings consumes."""
    from src.walker import FlowCandle
    return [FlowCandle(date=c["date"], open=c["open"], high=c["high"],
                       low=c["low"], close=c["close"])
            for c in candles_2h]


def build_htf2h_module():
    """Engine with the htf bar-close constant made 2h-aware.

    Only `candle_ts_htf_close=[t+3600 ...]` moves to 7200. That list is the
    causality gate: it decides which parent bar has CLOSED and may therefore be
    read. Leaving it at 3600 while feeding 2h candles would let the engine read
    a 2h bar one hour before it closed.
    """
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
    assert s.count(t1) == 1, "sig"
    s = s.replace(t1, t1 + "    htf_bar_secs=3600,\n")

    a = "candle_ts_htf_close=[t+3600 for t in candle_ts_htf]"
    # TWO occurrences on purpose: one is the live line, one is the comment above
    # it that states the causality rule. Both must say the new constant or the
    # code and its own documentation would disagree.
    assert s.count(a) == 2, f"htf close anchor: {s.count(a)}"
    s = s.replace(a, "candle_ts_htf_close=[t+htf_bar_secs for t in candle_ts_htf]")

    import importlib.util
    p = ROOT / "backtest/tests/_htf2h_tmp.py"
    p.write_text(s, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("v18_htf2h", str(p))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert callable(m.simulate_htf_ltf_streak_halt), "patched entrypoint missing"
    return m.simulate_htf_ltf_streak_halt


def data_for_2h(scope):
    """LTF 15m + fine 1m unchanged; HTF replaced by 2h. Returns (d1h, d2h, ltf)."""
    from run_experiment import get_data
    from test_4_new_concepts import load_unseen, load_fine_1m
    from engine.v18_params import SWING
    from src.btc.btc_routes import _compute_swings

    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        fine = load_fine_1m(c15[0]["ts"], c15[-1]["ts"])
    else:
        d = get_data()
        c15, f15, c1h, f1h, fine = d["c15"], d["f15"], d["c1h"], d["f1h"], d["fine"]

    MB15 = SWING["min_bars_15m"]
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    c2h = resample_2h(c1h)
    flow = flow_2h(c2h)  # swings consume FlowCandle, not dicts
    # swings on the SAME min_bars as 1h (20 and 10) but over 2h bars: a
    # "swing" spans twice the clock hours. That is the honest plane test.
    sw20_2h = _compute_swings(flow, "continuous", min_bars=SWING["min_bars_1h"])
    sw10_2h = _compute_swings(flow, "continuous", min_bars=10)
    base = {"c15": c15, "sw15": sw15, "fine": fine}
    d1h = {"c1h": c1h,
           "sw20": _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"]),
           "sw10": _compute_swings(f1h, "continuous", min_bars=10)}
    return d1h, base, {"c1h": c2h, "sw20": sw20_2h, "sw10": sw10_2h}, len(c2h)


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  HTF 2h - structural test of the parent timeframe", flush=True)
    print("=" * 100, flush=True)

    from exp_sizing_combo import run as sim_fn
    from exp_equity_quality import equity_quality
    from experiment_registry import BP, EXPERIMENTS
    from run_experiment import net_r

    sim2h = build_htf2h_module()
    payload = {"stage": "htf_2h",
               "lens": "LTF 15m + fine 1m UNCHANGED; only the HTF parent plane moves 1h -> 2h",
               "resample": "exact, 2x1h, incomplete buckets dropped",
               "engine_patch": "candle_ts_htf_close t+3600 -> t+htf_bar_secs (7200 for 2h)",
               "pre_registered": {
                   "control": "1h arm must reproduce 24.85 exactly",
                   "no_gate": "measured not gated - is 2h better or worse",
                   "adopt": "nothing adopted"},
               "cells": {}, "bars": {}}

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] ===", flush=True)
        d1h, ltf, d2h, n2h = data_for_2h(scope)
        payload["bars"][scope] = {"n_2h_bars": n2h}
        print(f"  2h bars: {n2h}", flush=True)
        for name, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            # control: 1h
            b1 = sim_fn(sim2h, {**d1h, **ltf}, params)
            m1 = equity_quality(b1, YEARS[scope])
            exp_n, exp_net = BYBIT_BASE[name][scope]
            assert m1["n"] == exp_n and abs(m1["net"] - exp_net) < 0.5, (
                f"CONTROL FAIL {scope}/{name}: {m1['n']}/{m1['net']:.2f} "
                f"!= {exp_n}/{exp_net}")
            # 2h arm
            b2 = sim_fn(sim2h, {**d2h, **ltf}, params, htf_bar_secs=H2)
            m2 = equity_quality(b2, YEARS[scope])
            cell = {
                "h1": {"n": m1["n"], "net": round(m1["net"], 1),
                       "max_dd": m1["max_dd"], "pf": m1["pf"], "wr": m1["wr"]},
                "h2": {"n": m2["n"], "net": round(m2["net"], 1),
                       "max_dd": m2["max_dd"], "pf": m2["pf"], "wr": m2["wr"]},
            }
            payload["cells"][f"{scope}/{name}"] = cell
            print(f"  {scope}/{name} [ctrl 1h OK]  "
                  f"1h: n={m1['n']:>3} net={m1['net']:>+7.1f} DD={m1['max_dd']:>5.1f} "
                  f"PF={m1['pf']:>4.2f} | "
                  f"2h: n={m2['n']:>3} net={m2['net']:>+7.1f} DD={m2['max_dd']:>5.1f} "
                  f"PF={m2['pf']:>4.2f}", flush=True)

    payload["verdicts"] = {
        "twoh_beats_on_net": sum(1 for c in payload["cells"].values()
                                 if c["h2"]["net"] > c["h1"]["net"]),
        "cells": len(payload["cells"]),
        "twoh_trade_count_change": {k: c["h2"]["n"] - c["h1"]["n"]
                                    for k, c in payload["cells"].items()},
    }
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print("\n" + "=" * 100, flush=True)
    print("  2h beats 1h on net in "
          f"{payload['verdicts']['twoh_beats_on_net']}/{len(payload['cells'])} cells",
          flush=True)
    print("  trade-count change: "
          f"{payload['verdicts']['twoh_trade_count_change']}", flush=True)
    print("=" * 100, flush=True)
    print(f"wrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
