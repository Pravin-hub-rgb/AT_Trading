"""Trace swing 9 (15m, mb50): Jan 5 2023 00:30 start, B1 02:00, B2 only at Jan 6 16:30.

Question: the 2:00 low got breached at 19:30 (Jan 5) but no B2 fired. Why?
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings
from src.walker import FlowCandle

df = load_btc_df("15m")
df["timestamp"] = pd.to_datetime(df["timestamp"])

mask = (df["timestamp"] >= "2023-01-01") & (df["timestamp"] < "2023-01-08")
win = df[mask].reset_index(drop=True)
candles = [
    {"ts": int(r["ts"]), "date": r["timestamp"].strftime("%Y-%m-%d %H:%M:%S"), "open": float(r["open"]), "high": float(r["high"]), "low": float(r["low"]), "close": float(r["close"])}
    for _, r in win.iterrows()
]
flow = [FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"]) for c in candles]
print(f"bars: {len(candles)}  {candles[0]['date']} -> {candles[-1]['date']}")

res = _compute_swings(flow, "continuous", min_bars=50)
for s in res:
    si, ei = s["seg"]["start_idx"], s["seg"]["end_idx"]
    start = candles[si]["date"] if si < len(candles) else "?"
    end = candles[ei]["date"] if ei < len(candles) else "?"
    print(f"\nswing {s['swing_index']}: dir={s['dir']} kind={s['kind']} break_kind={s['break_kind']} "
          f"seg {start}({s['seg']['start_px']:.2f}) -> {end}({s['seg']['end_px']:.2f}) "
          f"conf@{s['confirmed_at_time']}")
    for b in s["breaks"]:
        bar = candles[b["idx"]]
        print(f"   {b['kind']:<4} {b['dir']:<4} @ {bar['date']}  px={b['px']:.2f}  bar O={bar['open']:.2f} H={bar['high']:.2f} L={bar['low']:.2f} C={bar['close']:.2f}")

# Definitive: replicate the REAL per-swing engine run (fresh engine from swing 8's start bar)
from src.firstswing import SwingEngine

s8 = next(s for s in res if candles[s["seg"]["start_idx"]]["date"] == "2023-01-05 00:30:00")
start_idx = s8["seg"]["start_idx"]
print("\n=== fresh engine from swing 8 start (real per-swing replication) ===")
print(f"swing 8: seg {candles[start_idx]['date']}({s8['seg']['start_px']}) -> "
      f"{candles[s8['seg']['end_idx']]['date']}({s8['seg']['end_px']}) dir={s8['dir']} "
      f"break_kind={s8['break_kind']} confirmed_at={s8['confirmed_at_time']}")
print("all marks:", [(b["kind"], b["time"], round(b["px"], 2)) for b in s8["breaks"]])

watch = {"2023-01-05 01:30:00", "2023-01-05 02:00:00", "2023-01-05 19:15:00", "2023-01-05 19:30:00",
         "2023-01-05 19:45:00", "2023-01-05 20:00:00", "2023-01-05 20:15:00", "2023-01-06 16:15:00",
         "2023-01-06 16:30:00", "2023-01-06 16:45:00", "2023-01-06 17:45:00"}
eng = SwingEngine({"min_bars": 50, "b2_gap_bars": 1})
for gi in range(start_idx, len(candles)):
    c, f = candles[gi], flow[gi]
    eng.process_bar(f, gi)
    if c["date"] in watch:
        lp, hp = eng.e_lo_pivot, eng.e_hi_pivot
        print(f"{c['date']}  L={c['low']:.2f}  state={eng.state:<8} dir={str(eng.dir):<5} "
              f"corner(lo-pivot)= {f'{lp.px:.2f}@{lp.time}' if lp else 'None'} "
              f"hi-pivot= {f'{hp.px:.2f}@{hp.time}' if hp else 'None'} "
              f"marks={[(b.kind, b.time, round(b.px,2)) for b in eng.break_marks]}")
    if eng.declared:
        print(f"DECLARED at {c['date']}  source={eng.confirm_source}")
        break

# What did the walker emit during 19:15 / 19:30 / 19:45?
print("\n=== walker-emitted sealed pivots per bar (19:00-20:30) ===")
eng2 = SwingEngine({"min_bars": 50, "b2_gap_bars": 1})
for gi in range(start_idx, len(candles)):
    c, f = candles[gi], flow[gi]
    if "2023-01-05 19:00:00" <= c["date"] <= "2023-01-05 20:30:00":
        # capture sealed pivots emitted by THIS bar via a patched process loop:
        # re-run walker manually is complex; instead use engine internals via process_bar + diff
        before_lo, before_hi = eng2.e_lo_pivot, eng2.e_hi_pivot
        n_marks = len(eng2.break_marks)
    eng2.process_bar(f, gi)
    if "2023-01-05 19:00:00" <= c["date"] <= "2023-01-05 20:30:00":
        dlo = f"{before_lo.px:.2f}@{before_lo.time} -> {eng2.e_lo_pivot.px:.2f}@{eng2.e_lo_pivot.time}" if eng2.e_lo_pivot and before_lo and (eng2.e_lo_pivot.px, eng2.e_lo_pivot.time) != (before_lo.px, before_lo.time) else "unchanged"
        print(f"{c['date']}  L={c['low']:.2f} H={c['high']:.2f}  e_lo_pivot: {dlo}  new marks: {len(eng2.break_marks)-n_marks}")

# ── NIFTY-STYLE per-day reseed: what would the per-day engine print? ────────
from src.firstswing import compute_swing_results

by_day = {}
for c, f in zip(candles, flow):
    by_day.setdefault(c["date"][:10], []).append((c, f))

for day in ["2023-01-05", "2023-01-06"]:
    day_cf = by_day[day]
    if day == "2023-01-05":
        day_cf = [cf for cf in day_cf if cf[0]["date"] >= "2023-01-05 00:30"]  # user: send from 00:30
    cd = [c for c, _ in day_cf]
    fd = [f for _, f in day_cf]
    res_d = compute_swing_results(fd, {"min_bars": 50, "b2_gap_bars": 1}, swing_count="whole")
    res_d = compute_swing_results(fd, {"min_bars": 50, "b2_gap_bars": 1}, swing_count="whole")
    print(f"\n=== NIFTY-STYLE per-day engine, {day} ({len(cd)} bars from {cd[0]['date'][11:16]}) ===")

# ── TRUE NIFTY MAPPING: 15m bars relabeled as 1m minutes (00:30=09:15, 00:45=09:16, ...) ──
from datetime import datetime, timedelta

day_cf = [cf for cf in by_day["2023-01-05"] if cf[0]["date"] >= "2023-01-05 00:30"]
base = datetime(2023, 1, 5, 9, 15)
nifty_candles, nifty_flow, tmap = [], [], {}
for i, (c, f) in enumerate(day_cf):
    t = (base + timedelta(minutes=i)).strftime("%H:%M:%S")
    d = f"2023-01-05 {t}"
    tmap[d] = c["date"]  # fake nifty time -> real 15m time
    nifty_candles.append({"date": d, "open": c["open"], "high": c["high"], "low": c["low"], "close": c["close"]})
    nifty_flow.append(FlowCandle(date=d, open=c["open"], high=c["high"], low=c["low"], close=c["close"]))

print(f"\n=== TRUE NIFTY ENGINE (15m OHLC as 1m, 00:30->09:15, {len(nifty_candles)} bars) ===")
for mb in (14, 50):
    res_n = compute_swing_results(nifty_flow, {"min_bars": mb, "b2_gap_bars": 1}, swing_count="whole")
    print(f"\n--- min_bars={mb} (nifty-style day) ---")
    for s in res_n:
        si, ei = s["seg"]["start_idx"], s["seg"]["end_idx"]
        print(f"swing#{s['swing_index']} dir={s['dir']} break_kind={s['break_kind']} "
              f"seg {nifty_candles[si]['date'][:8]}({s['seg']['start_px']:.2f}) -> "
              f"{nifty_candles[ei]['date'][:8]}({s['seg']['end_px']:.2f}) conf@{s['confirmed_at_time'][:8]}")
        for b in s["breaks"]:
            real = tmap.get(b["time"], "?")
            print(f"   {b['kind']:<4} {b['dir']:<4} @ nifty {b['time'][:8]}  = real 15m {real[11:16]}  px={b['px']:.2f}")
    for s in res_d:
        print(f"swing#{s['swing_index']} dir={s['dir']} break_kind={s['break_kind']} "
              f"seg {cd[s['seg']['start_idx']]['date'][11:16]}({s['seg']['start_px']:.2f}) -> "
              f"{cd[s['seg']['end_idx']]['date'][11:16]}({s['seg']['end_px']:.2f}) conf@{s['confirmed_at_time'][11:16]}")
        for b in s["breaks"]:
            print(f"   {b['kind']:<4} {b['dir']:<4} @ {b['time']}  px={b['px']:.2f}")
