import sys, random
sys.path.insert(0, "C:/Users/Pravin/Desktop/main/AT_Trading/live_stuff")
sys.path.insert(0, "C:/Users/Pravin/Desktop/main/AT_Trading/live_stuff/live")
from regime import atr_pct_series, RollingATR, regime_atr


def test_rolling_atr_matches_batch():
    random.seed(42)
    candles = []
    ts = 1700000000
    for i in range(60):
        ts += 900
        o = random.uniform(99, 101); c = random.uniform(99, 101)
        h = max(o, c) + random.uniform(0, 1); l = min(o, c) - random.uniform(0, 1)
        candles.append({"ts": ts, "open": o, "high": h, "low": l, "close": c})

    batch = atr_pct_series(candles, 14)

    roll = []
    ra = RollingATR(14)
    prev_close = None
    for cd in candles:
        if prev_close is None:
            prev_close = float(cd["close"])
        v = ra.update(float(cd["high"]), float(cd["low"]), float(cd["close"]), prev_close)
        roll.append(v)
        prev_close = float(cd["close"])

    maxdiff = max(abs(a - b) for a, b in zip(batch, roll))
    assert maxdiff < 1e-9, f"MISMATCH {maxdiff}"


def test_regime_atr():
    assert regime_atr(0.70, 0.65) == "decisive"
    assert regime_atr(0.50, 0.65) == "flip"
    assert regime_atr(0.65, 0.65) == "flip"