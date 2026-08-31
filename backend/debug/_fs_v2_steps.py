"""Trace FsV2 step by step for 28 Aug 1-min to understand the 10:21 FS."""
import sys
sys.path.insert(0, ".")
from src.config import DATA_DIR
import pandas as pd
from src.intraday import _prep_day
from src.firstswing import FirstSwingEngine
from src.walker import FlowCandle as FC
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

df1 = pd.read_csv(DATA_DIR / "nifty_1min.csv")
df1["timestamp"] = pd.to_datetime(df1["timestamp"])
df1["ts"] = df1["ts"].astype("int64")
df1 = df1.sort_values("timestamp")
aug28 = df1[df1["timestamp"].dt.strftime("%Y-%m-%d") == "2026-08-28"].copy()
c1 = _prep_day(aug28)

# Run FsV2 with no cap, printing every state change
eng = FirstSwingEngine({"timeCap": "15:00"})
prev_state = eng.state
prev_dir = eng.dir
prev_confirmed = eng.declared

for g_idx, c in enumerate(c1):
    ts = c.get("ts", 0)
    dt = datetime.fromtimestamp(int(ts), tz=IST).strftime("%Y-%m-%dT%H:%M:%S") if ts else f"2026-08-28T{c.get('time','00:00')}:00"
    fc = FC(date=dt, open=c["open"], high=c["high"], low=c["low"], close=c["close"])
    eng.process_bar(fc, g_idx)
    
    state_changed = eng.state != prev_state
    dir_changed = eng.dir != prev_dir
    declared_changed = eng.declared != prev_confirmed
    
    t = c["time"]
    # Print key events around 10:00-10:35
    if "10:00" <= t <= "10:35" or state_changed or dir_changed or declared_changed:
        markers = []
        if eng.break_marks and eng.break_marks[-1].idx == g_idx:
            bm = eng.break_marks[-1]
            markers.append(f"BREAK@{bm.kind}")
        print(f"  {t}  state={eng.state}  dir={eng.dir}  declared={eng.declared}  "
              f"end_idx={eng.end_idx}({eng.end_time})  conf_idx={eng.confirmed_at_idx}({eng.confirmed_at_time})  "
              f"locked_lvl={eng.locked_level:.2f}  {markers}")
    
    prev_state = eng.state
    prev_dir = eng.dir
    prev_confirmed = eng.declared

print(f"\nFinal: declared={eng.declared} dir={eng.dir}")
print(f"  end_idx={eng.end_idx} end_time={eng.end_time} end_px={eng.end_px}")
print(f"  confirmed_at_idx={eng.confirmed_at_idx} confirmed_at_time={eng.confirmed_at_time}")
print(f"  confirm_source={eng.confirm_source}")
print(f"  break_marks: {[(b.idx, c1[b.idx]['time'], b.kind, b.dir, b.px) for b in eng.break_marks]}")
