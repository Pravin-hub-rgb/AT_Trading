"""M3: HTF window replacement after downtime + boot stale-cap sweep.

Root cause: _track_window_regime had no branch for "sim's latest window is
open AND our restored window is open" with a DIFFERENT entry_ts. After a
crash where window A closed and window B opened while the bot was down, the
old branch silently refreshed metrics with B's prices but kept A's id/start_ts
— A became a ghost row in the DB and B was never persisted.

Fix: entry_ts match -> refresh (normal case). Mismatch -> close A with real
sim exit data (matched by entry_ts) or stale_cap when A's lifecycle fell
outside the sim slice, then adopt B. Boot sweep closes any open window whose
16d cap provably passed while down.
"""

import os
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent  # live_stuff/
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "backend"))

from persistence.database import Database
from persistence.trade_store import (
    open_htf_window, close_htf_window, get_open_htf_window,
)

CAP_DAYS = 16
NOW = int(time.time())


def make_loop(db):
    from live_loop import LiveLoop
    ll = LiveLoop.__new__(LiveLoop)
    ll.db = db
    ll._to_ist_short = lambda ts: "?"
    ll.chop_index = 50.0
    ll.regime = "flip"
    ll._chop_stale = True
    ll._update_htf_metrics = lambda: None
    for sfx in ("", "_b2"):
        setattr(ll, f"htf_window_open{sfx}", False)
        setattr(ll, f"htf_window_dir{sfx}", None)
        setattr(ll, f"htf_window_start_ts{sfx}", 0)
        setattr(ll, f"htf_entry_px{sfx}", 0.0)
        setattr(ll, f"htf_sl{sfx}", 0.0)
        setattr(ll, f"htf_hrisk{sfx}", 0.0)
        setattr(ll, f"htf_window_id{sfx}", None)
        setattr(ll, f"htf_current_r{sfx}", 0.0)
    return ll


def new_db():
    db = Database(os.path.join(tempfile.mkdtemp(prefix="m3_"), "t.db"))
    db.connect()
    db.create_tables()
    return db


def htf(entry_ts, dir_="long", outcome="open", exit_ts=0, exit_px=0.0, r=0.0):
    return {"entry_ts": entry_ts, "dir": dir_, "entry_price": 80000.0, "sl": 79000.0,
            "outcome": outcome, "exit_ts": exit_ts, "exit_price": exit_px, "r_multiple": r}


def db_row(db, window_id):
    return db.conn.execute("SELECT * FROM htf_windows WHERE id = ?", (window_id,)).fetchone()


def test_close_reopen_adopted():
    """PASS 1: A closed + B opened during downtime -> A closed w/ sim data, B persisted."""
    db = new_db()
    ll = make_loop(db)
    t1 = NOW - 6 * 86400
    t2 = NOW - 2 * 86400
    ll.htf_window_open = True
    ll.htf_window_start_ts = t1
    ll.htf_window_id = open_htf_window(db, "long", t1, 80000.0, t1 + CAP_DAYS * 86400,
                                       sl_price=79000.0, hrisk=1000.0,
                                       lvl_1_5r=81500.0, lvl_3r=83000.0, regime="flip")
    old_id = ll.htf_window_id
    trades = [htf(t1, "long", "3r", exit_ts=t2 - 86400, exit_px=83000.0, r=3.0),
              htf(t2, "long", "open")]
    ll._track_window_regime("flip", trades)
    a = db_row(db, old_id)
    assert a["status"] == "closed" and a["close_reason"] == "3r", f"A not closed w/ sim data: {dict(a)}"
    b = get_open_htf_window(db, regime="flip")
    assert b is not None and int(b["entry_ts"]) == t2, "B not persisted as open"
    assert ll.htf_window_start_ts == t2 and ll.htf_window_id == int(b["id"])
    assert ll.htf_window_dir == "long" and ll.htf_window_open is True
    print("PASS 1: close+reopen -> A closed with sim exit data, B adopted with new id")


def test_stale_cap_fallback():
    """PASS 2: A's lifecycle outside sim slice (no matching close) -> stale_cap at cap_ts."""
    db = new_db()
    ll = make_loop(db)
    t0 = NOW - 40 * 86400          # started 40d ago — 16d cap long past, outside 20d slice
    t2 = NOW - 86400
    ll.htf_window_open = True
    ll.htf_window_start_ts = t0
    old_id = open_htf_window(db, "short", t0, 80000.0, t0 + CAP_DAYS * 86400,
                             sl_price=81000.0, hrisk=1000.0,
                             lvl_1_5r=78500.0, lvl_3r=77000.0, regime="flip")
    ll.htf_window_id = old_id
    trades = [htf(t2, "short", "open")]
    ll._track_window_regime("flip", trades)
    a = db_row(db, old_id)
    assert a["status"] == "closed" and a["close_reason"] == "stale_cap", f"A not stale-capped: {dict(a)}"
    assert a["close_ts"] == t0 + CAP_DAYS * 86400, f"close_ts should be cap_ts: {a['close_ts']}"
    b = get_open_htf_window(db, regime="flip")
    assert b is not None and int(b["entry_ts"]) == t2 and ll.htf_window_id == int(b["id"])
    print("PASS 2: out-of-slice old window -> stale_cap at exactly cap_ts, B adopted")


