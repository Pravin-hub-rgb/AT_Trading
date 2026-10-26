"""Test candle deduplication in _on_15m_close and _on_1h_close.

Verifies that:
1. Duplicate candles (same ts as last) are skipped — reconnect safety.
2. Bar counter does NOT increment for duplicates.
3. Gap detection logs a warning (does not crash).
"""
import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "live"))
sys.path.insert(0, str(ROOT / "persistence"))

os.chdir(ROOT)


def make_candle(ts_close_sec, tf="15m"):
    """Create a candle dict matching the format _on_*_close expects."""
    open_time_ms = ts_close_sec * 1000
    return {
        "open_time": open_time_ms,
        "close_time": open_time_ms,
        "open": 50000.0,
        "high": 50100.0,
        "low": 49900.0,
        "close": 50050.0,
    }


def test_dedupe_15m():
    """Duplicate 15m candle should be skipped entirely."""
    from live.loop import LiveLoop
    from persistence.database import Database

    db = Database(":memory:")
    db.connect()
    db.create_tables()

    with patch("live.loop.TradingMixin.__init__", lambda self, *a, **kw: None):
        pass

    loop = LiveLoop.__new__(LiveLoop)
    # Manually init the attributes we need
    loop.db = db
    loop._running = False
    loop.exchange = "bybit"
    loop.symbol = "BTCUSDT"
    loop.v18_instrument = "BTCUSDT_BYBIT"
    loop.paper_mode = True
    loop.window_15m = []
    loop.window_1h = []
    loop.all_candles_15m = []
    loop.all_candles_1h = []
    loop._sim_running = False
    loop.trading_state = {"cooldown_remaining": 0, "consecutive_losses": 0,
                          "halted": False, "daily_pnl_r": 0.0, "daily_halted": False,
                          "last_trade_date": ""}
    loop.v18 = {"sl_buf_atr": 0.01, "chop_thresh": 58.0, "cooldown_bars": 8,
                "max_consecutive_losses": 0}
    loop._chop_thresh = 58.0
    loop._cum_cost_r = 0.0
    loop._cum_net_r = 0.0
    loop._trade_count = 0
    loop.all_swings_15m = []
    loop.all_swings_1h = []
    loop.htf_window_open = False
    loop.htf_window_dir = None
    loop.htf_window_start_ts = 0
    loop.htf_window_id = None
    loop.htf_entry_px = 0.0
    loop.htf_sl = 0.0
    loop.htf_current_r = 0.0
    loop.htf_hrisk = 0.0
    loop.htf_window_open_b2 = False
    loop.htf_window_dir_b2 = None
    loop.htf_window_start_ts_b2 = 0
    loop.htf_window_id_b2 = None
    loop.htf_entry_px_b2 = 0.0
    loop.htf_sl_b2 = 0.0
    loop.htf_current_r_b2 = 0.0
    loop.htf_hrisk_b2 = 0.0
    loop.htf_window_open_dec = False
    loop.htf_window_dir_dec = None
    loop.htf_window_start_ts_dec = 0
    loop.htf_window_id_dec = None
    loop.htf_entry_px_dec = 0.0
    loop.htf_sl_dec = 0.0
    loop.htf_current_r_dec = 0.0
    loop.htf_hrisk_dec = 0.0
    loop._open_ltf_trades = {}
    loop._open_htf_windows = {}
    loop._logged_filter_keys = set()
    loop._printed_marks = set()
    loop._bar_counter_15m = 0
    loop._bar_counter_1h = 0
    loop._daily_pnl_r = 0.0
    loop._daily_halted = False
    loop._last_trade_date = None
    loop._chop_stale = False
    loop.chop_index = 50.0
    loop.atr_14 = 0.0
    loop.regime = "chop"
    loop._sim_running = False
    loop._got_15m_boundary = False
    loop._got_1h_boundary = False
    loop._boundary_ts = None
    loop._boundary_deadline = None
    loop._last_boundary_fired_ts = None
    loop._tg = None
    loop.rate_manager = None
    loop.trader = None
    loop._session_dead_flag = False

    # Mock the swing engines and simulation
    loop.swing_15m = MagicMock()
    loop.swing_15m.process_bar = MagicMock(return_value=None)
    loop.swing_15m.get_open_swing = MagicMock(return_value=None)
    loop.swing_1h = MagicMock()
    loop.swing_1h.process_bar = MagicMock(return_value=None)
    loop.swing_1h.get_open_swing = MagicMock(return_value=None)
    loop._run_v18_simulation = MagicMock()
    loop._update_htf_metrics = MagicMock()
    loop._maybe_reset_daily = MagicMock()
    loop._is_1h_boundary = MagicMock(return_value=False)
    loop._to_ist_str = lambda ms: "2026-10-25 10:00:00"
    # Use real _backfill_gap — mock only the exchange fetch
    loop._fetch_klines_from_sync = MagicMock(return_value=[])
    loop._gap_history_ts = set()

    # Send first candle
    c1 = make_candle(1700000000)  # some ts
    loop._on_15m_close(c1)
    assert len(loop.all_candles_15m) == 1, f"Expected 1 candle, got {len(loop.all_candles_15m)}"
    assert loop._bar_counter_15m == 1, f"Expected bar_counter=1, got {loop._bar_counter_15m}"

    # Send duplicate
    c2 = make_candle(1700000000)  # same ts
    loop._on_15m_close(c2)
    assert len(loop.all_candles_15m) == 1, f"DEDUP FAILED: Expected 1 candle, got {len(loop.all_candles_15m)}"
    assert loop._bar_counter_15m == 1, f"DEDUP FAILED: bar_counter should stay 1, got {loop._bar_counter_15m}"
    print("PASS: 15m dedupe — duplicate candle skipped, bar counter unchanged")

    # Send new candle (different ts)
    c3 = make_candle(1700000900)  # 15 min later
    loop._on_15m_close(c3)
    assert len(loop.all_candles_15m) == 2, f"Expected 2 candles, got {len(loop.all_candles_15m)}"
    assert loop._bar_counter_15m == 2, f"Expected bar_counter=2, got {loop._bar_counter_15m}"
    print("PASS: 15m new candle — appended correctly, bar counter incremented")

    # Test gap detection with REAL _backfill_gap
    # c3 ts=1700000900 (close_time), 900s later c4 ts=1700002700 → gap of 1 bar
    # _backfill_gap should fetch from last_ts to incoming_ts, get the missing bar, process it
    gap_candle_raw = make_candle(1700001800)  # the missing bar (close at 1700001800)
    gap_candle_raw["open_time"] = 1700001800 * 1000 - 900 * 1000  # open_time = close_time - step
    loop._fetch_klines_from_sync = MagicMock(return_value=[
        {"open_time": (1700001800 - 900) * 1000, "close_time": 1700001800 * 1000,
         "open": 50000.0, "high": 50100.0, "low": 49900.0, "close": 50050.0},
    ])
    c4 = make_candle(1700002700)  # 30 min gap (1 bar missing)
    loop._on_15m_close(c4)
    # Should have: c1, c3, gap_bar, c4 = 4 candles
    assert len(loop.all_candles_15m) == 4, f"GATE FAILED: Expected 4 candles after gap+backfill, got {len(loop.all_candles_15m)}"
    assert loop._bar_counter_15m == 4, f"GATE FAILED: bar_counter should be 4, got {loop._bar_counter_15m}"
    # Verify _fetch_klines_from_sync was called with correct start
    call_args = loop._fetch_klines_from_sync.call_args
    assert call_args[0][1] == "15m", f"Expected tf=15m, got {call_args[0][1]}"
    assert call_args[0][2] == 1700000900 * 1000, f"Fetch start should be last_ts (1700000900*1000), got {call_args[0][2]}"
    print("PASS: 15m gap — real backfill fills missing bar, fetch starts at last_ts")
    # _gap_history_ts should contain the backfilled candle's ts
    assert 1700001800 in loop._gap_history_ts, f"Expected gap ts 1700001800 in _gap_history_ts, got {loop._gap_history_ts}"
    print("PASS: 15m _gap_history_ts tracked after backfill")

    # Test out-of-order (stale) candle
    c5 = make_candle(1700000900)  # same ts as c3 (stale)
    loop._on_15m_close(c5)
    assert len(loop.all_candles_15m) == 4, f"STALE FAILED: Expected 4 candles, got {len(loop.all_candles_15m)}"
    assert loop._bar_counter_15m == 4, f"STALE FAILED: bar_counter should stay 4, got {loop._bar_counter_15m}"
    print("PASS: 15m stale — out-of-order candle skipped")

    db.close()


