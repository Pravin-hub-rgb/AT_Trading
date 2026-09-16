"""Exit retry + order-of-operations test (C1/C2).

Proves the live exit path can never desync DB from exchange:
  1. Exchange close fails -> DB trade stays OPEN, cache intact, retried next tick
  2. Exchange close succeeds after retries -> DB closed, cache cleared
  3. Paper mode (no trader) -> DB closes immediately
  4. Exchange already flat (SL fired server-side) -> DB closes, no error
  5. close_position_retry distinguishes query-failure from genuinely-flat

Run: python live_stuff/tests/test_exit_retry.py
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # live_stuff/
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from persistence.database import Database
from persistence.trade_store import open_ltf_trade, get_ltf_trades
from live_loop import LiveLoop


class FakeTrader:
    """Fake Bybit trader — fails the first N close attempts, then succeeds."""

    is_connected = True

    def __init__(self, fail_times=0):
        self.fail_times = fail_times
        self.close_calls = 0

    def close_position_retry(self):
        self.close_calls += 1
        if self.close_calls <= self.fail_times:
            return {"retCode": -1, "retMsg": "timeout"}
        return {"retCode": 0, "retMsg": "closed", "closed": True}


class FakeRate:
    def is_stale(self):
        return False

    def age_min(self):
        return 0.0

    def get_rate(self):
        return 88.0

    def update(self):
        pass


def make_stub(trader):
    ll = LiveLoop.__new__(LiveLoop)
    ll.db = None  # set by caller
    ll.window_15m = [{"open": 79500.0, "close": 78900.0}]
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
    return ll


def open_cached_trade(ll, db):
    trade_id = open_ltf_trade(
        db, direction="long", entry_ts=1_700_000_000,
        entry_price=80000.0, sl_initial=79000.0,
        tp_price=83000.0, cap_ts=1_700_000_000 + 16 * 86400, htf_window_id=0,
    )
    ll._open_ltf_trade = {
        "id": trade_id, "direction": "long", "entry_ts": 1_700_000_000,
        "entry_price": 80000.0, "sl_initial": 79000.0, "sl_current": 79000.0,
        "tp_price": 83000.0, "cap_ts": 1_700_000_000 + 16 * 86400,
    }
    return trade_id


def db_status(db, trade_id):
    for r in get_ltf_trades(db):
        if r["id"] == trade_id:
            return r["status"]
    return "?"


def main():
    tmp = Path(tempfile.mkdtemp(prefix="exitretry_"))

    # 1. Exchange close FAILS -> DB stays open, cache intact, retried next tick
    db1 = Database(str(tmp / "t1.db")); db1.connect(); db1.create_tables()
    trader = FakeTrader(fail_times=99)
    ll = make_stub(trader); ll.db = db1
    tid = open_cached_trade(ll, db1)
    ll.on_tick(78900.0, 1_700_010_000)  # SL hit -> close attempt fails
    assert trader.close_calls == 1, "close should be attempted once per tick"
    assert db_status(db1, tid) == "open", "DB trade must STAY OPEN when exchange close fails"
    assert ll._open_ltf_trade is not None, "cache must stay intact for next-tick retry"
    ll.on_tick(78900.0, 1_700_010_001)  # next tick retries
    assert trader.close_calls == 2, "close must be retried on next tick"
    assert db_status(db1, tid) == "open"
    print("PASS 1: failed exchange close -> DB open + cache intact + retried")

    # 2. Exchange close succeeds after retries -> DB closed, cache cleared
    trader2 = FakeTrader(fail_times=2)
    db2 = Database(str(tmp / "t2.db")); db2.connect(); db2.create_tables()
    ll2 = make_stub(trader2); ll2.db = db2
    tid2 = open_cached_trade(ll2, db2)
    ll2.on_tick(78900.0, 1_700_010_000)  # fail 1
    ll2.on_tick(78900.0, 1_700_010_001)  # fail 2
    assert db_status(db2, tid2) == "open"
    ll2.on_tick(78900.0, 1_700_010_002)  # attempt 3 succeeds
    assert db_status(db2, tid2) == "closed", "DB must close once exchange close confirmed"
    assert ll2._open_ltf_trade is None, "cache must be cleared after confirmed close"
    print("PASS 2: retry-then-success -> DB closed + cache cleared")

    # 3. Paper mode (no trader) -> DB closes immediately, no exchange call
    db3 = Database(str(tmp / "t3.db")); db3.connect(); db3.create_tables()
    ll3 = make_stub(None); ll3.db = db3
    tid3 = open_cached_trade(ll3, db3)
    ll3.on_tick(78900.0, 1_700_010_000)
    assert db_status(db3, tid3) == "closed", "paper mode: DB closes immediately"
    assert ll3._open_ltf_trade is None
    print("PASS 3: paper mode (no trader) -> DB closes immediately")

    # 4. Exchange already flat (SL fired server-side) -> success, DB closes
    class FlatTrader:
        is_connected = True
        def close_position_retry(self):
            return {"retCode": 0, "retMsg": "no position", "closed": False}
    db4 = Database(str(tmp / "t4.db")); db4.connect(); db4.create_tables()
    ll4 = make_stub(FlatTrader()); ll4.db = db4
    tid4 = open_cached_trade(ll4, db4)
    ll4.on_tick(78900.0, 1_700_010_000)
    assert db_status(db4, tid4) == "closed", "already-flat counts as closed"
    print("PASS 4: exchange already flat -> DB closes cleanly")

    # 5. close_position_retry distinguishes query-failure from flat
    from bybit_order import BybitTrader
    class FlakySession:
        def __init__(self):
            self.calls = 0
        def get_positions(self, **kw):
            self.calls += 1
            if self.calls <= 2:
                raise ConnectionError("network down")  # query FAILS
            return {"result": {"list": []}}            # then genuinely flat
    class SessionTrader(BybitTrader):
        def __init__(self):
            self.symbol = "BTCUSDT"
            self.session = FlakySession()
        def place_market_order_retry(self, side, qty):
            raise AssertionError("close order must NOT be placed when query fails")
    result = BybitTrader.close_position_retry(SessionTrader())
    assert result.get("retCode") == 0, \
        f"query failures then flat must end in success, got {result}"
    print("PASS 5: query-failure retried, genuine flat -> success (no false close)")

    for d in (db1, db2, db3, db4):
        d.close()
    print("=" * 60)
    print("ALL EXIT RETRY CHECKS PASSED")


if __name__ == "__main__":
    main()
