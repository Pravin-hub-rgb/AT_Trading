"""Book-107 regime + rolling indicators.

Book 107 uses mode="atr_high" only: regime is decided by the 15m ATR%
(ATR(14)/close*100) against atr_high_thresh (default 0.65). No chop, no FD,
no decay legs, no soft/garch modes. This module holds only those pieces so
the live path never pays for the rest.
"""
import math


def atr_pct_series(candles, period=14):
    """Return list of ATR% (ATR(period)/close*100) aligned to candles."""
    n = len(candles)
    out = [0.0] * n
    if n == 0:
        return out
    trs = [0.0] * n
    for i in range(n):
        c = candles[i]
        h = float(c["high"]); l = float(c["low"]); cl = float(c["close"])
        prev_close = float(candles[i-1]["close"]) if i > 0 else cl
        tr = max(h - l, abs(h - prev_close), abs(l - prev_close))
        trs[i] = tr
    # Wilder smoothing
    atr = 0.0
    for i in range(n):
        if i < period:
            atr = (atr * i + trs[i]) / (i + 1) if i > 0 else trs[i]
            # simpler: seed with SMA over first period
        else:
            if i == period:
                atr = sum(trs[:period]) / period
            else:
                atr = (atr * (period - 1) + trs[i]) / period
        cl = float(candles[i]["close"])
        if cl > 0:
            out[i] = atr / cl * 100.0
    # fix first `period` bars with SMA seed
    if n >= period:
        atr = sum(trs[:period]) / period
        for i in range(period - 1, n):
            if i > period - 1:
                atr = (atr * (period - 1) + trs[i]) / period
            cl = float(candles[i]["close"])
            if cl > 0:
                out[i] = atr / cl * 100.0
    return out


class RollingATR:
    """O(1) per bar rolling ATR(period) and ATR%."""

    def __init__(self, period=14):
        self.period = period
        self.trs = []
        self.atr = None

    def update(self, high, low, close, prev_close):
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        self.trs.append(tr)
        if len(self.trs) <= self.period:
            self.atr = sum(self.trs) / len(self.trs)
        else:
            self.atr = (self.atr * (self.period - 1) + tr) / self.period
            # keep buffer bounded
            if len(self.trs) > self.period * 2:
                self.trs = self.trs[-self.period:]
        if close and close > 0:
            return self.atr / close * 100.0
        return 0.0


def regime_atr(atr_pct_value, thresh=0.65):
    """Book 107 regime router: high ATR% -> decisive, else flip."""
    return "decisive" if atr_pct_value > thresh else "flip"