"""Incremental HTF window tracker (brick 2).

Wraps `htf_windows.to_intervals` with change detection so the interval list is
only rebuilt when the underlying HTF trade set actually changes. v7 itself still
runs on the retained window (incrementalizing v7 is a separate brick); this
tracker removes the redundant to_intervals work and exposes a stable interface.
"""
from .htf_windows import to_intervals


class HTFWindowTracker:
    def __init__(self, window_end="exit", ext_stop_r=1.5):
        self.window_end = window_end
        self.ext_stop_r = ext_stop_r
        self._last_trade_sig = None
        self._cached = None

    def _sig(self, trades):
        return (len(trades),
                tuple((int(t.get("entry_ts", 0)), str(t.get("outcome", "")),
                       int(t.get("exit_ts", 0))) for t in (trades or [])))

    def update(self, trades, candles_htf=None, fine_ltf=None, fine_ts=None):
        sig = self._sig(trades)
        if sig == self._last_trade_sig and self._cached is not None:
            return self._cached, False
        iv = to_intervals(trades or [], candles_htf=candles_htf, fine_ltf=fine_ltf,
                          fine_ts=fine_ts, ext_stop_r=self.ext_stop_r,
                          window_end=self.window_end)
        self._cached = iv
        self._last_trade_sig = sig
        return iv, True

    @property
    def intervals(self):
        return self._cached if self._cached is not None else []

    @property
    def starts(self):
        return [iv[0] for iv in (self._cached or [])]