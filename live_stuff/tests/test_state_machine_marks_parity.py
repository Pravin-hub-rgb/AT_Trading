"""Parity: state machine mark detection vs batch sim swing marks (full IS history)."""
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
from book import get_book_params
from live.state_machine import StateMachine


def _load():
    df15 = load_btc_df("15m", "BTCUSDT_BYBIT")
    c15 = [{"date": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "ts": int(r.ts),
            "open": float(r.open), "high": float(r.high), "low": float(r.low),
            "close": float(r.close)} for r in df15.itertuples()]
    return c15


def _batch_marks(candles, min_bars):
    eng = PersistentSwingEngine("15m", opts={"minBars": min_bars})
    marks = []
    seen = set()
    for i, cd in enumerate(candles):
        fc = FlowCandle(date=cd["date"], open=cd["open"], high=cd["high"],
                        low=cd["low"], close=cd["close"])
        r = eng.process_bar(fc, i)
        if r:
            for m in (r.get("breaks") or []):
                k = (r.get("swing_index"), int(m.get("idx")), str(m.get("kind")), str(m.get("dir")))
                if k in seen:
                    continue
                seen.add(k)
                marks.append(k)
    os_ = eng.get_open_swing()
    if os_ and os_.get("breaks"):
        for m in os_["breaks"]:
            k = (os_.get("swing_index"), int(m.get("idx")), str(m.get("kind")), str(m.get("dir")))
            if k in seen:
                continue
            seen.add(k)
            marks.append(k)
    return marks, seen


def test_marks_parity_15m():
    c15 = _load()
    v18 = get_book_params(None)
    sm = StateMachine(v18)
    eng15 = PersistentSwingEngine("15m", opts={"minBars": 50})
    for i, cd in enumerate(c15):
        fc = FlowCandle(date=cd["date"], open=cd["open"], high=cd["high"],
                        low=cd["low"], close=cd["close"])
        ev = eng15.process_bar(fc, i)
        os_ = eng15.get_open_swing()
        sm.on_15m_bar(cd, i, swing_event=ev, open_swing=os_)

    sm_set = set((m.get("swing_index"), int(m.get("idx")), str(m.get("kind")),
                  str(m.get("dir"))) for m in sm.detected_marks)
    batch, batch_set = _batch_marks(c15, 50)
    assert sm_set == batch_set, "mark set mismatch: sm=%d batch=%d" % (len(sm_set), len(batch_set))
    print("15m marks: sm=%d batch=%d" % (len(sm_set), len(batch_set)))
