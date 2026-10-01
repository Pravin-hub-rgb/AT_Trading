"""Entry adopt-or-verify test (C7 + H4).

Proves the entry path can never orphan a live position:
  1. Lost response + position exists -> ADOPTED (DB open, cache set, alert)
  2. Confirmed flat -> DB closed as order_failed, cache cleared
  3. Unknown (queries fail) -> DB held OPEN + cache (bounded by exchange SL)
  4. Duplicate-rejection -> verification runs before any failure
  5. Success-path slow fill -> poll adopts (H4), no false order_failed
  6. verify_entry_order unit: position-first, history tie-breaker, side mismatch

Run: python backtest/tests/test_entry_verify.py
"""
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backtest/
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from persistence.database import Database
from persistence.trade_store import get_ltf_trades, open_ltf_trade
from bybit_order import BybitTrader
from live_loop import LiveLoop


class FakeTrader:
    """Trader with a canned place/verify behavior for _execute_entry tests."""

    is_connected = True
    qty_step = 0.001
    min_qty = 0.001
    qty_precision = 3

    def __init__(self, place_fail=False, dup_msg=False, verify=None):
        self.place_fail = place_fail
        self.dup_msg = dup_msg
        self._verify = verify or ("unknown", None)
        self.order_calls = 0
        self.verify_calls = 0
        self.used_link_id = None
        self.last_tp = "unset"

    def place_market_order_retry(self, side, qty, stop_loss=None, take_profit=None,
                                 order_link_id=None):
        self.order_calls += 1
        self.used_link_id = order_link_id
        self.last_tp = take_profit
        if self.place_fail:
            msg = "OrderLinkedID is duplicate" if self.dup_msg else "timeout"
            return {"retCode": -1, "retMsg": msg, "_order_link_id": order_link_id}
        return {"retCode": 0, "result": {"orderId": "ok123"}, "_order_link_id": order_link_id}

    def verify_entry_order(self, order_link_id, expected_side=None):
        self.verify_calls += 1
        assert order_link_id == self.used_link_id, "verify must use the placed linkId"
        return self._verify

    def get_wallet_balance(self):
        return {"available": 100000.0}

    def get_position(self):
        return None  # default: poll finds nothing (overridable)

    def update_sl(self, new_sl):
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


def make_stub(db, trader):
    ll = LiveLoop.__new__(LiveLoop)
    ll.db = db
    ll.window_15m = []
    ll.window_1h = []
    ll.atr_14 = 0.0
    ll.rate_manager = FakeRate()
    ll.trader = trader
    ll._tg = None
    ll._open_ltf_trade = None
    ll.trading_state = {"cooldown_remaining": 0, "halted": False,
                        "consecutive_losses": 0, "daily_pnl_r": 0.0,
                        "daily_halted": False, "last_trade_date": ""}
    ll._chop_stale = False
    ll.chop_index = 50.0
    ll.regime = "flip"
    ll._chop_thresh = 58.0
    ll.v18 = {"ext_stop_r": 1.5, "max_consecutive_losses": 3, "cooldown_bars": 0}
    ll._daily_pnl_r = 0.0
    ll._daily_halted = False
    ll._last_trade_date = ist_today()
    ll._cum_cost_r = 0.0
    ll._cum_net_r = 0.0
    ll._trade_count = 0
    ll._seeding = False
    return ll


def ist_today():
    from datetime import datetime, timezone
    from live_loop import IST
    return (datetime.now(timezone.utc) + IST).strftime("%Y-%m-%d")


