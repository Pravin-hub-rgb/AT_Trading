"""Parity: state machine entry set vs batch sim (full IS history)."""
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


def test_entry_set_parity_15m():
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
    eng15 = PersistentSwingEngine("15m", opts={"minBars": 50})
    eng1h = PersistentSwingEngine("1h", opts={"minBars": 15})

    # iterate 15m bars; on 1h boundary, feed 1h engine
    hi = 0
    for i, cd in enumerate(c15):
        # feed 1h bars whose ts <= cd ts
        while hi < len(c1h) and c1h[hi]["ts"] <= cd["ts"]:
            fc1 = FlowCandle(date=c1h[hi]["date"], open=c1h[hi]["open"], high=c1h[hi]["high"],
                             low=c1h[hi]["low"], close=c1h[hi]["close"])
            ev1 = eng1h.process_bar(fc1, hi)
            os1 = eng1h.get_open_swing()
            sm.on_1h_bar(c1h[hi], hi, swing_event=ev1, open_swing=os1, auto_recompute=True)
            hi += 1
        fc = FlowCandle(date=cd["date"], open=cd["open"], high=cd["high"],
                        low=cd["low"], close=cd["close"])
        ev = eng15.process_bar(fc, i)
        os_ = eng15.get_open_swing()
        sm.on_15m_bar(cd, i, swing_event=ev, open_swing=os_)

    # batch sim entries
    sw15 = []
    eng = PersistentSwingEngine("15m", opts={"minBars": 50})
    for i, cd in enumerate(c15):
        fc = FlowCandle(date=cd["date"], open=cd["open"], high=cd["high"], low=cd["low"], close=cd["close"])
        r = eng.process_bar(fc, i)
        if r:
            sw15.append(r)
    os_ = eng.get_open_swing()
    if os_ and os_.get("breaks"):
        sw15.append(os_)

    sw1h = []
    eng = PersistentSwingEngine("1h", opts={"minBars": 15})
    for i, cd in enumerate(c1h):
        fc = FlowCandle(date=cd["date"], open=cd["open"], high=cd["high"], low=cd["low"], close=cd["close"])
        r = eng.process_bar(fc, i)
        if r:
            sw1h.append(r)
    os_ = eng.get_open_swing()
    if os_ and os_.get("breaks"):
        sw1h.append(os_)

    res = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=[], **v18)
    batch_entries = set((int(t["entry_ts"]), str(t["dir"])) for t in res.get("ltf_trades", []))
    sm_entries = set((int(e["entry_ts"]), str(e["dir"])) for e in sm.detected_entries)

    print("detected_marks=%d detected_entries=%d" % (len(sm.detected_marks), len(sm.detected_entries)))
    print("gate_counts:", sm.gate_counts)
    missing = batch_entries - sm_entries
    extra = sm_entries - batch_entries
    print("missing=%d extra=%d" % (len(missing), len(extra)))
    if missing:
        print("first missing:", sorted(missing)[:5])
    if extra:
        print("first extra:", sorted(extra)[:5])

    assert sm_entries == batch_entries, "entry set mismatch"
