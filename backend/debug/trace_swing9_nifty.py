# CLEAN TEST: Feed Jan-5 OHLC (from 00:30, where swing 9 calc starts) into the
# nifty-style engine: each 15m bar treated as one 1m minute (00:30 -> 09:15).
# Print every mark with its REAL 15m time. Question: does B2 print at the 19:30 breach?
import sys
from pathlib import Path
from datetime import datetime, timedelta
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from src.btc.btc_config import load_btc_df
from src.walker import FlowCandle
from src.firstswing import compute_swing_results

df = load_btc_df("15m")
df["timestamp"] = pd.to_datetime(df["timestamp"])
day_df = df[(df["timestamp"] >= "2023-01-05 00:30") & (df["timestamp"] <= "2023-01-05 23:45")]
day = [
    {"date": r["timestamp"].strftime("%Y-%m-%d %H:%M:%S"), "open": float(r["open"]),
     "high": float(r["high"]), "low": float(r["low"]), "close": float(r["close"])}
    for _, r in day_df.iterrows()
]
print(f"bars from 2023-01-05 00:30: {len(day)}  (first {day[0]['date']}, last {day[-1]['date']})")

base = datetime(2023, 1, 5, 9, 15)
flow, tmap = [], {}
for i, c in enumerate(day):
    nf = (base + timedelta(minutes=i)).strftime("%Y-%m-%d %H:%M:%S")
    tmap[f"{nf[11:16]}"] = c["date"][11:16]          # nifty HH:MM -> real HH:MM
    flow.append(FlowCandle(date=nf, open=c["open"], high=c["high"],
                           low=c["low"], close=c["close"]))

for mb in (14, 50):
    res = compute_swing_results(flow, {"min_bars": mb, "b2_gap_bars": 1}, swing_count="whole")
    print(f"\n--- min_bars={mb}: {len(res)} swing(s) ---")
    for s in res:
        print(f"swing#{s['swing_index']} dir={s['dir']} break_kind={s['break_kind']} "
              f"confirmed_at={tmap.get(s['confirmed_at_time'], s['confirmed_at_time'])} (real)")
        for b in s["breaks"]:
            print(f"   {b['kind']:<4} {b['dir']:<4} nifty {b['time']}  = real {tmap.get(b['time'],'?')}  px={b['px']:.2f}")

# ── debug: why 0 swings? walk the nifty engine manually ─────────────────────
from src.firstswing import SwingEngine
eng = SwingEngine({"min_bars": 14, "b2_gap_bars": 1})
print("\n=== manual walk, min_bars=14, nifty times ===")
for i, f in enumerate(flow):
    eng.process_bar(f, i)
    if eng.break_marks and len(eng.break_marks) > getattr(eng, "_last_n", 0):
        b = eng.break_marks[-1]
        print(f"  {f.date[11:16]}  mark {b.kind} {b.dir} px={b.px:.2f}  (real {tmap.get(f.date[11:16],'?')})")
        eng._last_n = len(eng.break_marks)
    if i in (1, 16, 45, 60, 75, 93):
        lp = eng.e_lo_pivot
        print(f"  bar#{i} {f.date[11:16]} state={eng.state} dir={eng.dir} declared={eng.declared} "
              f"bars_seen={eng.bars_seen} corner={f'{lp.px:.2f}@{lp.time}' if lp else None}")
print(f"final: declared={eng.declared} state={eng.state} dir={eng.dir} marks={[(b.kind,b.time) for b in eng.break_marks]}")
