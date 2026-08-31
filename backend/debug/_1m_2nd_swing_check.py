"""Check the 1-min second swing - what does the user see as 'FS at 10:21'?"""
import sys
sys.path.insert(0, ".")
from src.config import DATA_DIR
import pandas as pd
from src.intraday import _classify_first_swing_v2, _prep_day
from src.firstswing import FirstSwingEngine
from src.walker import FlowCandle as _FC
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

df5 = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df5["timestamp"] = pd.to_datetime(df5["timestamp"])
df5["ts"] = df5["ts"].astype("int64")
df5 = df5.sort_values("timestamp")
aug28_5 = df5[df5["timestamp"].dt.strftime("%Y-%m-%d") == "2026-08-28"].copy()

df1 = pd.read_csv(DATA_DIR / "nifty_1min.csv")
df1["timestamp"] = pd.to_datetime(df1["timestamp"])
df1["ts"] = df1["ts"].astype("int64")
df1 = df1.sort_values("timestamp")
aug28_1 = df1[df1["timestamp"].dt.strftime("%Y-%m-%d") == "2026-08-28"].copy()

c1 = _prep_day(aug28_1)
c5 = _prep_day(aug28_5)

print("=== 1-min first swing ===")
fs1_dir, _, _, fs1_conf, fs1_end_idx, fs1_end_px, fs1_end_time = _classify_first_swing_v2(c1, "2026-08-28")
print(f"  dir={fs1_dir} fs_confirmed_idx={fs1_conf} end_idx={fs1_end_idx} end_time={fs1_end_time}")
print(f"  1-min bar {fs1_conf} = {c1[fs1_conf]['time']}")

# Now run the second swing engine on 1-min data
print("\n=== 1-min second swing (seeded from 1-min FS end+1) ===")
seed_idx = fs1_end_idx + 1  # 09:28
if seed_idx < len(c1):
    seed_c = c1[seed_idx]
    seed_dt = datetime.fromtimestamp(int(seed_c.get("ts", 0)), tz=IST).strftime("%Y-%m-%dT%H:%M:%S") if seed_c.get("ts") else f"2026-08-28T{seed_c.get('time','00:00')}:00"
    seed_fc = _FC(date=seed_dt, open=float(seed_c["open"]), high=float(seed_c["high"]), low=float(seed_c["low"]), close=float(seed_c["close"]))
    eng2 = FirstSwingEngine()
    eng2.reset_with_candle(seed_fc, seed_idx)
    print(f"  Seeded at 1-min idx={seed_idx} time={c1[seed_idx]['time']} price={seed_fc.low:.2f}")
    
    for j in range(seed_idx+1, len(c1)):
        mc = c1[j]
        dt = datetime.fromtimestamp(int(mc.get("ts", 0)), tz=IST).strftime("%Y-%m-%dT%H:%M:%S") if mc.get("ts") else f"2026-08-28T{mc.get('time','00:00')}:00"
        fc = _FC(date=dt, open=float(mc["open"]), high=float(mc["high"]), low=float(mc["low"]), close=float(mc["close"]))
        eng2.process_bar(fc, j)
    
    print(f"  eng2.declared={eng2.declared} dir={eng2.dir} confirmed_at_idx={eng2.confirmed_at_idx} confirmed_at_time={eng2.confirmed_at_time}")
    if eng2.declared:
        print(f"  start_px={eng2.start_px} end_px={eng2.end_px}")
        print(f"  Break marks: {[(b.idx, c1[b.idx]['time'], b.kind, b.dir, b.px) for b in eng2.break_marks]}")
        # Map to 5-min
        for k5, c5b in enumerate(c5):
            if c5b.get("ts", 0) >= c1[eng2.confirmed_at_idx].get("ts", 0):
                print(f"  Mapped to 5-min bar {k5} time={c5b['time']}")
                break

# Also check: what 1-min bar is at 10:21?
print("\n=== 1-min bars around 10:21 ===")
for i, c in enumerate(c1):
    t = c["time"]
    if "10:20" <= t <= "10:25":
        print(f"  idx={i} time={t} O={c['open']:.2f} H={c['high']:.2f} L={c['low']:.2f} C={c['close']:.2f}")
