"""Bar-by-bar parity tester (brick 4).

Runs an incremental engine one candle at a time over a real window and compares
its trade list to the batch oracle at *every* step. This is the safety net for
the O(1) rewrite: any incremental implementation must pass this test.

Usage:
    python tests/test_bar_by_bar_parity.py            # runs with IncrementalSim
"""
import os, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.join(ROOT, "live"))
BTC_DATA = "C:/Users/Pravin/Desktop/main/btc_data"
if not os.path.isdir(os.path.join(BTC_DATA, "is")):
    import pytest
    pytest.skip("btc_data not available", allow_module_level=True)

sys.path.insert(0, "C:/Users/Pravin/Desktop/main/AT_Trading/backend")

import pytest
from src.btc.btc_config import load_btc_df
from _vendored.walker import FlowCandle
from _vendored.persistent_swing import PersistentSwingEngine
from _vendored.unified import simulate_htf_ltf_streak_halt
from book import get_book_params
from live.incremental import IncrementalSim
from live.retention import trim_candles_and_swings
from parity import trade_list_diff


def load_window(n15_tail):
    df15 = load_btc_df("15m", "BTCUSDT_BYBIT")
    df1h = load_btc_df("1h", "BTCUSDT_BYBIT")
    df15 = df15.tail(n15_tail).reset_index(drop=True)
    t0 = int(df15.iloc[0]["ts"]); t1 = int(df15.iloc[-1]["ts"])
    df1h = df1h[(df1h["ts"] >= t0) & (df1h["ts"] <= t1)].reset_index(drop=True)
    c15 = [{"date": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "ts": int(r.ts),
            "open": float(r.open), "high": float(r.high), "low": float(r.low), "close": float(r.close)}
           for r in df15.itertuples()]
    c1h = [{"date": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "ts": int(r.ts),
            "open": float(r.open), "high": float(r.high), "low": float(r.low), "close": float(r.close)}
           for r in df1h.itertuples()]
    return c15, c1h


def build_swings_upto(candles, min_bars, is15, upto):
    eng = PersistentSwingEngine("15m" if is15 else "1h", opts={"minBars": min_bars})
    out = []
    for i in range(upto):
        cd = candles[i]
        fc = FlowCandle(date=cd["date"], open=cd["open"], high=cd["high"], low=cd["low"], close=cd["close"])
        r = eng.process_bar(fc, i)
        if r:
            out.append(r)
    try:
        os_ = eng.get_open_swing()
        if os_ and os_.get("breaks"):
            out = out + [os_]
    except Exception:
        pass
    return out


def run_batch(c15, c1h, sw15, sw1h, v18):
    res = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=[], **v18)
    return res.get("ltf_trades", [])


def test_bar_by_bar_incremental_parity():
    v18 = get_book_params(None)
    c15, c1h = load_window(200)   # modest window to keep runtime sane
    n15 = len(c15)
    # warmup: start after 80 bars so swings exist
    start = 80
    inc = IncrementalSim(v18, keep_days=90)
    open_swings_cache = {"15m": None, "1h": None}
    mismatches = []
    t0 = time.time()
    for i in range(start, n15):
        # build swings up to i+1
        sw15 = build_swings_upto(c15, 50, True, i + 1)
        # h: find how many 1h bars correspond
        t_end = c15[i]["ts"]
        n1h = sum(1 for c in c1h if c["ts"] <= t_end)
        sw1h = build_swings_upto(c1h, 15, False, n1h)
        prefix15 = c15[:i + 1]
        prefix1h = [c for c in c1h if c["ts"] <= t_end]

        # open swings
        # rebuild open swings from engines (approx): use last open swing by re-running
        # (build_swings_upto already appends open swing if it has breaks)

        batch_trades = run_batch(prefix15, prefix1h, sw15, sw1h, v18)

        res, changed = inc.on_bar(prefix15, prefix1h, sw15, sw1h, force=True)
        inc_trades = (res or {}).get("ltf_trades", []) if res else []

        diff = trade_list_diff(batch_trades, inc_trades)
        if not diff["equal"]:
            mismatches.append((i, c15[i]["ts"], diff))
            if len(mismatches) >= 5:
                break

    elapsed = time.time() - t0
    print(f"bar-by-bar: {n15 - start} bars in {elapsed:.1f}s, mismatches={len(mismatches)}")
    if mismatches:
        for m in mismatches[:3]:
            print("  MISMATCH at bar", m[0], "ts", m[1], m[2].get("reason"))
    assert not mismatches, f"{len(mismatches)} bar-level mismatches; first={mismatches[0] if mismatches else None}"