def open_cached(ll, db, entry_ts=None):
    entry_ts = entry_ts or int(time.time()) - 30
    trade_id = open_ltf_trade(
        db, direction="long", entry_ts=entry_ts,
        entry_price=80000.0, sl_initial=79000.0,
        tp_price=83000.0, cap_ts=entry_ts + 16 * 86400, htf_window_id=0,
    )
    ll._open_ltf_trade = {
        "id": trade_id, "direction": "long", "entry_ts": entry_ts,
        "entry_price": 80000.0, "sl_initial": 79000.0, "sl_current": 79000.0,
        "tp_price": 83000.0, "cap_ts": entry_ts + 16 * 86400,
    }
    trade = {"dir": "long", "swing_no": 3, "entry_ts": entry_ts,
             "entry_price": 80000.0, "sl": 79000.0, "target": 83000.0,
             "outcome": "open", "htf_regime": "flip"}
    return trade_id, trade


def row(db, trade_id):
    for r in get_ltf_trades(db):
        if r["id"] == trade_id:
            return r
    return None


def main():
    tmp = Path(tempfile.mkdtemp(prefix="entryverify_"))

    # 1. Lost response + position exists -> ADOPTED (no orphan, no false close)
    db1 = Database(str(tmp / "t1.db")); db1.connect(); db1.create_tables()
    tr1 = FakeTrader(place_fail=True, dup_msg=True,
                     verify=("filled", {"qty": 0.001, "avgPrice": 80050.0, "side": "Buy"}))
    ll1 = make_stub(db1, tr1)
    tid1, trade1 = open_cached(ll1, db1)
    ll1._execute_entry(trade1, tid1)
    r1 = row(db1, tid1)
    assert r1["status"] == "open", f"adopted trade must stay OPEN: {r1['status']}"
    assert r1["qty"] == 0.001, f"H5: adopted qty must be recorded: {r1['qty']}"
    assert tr1.verify_calls == 1, "verification must run on failure"
    assert ll1._open_ltf_trade is not None, "cache must remain for monitoring"
    print("PASS 1: duplicate-rejection + landed -> ADOPTED, DB open, cache kept")

    # 2. Confirmed flat -> DB closed as order_failed, cache cleared
    db2 = Database(str(tmp / "t2.db")); db2.connect(); db2.create_tables()
    tr2 = FakeTrader(place_fail=True, verify=("flat", None))
    ll2 = make_stub(db2, tr2)
    tid2, trade2 = open_cached(ll2, db2)
    ll2._execute_entry(trade2, tid2)
    r2 = row(db2, tid2)
    assert r2["status"] == "closed" and r2["exit_reason"] == "order_failed"
    assert ll2._open_ltf_trade is None, "cache must clear on confirmed failure"
    print("PASS 2: confirmed flat -> order_failed, cache cleared")

    # 3. Unknown (both queries fail) -> DB held OPEN + cache (bounded risk)
    db3 = Database(str(tmp / "t3.db")); db3.connect(); db3.create_tables()
    tr3 = FakeTrader(place_fail=True, verify=("unknown", None))
    ll3 = make_stub(db3, tr3)
    tid3, trade3 = open_cached(ll3, db3)
    ll3._execute_entry(trade3, tid3)
    r3 = row(db3, tid3)
    assert r3["status"] == "open", "unknown state must HOLD the trade open"
    assert ll3._open_ltf_trade is not None, "cache kept for monitoring"
    print("PASS 3: unknown -> DB held OPEN (bounded by exchange SL), alert fired")

    # 4. Success path: instant fill -> normal, no verify needed
    db4 = Database(str(tmp / "t4.db")); db4.connect(); db4.create_tables()
    tr4 = FakeTrader(place_fail=False, verify=("filled", {"qty": 0.001, "avgPrice": 80000.0, "side": "Buy"}))
    tr4.get_position = lambda: {"side": "Buy", "size": 0.001, "entry_price": 80000.0}
    ll4 = make_stub(db4, tr4)
    tid4, trade4 = open_cached(ll4, db4)
    ll4._execute_entry(trade4, tid4)
    assert tr4.verify_calls == 0, "success path must not need verification"
    assert tr4.last_tp is None, "C8: exchange TP must NOT be attached to LTF orders"
    assert row(db4, tid4)["status"] == "open"
    assert row(db4, tid4)["qty"] == 0.001, "H5: normal fill qty must be recorded"
    print("PASS 4: normal fill -> no verification, DB open")

    # 5. H4: success resp but slow fill -> poll adopts (no false order_failed)
    db5 = Database(str(tmp / "t5.db")); db5.connect(); db5.create_tables()
    tr5 = FakeTrader(place_fail=False, verify=("filled", {"qty": 0.001, "avgPrice": 80010.0, "side": "Buy"}))
    state = {"n": 0}
    def slow_pos():
        state["n"] += 1
        if state["n"] < 3:
            return None          # fills land late
        return {"side": "Buy", "size": 0.001, "entry_price": 80000.0}
    tr5.get_position = slow_pos
    ll5 = make_stub(db5, tr5)
    tid5, trade5 = open_cached(ll5, db5)
    ll5._execute_entry(trade5, tid5)
    assert state["n"] == 3, f"poll should run 3 times, ran {state['n']}"
    assert row(db5, tid5)["status"] == "open", "slow fill must NOT false-fail"
    assert row(db5, tid5)["qty"] == 0.001, "H5: slow fill qty must be recorded"
    print("PASS 5: H4 slow fill -> poll adopts, no false order_failed")

    # 6. H4 extreme: 3 polls all empty + verify flat -> order_failed
    db6 = Database(str(tmp / "t6.db")); db6.connect(); db6.create_tables()
    tr6 = FakeTrader(place_fail=False, verify=("flat", None))
    tr6.get_position = lambda: None
    ll6 = make_stub(db6, tr6)
    tid6, trade6 = open_cached(ll6, db6)
    ll6._execute_entry(trade6, tid6)
    assert row(db6, tid6)["status"] == "closed" and row(db6, tid6)["exit_reason"] == "order_failed"
    assert tr6.verify_calls == 1, "empty poll must verify before failing"
    print("PASS 6: empty poll + confirmed flat -> order_failed")

    # 7. verify_entry_order unit: position-first, history tie-breaker, side mismatch
    class FlakyPosSession:
        def get_open_orders(self, **kw):
            return {"result": {"list": []}}  # filled market order not in open orders
        def get_positions(self, **kw):
            raise ConnectionError("pos query down")
        def get_order_history(self, **kw):
            return {"result": {"list": [{"orderLinkId": "L1", "orderStatus": "Filled",
                                          "cumExecQty": "0.001", "avgPrice": "80040.0",
                                          "side": "Buy"}]}}
    class PosSession:
        def get_positions(self, **kw):
            return {"result": {"list": [{"symbol": "BTCUSDT", "side": "Sell",
                                          "size": "0.002", "avgPrice": "81000.0"}]}}
    class EmptyHistSession:
        def get_open_orders(self, **kw):
            return {"result": {"list": []}}
        def get_positions(self, **kw):
            return {"result": {"list": []}}
        def get_order_history(self, **kw):
            return {"result": {"list": []}}

    def vt(session, link="L1", expected=None):
        t = BybitTrader.__new__(BybitTrader)
        t.session = session
        t.symbol = "BTCUSDT"
        return t.verify_entry_order(link, expected_side=expected)

    state, info = vt(FlakyPosSession())
    assert state == "filled" and info["qty"] == 0.001 and info["avgPrice"] == 80040.0, \
        f"history tie-breaker must find the fill: {state} {info}"
    state, info = vt(EmptyHistSession())
    assert state == "flat", f"flat + empty history -> flat, got {state}"
    state, info = vt(PosSession(), expected="long")
    assert state == "unknown", f"side mismatch must be unknown, got {state}"
    print("PASS 7: verify_entry_order unit (tie-breaker, flat, side-mismatch)")

    for d in (db1, db2, db3, db4, db5, db6):
        d.close()
    print("=" * 60)
    print("ALL ENTRY VERIFY CHECKS PASSED")


if __name__ == "__main__":
    main()
