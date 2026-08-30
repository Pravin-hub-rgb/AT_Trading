"""Trace what normal_lows contains at the moment of long trade entry."""
import sys
sys.path.insert(0, "backend")
import pandas as pd
from src.intraday import _prep_day, _classify_first_swing_v2, DEFAULT_CFG, FALLBACK_AVG_RANGE, MIN_CANDLES
from src.walker import WalkerEngine, FlowCandle
from src.config import DATA_DIR

df = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["date"] = df["timestamp"].dt.date
sub = df[df["date"] == pd.Timestamp("2026-05-29").date()].copy()
sub = sub.reset_index(drop=True)
sub["time"] = sub["timestamp"].dt.strftime("%H:%M")

candles = _prep_day(sub)
walker = WalkerEngine()
normal_lows = []
normal_highs = []

# Feed bar-by-bar
for i, c in enumerate(candles):
    fc = FlowCandle(date=f"2026-05-29T{c['time']}:00", open=c["open"], high=c["high"], low=c["low"], close=c["close"])
    pivots = walker.process_bar(fc, i)
    new_p = list(pivots)  # COPY because list of pivots is the reference
    for p in new_p:
        if p.kind == "H":
            normal_highs.append(p)
        else:
            normal_lows.append(p)
    # Print state at each bar
    if c["time"] in ("09:30", "09:40", "09:45", "09:50", "09:55", "10:00", "10:50"):
        nL = len(normal_lows)
        last_L = normal_lows[-1] if normal_lows else None
        last_H = normal_highs[-1] if normal_highs else None
        print(f"bar={i:02d} {c['time']}: lows={nL}, last_L=({last_L.time if last_L else 'NA'} {last_L.px if last_L else 'NA'}), last_H=({last_H.time if last_H else 'NA'} {last_H.px if last_H else 'NA'}), new_this_bar={[(p.time, p.kind, p.px, p.sealed) for p in new_p]}")
