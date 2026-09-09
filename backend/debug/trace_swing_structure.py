import sys, bisect
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt, _chop_series_1h
from src.btc.engines.v7_timecap import simulate_btc_trades_v7
from src.walker import FlowCandle

def load_window(tf):
    df = load_btc_df(tf)
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({"date": date, "ts": int(row.ts), "open": float(row.open), "high": float(row.high), "low": float(row.low), "close": float(row.close), "volume": 0, "oi": 0})
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high), low=float(row.low), close=float(row.close)))
    return candles, flow

c1h, f1h = load_window("1h")
c15, f15 = load_window("15m")
sw1h = _compute_swings(f1h, "continuous", min_bars=20)
sw15 = _compute_swings(f15, "continuous", min_bars=50)
t0 = min(c1h[0]["ts"], c15[0]["ts"])
t1 = max(c1h[-1]["ts"], c15[-1]["ts"])
fine = _load_fine_1m(t0, t1)

print("=== FIRST 15 SWINGS (1h, mb20) ===")
print()
for i, s in enumerate(sw1h[:15]):
    conf_idx = s.get("confirmed_at_idx", -1)
    conf_date = c1h[conf_idx]["date"] if 0 <= conf_idx < len(c1h) else "?"
    start_idx = s.get("start_idx", -1)
    start_date = c1h[start_idx]["date"] if 0 <= start_idx < len(c1h) else "?"
    end_idx = s.get("end_idx", -1)
    end_date = c1h[end_idx]["date"] if 0 <= end_idx < len(c1h) else "?"
    print(f"  [{i:2d}] dir={s['dir']:5s} kind={s.get('kind','?'):3s} start={start_date} end={end_date} confirmed={conf_date}")

import sys
sys.path.insert(0, 'backend')

from src.btc.btc_config import load_btc_df
from src.walker import FlowCandle
from src.btc.btc_routes import _compute_swings

df = load_btc_df('1h')
candles = []
flow = []
for row in df.itertuples():
    date = row.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    candles.append({'date': date, 'ts': int(row.ts), 'open': float(row.open), 'high': float(row.high), 'low': float(row.low), 'close': float(row.close)})
    flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high), low=float(row.low), close=float(row.close)))

print(f'1h bars: {len(candles)}', flush=True)
sw1h = _compute_swings(flow, 'continuous', min_bars=20)
print(f'1h swings: {len(sw1h)}', flush=True)

print()
print('=== FIRST 20 SWINGS (1h, mb20) ===')
print()
for i, s in enumerate(sw1h[:20]):
    conf_idx = s.get('confirmed_at_idx', -1)
    conf_date = candles[conf_idx]['date'] if 0 <= conf_idx < len(candles) else '?'
    start_idx = s.get('start_idx', -1)
    start_date = candles[start_idx]['date'] if 0 <= start_idx < len(candles) else '?'
    print(f'  [{i:2d}] dir={s["dir"]:5s} start={start_date} confirmed={conf_date}')

print()
print('=== SWING BREAKS (B1/B2/FLIP) ===')
print()
breaks = []
for i in range(1, min(30, len(sw1h))):
    prev = sw1h[i-1]
    curr = sw1h[i]
    conf_idx = curr.get('confirmed_at_idx', -1)
    if conf_idx < 0:
        continue
    conf_date = candles[conf_idx]['date']
    if curr['dir'] != prev['dir']:
        break_type = 'FLIP'
    else:
        same_count = 1
        for j in range(i-1, -1, -1):
            if sw1h[j]['dir'] == curr['dir']:
                same_count += 1
            else:
                break
        break_type = 'B2' if same_count >= 2 else 'B1'
    breaks.append({'idx': i, 'type': break_type, 'dir': curr['dir'], 'conf_date': conf_date})

for b in breaks[:20]:
    print(f'  swing[{b["idx"]:2d}] type={b["type"]:5s} dir={b["dir"]:5s} confirmed={b["conf_date"]}')

import sys
sys.path.insert(0, 'backend')

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings
from src.walker import FlowCandle

df = load_btc_df('1h')
candles, flow = [], []
for row in df.itertuples():
    date = row.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    candles.append({'date': date, 'ts': int(row.ts), 'open': float(row.open), 'high': float(row.high), 'low': float(row.low), 'close': float(row.close)})
    flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high), low=float(row.low), close=float(row.close)))

print(f'1h bars: {len(candles)}', flush=True)
sw1h = _compute_swings(flow, 'continuous', min_bars=20)
print(f'1h swings: {len(sw1h)}', flush=True)

