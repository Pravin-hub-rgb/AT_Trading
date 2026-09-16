"""M9: rate refresh must never block the event loop on the trade path.

Before M9: _calculate_qty called rate_manager.update() synchronously — a stale
rate triggered up to 2 blocking requests.get(timeout=10) calls (~20s worst
case) right before placing an order, freezing the whole asyncio loop
(ticks, SL checks, exit retries).

After M9: update() runs in _session_watch via asyncio.to_thread (every 30s,
no-ops when fresh); _calculate_qty sizes from the cache and only warns when
the cache is stale.
"""

import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent  # live_stuff/
sys.path.insert(0, str(HERE))

LIVE_LOOP = HERE / "live_loop.py"


def make_loop(rate):
    import live_loop as llmod
    from live_loop import LiveLoop
    ll = LiveLoop.__new__(LiveLoop)

    class FakeTrader:
        qty_step = 0.001
        min_qty = 0.001
        is_connected = False

    ll.trader = FakeTrader()
    ll.rate_manager = rate
    llmod.read_risk_inr = lambda: 250.0
    return ll


def make_rate(age_s):
    """Bare RateManager (no disk load) with _fetch_rate wired to explode.

    RateManager.__new__ is the custom SINGLETON — calling it returns the same
    shared instance every time. Reset _instance first so every make_rate()
    yields a clean object (no attribute leakage between tests).
    """
    from rate_manager import RateManager
    RateManager._instance = None
    rm = RateManager.__new__(RateManager)
    rm.usdt_inr_rate = 88.0
    rm.rate_last_updated = time.time() - age_s
    rm.rate_file = None

    def boom():
        raise AssertionError("network fetch must not happen on this path")

    rm._fetch_rate = boom
    return rm


def test_qty_path_never_fetches():
    """PASS 1: _calculate_qty works with update() poisoned — it must not call it."""
    rate = make_rate(0.0)

    def update_boom():
        raise AssertionError("M9: _calculate_qty must not call rate_manager.update()")

    rate.update = update_boom
    ll = make_loop(rate)
    qty = ll._calculate_qty(80000.0, 79000.0)
    assert abs(qty - 0.003) < 1e-9, f"expected 0.003, got {qty}"
    print("PASS 1: _calculate_qty sizes from cache, never calls update()")


def test_is_stale_logic():
    """PASS 2: is_stale()/age_min() on the real RateManager class."""
    fresh = make_rate(0.0)
    assert not fresh.is_stale(), "fresh rate must not be stale"
    assert fresh.age_min() < 1.0
    old = make_rate(3600.0)  # 1h old, interval is 900s
    assert old.is_stale(), "1h-old rate must be stale"
    assert 59.0 < old.age_min() < 62.0
    print("PASS 2: is_stale()/age_min() correct (fresh vs 1h-old)")


def test_update_noop_when_fresh():
    """PASS 3: update() early-returns on a fresh cache — no fetch, no crash."""
    rm = make_rate(0.0)
    rm.update()  # must return before reaching _fetch_rate (which explodes)
    assert abs(rm.usdt_inr_rate - 88.0) < 1e-9
    print("PASS 3: update() no-ops on fresh cache (no network)")


def test_watch_uses_to_thread():
    """PASS 4 (source guard): _session_watch refreshes via asyncio.to_thread;
    no bare update() call remains anywhere in live_loop.py."""
    src = LIVE_LOOP.read_text(encoding="utf-8")
    assert "await asyncio.to_thread(self.rate_manager.update)" in src, \
        "_session_watch must refresh the rate via asyncio.to_thread"
    assert "self.rate_manager.update()" not in src, \
        "bare update() call found — a blocking fetch returned to a sync path"
    print("PASS 4: only off-loop rate refresh exists (to_thread in _session_watch)")


if __name__ == "__main__":
    test_qty_path_never_fetches()
    test_is_stale_logic()
    test_update_noop_when_fresh()
    test_watch_uses_to_thread()
    print("=" * 50)
    print("ALL M9 ASYNC RATE CHECKS PASSED")
