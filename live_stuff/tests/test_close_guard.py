"""Close-guard test (C4 + M2).

Proves a double-close can never corrupt the books:
  1. Double close_ltf_trade -> second returns 0, FIRST exit values preserved
  2. Journal closed-branch on already-closed id -> NO double accounting
     (daily PnL, _trade_count, _cum_net_r unchanged) + cache sync fires
  3. on_tick on already-closed trade -> daily PnL unchanged, cache cleared
  4. Normal single close -> rowcount 1, values recorded

Run: python live_stuff/tests/test_close_guard.py
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # live_stuff/
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from persistence.database import Database
from persistence.trade_store import open_ltf_trade, close_ltf_trade, get_ltf_trades
from live_loop import LiveLoop


class FakeTrader:
    is_connected = True


class FakeRate:
    def get_rate(self):
        return 88.0

    def update(self):
        pass


def make_stub(db, trader=None):
    ll = LiveLoop.__new__(LiveLoop)
    ll.db = db
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


def open_row(db, entry_ts=1_700_000_000):
    return open_ltf_trade(
        db, direction="long", entry_ts=entry_ts,
        entry_price=80000.0, sl_initial=79000.0,
        tp_price=83000.0, cap_ts=entry_ts + 16 * 86400, htf_window_id=0,
    )


def closed_sim_trade(entry_ts=1_700_000_000, direction="long"):
    return {
        "dir": direction, "swing_no": 3, "break_kind": "B2",
        "htf_regime": "flip", "entry_ts": entry_ts,
        "entry_price": 80000.0, "sl": 79000.0, "target": 83000.0,
        "exit_idx": None, "exit_ts": entry_ts + 3600, "exit_date": "",
        "exit_price": 79000.0, "outcome": "sl", "r_multiple": -1.0,
        "bars_held": 5,
    }


def row(db, trade_id):
    for r in get_ltf_trades(db):
        if r["id"] == trade_id:
            return r
    return None


def main():
    tmp = Path(tempfile.mkdtemp(prefix="closeguard_"))

    # 1. Double close -> second returns 0, FIRST exit values preserved
    db1 = Database(str(tmp / "t1.db")); db1.connect(); db1.create_tables()
    tid = open_row(db1)
    n1 = close_ltf_trade(db1, tid, 1_700_010_000, 79000.0, "sl", -1.0)
    n2 = close_ltf_trade(db1, tid, 1_700_999_999, 65000.0, "cap", 99.0)  # bogus overwrite attempt
    assert n1 == 1 and n2 == 0, f"rowcounts must be 1 then 0, got {n1},{n2}"
    r = row(db1, tid)
    assert r["exit_ts"] == 1_700_010_000 and r["exit_price"] == 79000.0
    assert r["exit_reason"] == "sl" and r["r_multiple"] == -1.0, "first close values must win"
    print("PASS 1: double close -> first values preserved, second is no-op")

    # 2. Journal closed-branch with rowcount 0 -> NO accounting, cache syncs
    #    (defensive path: forced via monkeypatch, unreachable via normal dedup)
    import live_loop as ll_mod
    db2 = Database(str(tmp / "t2.db")); db2.connect(); db2.create_tables()
    ll = make_stub(db2, FakeTrader())
    ll._get_existing_trades_set = lambda: set()  # bypass dedup -> hit closed branch
    ll_mod.close_ltf_trade = lambda *a, **k: 0    # simulate already-closed
    # fresh db -> the journal row will get id 1; cache must match for the sync
    ll._open_ltf_trade = {"id": 1, "direction": "long", "entry_ts": 1_700_000_000,
                          "entry_price": 80000.0, "sl_initial": 79000.0,
                          "sl_current": 79000.0, "tp_price": 83000.0}
    ll._journal_trades([closed_sim_trade()])
    assert ll._trade_count == 0, f"trade_count must not increment, got {ll._trade_count}"
    assert ll._daily_pnl_r == 0.0, f"daily PnL must not double-count, got {ll._daily_pnl_r}"
    assert ll._cum_net_r == 0.0 and ll._cum_cost_r == 0.0, "cost accounting must be skipped"
    assert ll._open_ltf_trade is None, "cache must sync to the closed trade"
    ll_mod.close_ltf_trade = close_ltf_trade  # restore
    print("PASS 2: journal closed-branch rowcount-0 -> no accounting, cache synced")

    # 3. on_tick on already-closed trade -> daily PnL unchanged, cache cleared
    db3 = Database(str(tmp / "t3.db")); db3.connect(); db3.create_tables()
    ll3 = make_stub(db3, trader=None)
    tid3 = open_row(db3)
    ll3._open_ltf_trade = {"id": tid3, "direction": "long", "entry_ts": 1_700_000_000,
                           "entry_price": 80000.0, "sl_initial": 79000.0,
                           "sl_current": 79000.0, "tp_price": 83000.0,
                           "cap_ts": 1_700_000_000 + 16 * 86400}
    # close it out-of-band (as if the sim/reconcile already did)
    close_ltf_trade(db3, tid3, 1_700_009_000, 78950.0, "sl", -1.05)
    pnl_before = ll3._daily_pnl_r
    ll3.on_tick(78900.0, 1_700_010_000)  # SL hit -> close returns 0 rows
    assert ll3._daily_pnl_r == pnl_before, f"daily PnL must not double-count: {ll3._daily_pnl_r} vs {pnl_before}"
    assert ll3._open_ltf_trade is None, "stale cache must be cleared"
    print("PASS 3: on_tick on closed trade -> no double daily-PnL, cache cleared")

    # 4. Normal single close -> rowcount 1, values recorded
    db4 = Database(str(tmp / "t4.db")); db4.connect(); db4.create_tables()
    tid4 = open_row(db4)
    assert close_ltf_trade(db4, tid4, 1_700_020_000, 79200.0, "trail", -0.8) == 1
    r4 = row(db4, tid4)
    assert r4["status"] == "closed" and r4["exit_reason"] == "trail" and r4["r_multiple"] == -0.8
    print("PASS 4: normal single close -> rowcount 1, values recorded")

    for d in (db1, db2, db3, db4):
        d.close()
    print("=" * 60)
    print("ALL CLOSE GUARD CHECKS PASSED")


if __name__ == "__main__":
    main()
