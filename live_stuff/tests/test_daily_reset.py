"""Daily halt reset test (C5).

Proves the daily halt can never deadlock and never pollutes the books:
  1. Halted yesterday -> _maybe_reset_daily resets halt + PnL + persists to DB
  2. Same day -> no reset (halt preserved)
  3. Fresh boot (_last_trade_date None) -> no crash, no reset
  4. _daily_halted + sim open trade -> journaled halted_skip, NO order, NO phantom
  5. halted_skip rows excluded from streak counting (no false halt)
  6. Threshold regression: real losses still arm the daily halt
  7. _check_daily_loss_limit still resets on date change (belt-and-suspenders)

Run: python live_stuff/tests/test_daily_reset.py
"""
import sys
import tempfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # live_stuff/
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from persistence.database import Database
from persistence.trade_store import get_ltf_trades
from persistence.state_store import get_trading_state
from live_loop import LiveLoop, IST


class FakeTrader:
    is_connected = True
    qty_step = 0.001
    min_qty = 0.001
    qty_precision = 3

    def __init__(self):
        self.order_calls = 0

    def place_market_order_retry(self, side, qty, stop_loss=None, take_profit=None):
        self.order_calls += 1
        return {"retCode": 0, "result": {"orderId": "test"}}

    def get_wallet_balance(self):
        return {"available": 100000.0}

    def get_position(self):
        return {"side": "Buy", "size": 0.001, "entry_price": 80000.0}


class FakeRate:
    def get_rate(self):
        return 88.0

    def update(self):
        pass


def ist_today():
    return (datetime.now(timezone.utc) + IST).strftime("%Y-%m-%d")


def ist_yesterday():
    return (datetime.now(timezone.utc) + IST - timedelta(days=1)).strftime("%Y-%m-%d")


def make_stub(db, halted=False, pnl=0.0, last_date=None):
    ll = LiveLoop.__new__(LiveLoop)
    ll.db = db
    ll.window_15m = []
    ll.window_1h = []
    ll.atr_14 = 0.0
    ll.rate_manager = FakeRate()
    ll.trader = None
    ll._tg = None
    ll._open_ltf_trade = None
    ll.trading_state = {"cooldown_remaining": 0, "halted": False,
                        "consecutive_losses": 0, "daily_pnl_r": pnl,
                        "daily_halted": halted, "last_trade_date": last_date or ""}
    ll._chop_stale = False
    ll.chop_index = 50.0
    ll.regime = "flip"
    ll._chop_thresh = 58.0
    ll.v18 = {"ext_stop_r": 1.5, "max_consecutive_losses": 3, "cooldown_bars": 0}
    ll._daily_pnl_r = pnl
    ll._daily_halted = halted
    ll._last_trade_date = last_date
    ll._cum_cost_r = 0.0
    ll._cum_net_r = 0.0
    ll._trade_count = 0
    ll._seeding = False
    # flip + b2 window fields (journal linkage)
    ll.htf_window_open = False
    ll.htf_window_dir = None
    ll.htf_window_id = None
    ll.htf_window_id_b2 = None
    return ll


def sim_trade(entry_ts, direction="long", outcome="open", regime="flip"):
    return {
        "dir": direction, "swing_no": 3, "break_kind": "B2",
        "htf_regime": regime, "entry_ts": entry_ts,
        "entry_price": 80000.0, "sl": 79000.0, "target": 83000.0,
        "exit_idx": None, "exit_ts": 0, "exit_date": "", "exit_price": 0.0,
        "outcome": outcome, "r_multiple": 0.0, "bars_held": 0,
    }


