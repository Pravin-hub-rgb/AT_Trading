import sys, random
sys.path.insert(0, "C:/Users/Pravin/Desktop/main/AT_Trading/live_stuff")
sys.path.insert(0, "C:/Users/Pravin/Desktop/main/AT_Trading/live_stuff/live")
from regime import atr_pct_series, RollingATR

random.seed(42)
candles = []
ts = 1700000000
prev = 100.0
for i in range(60):
    ts += 900
    o = random.uniform(99,101); c = random.uniform(99,101)
    h = max(o,c)+random.uniform(0,1); l = min(o,c)-random.uniform(0,1)
    candles.append({"ts":ts,"open":o,"high":h,"low":l,"close":c})
    prev = c

batch = atr_pct_series(candles, 14)

# rolling
roll = []
ra = RollingATR(14)
prev_close = None
for cd in candles:
    if prev_close is None:
        prev_close = float(cd["close"])
    v = ra.update(float(cd["high"]), float(cd["low"]), float(cd["close"]), prev_close)
    roll.append(v)
    prev_close = float(cd["close"])

maxdiff = max(abs(a-b) for a,b in zip(batch, roll))
print("max diff rolling vs batch:", maxdiff)
assert maxdiff < 1e-9, "MISMATCH"
print("PASS: rolling ATR matches batch within", maxdiff)