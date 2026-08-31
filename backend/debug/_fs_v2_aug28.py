"""Check FsV2 directly on 1-min for 28 Aug — find FS at 10:21."""
import sys
sys.path.insert(0, ".")
from src.config import DATA_DIR
import pandas as pd
from src.intraday import _prep_day
from src.firstswing import FirstSwingEngine, compute_fs_v2_results
from src.walker import FlowCandle as FC
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

df1 = pd.read_csv(DATA_DIR / "nifty_1min.csv")
df1["timestamp"] = pd.to_datetime(df1["timestamp"])
df1["ts"] = df1["ts"].astype("int64")
df1 = df1.sort_values("timestamp")
aug28 = df1[df1["timestamp"].dt.strftime("%Y-%m-%d") == "2026-08-28"].copy()
c1 = _prep_day(aug28)

# 1) Run FirstSwingEngine directly
print("=== 1min FirstSwingEngine (default timeCap=09:29) ===")
eng = FirstSwingEngine()
for g_idx, c in enumerate(c1):
    ts = c.get("ts", 0)
    dt = datetime.fromtimestamp(int(ts), tz=IST).strftime("%Y-%m-%dT%H:%M:%S") if ts else f"2026-08-28T{c.get('time','00:00')}:00"
    fc = FC(date=dt, open=c["open"], high=c["high"], low=c["low"], close=c["close"])
    eng.process_bar(fc, g_idx)
print(f"  declared={eng.declared} dir={eng.dir}")
print(f"  end_idx={eng.end_idx} end_time={eng.end_time} end_px={eng.end_px}")
print(f"  confirmed_at_idx={eng.confirmed_at_idx} confirmed_at_time={eng.confirmed_at_time}")
print(f"  start_idx={eng.start_idx} start_time={eng.start_time} start_px={eng.start_px}")

# 2) Run compute_fs_v2_results (same as frontend)
print("\n=== compute_fs_v2_results(timeCap=09:29) ===")
fcs = []
for c in c1:
    ts = c.get("ts", 0)
    dt = datetime.fromtimestamp(int(ts), tz=IST).strftime("%Y-%m-%dT%H:%M:%S") if ts else f"2026-08-28T{c.get('time','00:00')}:00"
    fcs.append(FC(date=dt, open=c["open"], high=c["high"], low=c["low"], close=c["close"]))
results = compute_fs_v2_results(fcs, {"timeCap": "09:29"})
for r in results:
    if r.day == "2026-08-28" and r.seg:
        c = c1[r.conf_idx]
        print(f"  conf_idx={r.conf_idx} time={c['time']} dir={r.dir}")
        print(f"  seg start_idx={r.seg.start_idx} end_idx={r.seg.end_idx} end_px={r.seg.end_px}")
        for b in r.breaks or []:
            print(f"  break idx={b.idx} time={c1[b.idx]['time']} kind={b.kind} dir={b.dir} px={b.px}")

# 3) Try with timeCap=None / 15:00 to see if a different FS is found
print("\n=== FirstSwingEngine with timeCap='15:00' (no cap) ===")
eng2 = FirstSwingEngine({"timeCap": "15:00"})
for g_idx, c in enumerate(c1):
    ts = c.get("ts", 0)
    dt = datetime.fromtimestamp(int(ts), tz=IST).strftime("%Y-%m-%dT%H:%M:%S") if ts else f"2026-08-28T{c.get('time','00:00')}:00"
    fc = FC(date=dt, open=c["open"], high=c["high"], low=c["low"], close=c["close"])
    eng2.process_bar(fc, g_idx)
print(f"  declared={eng2.declared} dir={eng2.dir}")
print(f"  end_idx={eng2.end_idx} end_time={eng2.end_time} end_px={eng2.end_px}")
print(f"  confirmed_at_idx={eng2.confirmed_at_idx} confirmed_at_time={eng2.confirmed_at_time}")
print(f"  start_idx={eng2.start_idx} start_time={eng2.start_time} start_px={eng2.start_px}")
print(f"  break_marks: {[(b.idx, c1[b.idx]['time'], b.kind, b.dir, b.px) for b in eng2.break_marks]}")
