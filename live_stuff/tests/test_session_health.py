"""H6 + H10/H11 tests: session health, probe-guard separation."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock, patch, PropertyMock


class FakeHTTP:
    """Simulates pybit HTTP session with controllable probe behavior."""
    def __init__(self, probe_ok=True, probe_side_effect=None):
        self._probe_ok = probe_ok
        self._probe_side_effect = probe_side_effect
        self._call_count = 0

    def get_wallet_balance(self, accountType="UNIFIED"):
        self._call_count += 1
        if self._probe_side_effect:
            raise self._probe_side_effect("network down")
        if not self._probe_ok:
            return {"retCode": -1, "retMsg": "error"}
        return {"retCode": 0, "result": {"list": [{"coin": []}]}}

    def get_positions(self, **kwargs):
        return {"retCode": 0, "result": {"list": []}}


def make_trader(probe_ok=True, probe_side_effect=None):
    """Build a BybitTrader with a fake session."""
    from bybit_order import BybitTrader
    t = BybitTrader.__new__(BybitTrader)
    t.session = FakeHTTP(probe_ok=probe_ok, probe_side_effect=probe_side_effect)
    t.api_key = "test_key"
    t.api_secret = "test_secret"
    t.demo = False
    t.symbol = "BTCUSDT"
    t._last_probe_ok = True
    return t


# --- H6 tests (probe, reconnect, watch) ---

def test_probe_success():
    """PASS 1: live session -> probe returns True."""
    t = make_trader(probe_ok=True)
    assert t._probe() is True, "probe should return True for live session"
    print("PASS 1: probe success")


def test_probe_failure():
    """PASS 2: dead session -> probe returns False."""
    t = make_trader(probe_ok=False)
    assert t._probe() is False, "probe should return False for dead session"
    print("PASS 2: probe failure")


def test_probe_no_session():
    """PASS 3: no session object -> probe returns None."""
    t = make_trader()
    t.session = None
    assert t._probe() is None, "probe should return None when no session"
    print("PASS 3: probe no session")


def test_probe_exception():
    """PASS 4: network exception -> probe returns False, no crash."""
    import requests
    t = make_trader(probe_side_effect=requests.ConnectionError)
    assert t._probe() is False, "probe should return False on exception"
    print("PASS 4: probe exception")


def test_reconnect_success():
    """PASS 5: reconnect with valid credentials -> session restored."""
    t = make_trader(probe_ok=False)
    live_session = FakeHTTP(probe_ok=True)
    with patch("bybit_order.HTTP", return_value=live_session):
        ok = t._reconnect()
    assert ok is True, "reconnect should succeed"
    assert t.session is live_session, "session should be replaced"
    print("PASS 5: reconnect success")


def test_reconnect_failure():
    """PASS 6: reconnect with bad credentials -> fails gracefully."""
    t = make_trader(probe_ok=False)
    t.api_key = ""
    t.api_secret = ""
    ok = t._reconnect()
    assert ok is False, "reconnect should fail with empty credentials"
    print("PASS 6: reconnect failure (no credentials)")


def test_probe_uses_real_api():
    """PASS 7: probe calls get_wallet_balance, not just checks object."""
    t = make_trader(probe_ok=True)
    mock_session = MagicMock()
    mock_session.get_wallet_balance.return_value = {"retCode": 0}
    t.session = mock_session
    result = t._probe()
    mock_session.get_wallet_balance.assert_called_once_with(accountType="UNIFIED")
    assert result is True
    print("PASS 7: probe calls real API")


# --- H10 tests (is_connected cheap check, no network) ---

def test_is_connected_no_network_call():
    """PASS 8: is_connected does NOT make API call — cheap local check."""
    t = make_trader(probe_ok=True)
    t.session._call_count = 0
    result = t.is_connected
    assert result is True
    assert t.session._call_count == 0, f"is_connected made {t.session._call_count} API call(s) — should be 0"
    print("PASS 8: is_connected makes no API call")


def test_is_connected_true_with_session():
    """PASS 9: is_connected=True when session exists, even if probe would fail."""
    t = make_trader(probe_ok=False)
    # Session exists but probe would return False
    assert t.session is not None
    assert t.is_connected is True, "is_connected should be True if session exists"
    print("PASS 9: is_connected True with session (probe irrelevant)")


def test_is_connected_false_without_session():
    """PASS 10: is_connected=False when no session."""
    t = make_trader()
    t.session = None
    assert t.is_connected is False
    print("PASS 10: is_connected False without session")


def test_healthy_reflects_cached_probe():
    """PASS 11: _healthy returns cached probe result, not live probe."""
    t = make_trader(probe_ok=True)
    # Set cached result to False (simulating a past probe failure)
    t._last_probe_ok = False
    # _healthy should return False even though a live probe would succeed
    assert t._healthy is False, "_healthy should return cached result"
    print("PASS 11: _healthy reflects cached probe")


def test_healthy_defaults_to_session():
    """PASS 12: _healthy defaults to session existence if no probe yet."""
    t = make_trader()
    if hasattr(t, "_last_probe_ok"):
        del t._last_probe_ok
    assert t._healthy is True, "_healthy should default to session exists"
    print("PASS 12: _healthy defaults to session existence")


def test_probe_caches_result():
    """PASS 13: _probe() updates _last_probe_ok for _healthy."""
    t = make_trader(probe_ok=True)
    t._last_probe_ok = False
    t._probe()
    assert t._last_probe_ok is True, "_probe should cache True on success"
    print("PASS 13: probe caches result")


if __name__ == "__main__":
    test_probe_success()
    test_probe_failure()
    test_probe_no_session()
    test_probe_exception()
    test_reconnect_success()
    test_reconnect_failure()
    test_probe_uses_real_api()
    test_is_connected_no_network_call()
    test_is_connected_true_with_session()
    test_is_connected_false_without_session()
    test_healthy_reflects_cached_probe()
    test_healthy_defaults_to_session()
    test_probe_caches_result()
    print("=" * 50)
    print("ALL SESSION HEALTH + H10/H11 CHECKS PASSED")