for i, s in enumerate(sw1h[:10]):
    conf_idx = s.get('confirmed_at_idx', -1)
    conf_date = candles[conf_idx]['date'] if 0 <= conf_idx < len(candles) else '?'
    print(f'  [{i:2d}] dir={s["dir"]:5s} confirmed={conf_date}')

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

print("Starting...", flush=True)

from src.btc.btc_config import load_btc_df

print("Loaded config", flush=True)

df = load_btc_df("1h")
print(f"1h rows: {len(df)}", flush=True)
print(f"Columns: {list(df.columns)}", flush=True)
print(f"First row: {df.iloc[0]}", flush=True)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings
from src.walker import FlowCandle

def load_window(tf):
    df = load_btc_df(tf)
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({"date": date, "ts": int(row.ts), "open": float(row.open), "high": float(row.high), "low": float(row.low), "close": float(row.close), "volume": 0, "oi": 0})
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high), low=float(row.low), close=float(row.close)))
    return candles, flow

print("Loading 1h data...", flush=True)
c1h, f1h = load_window("1h")
print(f"1h bars: {len(c1h)}", flush=True)

print("Computing swings...", flush=True)
sw1h = _compute_swings(f1h, "continuous", min_bars=20)
print(f"1h swings: {len(sw1h)}", flush=True)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings
from src.walker import FlowCandle

def load_window(tf):
    df = load_btc_df(tf)
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({"date": date, "ts": int(row.ts), "open": float(row.open), "high": float(row.high), "low": float(row.low), "close": float(row.close), "volume": 0, "oi": 0})
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high), low=float(row.low), close=float(row.close)))
    return candles, flow

c1h, f1h = load_window("1h")
sw1h = _compute_swings(f1h, "continuous", min_bars=20)

print("=== FIRST 20 SWINGS (1h, mb20) ===")
print()
for i, s in enumerate(sw1h[:20]):
    conf_idx = s.get("confirmed_at_idx", -1)
    conf_date = c1h[conf_idx]["date"] if 0 <= conf_idx < len(c1h) else "?"
    start_idx = s.get("start_idx", -1)
    start_date = c1h[start_idx]["date"] if 0 <= start_idx < len(c1h) else "?"
    print(f"  [{i:2d}] dir={s['dir']:5s} start={start_date} confirmed={conf_date}")

print()
print("=== SWING BREAKS (B1/B2/FLIP) ===")
print()
breaks = []
for i in range(1, min(30, len(sw1h))):
    prev = sw1h[i-1]
    curr = sw1h[i]
    conf_idx = curr.get("confirmed_at_idx", -1)
    if conf_idx < 0:
        continue
    conf_ts = int(c1h[conf_idx]["ts"])
    conf_date = c1h[conf_idx]["date"]
    if curr["dir"] != prev["dir"]:
        break_type = "FLIP"
    else:
        same_count = 1
        for j in range(i-1, -1, -1):
            if sw1h[j]["dir"] == curr["dir"]:
                same_count += 1
            else:
                break
        break_type = "B2" if same_count >= 2 else "B1"
    breaks.append({"idx": i, "type": break_type, "dir": curr["dir"], "conf_ts": conf_ts, "conf_date": conf_date})

for b in breaks[:20]:
    print(f"  swing[{b['idx']:2d}] type={b['type']:5s} dir={b['dir']:5s} confirmed={b['conf_date']}")

import sys, bisect
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt, _chop_series_1h
from src.walker import FlowCandle

def load_window(tf):
    df = load_btc_df(tf)
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({"date": date, "ts": int(row.ts), "open": float(row.open), "high": float(row.high), "low": float(row.low), "close": float(row.close), "volume": 0, "oi": 0})
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high), low=float(row.low), close=float(row.close)))
    return candles, flow

c1h, f1h = load_window("1h")
c15, f15 = load_window("15m")
sw1h = _compute_swings(f1h, "continuous", min_bars=20)
sw15 = _compute_swings(f15, "continuous", min_bars=50)
t0 = min(c1h[0]["ts"], c15[0]["ts"])
t1 = max(c1h[-1]["ts"], c15[-1]["ts"])
fine = _load_fine_1m(t0, t1)

print("=== FIRST 20 SWINGS (1h, mb20) ===")
print()
for i, s in enumerate(sw1h[:20]):
    conf_idx = s.get("confirmed_at_idx", -1)
    conf_date = c1h[conf_idx]["date"] if 0 <= conf_idx < len(c1h) else "?"
    start_idx = s.get("start_idx", -1)
    start_date = c1h[start_idx]["date"] if 0 <= start_idx < len(c1h) else "?"
    print(f"  [{i:2d}] dir={s['dir']:5s} start={start_date} confirmed={conf_date}")

