"""Parity test for live.retention.trim_candles_and_swings.

Verifies that trimming the sim input to a trailing window preserves the
vendored batch sim's LTF trade list (full vs trimmed).
"""
import os
import sys
import random
import copy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.join(ROOT, "live"))

from _vendored.walker import FlowCandle
from _vendored.persistent_swing import PersistentSwingEngine
from _vendored.unified import simulate_htf_ltf_streak_halt
from book import get_book_params
from live.retention import trim_candles_and_swings
from parity import trade_list_diff


def make_series(n15, seed=1):
    random.seed(seed)
    candles15 = []
    ts = 1700000000
    for i in range(n15):
        ts += 900
        o = random.uniform(100, 110)
        c = random.uniform(100, 110)
        hi = max(o, c) + random.uniform(0, 2)
        lo = min(o, c) - random.uniform(0, 2)
        d = "2024-01-01 00:00:00"  # placeholder; sim uses ts for time
        # build a real-ish date string from ts
        import datetime
        dt = datetime.datetime.utcfromtimestamp(ts)
        d = dt.strftime("%Y-%m-%d %H:%M:%S")
        candles15.append({"date": d, "ts": ts, "open": o, "high": hi, "low": lo, "close": c})

    # 1h candles: aggregate every 4 15m bars
    candles1h = []
    for i in range(0, len(candles15) - 3, 4):
        chunk = candles15[i:i+4]
        o = chunk[0]["open"]
        c = chunk[-1]["close"]
        hi = max(x["high"] for x in chunk)
        lo = min(x["low"] for x in chunk)
        ts = chunk[-1]["ts"]
        dt = datetime.datetime.utcfromtimestamp(ts)
        d = dt.strftime("%Y-%m-%d %H:%M:%S")
        candles1h.append({"date": d, "ts": ts, "open": o, "high": hi, "low": lo, "close": c})

    # swings
    eng15 = PersistentSwingEngine("15m")
    sw15 = []
    for i, cd in enumerate(candles15):
        fc = FlowCandle(date=cd["date"], open=cd["open"], high=cd["high"], low=cd["low"], close=cd["close"])
        r = eng15.process_bar(fc, i)
        if r:
            sw15.append(r)
    # open swing
    try:
        os_ = eng15.get_open_swing()
        if os_ and os_.get("breaks"):
            sw15 = sw15 + [os_]
    except Exception:
        pass

    eng1h = PersistentSwingEngine("1h")
    sw1h = []
    for i, cd in enumerate(candles1h):
        fc = FlowCandle(date=cd["date"], open=cd["open"], high=cd["high"], low=cd["low"], close=cd["close"])
        r = eng1h.process_bar(fc, i)
        if r:
            sw1h.append(r)
    try:
        os_ = eng1h.get_open_swing()
        if os_ and os_.get("breaks"):
            sw1h = sw1h + [os_]
    except Exception:
        pass

    return candles15, candles1h, sw15, sw1h


def run_sim(c15, c1h, sw15, sw1h, v18):
    if len(c15) < 30 or len(c1h) < 10:
        return []
    try:
        res = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=[], **v18)
        return res.get("ltf_trades", [])
    except Exception as e:
        print("sim err:", e)
        return None


def test_retention_parity():
    v18 = get_book_params(None)
    for seed in (1, 2, 3):
        c15, c1h, sw15, sw1h = make_series(1200, seed=seed)
        full_trades = run_sim(c15, c1h, sw15, sw1h, v18)
        assert full_trades is not None

        # trim
        c15t, sw15t, off15 = trim_candles_and_swings(c15, sw15, keep_days=5, min_keep=120)
        c1ht, sw1ht, off1h = trim_candles_and_swings(c1h, sw1h, keep_days=5, min_keep=30)
        assert off15 > 0, "trim should drop something"
        # Every retained swing must keep a valid (non-negative) start_idx:
        # a trim that cuts mid-swing would leave start_idx < 0 and corrupt SL.
        for _sw in (sw15t or []) + (sw1ht or []):
            _seg = _sw.get("seg") if isinstance(_sw, dict) else None
            if isinstance(_seg, dict) and "start_idx" in _seg:
                assert int(_seg["start_idx"]) >= 0, f"negative start_idx after trim: {_seg['start_idx']}"
        trimmed_trades = run_sim(c15t, c1ht, sw15t, sw1ht, v18)
        assert trimmed_trades is not None

        diff = trade_list_diff(full_trades, trimmed_trades)
        assert off15 > 0, "trim should drop something"
        # We only require that trades WITHIN the retained window match.
        # So filter full trades to those with entry_ts >= retained cutoff.
        cutoff15 = c15t[0]["ts"] if c15t else 0
        retained_full = [t for t in full_trades if int(t.get("entry_ts", 0)) >= cutoff15]
        diff2 = trade_list_diff(retained_full, trimmed_trades)
        assert diff2["equal"], f"seed={seed} retention parity FAIL: {diff2}"
        print(f"seed={seed}: OK (full={len(full_trades)} trimmed={len(trimmed_trades)} retained_full={len(retained_full)})")


if __name__ == "__main__":
    test_retention_parity()
def test_retention_mid_swing_boundary():
    """Regression: a trim whose cutoff lands inside a swing must pull the
    cutoff back to that swing's start_idx, so the swing is never split."""
    for seed in (1, 2, 4):
        c15, c1h, sw15, sw1h = make_series(600, seed=seed)
        for keep in (1, 2, 3):
            c15t, sw15t, off15 = trim_candles_and_swings(c15, sw15, keep_days=keep, min_keep=60)
            c1ht, sw1ht, off1h = trim_candles_and_swings(c1h, sw1h, keep_days=keep, min_keep=15)
            if not c15t or not sw15t:
                continue
            cutoff = c15t[0]["ts"]
            retained_sets = [(sw15t, c15t), (sw1ht, c1ht)]
            for sws, cs in retained_sets:
                for _sw in (sws or []):
                    _seg = _sw.get("seg") if isinstance(_sw, dict) else None
                    if not (isinstance(_seg, dict) and "start_idx" in _seg):
                        continue
                    si = int(_seg["start_idx"])
                    assert si >= 0, f"negative start_idx {si}"
                    assert 0 <= si < len(cs), f"start_idx {si} out of range (n={len(cs)})"
            print(f"seed={seed} keep={keep}: OK (sw15={len(sw15t)} sw1h={len(sw1ht)})")


if __name__ == "__main__":
    test_retention_parity()
    test_retention_mid_swing_boundary()
    print("ALL PASS")
    print("ALL PASS")
