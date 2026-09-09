"""Color audit: what candle color does each mark type print on? (15m, full sample)

Answers: 'does the engine already behave like a red/green gate?'
- color of B1/B2/FLIP mark bars (close vs open)
- swallowed breaches: bars whose low breached the pre-bar corner but no B2 fired
  -> color split of those (green sweep vs red swallowed)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings
from src.firstswing import SwingEngine
from src.walker import FlowCandle

df = load_btc_df("15m")
df["timestamp"] = pd.to_datetime(df["timestamp"])
win = df[df["timestamp"] >= "2023-01-01"].reset_index(drop=True)
candles = [
    {"date": r["timestamp"].strftime("%Y-%m-%d %H:%M:%S"), "open": float(r["open"]), "high": float(r["high"]),
     "low": float(r["low"]), "close": float(r["close"])}
    for _, r in win.iterrows()
]
flow = [FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"]) for c in candles]
print(f"bars: {len(candles)}  {candles[0]['date']} -> {candles[-1]['date']}")

res = _compute_swings(flow, "continuous", min_bars=50)

# 1) color of every printed mark
from collections import Counter
mark_color = Counter()
for s in res:
    for b in s["breaks"]:
        bar = candles[b["idx"]]
        col = "green" if bar["close"] > bar["open"] else ("red" if bar["close"] < bar["open"] else "flat")
        mark_color[(b["kind"], b["dir"], col)] += 1
print("\n=== printed-mark colors ===")
for kind in ("B1", "B2", "FLIP"):
    tot = sum(v for (k, d, c), v in mark_color.items() if k == kind)
    g = sum(v for (k, d, c), v in mark_color.items() if k == kind and c == "green")
    r_ = sum(v for (k, d, c), v in mark_color.items() if k == kind and c == "red")
    f_ = sum(v for (k, d, c), v in mark_color.items() if k == kind and c == "flat")
    print(f"{kind:<4} total={tot:<5} green={g:<5} red={r_:<5} flat={f_}")

# 2) swallowed breaches: replay engine, watch corner state
eng = SwingEngine({"min_bars": 50, "b2_gap_bars": 1})
swallowed = Counter()   # (dir, color)
fired = Counter()       # (dir, color)
prev_lo = prev_hi = None
for i, (c, f) in enumerate(zip(candles, flow)):
    pl, ph = prev_lo, prev_hi
    n_before = len(eng.break_marks)
    eng.process_bar(f, i)
    n_after = len(eng.break_marks)
    col = "green" if c["close"] > c["open"] else ("red" if c["close"] < c["open"] else "flat")
    lp = eng.e_lo_pivot
    hp = eng.e_hi_pivot
    # down-side: bar low breached the pre-bar lo corner
    if pl is not None and c["low"] < pl.px:
        if n_after > n_before and any(b.kind == "B2" and b.dir == "down" for b in eng.break_marks[n_before:]):
            fired[("down", col)] += 1
        elif lp is not None and lp.px == c["low"] and lp.time == c["date"][11:16]:
            swallowed[("down", col)] += 1
    if ph is not None and c["high"] > ph.px:
        if n_after > n_before and any(b.kind == "B2" and b.dir == "up" for b in eng.break_marks[n_before:]):
            fired[("up", col)] += 1
        elif hp is not None and hp.px == c["high"] and hp.time == c["date"][11:16]:
            swallowed[("up", col)] += 1
    prev_lo, prev_hi = lp, hp

print("\n=== B2 breach bars: fired vs swallowed (by color) ===")
print(f"{'dir':<5} {'color':<6} {'fired':>6} {'swallowed':>10}")
for d in ("down", "up"):
    for c_ in ("red", "green", "flat"):
        print(f"{d:<5} {c_:<6} {fired[(d, c_)]:>6} {swallowed[(d, c_)]:>10}")

# 3) what happened AFTER a swallow: did the new corner eventually get broken (B2 fires later)?
print("\n(not computed here — see v21 for the counterfactual)")
