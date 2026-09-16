import sys, os, tempfile, traceback
sys.path.insert(0, 'live_stuff')
from pathlib import Path

try:
    from persistence.database import Database
    from persistence.trade_store import open_ltf_trade, get_ltf_trades, update_trade_qty

    tmp = tempfile.mkdtemp()
    db = Database(str(Path(tmp) / "test.db"))
    db.connect()
    db.create_tables()

    trade_id = open_ltf_trade(db, direction="long", entry_ts=1000, entry_price=50000.0,
                              sl_initial=49000.0, tp_price=51000.0, cap_ts=1000+86400, htf_window_id=1)

    row = [r for r in get_ltf_trades(db) if r["id"] == trade_id][0]
    print(f"Before update: qty = {row['qty']!r}")

    update_trade_qty(db, trade_id, 0.003)

    row = [r for r in get_ltf_trades(db) if r["id"] == trade_id][0]
    print(f"After update:  qty = {row['qty']!r}")
    print(f"Expected:      qty = 0.003")
    print("PASS" if row["qty"] == 0.003 else "FAIL")
    db.close()
except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()