print()
print("=== SWING BREAKS (B1/B2/FLIP) ===")
print()
breaks = []
for i in range(1, min(30, len(sw1h))):
    prev = sw1h[i-1]
    curr = sw1h[i]
    conf_idx = curr.get("confirmed_at_idx", -1)
    if conf_idx < 0:
        continue
    conf_ts = int(c1h[conf_idx]["ts"])
    conf_date = c1h[conf_idx]["date"]
    if curr["dir"] != prev["dir"]:
        break_type = "FLIP"
    else:
        same_count = 1
        for j in range(i-1, -1, -1):
            if sw1h[j]["dir"] == curr["dir"]:
                same_count += 1
            else:
                break
        break_type = "B2" if same_count >= 2 else "B1"
    breaks.append({"idx": i, "type": break_type, "dir": curr["dir"], "conf_ts": conf_ts, "conf_date": conf_date})

for b in breaks[:20]:
    print(f"  swing[{b['idx']:2d}] type={b['type']:5s} dir={b['dir']:5s} confirmed={b['conf_date']}")

import sys, bisect
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt, _chop_series_1h
from src.btc.engines.v7_timecap import simulate_btc_trades_v7
from src.walker import FlowCandle

def load_window(tf):
    df = load_btc_df(tf)
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({"date": date, "ts": int(row.ts), "open": float(row.open), "high": float(row.high), "low": float(row.low), "close": float(row.close), "volume": 0, "oi": 0})
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high), low=float(row.low), close=float(row.close)))
    return candles, flow

c1h, f1h = load_window("1h")
c15, f15 = load_window("15m")
sw1h = _compute_swings(f1h, "continuous", min_bars=20)
sw15 = _compute_swings(f15, "continuous", min_bars=50)
t0 = min(c1h[0]["ts"], c15[0]["ts"])
t1 = max(c1h[-1]["ts"], c15[-1]["ts"])
fine = _load_fine_1m(t0, t1)

print("=== FIRST 15 SWINGS (1h, mb20) ===")
print()
for i, s in enumerate(sw1h[:15]):
    conf_idx = s.get("confirmed_at_idx", -1)
    conf_date = c1h[conf_idx]["date"] if 0 <= conf_idx < len(c1h) else "?"
    start_idx = s.get("start_idx", -1)
    start_date = c1h[start_idx]["date"] if 0 <= start_idx < len(c1h) else "?"
    end_idx = s.get("end_idx", -1)
    end_date = c1h[end_idx]["date"] if 0 <= end_idx < len(c1h) else "?"
    print(f"  [{i:2d}] dir={s['dir']:5s} kind={s.get('kind','?'):3s} start={start_date} end={end_date} confirmed={conf_date}")

print()
print("=== SWING BREAKS (B1/B2/FLIP) ===")
print()
breaks = []
for i in range(1, len(sw1h)):
    prev = sw1h[i-1]
    curr = sw1h[i]
    conf_idx = curr.get("confirmed_at_idx", -1)
    if conf_idx < 0:
        continue
    conf_ts = int(c1h[conf_idx]["ts"])
    conf_date = c1h[conf_idx]["date"]
    if curr["dir"] != prev["dir"]:
        break_type = "FLIP"
    else:
        same_count = 1
        for j in range(i-1, -1, -1):
            if sw1h[j]["dir"] == curr["dir"]:
                same_count += 1
            else:
                break
        break_type = "B2" if same_count >= 2 else "B1"
    breaks.append({"idx": i, "type": break_type, "dir": curr["dir"], "conf_ts": conf_ts, "conf_date": conf_date})

print("First 20 breaks:")
for b in breaks[:20]:
    print(f"  swing[{b['idx']:2d}] type={b['type']:5s} dir={b['dir']:5s} confirmed={b['conf_date']}")

print()
print("=== HTF FLIP WINDOWS (first 10) ===")
htf_flip = simulate_btc_trades_v7(c1h, sw1h, entry_break="flip", sl_mode="swing", rr_target=3.0, trailing="off", breakeven_r=0.0, skip_first=True, fine=fine, cap_days=16)
for i, t in enumerate(htf_flip[:10]):
    print(f"  [{i}] dir={t['dir']} entry={t['entry_date']} exit={t['exit_date']} outcome={t['outcome']}")

print()
print("=== HTF B2 WINDOWS (first 10) ===")
htf_b2 = simulate_btc_trades_v7(c1h, sw1h, entry_break="b2", sl_mode="swing", rr_target=3.0, trailing="off", breakeven_r=0.0, skip_first=True, fine=fine, cap_days=16)
for i, t in enumerate(htf_b2[:10]):
    print(f"  [{i}] dir={t['dir']} entry={t['entry_date']} exit={t['exit_date']} outcome={t['outcome']}")