def test_same_window_no_change():
    """PASS 3: same window open on both sides -> refresh only, no DB churn."""
    db = new_db()
    ll = make_loop(db)
    t1 = NOW - 3 * 86400
    ll.htf_window_open = True
    ll.htf_window_start_ts = t1
    wid = open_htf_window(db, "long", t1, 80000.0, t1 + CAP_DAYS * 86400,
                          sl_price=79000.0, hrisk=1000.0,
                          lvl_1_5r=81500.0, lvl_3r=83000.0, regime="flip")
    ll.htf_window_id = wid
    trades = [htf(t1, "long", "open")]
    ll._track_window_regime("flip", trades)
    n = db.conn.execute("SELECT COUNT(*) FROM htf_windows").fetchone()[0]
    assert n == 1, f"same-window refresh must not add rows, got {n}"
    a = db_row(db, wid)
    assert a["status"] == "open", "same window must stay open"
    assert ll.htf_window_id == wid and ll.htf_window_start_ts == t1
    print("PASS 3: same-window steady state -> refresh only, zero DB changes")


def test_boot_stale_cap_sweep():
    """PASS 4: boot restore finds a window whose 16d cap passed while down -> closed, not restored."""
    db = new_db()
    ll = make_loop(db)
    t0 = NOW - 20 * 86400          # 16d cap passed 4 days ago
    open_htf_window(db, "long", t0, 80000.0, t0 + CAP_DAYS * 86400,
                    sl_price=79000.0, hrisk=1000.0, lvl_1_5r=81500.0, lvl_3r=83000.0, regime="flip")
    ll._restore_htf_state()
    row = db.conn.execute("SELECT * FROM htf_windows").fetchone()
    assert row["status"] == "closed" and row["close_reason"] == "stale_cap"
    assert ll.htf_window_open is False and ll.htf_window_id is None, "stale window must not be restored"
    print("PASS 4: boot sweep closes cap-expired window, does not restore")


def test_boot_restore_normal():
    """PASS 5: boot restore of a live (within-cap) window unchanged."""
    db = new_db()
    ll = make_loop(db)
    t1 = NOW - 2 * 86400
    wid = open_htf_window(db, "short", t1, 80000.0, t1 + CAP_DAYS * 86400,
                          sl_price=81000.0, hrisk=1000.0, lvl_1_5r=78500.0, lvl_3r=77000.0,
                          regime="flip")
    ll._restore_htf_state()
    assert ll.htf_window_open is True and ll.htf_window_id == wid
    assert ll.htf_window_start_ts == t1 and ll.htf_window_dir == "short"
    print("PASS 5: within-cap window restores normally")


def test_close_while_down_regression():
    """PASS 6 (regression): A closed during downtime, nothing reopened -> existing close branch."""
    db = new_db()
    ll = make_loop(db)
    t1 = NOW - 5 * 86400
    ll.htf_window_open = True
    ll.htf_window_start_ts = t1
    wid = open_htf_window(db, "long", t1, 80000.0, t1 + CAP_DAYS * 86400,
                          sl_price=79000.0, hrisk=1000.0,
                          lvl_1_5r=81500.0, lvl_3r=83000.0, regime="flip")
    ll.htf_window_id = wid
    trades = [htf(t1, "long", "-1r", exit_ts=NOW - 4 * 86400, exit_px=79000.0, r=-1.0)]
    ll._track_window_regime("flip", trades)
    a = db_row(db, wid)
    assert a["status"] == "closed" and a["close_reason"] == "-1r"
    assert ll.htf_window_open is False and ll.htf_window_id is None
    print("PASS 6: plain close-while-down still works (sim-authoritative)")


if __name__ == "__main__":
    test_close_reopen_adopted()
    test_stale_cap_fallback()
    test_same_window_no_change()
    test_boot_stale_cap_sweep()
    test_boot_restore_normal()
    test_close_while_down_regression()
    print("=" * 50)
    print("ALL M3 WINDOW-REPLACE CHECKS PASSED")


