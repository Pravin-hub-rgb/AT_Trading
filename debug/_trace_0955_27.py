"""Trace why 09:55 bar (low 24189.30) doesn't trigger pace_break at bar 8"""
import sys
sys.path.insert(0, ".")
import pandas as pd
from src.config import DATA_DIR
from src.intraday import _prep_day, _classify_first_swing_v2
from src.walker import WalkerEngine, FlowCandle

# Load 1-min data for 27 Aug
df1 = pd.read_csv(DATA_DIR / "nifty_1min.csv")
df1["ts_str"] = df1["timestamp"].astype(str).str[:10]
day_1m = df1[df1["ts_str"] == "2026-08-27"].reset_index(drop=True)
day_1m["timestamp"] = pd.to_datetime(day_1m["timestamp"])

m1_candles = _prep_day(day_1m)
print(f"Total 1-min candles: {len(m1_candles)}")

# Detect 1-min FS
fs1_1min_dir, _, _, fs1_1min_confirmed_idx, fs1_1min_end_idx, fs1_1min_end_px, fs1_1min_end_time = _classify_first_swing_v2(m1_candles, "2026-08-27")
print(f"FS1 (1-min): dir={fs1_1min_dir}, confirmed_idx={fs1_1min_confirmed_idx}, end_idx={fs1_1min_end_idx}, end_px={fs1_1min_end_px}, end_time={fs1_1min_end_time}")

# Seed second swing engine from FS1 end + 1
from src.firstswing import FirstSwingEngine
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
seed_idx = fs1_1min_end_idx + 1
print(f"Seed idx for FS2: {seed_idx}")

eng2 = FirstSwingEngine({"timeCap": "00:00", "minBars": 14})
seed_c = m1_candles[seed_idx]
seed_dt = datetime.fromtimestamp(int(seed_c.get("ts", 0)), tz=IST).strftime("%Y-%m-%dT%H:%M:%S") if seed_c.get("ts") else f"2026-08-27T{seed_c.get('time','00:00')}:00"
seed_fc = FlowCandle(date=seed_dt, open=float(seed_c["open"]), high=float(seed_c["high"]), low=float(seed_c["low"]), close=float(seed_c["close"]))
eng2.reset_with_candle(seed_fc, seed_idx)

for j in range(seed_idx+1, len(m1_candles)):
    mc = m1_candles[j]
    dt = datetime.fromtimestamp(int(mc.get("ts", 0)), tz=IST).strftime("%Y-%m-%dT%H:%M:%S") if mc.get("ts") else f"2026-08-27T{mc.get('time','00:00')}:00"
    fc = FlowCandle(date=dt, open=float(mc["open"]), high=float(mc["high"]), low=float(mc["low"]), close=float(mc["close"]))
    eng2.process_bar(fc, j)
    if eng2.declared:
        print(f"FS2 declared: dir={eng2.dir}, start_idx={eng2.start_idx}, start_px={eng2.start_px}, end_idx={eng2.end_idx}, end_px={eng2.end_px}, confirmed_at_idx={eng2.confirmed_at_idx}")
        break

# Now walk through with Walker to see pivots
walker = WalkerEngine()
normal_lows_1m = []
normal_highs_1m = []

print()
print("Walking 1-min candles with Walker:")
for k, mc in enumerate(m1_candles):
    dt_str = f"2026-08-27T{mc['time']}:00"
    fc = FlowCandle(date=dt_str, open=float(mc["open"]), high=float(mc["high"]), low=float(mc["low"]), close=float(mc["close"]))
    pivots = walker.process_bar(fc, k)
    for p in pivots:
        if p.kind == "L":
            normal_lows_1m.append(p)
        else:
            normal_highs_1m.append(p)
    
    # Show key times
    t = mc["time"]
    if t in ("09:48", "09:49", "09:50", "09:51", "09:52", "09:53", "09:54", "09:55", "09:56", "09:57", "09:58"):
        low = mc["low"]
        high = mc["high"]
        piv = next((p for p in reversed(normal_lows_1m) if p.idx < k), None)
        piv_h = next((p for p in reversed(normal_highs_1m) if p.idx < k), None)
        fs2_end = 24228.2  # FS2 end high
        
        # Check SHORT conditions
        short_cond = piv is not None and low < piv.px
        short_cond2 = low < fs2_end  # direct check against FS2 end
        
        marker = ""
        if short_cond:
            marker += f" [BREAK below piv {piv.px:.2f}]"
        if short_cond2 and k >= eng2.confirmed_at_idx:
            marker += f" [BELOW FS2 end {fs2_end:.2f}]"
            
        print(f"  {t} (idx {k}): O={mc['open']:.2f} H={high:.2f} L={low:.2f} C={mc['close']:.2f} pivots: H={piv_h.px if piv_h else None} L={piv.px if piv else None}{marker}")
