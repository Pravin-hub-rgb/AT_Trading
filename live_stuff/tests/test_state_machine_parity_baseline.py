"""Safety-net parity baseline: Book 107 batch sim on full IS/OOS history.

Locks the measured baseline counts so the incremental state machine (Phase 1)
has a fixed target to match byte-for-byte. Skipped if btc_data is absent.
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
import pandas as pd

from src.btc.btc_config import load_btc_df
from _vendored.walker import FlowCandle
from _vendored.persistent_swing import PersistentSwingEngine
from _vendored.unified import simulate_htf_ltf_streak_halt
from book import get_book_params


def _load_full(is_mode):
    IST = 19800
    if is_mode:
        df15 = load_btc_df("15m", "BTCUSDT_BYBIT")
        df1h = load_btc_df("1h", "BTCUSDT_BYBIT")
        c15 = [{"date": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "ts": int(r.ts),
                "open": float(r.open), "high": float(r.high), "low": float(r.low),
                "close": float(r.close)} for r in df15.itertuples()]
        c1h = [{"date": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "ts": int(r.ts),
                "open": float(r.open), "high": float(r.high), "low": float(r.low),
                "close": float(r.close)} for r in df1h.itertuples()]
    else:
        oos = "C:/Users/Pravin/Desktop/main/btc_data/oos"
        df15 = pd.read_csv(os.path.join(oos, "BTCUSDT_15m.csv"))
        df1h = pd.read_csv(os.path.join(oos, "BTCUSDT_1h.csv"))
        ts15 = (pd.to_datetime(df15["timestamp"]).astype("int64") // 10**9) - IST
        ts1h = (pd.to_datetime(df1h["timestamp"]).astype("int64") // 10**9) - IST
        c15 = [{"date": str(r.timestamp), "ts": int(t), "open": float(r.open),
                "high": float(r.high), "low": float(r.low), "close": float(r.close)}
               for r, t in zip(df15.itertuples(), ts15)]
        c1h = [{"date": str(r.timestamp), "ts": int(t), "open": float(r.open),
                "high": float(r.high), "low": float(r.low), "close": float(r.close)}
               for r, t in zip(df1h.itertuples(), ts1h)]
    return c15, c1h


def _build_swings(candles, min_bars, is15):
    eng = PersistentSwingEngine("15m" if is15 else "1h", opts={"minBars": min_bars})
    out = []
    for i, cd in enumerate(candles):
        fc = FlowCandle(date=cd["date"], open=cd["open"], high=cd["high"],
                        low=cd["low"], close=cd["close"])
        r = eng.process_bar(fc, i)
        if r:
            out.append(r)
    return out


def _run(is_mode):
    v18 = get_book_params(None)
    c15, c1h = _load_full(is_mode)
    sw15 = _build_swings(c15, 50, True)
    sw1h = _build_swings(c1h, 15, False)
    res = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=[], **v18)
    return res.get("ltf_trades", [])


def test_baseline_is_count():
    trades = _run(True)
    # Measured baseline on current data: 529 (historical pin 520; Bybit revision drift).
    assert len(trades) == 529, "IS trade count changed: %d (expected 529)" % len(trades)


def test_baseline_oos_count():
    trades = _run(False)
    # Measured baseline on current data: 291 (historical pin 290; Bybit revision drift).
    assert len(trades) == 291, "OOS trade count changed: %d (expected 291)" % len(trades)
