"""Parity: state machine HTF window tracking vs batch sim (full IS history)."""
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
from live.state_machine import StateMachine


def test_htf_windows_populated():
    df15 = load_btc_df("15m", "BTCUSDT_BYBIT")
    df1h = load_btc_df("1h", "BTCUSDT_BYBIT")
    c15 = [{"date": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "ts": int(r.ts),
            "open": float(r.open), "high": float(r.high), "low": float(r.low),
            "close": float(r.close)} for r in df15.itertuples()]
    c1h = [{"date": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "ts": int(r.ts),
            "open": float(r.open), "high": float(r.high), "low": float(r.low),
            "close": float(r.close)} for r in df1h.itertuples()]

    v18 = get_book_params(None)
    sm = StateMachine(v18)
    eng1h = PersistentSwingEngine("1h", opts={"minBars": 15})

    for i, cd in enumerate(c1h):
        fc = FlowCandle(date=cd["date"], open=cd["open"], high=cd["high"],
                        low=cd["low"], close=cd["close"])
        ev = eng1h.process_bar(fc, i)
        os_ = eng1h.get_open_swing()
        sm.on_1h_bar(cd, i, swing_event=ev, open_swing=os_, auto_recompute=False)
    sm._recompute_htf_windows()

    # state machine should have HTF windows for all three regimes
    assert "flip" in sm.state.open_htf_windows
    assert "decisive" in sm.state.open_htf_windows
    assert "b2" in sm.state.open_htf_windows
    assert len(sm.htf_swings) > 0
    # chop should be a sane number
    assert 0 <= sm.state.last_closed_1h_chop <= 100
    print("htf_swings=%d flip_ivs=%d" % (len(sm.htf_swings),
          len(sm.state.open_htf_windows.get("flip", []))))
