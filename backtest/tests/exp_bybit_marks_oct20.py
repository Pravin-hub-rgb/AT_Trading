"""Fetch Bybit klines from Oct 20 2026, run swing engine, print B1/B2/FLIP/DECISIVE marks.

Lets you verify swing marks against TradingView for a specific date range.
Uses the live_stuff Bybit backfill + the vendored swing engine (same as live).
"""
import sys, time, json
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff"))

from bybit_streamer import backfill_klines_bybit
from _vendored.persistent_swing import PersistentSwingEngine
from persistence.database import Database
from _vendored.walker import FlowCandle
from book import SWING

IST = timedelta(hours=5, minutes=30)

# Oct 20 2026 00:00 IST = Oct 19 2026 18:30 UTC
start_dt = datetime(2026, 10, 19, 18, 30, 0, tzinfo=timezone.utc)
start_ms = int(start_dt.timestamp() * 1000)

now_ms = int(time.time() * 1000)
want_15m = min(20000, (now_ms - start_ms) // 900000 + 50)
want_1h = min(5000, (now_ms - start_ms) // 3600000 + 50)

print(f"[fetch] 15m from {start_dt} ({want_15m} bars max), 1h ({want_1h} bars max)")

raw_15m = backfill_klines_bybit("BTCUSDT", "15", limit=want_15m, demo=True, start_ms=start_ms)
raw_1h = backfill_klines_bybit("BTCUSDT", "60", limit=want_1h, demo=True, start_ms=start_ms)

# Filter out live/incomplete candles
raw_15m = [c for c in raw_15m if c.get("close_time", c.get("open_time", 0)) <= now_ms]
raw_1h = [c for c in raw_1h if c.get("close_time", c.get("open_time", 0)) <= now_ms]
print(f"[fetch] 15m: {len(raw_15m)} candles, 1h: {len(raw_1h)} candles")

def normalize(raw):
    candles = []
    for c in raw:
        ts = int(c["close_time"]) // 1000
        utc_dt = datetime.fromtimestamp(int(c["open_time"]) // 1000, tz=timezone.utc)
        ist_dt = utc_dt + IST
        date = ist_dt.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({
            "date": date, "ts": ts,
            "open": float(c["open"]), "high": float(c["high"]),
            "low": float(c["low"]), "close": float(c["close"]),
        })
    candles.sort(key=lambda x: x["ts"])
    return candles

candles_15m = normalize(raw_15m)
candles_1h = normalize(raw_1h)

print(f"[norm] 15m range: {candles_15m[0]['date']} -> {candles_15m[-1]['date']}")
print(f"[norm] 1h  range: {candles_1h[0]['date']} -> {candles_1h[-1]['date']}")

# Run swing engine
db = Database(":memory:")
db.connect()
db.create_tables()

sw15_eng = PersistentSwingEngine("15m", db, {"minBars": SWING["min_bars_15m"], "timeCap": "00:00"})
sw1h_eng = PersistentSwingEngine("1h", db, {"minBars": SWING["min_bars_1h"], "timeCap": "00:00"})

all_swings_15m = []
all_swings_1h = []

for i, c in enumerate(candles_15m):
    fc = FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"])
    r = sw15_eng.process_bar(fc, i)
    if r:
        all_swings_15m.append(r)

for i, c in enumerate(candles_1h):
    fc = FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"])
    r = sw1h_eng.process_bar(fc, i)
    if r:
        all_swings_1h.append(r)

print(f"\n[swings] 15m: {len(all_swings_15m)} swings, 1h: {len(all_swings_1h)} swings")

# Print all break marks from 15m swings
print("\n" + "=" * 90)
print("  15M SWING BREAKS (B1/B2/FLIP/DECISIVE) — verify on TradingView")
print("=" * 90)

for s in all_swings_15m:
    seg = s.get("seg", {})
    dir_label = "UP" if s.get("dir") == "up" else "DOWN"
    kind = s.get("kind", "?")
    conf = s.get("confirmed_at_time", "")
    print(f"\n  Swing #{s.get('swing_index')} | dir={dir_label} | kind={kind} | confirmed={conf}")
    print(f"  start: {seg.get('start_time', '?')} px={seg.get('start_px', '?'):.2f}")
    print(f"  end:   {seg.get('end_time', '?')} px={seg.get('end_px', '?'):.2f}")
    for b in s.get("breaks", []):
        print(f"    BREAK  {b['kind']:8s} dir={b['dir']:5s} time={b['time']} px={b['px']:.2f}")

# Print 1h swing breaks
print("\n" + "=" * 90)
print("  1H SWING BREAKS")
print("=" * 90)

for s in all_swings_1h:
    seg = s.get("seg", {})
    dir_label = "UP" if s.get("dir") == "up" else "DOWN"
    kind = s.get("kind", "?")
    conf = s.get("confirmed_at_time", "")
    print(f"\n  Swing #{s.get('swing_index')} | dir={dir_label} | kind={kind} | confirmed={conf}")
    print(f"  start: {seg.get('start_time', '?')} px={seg.get('start_px', '?'):.2f}")
    print(f"  end:   {seg.get('end_time', '?')} px={seg.get('end_px', '?'):.2f}")
    for b in s.get("breaks", []):
        print(f"    BREAK  {b['kind']:8s} dir={b['dir']:5s} time={b['time']} px={b['px']:.2f}")

# Summary of marks on Oct 20
print("\n" + "=" * 90)
print("  ALL BREAKS ON 2026-10-20 (IST)")
print("=" * 90)
count = 0
for s in all_swings_15m + all_swings_1h:
    for b in s.get("breaks", []):
        if str(b.get("time", "")).startswith("2026-10-20"):
            tf = "15m" if s in all_swings_15m else "1h"
            print(f"  [{tf}] {b['time']} {b['kind']:8s} dir={b['dir']:5s} px={b['px']:.2f} swing#{s.get('swing_index')}")
            count += 1
if count == 0:
    print("  (no breaks on Oct 20 — check date range)")
print(f"\nTotal breaks on Oct 20: {count}")
