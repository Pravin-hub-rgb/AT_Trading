"""Stale-entry guard test (C3).

Proves the live loop never executes a trade that is not fresh:
  1. Seed-phase open trade -> journaled stale_skip, NO order, no dead row
  2. Seed-phase CLOSED trades -> journaled normally (history preserved)
  3. Fresh open trade in steady state -> executed
  4. Stale open trade in steady state -> stale_skip
  5. In-trade + new sim trade -> refused (no double entry)
  6. stale_skip rows NEVER count toward streak halt
  7. Boot-time SL sync fires when in trade

Run: python backtest/tests/test_stale_entry.py
"""
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backtest/
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from persistence.database import Database
from persistence.trade_store import get_ltf_trades
from live_loop import LiveLoop


class FakeTrader:
    is_connected = True
    qty_step = 0.001
    min_qty = 0.001
    qty_precision = 3

    def __init__(self):
        self.order_calls = 0
        self.sl_calls = []

    def place_market_order_retry(self, side, qty, stop_loss=None, take_profit=None, order_link_id=None):
        self.order_calls += 1
        return {"retCode": 0, "result": {"orderId": "test"}}
    def get_position(self):
        return {"side": "Buy", "size": 0.001, "entry_price": 80000.0}
    def verify_entry_order(self, order_link_id, expected_side=None):
        return ("flat", None)

    def get_wallet_balance(self):
        return {"available": 100000.0}

    def get_position(self):
        return {"side": "Buy", "size": 0.001, "entry_price": 80000.0}

    def update_sl(self, new_sl):
        self.sl_calls.append(float(new_sl))
        return {"retCode": 0}


class FakeRate:
    def is_stale(self):
        return False

    def age_min(self):
        return 0.0

    def get_rate(self):
        return 88.0

    def update(self):
        pass


def make_stub(trader=None, seeding=False):
    ll = LiveLoop.__new__(LiveLoop)
    ll.db = None  # set by caller
    ll.window_15m = []
    ll.window_1h = []
    ll.atr_14 = 0.0
    ll.rate_manager = FakeRate()
    ll.trader = trader
    ll._tg = None
    ll._open_ltf_trade = None
    ll.trading_state = {"cooldown_remaining": 0, "halted": False,
                        "consecutive_losses": 0, "daily_pnl_r": 0.0}
    ll._chop_stale = False
    ll.chop_index = 50.0
    ll.regime = "flip"
    ll._chop_thresh = 58.0
    ll.v18 = {"ext_stop_r": 1.5, "max_consecutive_losses": 3, "cooldown_bars": 0}
    ll._daily_pnl_r = 0.0
    ll._daily_halted = False
    ll._last_trade_date = None
    ll._cum_cost_r = 0.0
    ll._cum_net_r = 0.0
    ll._trade_count = 0
    ll._seeding = seeding
    # flip + b2 window fields (journal linkage)
    ll.htf_window_open = False
    ll.htf_window_dir = None
    ll.htf_window_start_ts = 0
    ll.htf_window_id = None
    ll.htf_entry_px = 0.0
    ll.htf_sl = 0.0
    ll.htf_current_r = 0.0
    ll.htf_hrisk = 0.0
    ll.htf_window_open_b2 = False
    ll.htf_window_dir_b2 = None
    ll.htf_window_start_ts_b2 = 0
    ll.htf_window_id_b2 = None
    ll.htf_entry_px_b2 = 0.0
    ll.htf_sl_b2 = 0.0
    ll.htf_current_r_b2 = 0.0
    ll.htf_hrisk_b2 = 0.0
    return ll


def sim_trade(entry_ts, direction="long", outcome="open", regime="flip"):
    """Fake sim trade as returned by simulate_htf_ltf_streak_halt."""
    return {
        "dir": direction, "swing_no": 3, "break_kind": "B2",
        "htf_regime": regime, "entry_ts": entry_ts,
        "entry_price": 80000.0, "sl": 79000.0, "target": 83000.0,
        "exit_idx": None, "exit_ts": entry_ts + 3600 if outcome != "open" else 0,
        "exit_date": "", "exit_price": 79000.0 if outcome == "sl" else 0.0,
        "outcome": outcome, "r_multiple": -1.0 if outcome == "sl" else 0.0,
        "bars_held": 0,
    }


def row_by_id(db, trade_id):
    for r in get_ltf_trades(db):
        if r["id"] == trade_id:
            return r
    return None


