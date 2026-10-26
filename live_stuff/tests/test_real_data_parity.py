"""Real-data parity test: validates Steps A/B against btc_data/is history.

Skipped automatically if the btc_data folder is not present (CI/portable env).
"""
import os, sys
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


def build_swings(candles, min_bars, is15):
    eng = PersistentSwingEngine("15m" if is15 else "1h", opts={"minBars": min_bars})
    out = []
    for i, cd in enumerate(candles):
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


def run_sim(c15, c1h, sw15, sw1h, v18):
    res = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=[], **v18)
    return res.get("ltf_trades", [])


def test_real_data_incremental_parity():
    v18 = get_book_params(None)
    c15, c1h = load_window(2000)
    sw15 = build_swings(c15, 50, True)
    sw1h = build_swings(c1h, 15, False)
    full = run_sim(c15, c1h, sw15, sw1h, v18)
    inc = IncrementalSim(v18, keep_days=90)
    res, changed = inc.on_bar(c15, c1h, sw15, sw1h, force=True)
    inc_trades = (res or {}).get("ltf_trades", [])
    assert trade_list_diff(full, inc_trades)["equal"], "incremental != batch"
    # idempotency
    _, changed2 = inc.on_bar(c15, c1h, sw15, sw1h)
    assert changed2 is False


def test_real_data_retention_parity():
    v18 = get_book_params(None)
    c15, c1h = load_window(2000)
    sw15 = build_swings(c15, 50, True)
    sw1h = build_swings(c1h, 15, False)
    full = run_sim(c15, c1h, sw15, sw1h, v18)
    c15t, sw15t, off15 = trim_candles_and_swings(c15, sw15, keep_days=14, min_keep=120)
    c1ht, sw1ht, off1h = trim_candles_and_swings(c1h, sw1h, keep_days=14, min_keep=30)
    assert off15 > 0
    trimmed = run_sim(c15t, c1ht, sw15t, sw1ht, v18)
    cutoff = c15t[0]["ts"]
    retained_full = [t for t in full if int(t.get("entry_ts", 0)) >= cutoff]
    assert trade_list_diff(retained_full, trimmed)["equal"], "retention parity failed"
