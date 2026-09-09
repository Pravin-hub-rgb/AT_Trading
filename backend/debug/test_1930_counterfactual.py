"""Counterfactual: swing 9, Jan 5 19:30 bar.

Real bar: O=16780.79 H=16810.00 L=16753.00 C=16803.83 (green OUTSIDE bar:
broke prev low 16777.86 AND prev high 16803.00) -> engine sealed 16753 as
new pivot, NO B2.

Hypothetical: same bar but H=16802, C=16801 (still green, still breaks the
low, but does NOT break 19:15's high) -> what does the engine do?

If 'seal requires the opposite-side break', then hypothetical should print
B2 at 19:30 (plain breach, no re-anchor).
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

def build(modify_1930: bool):
    candles = []
    for _, r in win.iterrows():
        d = r["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        o, h, l, c = float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"])
        if modify_1930 and d == "2023-01-05 19:30:00":
            o, h, l, c = 16780.79, 16802.00, 16753.00, 16801.00  # green, no prev-high break
        candles.append({"date": d, "open": o, "high": h, "low": l, "close": c})
    flow = [FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"]) for c in candles]
    return candles, flow

for label, mod in (("ORIGINAL (H=16810 outside bar)", False), ("HYPOTHETICAL (H=16802, no high break)", True)):
    candles, flow = build(mod)
    res = _compute_swings(flow, "continuous", min_bars=50)
    print(f"\n=== {label} ===")
    for s in res:
        si = s["seg"]["start_idx"]
        start = candles[si]["date"] if si < len(candles) else "?"
        if not start.startswith("2023-01-05"):
            continue
        end = candles[s["seg"]["end_idx"]]["date"]
        print(f"swing#{s['swing_index']} dir={s['dir']} break_kind={s['break_kind']} "
              f"seg {start}({s['seg']['start_px']:.2f}) -> {end}({s['seg']['end_px']:.2f}) conf@{s['confirmed_at_time']}")
        for b in s["breaks"]:
            bar = candles[b["idx"]]
            print(f"   {b['kind']:<4} {b['dir']:<4} @ {bar['date']}  px={b['px']:.2f}  bar O={bar['open']:.2f} H={bar['high']:.2f} L={bar['low']:.2f} C={bar['close']:.2f}")
