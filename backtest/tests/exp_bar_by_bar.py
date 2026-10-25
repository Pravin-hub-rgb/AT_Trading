"""Show exact bar-by-bar mark production for Oct 20 15m."""
import sys, time
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

start_dt = datetime(2026, 10, 19, 18, 30, 0, tzinfo=timezone.utc)
start_ms = int(start_dt.timestamp() * 1000)
now_ms = int(time.time() * 1000)

raw = backfill_klines_bybit('BTCUSDT', '15', limit=516, demo=True, start_ms=start_ms)
raw = [c for c in raw if c.get('close_time', 0) <= now_ms]
raw.sort(key=lambda k: k['open_time'])

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
            "_ot": c["open_time"], "_ct": c["close_time"],
        })
    candles.sort(key=lambda x: x["ts"])
    return candles

candles = normalize(raw)

db = Database(":memory:")
db.connect()
db.create_tables()
eng = PersistentSwingEngine("15m", db, {"minBars": SWING["min_bars_15m"], "timeCap": "00:00"})

print("=" * 100)
print("  BAR-BY-BAR: every candle processed, every mark produced")
print("  Start: Oct 20 2026 00:00 IST (first candle close = 00:15 IST)")
print("=" * 100)

for i, c in enumerate(candles[:80]):
    ist_open = datetime.fromtimestamp(c["_ot"] / 1000, tz=timezone.utc) + IST
    ist_close = datetime.fromtimestamp(c["_ct"] / 1000, tz=timezone.utc) + IST
    fc = FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"])
    result = eng.process_bar(fc, i)

    marks_str = ""
    if result:
        seg = result.get("seg", {})
        marks_str = "  >> SWING #{} dir={} kind={} start={} end={} ".format(
            result.get("swing_index"), result.get("dir"), result.get("kind"),
            seg.get("start_time", "?"), seg.get("end_time", "?"))

    breaks_str = ""
    if result and result.get("breaks"):
        for b in result.get("breaks", []):
            breaks_str += "  BREAK {} dir={} time={} px={:.2f} | ".format(
                b["kind"], b["dir"], b["time"], b["px"])

    print("{:4d} | close={:20s} | O={:.1f} H={:.1f} L={:.1f} C={:.1f}{} | g_idx={}".format(
        i,
        ist_close.strftime("%Y-%m-%d %H:%M"),
        c["open"], c["high"], c["low"], c["close"],
        marks_str,
        i))
    if breaks_str:
        print("      " + breaks_str)

    if result:
        open_s = eng.get_open_swing()
        if open_s and open_s.get("breaks"):
            for b in open_s.get("breaks", []):
                print("      [OPEN SWING] {} dir={} time={} px={:.2f} idx={} swing#{}{}".format(
                    b["kind"], b["dir"], b["time"], b["px"], b.get("idx", -1),
                    open_s.get("swing_index", -1),
                    " (swing just declared)" if result else ""))
