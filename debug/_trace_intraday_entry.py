"""Trace entry loop in intraday.py for 27 Aug"""
import sys
sys.path.insert(0, ".")
import pandas as pd
from src.config import DATA_DIR
from src.intraday import _prep_day, _classify_first_swing_v2, simulate_day, resolve_cfg
from src.walker import WalkerEngine, FlowCandle
from datetime import datetime, timezone, timedelta

# Load data
df5 = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df5["ts_str"] = df5["timestamp"].astype(str).str[:10]
day_5m = df5[df5["ts_str"] == "2026-08-27"].reset_index(drop=True)
day_5m["timestamp"] = pd.to_datetime(day_5m["timestamp"])

df1 = pd.read_csv(DATA_DIR / "nifty_1min.csv")
df1["ts_str"] = df1["timestamp"].astype(str).str[:10]
day_1m = df1[df1["ts_str"] == "2026-08-27"].reset_index(drop=True)
day_1m["timestamp"] = pd.to_datetime(day_1m["timestamp"])

# Manually walk through entry loop logic
from src.firstswing import FirstSwingEngine

IST = timezone(timedelta(hours=5, minutes=30))
candles = _prep_day(day_5m)
m1_candles = _prep_day(day_1m)

# Detect FS1 on 1-min
fs1_1min_dir, _, _, fs1_1min_confirmed_idx, fs1_1min_end_idx, fs1_1min_end_px, fs1_1min_end_time = _classify_first_swing_v2(m1_candles, "2026-08-27")
print(f"FS1: dir={fs1_1min_dir}, end_idx={fs1_1min_end_idx}, end_px={fs1_1min_end_px}")

# FS2 detection
seed_idx = fs1_1min_end_idx + 1
eng2 = FirstSwingEngine({"timeCap": "00:00", "minBars": 14})
seed_c = m1_candles[seed_idx]
seed_dt = datetime.fromtimestamp(int(seed_c.get("ts", 0)), tz=IST).strftime("%Y-%m-%dT%H:%M:%S")
seed_fc = FlowCandle(date=seed_dt, open=float(seed_c["open"]), high=float(seed_c["high"]), low=float(seed_c["low"]), close=float(seed_c["close"]))
eng2.reset_with_candle(seed_fc, seed_idx)

for j in range(seed_idx+1, len(m1_candles)):
    mc = m1_candles[j]
    dt = datetime.fromtimestamp(int(mc.get("ts", 0)), tz=IST).strftime("%Y-%m-%dT%H:%M:%S")
    fc = FlowCandle(date=dt, open=float(mc["open"]), high=float(mc["high"]), low=float(mc["low"]), close=float(mc["close"]))
    eng2.process_bar(fc, j)
    if eng2.declared:
        break

fs2_end_px = eng2.end_px
fs2_dir = "buying" if eng2.dir == "up" else "selling"
print(f"FS2: dir={fs2_dir}, end_px={fs2_end_px}")

# Walk through 5-min bars
walker_1m = WalkerEngine()
normal_lows_1m = []
normal_highs_1m = []

# Get 5-min FS1 info
from src.intraday import _classify_first_swing
fs1_dir, _, _, fs1_confirmed_idx, fs1_end_idx, fs1_end_px, fs1_end_time = _classify_first_swing(candles, "2026-08-27", 1)
print(f"FS1 (5-min): dir={fs1_dir}, end_idx={fs1_end_idx}, end_px={fs1_end_px}")

# Determine swing_dir and want_dir
swing_dir = fs1_dir
want_dir = -1  # bearish
trade_mode = "conservative"
cur_swing = fs2_dir if trade_mode == "conservative" else swing_dir

print(f"trade_mode={trade_mode}, cur_swing={cur_swing}")
print()

# Walk 5-min bars
for i in range(len(candles)):
    cur = candles[i]
    t = cur["time"]
    
    # Skip early bars
    if i < 7:
        continue
    
    # Check if FS2 confirmed
    if i > fs1_end_idx:
        cur_swing = fs2_dir
    
    trade_dir = -1 if cur_swing == "buying" else 1
    aligned = trade_dir == want_dir
    
    # Check 1-min bars in this 5-min window
    cur_5_ts = cur["ts"]
    prev_5_ts = candles[i - 1]["ts"] if i > 0 else 0
    
    found_brk = None
    for k in range(len(m1_candles)):
        mc = m1_candles[k]
        if mc["ts"] > prev_5_ts and mc["ts"] <= cur_5_ts:
            # Feed walker
            dt_str = f"2026-08-27T{mc['time']}:00"
            fc = FlowCandle(date=dt_str, open=float(mc["open"]), high=float(mc["high"]), low=float(mc["low"]), close=float(mc["close"]))
            pivots = walker_1m.process_bar(fc, k)
            for p in pivots:
                if p.kind == "L":
                    normal_lows_1m.append(p)
                else:
                    normal_highs_1m.append(p)
            
            # Check break
            if trade_dir == -1 and normal_lows_1m:
                for piv in reversed(normal_lows_1m):
                    if piv.idx <= k:
                        if mc["low"] < piv.px:
                            found_brk = {"level": piv.px, "time": mc["time"], "idx": k, "low": mc["low"]}
                        break  # BUG: breaks regardless of condition!
    
    # Check conditions
    swing_end_check = cur["low"] < fs2_end_px if trade_dir == -1 else cur["high"] > fs2_end_px
    
    if found_brk or i <= 11:
        print(f"Bar {i} ({t}): trade_dir={trade_dir}, aligned={aligned}, cur_swing={cur_swing}")
        print(f"  cur 5-min: O={cur['open']:.2f} H={cur['high']:.2f} L={cur['low']:.2f}")
        if found_brk:
            print(f"  FOUND BREAK: {found_brk['time']} low={found_brk['low']:.2f} < piv {found_brk['level']:.2f}")
            print(f"  Swing end check: cur.low {cur['low']:.2f} < fs2_end {fs2_end_px:.2f} = {swing_end_check}")
        else:
            print(f"  NO BREAK found in 1-min bars")
        print()
    
    if i >= 11:
        break
