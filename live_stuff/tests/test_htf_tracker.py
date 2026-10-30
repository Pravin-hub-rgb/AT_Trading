import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from live.htf_windows import to_intervals
from live.htf_tracker import HTFWindowTracker


def _trades():
    return [
        {"entry_ts": 1000, "exit_ts": 2000, "dir": "long", "entry_price": 100.0, "sl": 95.0, "outcome": "tp"},
        {"entry_ts": 3000, "exit_ts": 4000, "dir": "short", "entry_price": 110.0, "sl": 115.0, "outcome": "sl"},
    ]


def test_tracker_matches_to_intervals():
    trades = _trades()
    candles = [{"ts": 5000}]
    tr = HTFWindowTracker(window_end="exit", ext_stop_r=1.5)
    iv, rebuilt = tr.update(trades, candles_htf=candles)
    assert rebuilt is True
    assert iv == to_intervals(trades, candles_htf=candles, window_end="exit", ext_stop_r=1.5)


def test_tracker_caches_when_unchanged():
    trades = _trades()
    candles = [{"ts": 5000}]
    tr = HTFWindowTracker()
    iv1, r1 = tr.update(trades, candles_htf=candles)
    iv2, r2 = tr.update(trades, candles_htf=candles)
    assert r1 is True and r2 is False
    assert iv1 == iv2


def test_tracker_rebuilds_on_new_trade():
    trades = _trades()
    candles = [{"ts": 5000}]
    tr = HTFWindowTracker()
    tr.update(trades, candles_htf=candles)
    trades2 = trades + [{"entry_ts": 5000, "exit_ts": 6000, "dir": "long", "entry_price": 120.0, "sl": 115.0, "outcome": "tp"}]
    iv2, r2 = tr.update(trades2, candles_htf=candles)
    assert r2 is True
    assert iv2 == to_intervals(trades2, candles_htf=candles)