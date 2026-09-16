"""B2 window bookkeeping test — dual-regime HTF window tracking.

Proves the live loop tracks flip AND b2 HTF windows independently:
  1. Both windows can be open simultaneously (separate v7 runs)
  2. DB rows carry the correct regime tag
  3. LTF trades link to the window of their OWN htf_regime tag
  4. Flip close leaves b2 window untouched
  5. Boot restore brings back BOTH open windows
  6. _active_htf() follows the regime switch (chop > thresh → b2)

Run: python live_stuff/tests/test_b2_window_tracking.py
"""
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # live_stuff/
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from persistence.database import Database
from persistence.trade_store import get_open_htf_window, get_ltf_trades
from live_loop import LiveLoop


def make_stub(regime="flip"):
    """LiveLoop without __init__ — only the attrs the tracked methods touch."""
    ll = LiveLoop.__new__(LiveLoop)
    ll.window_15m = []
    ll.window_1h = []
    ll.trading_state = {"cooldown_remaining": 0}
    ll._chop_stale = True
    ll.chop_index = 50.0
    ll.atr_14 = 0.0
    ll.regime = regime
    ll._chop_thresh = 58.0
    ll.v18 = {"ext_stop_r": 1.5, "chop_thresh": 58.0}
    ll._tg = None
    ll.trader = None
    ll._open_ltf_trade = None
    ll._daily_pnl_r = 0.0
    ll._daily_halted = False
    ll._last_trade_date = None
    # flip window fields
    ll.htf_window_open = False
    ll.htf_window_dir = None
    ll.htf_window_start_ts = 0
    ll.htf_window_id = None
    ll.htf_entry_px = 0.0
    ll.htf_sl = 0.0
    ll.htf_current_r = 0.0
    ll.htf_hrisk = 0.0
    # b2 window fields
    ll.htf_window_open_b2 = False
    ll.htf_window_dir_b2 = None
    ll.htf_window_start_ts_b2 = 0
    ll.htf_window_id_b2 = None
    ll.htf_entry_px_b2 = 0.0
    ll.htf_sl_b2 = 0.0
    ll.htf_current_r_b2 = 0.0
    ll.htf_hrisk_b2 = 0.0
    return ll


def htf_trade(entry_ts, direction="long", outcome="open", entry=80000.0, sl=79000.0):
    """Fake HTF trade as returned by simulate_htf_ltf_streak_halt."""
    d = 1 if direction == "long" else -1
    return {
        "dir": direction, "outcome": outcome,
        "entry_ts": entry_ts, "entry_price": entry, "sl": sl,
        "exit_ts": entry_ts + 3600 if outcome != "open" else 0,
        "exit_price": sl if outcome == "sl" else entry + 3 * abs(entry - sl) * d,
        "r_multiple": -1.0 if outcome == "sl" else 3.0,
    }


def ltf_trade(entry_ts, direction="long", regime="flip"):
    return {
        "dir": direction, "swing_no": 3, "break_kind": "B2",
        "htf_regime": regime,
        "entry_ts": entry_ts, "entry_price": 80100.0, "sl": 79900.0,
        "target": 80700.0,
        "exit_idx": None, "exit_ts": 0, "exit_date": "", "exit_price": 0.0,
        "outcome": "open", "r_multiple": 0.0, "bars_held": 0,
    }


