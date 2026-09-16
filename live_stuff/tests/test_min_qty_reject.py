"""M10: reject when computed qty < exchange minimum (silent risk overrun).

Before M10: qty = max(min_qty, computed) — a computed qty below the exchange
minimum was silently forced up to min_qty, multiplying real risk by
min_qty/computed (several x risk_inr on wide stops), or exceeding available
balance in the sized-down path (margin rejection).

After M10: both paths REJECT (return 0.0 -> caller skips the trade) and log
the risk that forcing would have taken.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class FakeTrader:
    def __init__(self, qty_step=0.001, min_qty=0.001, is_connected=False,
                 available=None):
        self.qty_step = qty_step
        self.min_qty = min_qty
        self.is_connected = is_connected
        self._available = available

    def get_wallet_balance(self):
        return {"available": self._available}


class FakeRate:
    def update(self):
        pass

    def get_rate(self):
        return 88.0


def make_loop(risk_inr, trader):
    import live_loop as llmod
    from live_loop import LiveLoop
    ll = LiveLoop.__new__(LiveLoop)
    ll.trader = trader
    ll.rate_manager = FakeRate()
    llmod.read_risk_inr = lambda: risk_inr
    return ll


def test_below_min_rejected():
    """PASS 1: computed qty rounds below min -> REJECT, not force.

    risk=50 INR -> $0.568; stop=2000, fee_buffer=88 -> qty=0.00027 -> rounds to 0.0.
    Before M10 this traded 0.001 BTC = $2.09 forced risk = 3.7x planned.
    """
    ll = make_loop(50.0, FakeTrader())
    qty = ll._calculate_qty(80000.0, 78000.0)
    assert qty == 0.0, f"M10: below-min must reject (0.0), got {qty}"
    print("PASS 1: below-min computed qty rejected")


def test_sub_step_below_min_rejected():
    """PASS 2: qty between qty_step and min_qty (finer step) -> REJECT.

    risk=150 INR -> $1.70; qty=0.000816 with qty_step=0.0001 -> rounds to 0.0008
    which is >= qty_step but < min_qty=0.001 -> must reject.
    """
    ll = make_loop(150.0, FakeTrader(qty_step=0.0001, min_qty=0.001))
    qty = ll._calculate_qty(80000.0, 78000.0)
    assert qty == 0.0, f"M10: sub-min rounded qty must reject, got {qty}"
    print("PASS 2: sub-step rounded qty below min rejected")


def test_normal_qty_unaffected():
    """PASS 3: normal sizing unchanged (regression).

    risk=250 INR -> $2.84; stop=1000, buffer=88 -> qty=0.00261 -> 0.003 >= min.
    Matches the qty every other live test observes.
    """
    ll = make_loop(250.0, FakeTrader())
    qty = ll._calculate_qty(80000.0, 79000.0)
    assert abs(qty - 0.003) < 1e-9, f"M10: normal qty must stay 0.003, got {qty}"
    print("PASS 3: normal sizing unaffected (0.003)")


def test_balance_sized_below_min_rejected():
    """PASS 4: balance-down path below min -> REJECT (would exceed balance).

    Available 1.0 USDT, required 0.003*80000=240 > 0.95 -> sized down to
    1.0*0.9/80000 = 0.000011 -> rounds to 0.0 < min.
    Before M10: forced to 0.001 BTC = $80 notional on a $1 balance.
    """
    ll = make_loop(250.0, FakeTrader(is_connected=True, available=1.0))
    qty = ll._calculate_qty(80000.0, 79000.0)
    assert qty == 0.0, f"M10: balance-sized below-min must reject, got {qty}"
    print("PASS 4: balance-sized qty below min rejected")


if __name__ == "__main__":
    test_below_min_rejected()
    test_sub_step_below_min_rejected()
    test_normal_qty_unaffected()
    test_balance_sized_below_min_rejected()
    print("=" * 50)
    print("ALL M10 MIN-QTY REJECT CHECKS PASSED")
