"""M1 + M4 + M5 batch tests.

M1: ltf_trades.htf_window_id nullable (table-rebuild migration, journal
    writes NULL instead of the 0 sentinel).
M4: query-path indexes exist after create_tables.
M5: close orders attach SL (position's own SL; panic SL for orphans).
"""

import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent  # live_stuff/
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "backend"))

from persistence.database import Database
from persistence.trade_store import open_ltf_trade, get_ltf_trades

OLD_SCHEMA = """CREATE TABLE IF NOT EXISTS ltf_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    direction TEXT NOT NULL,
    entry_ts INTEGER NOT NULL,
    entry_price REAL NOT NULL,
    sl_initial REAL NOT NULL,
    sl_current REAL NOT NULL,
    tp_price REAL NOT NULL,
    cap_ts INTEGER NOT NULL,
    htf_window_id INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('open','closed')),
    exit_ts INTEGER,
    exit_price REAL,
    exit_reason TEXT,
    r_multiple REAL,
    trail_next_pivot REAL,
    trail_activation_idx INTEGER,
    trail_confirmed BOOLEAN
)"""


def test_m1_migration():
    """PASS 1: old NOT NULL schema + 0-sentinel row -> rebuilt nullable, data kept."""
    db = Database(os.path.join(tempfile.mkdtemp(prefix="m1_"), "t.db"))
    db.connect()
    db._conn.execute(OLD_SCHEMA)  # simulate a pre-M1 database
    db._conn.execute(
        "INSERT INTO ltf_trades (direction, entry_ts, entry_price, sl_initial, "
        "sl_current, tp_price, cap_ts, htf_window_id, status) "
        "VALUES ('long', 1, 80000.0, 79000.0, 79000.0, 83000.0, 2, 0, 'open')")
    db._conn.commit()
    db.create_tables()  # triggers the rebuild migration

    cols = {r[1]: r for r in db.conn.execute("PRAGMA table_info(ltf_trades)").fetchall()}
    assert cols["htf_window_id"][3] == 0, "htf_window_id must no longer be NOT NULL"
    row = get_ltf_trades(db)[0]
    assert row["htf_window_id"] == 0 and row["direction"] == "long", "old row must survive"
    print("PASS 1: NOT NULL dropped via rebuild, existing row preserved")


def test_m1_idempotent_and_null_insert():
    """PASS 2: create_tables twice is safe; journal can now write NULL."""
    db = Database(os.path.join(tempfile.mkdtemp(prefix="m1b_"), "t.db"))
    db.connect()
    db._conn.execute(OLD_SCHEMA)
    db._conn.commit()
    db.create_tables()
    db.create_tables()  # second run — must not raise / rebuild again
    tid = open_ltf_trade(db, "short", 100, 80000.0, 81000.0, 77000.0, 200,
                         htf_window_id=None)  # M1: NULL, not 0
    row = get_ltf_trades(db)[0]
    assert row["id"] == tid and row["htf_window_id"] is None, "NULL window id must persist"
    print("PASS 2: migration idempotent; journal writes NULL window id")


def test_m4_indexes():
    """PASS 3: indexes exist after create_tables (incl. post-rebuild)."""
    db = Database(os.path.join(tempfile.mkdtemp(prefix="m4_"), "t.db"))
    db.connect()
    db._conn.execute(OLD_SCHEMA)  # force the rebuild path
    db._conn.commit()
    db.create_tables()
    names = {r[0] for r in db.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index'").fetchall()}
    for idx in ("idx_ltf_entry_ts", "idx_ltf_status_entry",
                "idx_htf_status_regime", "idx_marks_tf_ts"):
        assert idx in names, f"missing index {idx}"
    print("PASS 3: all 4 M4 indexes exist (survive the M1 rebuild)")


class FakeSession:
    """Bybit session fake: one open position, captures place_order params."""

    def __init__(self, raw_pos):
        self.raw_pos = raw_pos
        self.last_order = None

    def get_positions(self, **kw):
        return {"retCode": 0, "result": {"list": self.raw_pos}}

    def place_order(self, **params):
        self.last_order = params
        self.raw_pos = []  # position closed
        return {"retCode": 0, "result": {"orderId": "1"}}

    def get_wallet_balance(self, **kw):
        return {"retCode": 0, "result": {"list": []}}


def make_trader(raw_pos):
    from bybit_order import BybitTrader
    t = BybitTrader.__new__(BybitTrader)
    t.session = FakeSession(raw_pos)
    t.symbol = "BTCUSDT"
    t.demo = False
    t.api_key = "k"
    t.api_secret = "s"
    t._last_probe_ok = True
    return t


def raw_pos(sl="79000.0"):
    return [{"symbol": "BTCUSDT", "side": "Buy", "size": "0.001",
             "avgPrice": "80000.0", "stopLoss": sl, "liqPrice": "",
             "unrealisedPnl": "0", "leverage": "1"}]


def test_m5_close_carries_position_sl():
    """PASS 4: close order re-attaches the position's own exchange SL."""
    t = make_trader(raw_pos(sl="79000.0"))
    resp = t.close_position_retry(max_attempts=1)
    assert resp.get("retCode") == 0
    assert t.session.last_order["stopLoss"] == "79000.0", \
        f"close order must carry the position SL, got {t.session.last_order}"
    assert t.session.last_order["side"] == "Sell"
    print("PASS 4: close order carries the position's exchange SL (79000.0)")


def test_m5_panic_sl_for_orphan():
    """PASS 5: orphan with no exchange SL gets the wide panic SL (±5%)."""
    t = make_trader(raw_pos(sl="0.0000"))
    resp = t.close_position_retry(max_attempts=1)
    assert resp.get("retCode") == 0
    assert t.session.last_order["stopLoss"] == "76000.0", \
        f"orphan close must get panic SL 80000*0.95=76000.0, got {t.session.last_order}"
    print("PASS 5: unprotected orphan close gets panic SL at -5% (76000.0)")


def test_m5_short_orphan_panic_direction():
    """PASS 6: short orphan panic SL is ABOVE entry (+5%)."""
    pos = raw_pos(sl="0.0000")
    pos[0]["side"] = "Sell"
    t = make_trader(pos)
    resp = t.close_position_retry(max_attempts=1)
    assert resp.get("retCode") == 0
    assert t.session.last_order["stopLoss"] == "84000.0", \
        f"short orphan panic SL must be +5% (84000.0), got {t.session.last_order}"
    assert t.session.last_order["side"] == "Buy"
    print("PASS 6: short orphan panic SL at +5% (84000.0), close side Buy")


if __name__ == "__main__":
    test_m1_migration()
    test_m1_idempotent_and_null_insert()
    test_m4_indexes()
    test_m5_close_carries_position_sl()
    test_m5_panic_sl_for_orphan()
    test_m5_short_orphan_panic_direction()
    print("=" * 50)
    print("ALL M1/M4/M5 BATCH CHECKS PASSED")

