"""Shadow timeframes: 30m and 2h as EVIDENCE on the shipped 15m/1h book.

Pre-registered in docs/SHADOW_TIMEFRAME_IDEAS.md before this file existed. Read
that doc first - it fixes the arms, the hit criteria and the honesty limits.

WHAT THIS IS NOT
================
Not a plane change. The LTF stays 15m, the HTF stays 1h, min_bars stays 50, and
the control book must reproduce the published numbers exactly. 30m and 2h are
only used to LABEL entries that the shipped engine already produced.

CAUSALITY IS THE WHOLE GAME HERE
================================
Every label is computed from bars that had CLOSED at the entry instant
E = entry_ts + 900 (15m). For a bar of length B stamped t, it is closed at t+B,
so the newest usable bar is the largest t with t+B <= E. Off-by-one here would
silently peek at the future, which is the one failure mode this repo has
repeatedly paid for:

  * v18:269 `candle_ts_htf_close=[t+3600 ...]`  - hard-coded parent bar length
  * v18:539 `s + 2700` window gate                - = htf_secs - ltf_secs
  * log 104/105 shipped 2h numbers with the 1h gate still in place

The helper `last_closed()` below is the single place that arithmetic lives, and
it is unit-checked in main() before any result is reported.

WHAT PHASE 1 CAN AND CANNOT SAY
===============================
It reports COMPOSITION: which part of the existing book is worse. It cannot say
a filter helps, because removing a trade frees the slot and admits a replacement
- the wick work measured path-true skip at -39.0R IS where gray was +28.1R. Any
survivor of Phase 1 must be re-run in-engine gray-vs-skip before it counts.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_shadow_tf.py
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

OUT = ROOT / "live_stuff/tests/_shadow_tf.json"
M15, M30, H1, H2 = 900, 1800, 3600, 7200
ENTRY_OFFSET = M15          # entry instant = ltf bar ts + 900
BYBIT_BASE = {"champion": {"is": (500, 325.8), "oos": (279, 70.2)},
              "utcsat": {"is": (454, 358.9), "oos": (253, 60.2)},
              "age10": {"is": (130, 435.7), "oos": (76, 43.2)}}
YEARS = {"is": 3.67, "oos": 2.0}
LANES = (("champion", "champion_multi_sw10"),
         ("utcsat", "utcsat_multi_sw10"),
         ("age10", "age10_dirmatch_swingpause_single_sw10"))


def last_closed(ts_sorted, close_ts_sorted, instant):
    """Index of the newest bar whose CLOSE time is <= instant, else -1.

    This is the only place the causality arithmetic lives. `instant` is the
    moment the 15m entry becomes knowable, i.e. entry_ts + 900.
    """
    lo, hi, ans = 0, len(close_ts_sorted) - 1, -1
    while lo <= hi:
        mid = (lo + hi) // 2
        if close_ts_sorted[mid] <= instant:
            ans, lo = mid, mid + 1
        else:
            hi = mid - 1
    return ans


def dir_series(candles, bar_secs):
    """Per-bar direction (1 long / -1 short / 0 flat) with CLOSE timestamps.

    Direction is the sign of close-open for that bar: unambiguous, needs no
    lookback, and therefore cannot itself introduce a lag or a peek.
    """
    ts = [int(c["ts"]) for c in candles]
    closes = [t + bar_secs for t in ts]
    d = []
    for c in candles:
        o, cl = float(c["open"]), float(c["close"])
        d.append(1 if cl > o else (-1 if cl < o else 0))
    return ts, closes, d


def swing_dir_series(swings):
    """Forward-filled swing direction over time, from the engine's own swings."""
    ev = []
    for s in swings:
        t = s.get("ts", s.get("time", s.get("index")))
        d = s.get("dir", s.get("direction"))
        if t is not None and d is not None:
            ev.append((int(t), 1 if str(d).lower() in ("long", "up", "1", "bull")
                       else -1))
    ev.sort()
    return ev
# END_MARKER


