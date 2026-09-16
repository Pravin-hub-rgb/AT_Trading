"""H6 tests: session health probe, reconnect, background watch."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock, patch, PropertyMock


class FakeHTTP:
    """Simulates pybit HTTP session with controllable probe behavior."""
    def __init__(self, probe_ok=True, probe_side_effect=None):
        self._probe_ok = probe_ok
        self._probe_side_effect = probe_side_effect

    def get_wallet_balance(self, accountType="UNIFIED"):
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
    t.logger = None  # should not be used after fix
    return t


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
    # Patch HTTP to return a live session on reconnect
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


if __name__ == "__main__":
    test_probe_success()
    test_probe_failure()
    test_probe_no_session()
    test_probe_exception()
    test_reconnect_success()
    test_reconnect_failure()
    test_probe_uses_real_api()
    print("=" * 50)
    print("ALL SESSION HEALTH CHECKS PASSED")
