"""Show candles + pivots + entry + SL for 29 May 2026.
Clearly marks the entry candle and shows the 9:55 low in context."""
import sys
sys.path.insert(0, "backend")
import pandas as pd
from src.intraday import _prep_day
from src.walker import WalkerEngine, FlowCandle
from src.config import DATA_DIR

df = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["date"] = df["timestamp"].dt.date
sub = df[df["date"] == pd.Timestamp("2026-05-29").date()].copy().reset_index(drop=True)
sub["time"] = sub["timestamp"].dt.strftime("%H:%M")

candles = _prep_day(sub)
walker = WalkerEngine()
# Track seals as they happen (key = bar_idx)
sealed_lows = {}   # idx -> px
sealed_highs = {}  # idx -> px

for i, row in sub.iterrows():
    fc = FlowCandle(date=f"2026-05-29T{row['time']}:00",
                    open=row["open"], high=row["high"], low=row["low"], close=row["close"])
    pivots = walker.process_bar(fc, i)
    for p in pivots:
        if p.kind == "L":
            sealed_lows[p.idx] = p.px
        else:
            sealed_highs[p.idx] = p.px

# Entry info (from _entry_trace output)
entries = [
    {"bar": 6,  "time": "09:45", "dir": "LONG",  "entry": 23912.0,  "sl": 23884.4,  "pivot_ref": "09:30 L=23885.4"},
    {"bar": 20, "time": "10:55", "dir": "LONG",  "entry": 23903.1,  "sl": 23876.65, "pivot_ref": "10:50 L=23877.65"},
]

# Show candles 09:15 to 11:00 (indices 0-23)
print("=" * 95)
print("  29 MAY 2026  —  5-MIN CANDLES + WALKER PIVOTS + TRADE ENTRY")
print("=" * 95)
print()
print(f"  {'bar':>4}  {'time':>5}  {'open':>9}  {'high':>9}  {'low':>9}  {'close':>9}  |  {'pivot':>12}  note")
print(f"  {'-'*4}  {'-'*5}  {'-'*9}  {'-'*9}  {'-'*9}  {'-'*9}  |  {'-'*12}  {'-'*20}")

for i, row in sub.iterrows():
    if i > 22:
        break
    t = row["time"]
    
    # Determine what was sealed at THIS bar (after process_bar ran)
    # sealed_lows[idx] means the pivot at idx was sealed by the bar at `idx`
    # The pivot at bar N gets sealed when bar N+1 confirms the leg flip
    # So at bar i, we know which pivots were sealed at or before i
    pivot_note = ""
    if i in sealed_lows:
        pivot_note = f"L={sealed_lows[i]}"
    elif i in sealed_highs:
        pivot_note = f"H={sealed_highs[i]}"
    
    note = ""
    marker = " "
    for e in entries:
        if e["bar"] == i:
            marker = ">>>"
            note = f"ENTRY {e['dir']} @ {e['entry']}  SL={e['sl']}  (uses {e['pivot_ref']})"
    
    # Highlight 9:55 candle
    if t == "09:55":
        note = "*** 9:55 LOW = 23887.4 (this candle's low, NOT a sealed pivot yet!)"
        marker = "!!!"

    print(f"  {marker}{i:>3}  {t:>5}  {row['open']:>9.2f}  {row['high']:>9.2f}  {row['low']:>9.2f}  {row['close']:>9.2f}  |  {pivot_note:>12}  {note}")

print()
print("=" * 95)
print("  KEY INSIGHT: 9:55 LOW vs ENTRY TIMING")
print("=" * 95)
print()
print("  ENTRY happens at bar 6 (09:45 candle closes at 09:50)")
print("  9:55 candle forms at bar 8 (closes at 10:00) — this is AFTER the entry!")
print()
print("  A pivot is only 'sealed' when the NEXT candle breaks the extreme.")
print("  The 9:55 low (23887.4) becomes a sealed pivot only when the")
print("  10:00 candle's high (23931.35) breaks above the 9:55 high (23907.70).")
print("  That confirmation happens at bar 9 — AFTER the entry at bar 6.")
print()
print("  At entry time (bar 6, 09:45), the most recent sealed L pivot was")
print("  09:30 L = 23885.4. That's the only valid option at that moment.")
print()
print("  TRADES:")
for e in entries:
    print(f"    {e['dir']} at {e['time']} bar={e['bar']}  entry={e['entry']}  SL={e['sl']}  (pivot_ref={e['pivot_ref']})")
