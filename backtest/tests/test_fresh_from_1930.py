"""Engine starting FRESH from Sep 8 19:30 — no lookback through engine."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from src.btc.btc_config import load_btc_df
from src.firstswing import SwingEngine
from src.walker import FlowCandle

df = load_btc_df("1h", "BTCUSDT_BYBIT")
candles = []
for row in df.itertuples():
    d = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    candles.append({"date": d, "ts": int(row.ts), "open": float(row.open),
                    "high": float(row.high), "low": float(row.low), "close": float(row.close)})

target = "2026-09-08 19:30:00"
seed_idx = next(i for i, c in enumerate(candles) if c["date"] == target)
print(f"Seed: {target} (bar {seed_idx})")
print(f"Starting engine FRESH from seed point — no lookback through engine\n")

eng = SwingEngine({"minBars": 20})
swing_index = 0

for i in range(seed_idx, len(candles)):
    c = candles[i]
    fc = FlowCandle(date=c["date"], open=c["open"], high=c["high"],
                    low=c["low"], close=c["close"])
    eng.process_bar(fc, i - seed_idx)

    if eng.declared:
        brks = [(b.kind, b.dir, round(b.px, 1)) for b in eng.break_marks]
        conf = c["date"]
        seg_start = eng.start_px
        seg_end = eng.end_px
        print(f"SWING {swing_index} DECLARED @ {conf}")
        print(f"  dir={eng.dir} | source={eng.confirm_source}")
        print(f"  seg: {seg_start:.1f} -> {seg_end:.1f}")
        for kind, dir_, px in brks:
            print(f"    {kind:5s} {dir_:4s} @ {px:.1f}")
        print()
        swing_index += 1
        eng = SwingEngine({"minBars": 20})
        eng.defer_same_bar_arm = True

print(f"OPEN SWING after {swing_index} declared:")
print(f"  dir={eng.dir}, armed={eng.armed}, state={eng.state}")
print(f"  break_marks: {[(b.kind, b.dir, round(b.px, 1)) for b in eng.break_marks]}")
print(f"  latest_sealed_high: {eng.latest_sealed_high.px:.1f}")
print(f"  latest_sealed_low: {eng.latest_sealed_low.px:.1f}")