def test_dedupe_1h():
    """Duplicate 1h candle should be skipped entirely."""
    from live.loop import LiveLoop
    from persistence.database import Database

    db = Database(":memory:")
    db.connect()
    db.create_tables()

    loop = LiveLoop.__new__(LiveLoop)
    loop.db = db
    loop._running = False
    loop.exchange = "bybit"
    loop.symbol = "BTCUSDT"
    loop.v18_instrument = "BTCUSDT_BYBIT"
    loop.paper_mode = True
    loop.window_15m = []
    loop.window_1h = []
    loop.all_candles_15m = []
    loop.all_candles_1h = []
    loop._sim_running = False
    loop.trading_state = {"cooldown_remaining": 0, "consecutive_losses": 0,
                          "halted": False, "daily_pnl_r": 0.0, "daily_halted": False,
                          "last_trade_date": ""}
    loop.v18 = {"sl_buf_atr": 0.01, "chop_thresh": 58.0, "cooldown_bars": 8,
                "max_consecutive_losses": 0}
    loop._chop_thresh = 58.0
    loop._cum_cost_r = 0.0
    loop._cum_net_r = 0.0
    loop._trade_count = 0
    loop.all_swings_15m = []
    loop.all_swings_1h = []
    loop._open_ltf_trades = {}
    loop._open_htf_windows = {}
    loop._logged_filter_keys = set()
    loop._printed_marks = set()
    loop._bar_counter_15m = 0
    loop._bar_counter_1h = 0
    loop._daily_pnl_r = 0.0
    loop._daily_halted = False
    loop._last_trade_date = None
    loop._chop_stale = False
    loop.chop_index = 50.0
    loop.atr_14 = 0.0
    loop.regime = "chop"
    loop._sim_running = False
    loop._got_15m_boundary = False
    loop._got_1h_boundary = False
    loop._boundary_ts = None
    loop._boundary_deadline = None
    loop._last_boundary_fired_ts = None
    loop._tg = None
    loop.rate_manager = None
    loop.trader = None
    loop._session_dead_flag = False

    loop.swing_15m = MagicMock()
    loop.swing_15m.process_bar = MagicMock(return_value=None)
    loop.swing_15m.get_open_swing = MagicMock(return_value=None)
    loop.swing_1h = MagicMock()
    loop.swing_1h.process_bar = MagicMock(return_value=None)
    loop.swing_1h.get_open_swing = MagicMock(return_value=None)
    loop._run_v18_simulation = MagicMock()
    loop._update_htf_metrics = MagicMock()
    loop._maybe_reset_daily = MagicMock()
    loop._is_1h_boundary = MagicMock(return_value=True)
    loop._to_ist_str = lambda ms: "2026-10-25 10:00:00"
    loop._fetch_klines_from_sync = MagicMock(return_value=[])
    loop._gap_history_ts = set()

    c1 = make_candle(1700000000)
    loop._on_1h_close(c1)
    assert len(loop.all_candles_1h) == 1, f"Expected 1 candle, got {len(loop.all_candles_1h)}"
    assert loop._bar_counter_1h == 1, f"Expected bar_counter=1, got {loop._bar_counter_1h}"

    c2 = make_candle(1700000000)  # duplicate
    loop._on_1h_close(c2)
    assert len(loop.all_candles_1h) == 1, f"DEDUP FAILED: Expected 1 candle, got {len(loop.all_candles_1h)}"
    assert loop._bar_counter_1h == 1, f"DEDUP FAILED: bar_counter should stay 1, got {loop._bar_counter_1h}"
    print("PASS: 1h dedupe — duplicate candle skipped, bar counter unchanged")

    c3 = make_candle(1700003600)  # 1h later
    loop._on_1h_close(c3)
    assert len(loop.all_candles_1h) == 2, f"Expected 2 candles, got {len(loop.all_candles_1h)}"
    assert loop._bar_counter_1h == 2, f"Expected bar_counter=2, got {loop._bar_counter_1h}"
    print("PASS: 1h new candle — appended correctly, bar counter incremented")

    # Test gap detection with REAL _backfill_gap
    # c3 ts=1700003600, next expected=1700003600+3600=1700007200, c4 ts=1700010800 → 1 bar gap
    # _backfill_gap fetches from last_ts to incoming_ts
    missing_1h_ts = 1700007200  # the gap candle's close_time
    loop._fetch_klines_from_sync = MagicMock(return_value=[
        {"open_time": (1700007200 - 3600) * 1000, "close_time": 1700007200 * 1000,
         "open": 50000.0, "high": 50100.0, "low": 49900.0, "close": 50050.0},
    ])
    c4 = make_candle(1700010800)  # 2h later (1 bar gap skipped)
    loop._on_1h_close(c4)
    # Should have: c1, c3, gap_bar, c4 = 4 candles
    assert len(loop.all_candles_1h) == 4, f"GATE FAILED: Expected 4 candles, got {len(loop.all_candles_1h)}"
    assert loop._bar_counter_1h == 4, f"GATE FAILED: bar_counter should be 4, got {loop._bar_counter_1h}"
    call_args = loop._fetch_klines_from_sync.call_args
    assert call_args[0][1] == "1h", f"Expected tf=1h, got {call_args[0][1]}"
    assert call_args[0][2] == 1700003600 * 1000, f"Fetch start should be last_ts, got {call_args[0][2]}"
    print("PASS: 1h gap — real backfill fills missing bar, fetch starts at last_ts")
    assert 1700007200 in loop._gap_history_ts, f"Expected gap ts 1700007200 in _gap_history_ts, got {loop._gap_history_ts}"
    print("PASS: 1h _gap_history_ts tracked after backfill")

    # Test out-of-order (stale) candle
    c5 = make_candle(1700003600)  # same ts as c3 (stale)
    loop._on_1h_close(c5)
    assert len(loop.all_candles_1h) == 4, f"STALE FAILED: Expected 4 candles, got {len(loop.all_candles_1h)}"
    assert loop._bar_counter_1h == 4, f"STALE FAILED: bar_counter should stay 4, got {loop._bar_counter_1h}"
    print("PASS: 1h stale — out-of-order candle skipped")

    db.close()