def main():
    now = int(time.time())
    fresh_ts = now - 60          # 1 bar old = fresh
    stale_ts = now - 86400       # 1 day old = stale
    tmp = Path(tempfile.mkdtemp(prefix="stale_"))

    # 1. Seed-phase open trade -> stale_skip, NO order, row CLOSED (no dead row)
    db1 = Database(str(tmp / "t1.db")); db1.connect(); db1.create_tables()
    tr = FakeTrader()
    ll = make_stub(tr, seeding=True); ll.db = db1
    ll._journal_trades([sim_trade(stale_ts, "long", "open")])
    rows = get_ltf_trades(db1)
    assert len(rows) == 1 and rows[0]["status"] == "closed", f"row must be closed: {rows}"
    assert rows[0]["exit_reason"] == "stale_skip", rows[0]["exit_reason"]
    assert tr.order_calls == 0, "seed-phase trade must NOT execute"
    assert ll._open_ltf_trade is None, "cache must not be set"
    print("PASS 1: seed open trade -> stale_skip, no order, no dead row")

    # 2. Seed-phase CLOSED trades -> journaled normally with real exit reason
    ll._journal_trades([sim_trade(stale_ts + 10, "long", "sl")])
    rows = get_ltf_trades(db1)
    closed = [r for r in rows if r["exit_reason"] == "sl"]
    assert len(closed) == 1 and closed[0]["r_multiple"] == -1.0, "closed history must journal normally"
    print("PASS 2: seed closed trade -> journaled normally (not stale_skip)")

    # 3. Fresh open trade in steady state -> EXECUTED
    db3 = Database(str(tmp / "t3.db")); db3.connect(); db3.create_tables()
    tr3 = FakeTrader()
    ll3 = make_stub(tr3, seeding=False); ll3.db = db3
    ll3._journal_trades([sim_trade(fresh_ts, "long", "open")])
    assert tr3.order_calls == 1, f"fresh trade must execute, order_calls={tr3.order_calls}"
    assert ll3._open_ltf_trade is not None, "cache must be set for fresh trade"
    print("PASS 3: fresh steady-state trade -> executed")

    # 4. Stale open trade in steady state -> stale_skip (no order)
    db4 = Database(str(tmp / "t4.db")); db4.connect(); db4.create_tables()
    tr4 = FakeTrader()
    ll4 = make_stub(tr4, seeding=False); ll4.db = db4
    ll4._journal_trades([sim_trade(stale_ts, "long", "open")])
    rows = get_ltf_trades(db4)
    assert rows[0]["exit_reason"] == "stale_skip" and tr4.order_calls == 0
    print("PASS 4: stale steady-state trade -> stale_skip, no order")

    # 5. In-trade + new sim trade -> refused (no double entry)
    db5 = Database(str(tmp / "t5.db")); db5.connect(); db5.create_tables()
    tr5 = FakeTrader()
    ll5 = make_stub(tr5, seeding=False); ll5.db = db5
    ll5._open_ltf_trade = {"id": 999, "direction": "short", "entry_ts": fresh_ts,
                           "entry_price": 81000.0, "sl_initial": 81500.0,
                           "sl_current": 81500.0, "tp_price": 80000.0}
    ll5._journal_trades([sim_trade(fresh_ts + 5, "long", "open")])
    assert tr5.order_calls == 0, "in-trade refusal must block execution"
    assert ll5._open_ltf_trade["id"] == 999, "existing cache must be untouched"
    rows = get_ltf_trades(db5)
    assert rows and rows[0]["exit_reason"] == "stale_skip"
    print("PASS 5: in-trade + new sim trade -> refused, cache untouched")

    # 6. stale_skip rows NEVER count toward streak halt
    db6 = Database(str(tmp / "t6.db")); db6.connect(); db6.create_tables()
    tr6 = FakeTrader()
    ll6 = make_stub(tr6, seeding=True); ll6.db = db6
    ll6._journal_trades([
        sim_trade(stale_ts, "long", "open"),
        sim_trade(stale_ts + 1, "short", "open"),
        sim_trade(stale_ts + 2, "long", "open"),
    ])
    ll6._persist_streak_state()
    assert ll6.trading_state["consecutive_losses"] == 0, \
        f"stale_skip must not count as losses, got {ll6.trading_state['consecutive_losses']}"
    assert not ll6.trading_state["halted"], "no false halt from stale_skip rows"
    print("PASS 6: stale_skip excluded from streak counting (no false halt)")

    # 7. Boot-time SL sync fires when in trade
    tr7 = FakeTrader()
    ll7 = make_stub(tr7); ll7.db = Database(str(tmp / "t7.db"))
    ll7.db.connect(); ll7.db.create_tables()
    ll7._open_ltf_trade = {"id": 1, "direction": "long", "sl_current": 79500.0}
    ll7._boot_sync_sl()
    assert tr7.sl_calls == [79500.0], f"boot SL sync must fire, got {tr7.sl_calls}"
    # and must NOT fire when flat
    ll7._open_ltf_trade = None
    ll7._boot_sync_sl()
    assert len(tr7.sl_calls) == 1, "no SL sync when flat"
    print("PASS 7: boot SL sync fires in-trade, skipped when flat")

    for d in (db1, db3, db4, db5, db6):
        d.close()
    ll7.db.close()
    print("=" * 60)
    print("ALL STALE ENTRY CHECKS PASSED")


if __name__ == "__main__":
    main()