# ---------------------------------------------------------------- swing lookup
def htf_swing_events(c1h, swings):
    """(close_time, dir) for each swing, using the CONFIRMATION bar's close.

    A swing is only knowable once confirmed, so the causally-valid stamp is
    c1h[confirmed_at_idx].ts + 3600 - never seg.start_idx, which is backdated
    and would leak. Verified: c1h[confirmed_at_idx]['date'] ==
    confirmed_at_time on 300/300 sampled swings.
    """
    ev = []
    for s in swings:
        i, d = s.get("confirmed_at_idx"), s.get("dir")
        if i is None or d is None or i >= len(c1h):
            continue
        ev.append((int(c1h[i]["ts"]) + H1, 1 if d == "up" else -1))
    ev.sort()
    return ev


def swing_dir_at(events, instant):
    """Direction of the most recently CONFIRMED swing as of `instant`."""
    lo, hi, ans = 0, len(events) - 1, 0
    while lo <= hi:
        mid = (lo + hi) // 2
        if events[mid][0] <= instant:
            ans, lo = events[mid][1], mid + 1
        else:
            hi = mid - 1
    return ans


def tdir(trade):
    """Trade direction as +1/-1. The books carry 'long'/'short' strings, but other
    harnesses in this repo emit ints, so accept both rather than assume."""
    d = trade.get("dir")
    if isinstance(d, str):
        return 1 if d.strip().lower() in ("long", "up", "bull", "buy", "1") else -1
    return 1 if int(d) > 0 else -1


def label_trade(trade, d30, d2h, sw1h, d30_leg1, broke_prior):
    """Attach S1-S4 labels. Every input is causal by construction."""
    td = tdir(trade)
    a30 = 1 if d30 == td else 0
    a2h = 1 if d2h == td else 0
    return {
        "S1_30m_agrees": a30,
        "S2a_leg1_agrees": (1 if d30_leg1 == td else 0) if d30_leg1 else None,
        "S2b_leg1_broke_prior": (1 if broke_prior else 0) if broke_prior is not None else None,
        "S3_2h_agrees": a2h,
        "S4_stack": 1 + a30 + a2h,
        "swing1h_agrees": (1 if sw1h == td else 0) if sw1h else None,
    }


def bucket_stats(trades, rs, key, want):
    """n / net / avgR / win-rate for trades whose label[key] == want."""
    sel = [(t, r) for t, r in zip(trades, rs) if t.get(key) == want]
    if not sel:
        return {"n": 0, "net": 0.0, "avg_r": 0.0, "wr": 0.0}
    net = sum(r for _, r in sel)
    n = len(sel)
    return {"n": n, "net": round(net, 1), "avg_r": round(net / n, 4),
            "wr": round(100.0 * sum(1 for _, r in sel if r > 0) / n, 1)}


# ---------------------------------------------------------------- small helpers
def _flow(candles):
    from src.walker import FlowCandle
    return [FlowCandle(date=c["date"], open=c["open"], high=c["high"],
                       low=c["low"], close=c["close"]) for c in candles]


def _bar_index(candles, instant):
    """Index of the 1h bar CONTAINING `instant` (i.e. the still-forming one)."""
    ts = [int(c["ts"]) for c in candles]
    i = -1
    for k, t in enumerate(ts):
        if t <= instant:
            i = k
        else:
            break
    return i if i >= 0 else None


def _prior_swing_px(c1h, swings, before_idx):
    """End price of the most recent swing confirmed strictly before `before_idx`.

    This is the level the forming bar would have to break to make S2b fire.
    Confirmation is required (not start) so the level is genuinely known.
    """
    best = None
    for s in swings:
        i = s.get("confirmed_at_idx")
        seg = s.get("seg") or {}
        if i is None or i is None or i >= before_idx:
            continue
        px = seg.get("end_px")
        if px is None:
            continue
        if best is None or i > best[0]:
            best = (i, float(px), 1 if s.get("dir") == "up" else -1)
    return best[1] if best else None