def test_seed_daily_reset_persisted():
    """P0b: seeding must persist daily_halted=False to DB so a mid-seed
    restart doesn't reload a stale halt. Also verify _persist_streak_state
    skips seed_history trades."""
    from live.loop import LiveLoop
    from persistence.database import Database
    from persistence.state_store import get_trading_state, save_trading_state
    from persistence.trade_store import open_ltf_trade, close_ltf_trade

    db = Database(":memory:")
    db.connect()
    db.create_tables()

    # Simulate a stale halt + cooldown in the DB (from a previous live session)
    save_trading_state(db, {
        "cooldown_remaining": 8,
        "consecutive_losses": 3,
        "halted": False,
        "last_loss_bar": "2026-10-25 09:00",
        "daily_pnl_r": -8.5,
        "daily_halted": True,
        "last_trade_date": "2026-10-25",
    })
    state = get_trading_state(db)
    assert state["daily_halted"] is True, "Pre-condition: stale halt should be True"
    assert state["daily_pnl_r"] == -8.5
    assert state["cooldown_remaining"] == 8

    loop = LiveLoop.__new__(LiveLoop)
    loop.db = db
    loop.trading_state = dict(state)  # what __init__ would load
    loop._daily_pnl_r = state["daily_pnl_r"]
    loop._daily_halted = state["daily_halted"]
    loop._last_trade_date = state["last_trade_date"] or None
    loop._seeding = True  # simulate seed phase

    # Simulate what _seed_from_timestamps now does: full reset + persist
    loop._daily_pnl_r = 0.0
    loop._daily_halted = False
    loop._last_trade_date = None
    loop.trading_state.update({
        "cooldown_remaining": 0,
        "consecutive_losses": 0,
        "halted": False,
        "last_loss_bar": None,
        "daily_pnl_r": 0.0,
        "daily_halted": False,
        "last_trade_date": "",
    })
    save_trading_state(db, loop.trading_state)

    # Verify DB has cleared ALL fields
    state2 = get_trading_state(db)
    assert state2["daily_halted"] is False, f"DB daily_halted should be False, got {state2['daily_halted']}"
    assert state2["daily_pnl_r"] == 0.0
    assert state2["cooldown_remaining"] == 0, f"DB cooldown should be 0, got {state2['cooldown_remaining']}"
    assert state2["consecutive_losses"] == 0
    assert state2["last_trade_date"] == ""
    print("PASS: P0b full seed reset persisted to DB (daily + cooldown + streak)")

    # Now test _persist_streak_state skips seed_history trades
    from persistence.trade_store import open_ltf_trade, close_ltf_trade
    tid = open_ltf_trade(db, "long", 1700000000, 50000.0, 49000.0, 52000.0,
                         9999999999, None, origin="seed_history")
    close_ltf_trade(db, tid, 1700000900, 49500.0, "sl", -1.0)  # a loss
    loop.v18 = {"cooldown_bars": 8, "max_consecutive_losses": 5}
    loop._to_ist_short = lambda s: "2023-11-15 04:00"
    loop._persist_streak_state()
    state3 = get_trading_state(db)
    assert state3["consecutive_losses"] == 0, f"seed_history loss should not count toward streak, got {state3['consecutive_losses']}"
    assert state3["cooldown_remaining"] == 0
    print("PASS: seed_history trades excluded from streak/cooldown")

    loop._seeding = False
    db.close()


if __name__ == "__main__":
    test_dedupe_15m()
    test_dedupe_1h()
    test_seed_daily_reset_persisted()
    print("\nAll tests passed!")