def main():
    tmp = Path(tempfile.mkdtemp(prefix="b2win_"))
    db = Database(str(tmp / "test.db"))
    db.connect()
    db.create_tables()

    # 0. migration: regime column exists
    cols = {r[1] for r in db.conn.execute("PRAGMA table_info(htf_windows)").fetchall()}
    assert "regime" in cols, f"regime column missing after create_tables: {cols}"
    print("PASS 0: regime column exists (fresh schema)")

    ll = make_stub()
    ll.db = db

    # 1. dual open — flip AND b2 windows open simultaneously
    flip_open = htf_trade(1_700_000_000, "long", "open")
    b2_open = htf_trade(1_700_010_000, "short", "open", entry=81000.0, sl=81500.0)
    ll._track_htf_windows([flip_open], [b2_open], [])
    assert ll.htf_window_open and ll.htf_window_open_b2, "both windows should be open"
    assert ll.htf_window_id is not None and ll.htf_window_id_b2 is not None
    assert ll.htf_window_id != ll.htf_window_id_b2, "window ids must differ"
    flip_id, b2_id = ll.htf_window_id, ll.htf_window_id_b2
    r_flip = get_open_htf_window(db, regime="flip")
    r_b2 = get_open_htf_window(db, regime="b2")
    assert r_flip and r_flip["id"] == flip_id and r_flip["regime"] == "flip"
    assert r_b2 and r_b2["id"] == b2_id and r_b2["regime"] == "b2"
    print("PASS 1: dual open — flip id", flip_id, "+ b2 id", b2_id, "both tagged in DB")

    # 2. journal linkage — each trade links to ITS OWN regime window
    ll._journal_trades([
        ltf_trade(1_700_020_000, "short", regime="b2"),
        ltf_trade(1_700_030_000, "long", regime="flip"),
    ])
    by_dir = {}
    for r in get_ltf_trades(db):
        by_dir.setdefault(r["direction"], []).append(r["htf_window_id"])
    assert b2_id in by_dir.get("short", []), f"b2 trade must link to b2 window {b2_id}, got {by_dir}"
    assert flip_id in by_dir.get("long", []), f"flip trade must link to flip window {flip_id}, got {by_dir}"
    print("PASS 2: LTF trades linked by their own htf_regime tag")

    # 3. flip closes - b2 window untouched
    flip_closed = htf_trade(1_700_000_000, "long", "sl")
    ll._track_htf_windows([flip_closed], [b2_open], [])
    assert not ll.htf_window_open, "flip window should be closed"
    assert ll.htf_window_open_b2, "b2 window must stay open"
    assert get_open_htf_window(db, regime="flip") is None
    assert get_open_htf_window(db, regime="b2") is not None
    print("PASS 3: flip close leaves b2 window open")

    # 4. boot restore - b2 window comes back from DB
    # (M3 boot sweep: refresh entry_ts to within the 16d cap first - a
    #  2023-dated window is correctly stale-capped and must NOT restore)
    with db.transaction() as conn:
        conn.execute("UPDATE htf_windows SET entry_ts = ? WHERE id = ?",
                     (int(time.time()) - 2 * 86400, b2_id))
    ll2 = make_stub()
    ll2.db = db
    ll2._restore_htf_state()
    assert ll2.htf_window_open_b2 and ll2.htf_window_id_b2 == b2_id, "b2 window must restore"
    assert not ll2.htf_window_open, "closed flip window must NOT restore"
    print("PASS 4: restore brings back open b2 window (id", b2_id, ")")

    # 5. _active_htf follows the regime switch
    ll2.regime = "b2"
    w = ll2._active_htf()
    assert w["tag"] == "B2" and w["open"] and w["dir"] == "short"
    ll2.regime = "flip"
    w = ll2._active_htf()
    assert w["tag"] == "FLIP" and not w["open"]
    print("PASS 5: _active_htf switches with regime (B2 open / FLIP none)")

    # 6. R-depth per window: feed a price via window_15m
    ll2.regime = "b2"
    ll2.window_15m = [{"close": 80800.0}]  # b2 short entry 81000 sl 81500 -> +0.4R
    ll2._chop_stale = False  # skip chop recompute (no 1h candles in stub)
    ll2._update_htf_metrics()
    assert abs(ll2.htf_current_r_b2 - 0.4) < 1e-9, f"b2 R should be +0.4, got {ll2.htf_current_r_b2}"
    print("PASS 6: b2 unrealized R = +0.4R (short 81000, price 80800, risk 500)")

    db.close()
    print("=" * 60)
    print("ALL B2 WINDOW CHECKS PASSED")


if __name__ == "__main__":
    main()