def _boot(trades, rs, key, n_boot=20000, seed=20260927):
    """Bootstrap avgR(agrees) - avgR(opposes), resampling each side's trades."""
    import random
    a = [r for t, r in zip(trades, rs) if t.get(key) == 1]
    b = [r for t, r in zip(trades, rs) if t.get(key) == 0]
    if len(a) < 20 or len(b) < 20:
        return {"diff": None, "ci95": None, "p_two_sided": None,
                "n_agrees": len(a), "n_opposes": len(b)}
    rng = random.Random(seed)
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    diffs = []
    for _ in range(n_boot):
        sa = sum(a[rng.randrange(len(a))] for _ in range(len(a))) / len(a)
        sb = sum(b[rng.randrange(len(b))] for _ in range(len(b))) / len(b)
        diffs.append(sa - sb)
    diffs.sort()
    pl = sum(1 for x in diffs if x <= 0) / n_boot
    pg = sum(1 for x in diffs if x >= 0) / n_boot
    return {"diff": round(ma - mb, 4),
            "ci95": [round(diffs[int(0.025 * n_boot)], 4),
                     round(diffs[int(0.975 * n_boot)], 4)],
            "p_two_sided": round(min(1.0, 2.0 * min(pl, pg)), 4),
            "n_agrees": len(a), "n_opposes": len(b), "n_boot": n_boot}