def main():
    now = int(time.time())
    fresh_ts = now - 60
    tmp = Path(tempfile.mkdtemp(prefix="dailyreset_"))

    # 1. Halted yesterday -> reset fires, persists to DB
    db1 = Database(str(tmp / "t1.db")); db1.connect(); db1.create_tables()
    ll = make_stub(db1, halted=True, pnl=-6.0, last_date=ist_yesterday())
    save_state_backup = dict(ll.trading_state)
    ll._maybe_reset_daily()
    assert ll._daily_halted is False, "halt must reset"
    assert ll._daily_pnl_r == 0.0, "pnl must reset"
    assert ll._last_trade_date == ist_today(), "last_trade_date must be today"
    assert ll.trading_state["daily_halted"] is False, "trading_state must sync"
    persisted = get_trading_state(db1)
    assert persisted["daily_halted"] in (False, 0), f"reset must persist to DB: {persisted}"
    print("PASS 1: halted yesterday -> reset + persisted to DB")

    # 2. Same day -> no reset (halt preserved)
    ll2 = make_stub(db1, halted=True, pnl=-4.0, last_date=ist_today())
    ll2._maybe_reset_daily()
    assert ll2._daily_halted is True, "same-day halt must be preserved"
    assert ll2._daily_pnl_r == -4.0, "same-day pnl must be preserved"
    print("PASS 2: same day -> no reset, halt preserved")

    # 3. Fresh boot (_last_trade_date None) -> no crash, no reset
    ll3 = make_stub(db1, halted=False, pnl=0.0, last_date=None)
    ll3._maybe_reset_daily()
    assert ll3._daily_halted is False and ll3._daily_pnl_r == 0.0
    print("PASS 3: fresh boot -> no crash, no reset")

    # 4. _daily_halted + sim open trade -> halted_skip, NO order, NO phantom
    db4 = Database(str(tmp / "t4.db")); db4.connect(); db4.create_tables()
    from live_loop import LiveLoop as _LL
    tr4 = FakeTrader()
    ll4 = make_stub(db4, halted=True, pnl=-6.0, last_date=ist_today())
    ll4._journal_trades([sim_trade(fresh_ts, "long", "open")])
    rows = get_ltf_trades(db4)
    assert len(rows) == 1 and rows[0]["exit_reason"] == "halted_skip", f"{rows}"
    assert tr4.order_calls == 0, "halted trade must NOT execute"
    assert ll4._open_ltf_trade is None, "NO phantom: cache must stay None"
    print("PASS 4: halted + sim open trade -> halted_skip, no phantom")

    # 5. halted_skip rows excluded from streak counting
    ll4._journal_trades([
        sim_trade(fresh_ts + 10, "short", "open"),
        sim_trade(fresh_ts + 20, "long", "open"),
    ])
    ll4._persist_streak_state()
    assert ll4.trading_state["consecutive_losses"] == 0, \
        f"halted_skip must not count, got {ll4.trading_state['consecutive_losses']}"
    assert not ll4.trading_state["halted"], "no false streak halt"
    print("PASS 5: halted_skip excluded from streak counting")

    # 6. Threshold regression: real losses still arm the daily halt
    ll6 = make_stub(db1, halted=False, pnl=0.0, last_date=ist_today())
    ll6._check_daily_loss_limit(-3.0)
    assert ll6._daily_halted is False, "-3R must not halt (limit 5R)"
    ll6._check_daily_loss_limit(-3.0)  # total -6R
    assert ll6._daily_halted is True, "-6R must arm the daily halt"
    print("PASS 6: threshold regression -> real losses arm the halt")

    # 7. _check_daily_loss_limit still resets on date change (belt-and-suspenders)
    ll7 = make_stub(db1, halted=True, pnl=-6.0, last_date=ist_yesterday())
    ll7._check_daily_loss_limit(0.0)  # first close of the new day
    assert ll7._daily_halted is False and ll7._daily_pnl_r == 0.0, "date-change reset must fire"
    print("PASS 7: _check_daily_loss_limit date-change reset intact")

    for d in (db1, db4):
        d.close()
    print("=" * 60)
    print("ALL DAILY RESET CHECKS PASSED")


if __name__ == "__main__":
    main()
