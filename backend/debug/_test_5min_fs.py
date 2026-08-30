import sys
sys.path.insert(0, 'backend')
from src.firstswing import FirstSwingEngine
from src.walker import FlowCandle
import pandas as pd
from src.config import DATA_DIR
from datetime import timezone, timedelta
df5=pd.read_csv(DATA_DIR/"nifty_5min.csv")
df5["timestamp"]=pd.to_datetime(df5["timestamp"])
aug=df5[df5["timestamp"].astype(str).str[:10]=="2026-08-28"].copy()
aug["ts"]=(aug["timestamp"].astype("int64")//1_000_000_000).astype("int64")
# prep like _prep_day
import pandas as pd
def prep(day):
    out=[]
    for i,row in enumerate(day.reset_index(drop=True).itertuples()):
        out.append({"index":i,"time":row.timestamp.strftime("%H:%M"),"ts":int(row.ts),"open":float(row.open),"high":float(row.high),"low":float(row.low),"close":float(row.close)})
    return out
c5=prep(aug)
IST=timezone(timedelta(hours=5, minutes=30))
from datetime import datetime
flow=[]
for c in c5:
    dt=datetime.fromtimestamp(c["ts"], tz=IST).strftime("%Y-%m-%dT%H:%M:%S")
    flow.append(FlowCandle(date=dt, open=c["open"], high=c["high"], low=c["low"], close=c["close"]))
eng=FirstSwingEngine()
for i,fc in enumerate(flow):
    eng.process_bar(fc,i)
    print(f"{fc.date[11:16]} idx={i} H={fc.high} L={fc.low} state={eng.state} dir={eng.dir} armed={eng.armed} confirmed={eng.dir_confirmed} declared={eng.declared} marks={eng.break_marks}")
    if eng.declared:
        print(f"declared at {fc.date} dir {eng.dir} start {eng.start_time} {eng.start_px} end {eng.end_time} {eng.end_px} conf {eng.confirmed_at_time}")
        break
if not eng.declared:
    print("not declared")
    print(eng.debug_pools())

# also test old engine
from src.swing_engine import FsV2Engine as Old
eng2=Old()
for i,fc in enumerate(flow):
    eng2.process_bar(fc,i)
    if eng2.declared:
        print("old declared", eng2.dir, eng2.start_time, eng2.end_time, eng2.confirmed_at_time)
        break