def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  Shadow timeframes - 30m / 2h as EVIDENCE on the shipped 15m/1h book", flush=True)
    print("  Phase 1 = COMPOSITION only. See docs/SHADOW_TIMEFRAME_IDEAS.md", flush=True)
    print("=" * 100, flush=True)
    selftest()

    from exp_sizing_combo import run as sim_fn
    from run_experiment import get_data, net_r
    from test_4_new_concepts import load_unseen, load_fine_1m
    from experiment_registry import BP, EXPERIMENTS
    from exp_tf_family import build_family_module, resample_30m
    from exp_htf_2h import resample_2h, flow_2h
    from src.btc.btc_routes import _compute_swings
    from engine.v18_params import SWING

    sim = build_family_module()
    payload = {"stage": "shadow_tf", "phase": 1,
               "note": "composition only - removing a trade is not gating it "
                       "(wick work: path-true skip -39.0R IS vs gray +28.1R)",
               "baseline": "raw shipped 15m/1h book, NOT the wick gate",
               "cells": {}}

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] ===", flush=True)
        if scope == "is":
            d = get_data()
            c15, c1h, f15 = d["c15"], d["c1h"], d["f15"]
            fine, sw10, sw15 = d["fine"], d["sw10"], d["sw15"]
        else:
            (c15, f15), (c1h, _) = load_unseen("15m"), load_unseen("1h")
            fine = load_fine_1m(c15[0]["ts"], c15[-1]["ts"])
            sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
            sw10 = _compute_swings(_flow(c1h), "continuous", min_bars=10)
        c30, c2h = resample_30m(c15), resample_2h(c1h)
        t30, cl30, d30 = dir_series(c30, M30)
        t2h, cl2h, d2h = dir_series(c2h, H2)
        ev1h = htf_swing_events(c1h, sw10)
        ev2h = htf_swing_events(c2h, _compute_swings(flow_2h(c2h), "continuous",
                                                      min_bars=5))
        print(f"  30m {len(c30)} | 2h {len(c2h)} | 1h swings {len(ev1h)} | "
              f"2h swings {len(ev2h)}", flush=True)

        htf = {"c1h": c1h, "sw20": _compute_swings(_flow(c1h), "continuous", min_bars=20),
               "sw10": sw10}
        ltf = {"c15": c15, "sw15": sw15}
        c1h_ts = [int(c["ts"]) for c in c1h]
        for lane, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            trades = sim_fn(sim, {**htf, **ltf, "fine": fine}, params)
            rs = [net_r([t]) for t in trades]
            en, ev_ = BYBIT_BASE[lane][scope]
            assert len(trades) == en and abs(sum(rs) - ev_) < 0.5, \
                f"CONTROL FAIL {scope}/{lane}: {len(trades)}/{sum(rs):.1f} != {en}/{ev_}"
            for t in trades:
                e = int(t["entry_ts"]) + ENTRY_OFFSET
                i30, i2h = last_closed(t30, cl30, e), last_closed(t2h, cl2h, e)
                leg1, broke = 0, None
                bi = _bar_index(c1h, e)
                if bi is not None and i30 >= 0 and t30[i30] == c1h_ts[bi]:
                    leg1 = d30[i30]
                    lvl = _prior_swing_px(c1h, sw10, bi)
                    if lvl is not None:
                        broke = (float(c30[i30]["high"]) > lvl if tdir(t) > 0
                                 else float(c30[i30]["low"]) < lvl)
                t.update(label_trade(t, d30[i30] if i30 >= 0 else 0,
                                     d2h[i2h] if i2h >= 0 else 0,
                                     swing_dir_at(ev1h, e), leg1, broke))
            cell = {"control": {"n": len(trades), "net": round(sum(rs), 1)},
                    "S1": {"agrees": bucket_stats(trades, rs, "S1_30m_agrees", 1),
                           "opposes": bucket_stats(trades, rs, "S1_30m_agrees", 0)},
                    "S3": {"agrees": bucket_stats(trades, rs, "S3_2h_agrees", 1),
                           "opposes": bucket_stats(trades, rs, "S3_2h_agrees", 0)},
                    "S4": {f"stack{k}": bucket_stats(trades, rs, "S4_stack", k)
                           for k in (1, 2, 3)},
                    "S1_boot": _boot(trades, rs, "S1_30m_agrees"),
                    "S3_boot": _boot(trades, rs, "S3_2h_agrees")}
            payload["cells"][f"{scope}/{lane}"] = cell
            b1, c1 = cell["S1"]["agrees"], cell["S1"]["opposes"]
            b3, c3 = cell["S3"]["agrees"], cell["S3"]["opposes"]
            print(f"  {lane:<9} ctrl n={len(trades):>3} net={sum(rs):>+7.1f} [EXACT]", flush=True)
            print(f"     S1 30m agree n={b1['n']:>3} avgR={b1['avg_r']:>+5.2f} | "
                  f"oppose n={c1['n']:>3} avgR={c1['avg_r']:>+5.2f} | diff "
                  f"{cell['S1_boot']['diff']} CI {cell['S1_boot']['ci95']} "
                  f"p={cell['S1_boot']['p_two_sided']}", flush=True)
            print(f"     S3 2h  agree n={b3['n']:>3} avgR={b3['avg_r']:>+5.2f} | "
                  f"oppose n={c3['n']:>3} avgR={c3['avg_r']:>+5.2f} | diff "
                  f"{cell['S3_boot']['diff']} CI {cell['S3_boot']['ci95']} "
                  f"p={cell['S3_boot']['p_two_sided']}", flush=True)
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


def selftest():
    """Prove the causality arithmetic BEFORE trusting any label it produces.

    A 30m bar stamped t closes at t+1800. An entry knowable at E may use it iff
    t+1800 <= E. Off by one here and the whole experiment silently peeks at the
    future, which is the exact failure this repo has paid for three times
    (v18:269 hard-coded parent bar length, v18:539 window gate, log 104's 2h
    numbers computed with a 1h gate). So the helper is checked, not trusted.
    """
    ts = [0, 1800, 3600, 5400, 7200]
    closes = [t + M30 for t in ts]
    assert last_closed(ts, closes, 1700) == -1, "used a bar that has not closed"
    assert last_closed(ts, closes, 1800) == 0, "boundary: close==instant must count"
    assert last_closed(ts, closes, 3599) == 0, "used the not-yet-closed leg"
    assert last_closed(ts, closes, 3600) == 1, "boundary wrong"
    assert last_closed(ts, closes, 10 ** 9) == len(ts) - 1, "tail wrong"
    assert last_closed([], [], 5) == -1, "empty input must not crash"
    print("  causality self-test: PASS (5 boundary cases + empty)", flush=True)


if __name__ == "__main__":
    main()
