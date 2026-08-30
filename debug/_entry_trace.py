"""Trace where the long at 09:45 is opened on 29 May 2026.
Show: which pace break triggered, which event chain, which candle."""
import sys
sys.path.insert(0, "backend")
import pandas as pd
from src.intraday import simulate_day, _prep_day, DEFAULT_CFG, FALLBACK_AVG_RANGE
from src.config import DATA_DIR

df = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["date"] = df["timestamp"].dt.date
sub = df[df["date"] == pd.Timestamp("2026-05-29").date()].copy().reset_index(drop=True)
sub["time"] = sub["timestamp"].dt.strftime("%H:%M")

cfg = dict(DEFAULT_CFG)
cfg["sl_mode"] = "prev_pivot"
cfg["sl_pivot_buffer"] = 1.0
r = simulate_day(sub, bias="bullish", cfg=cfg, ctx={"gap": "flat", "extreme": None, "avg_range": FALLBACK_AVG_RANGE})

# Show all candles 09:15 to 10:30
print("=== 29 May candles 09:15-10:30 ===")
print(f"{'idx':>4} {'time':>5} {'open':>9} {'high':>9} {'low':>9} {'close':>9}")
for i, c in enumerate(_prep_day(sub)[:30]):
    print(f"{i:>4} {c['time']:>5} {c['open']:>9.2f} {c['high']:>9.2f} {c['low']:>9.2f} {c['close']:>9.2f}")

print("\n=== All events for 29 May bullish ===")
for e in r["events"]:
    t = e.get("time", "")
    tp = e.get("type", "")
    extra = ""
    if "level" in e: extra = f" level={e['level']}"
    if "break_type" in e: extra = f" {e['break_type']}"
    print(f"  bar={e.get('bar','?'):>3} {t:>5}  {tp:32}{extra}")

print("\n=== Trades ===")
for t in r["trades"]:
    print(f"  {t['dir']} {t['entry_time']} entry={t['entry_price']} sl={t['sl']} target={t['target']} outcome={t.get('outcome')}")
    print(f"    btype={t.get('break_type')}")
    print(f"    pivot_ref={t.get('pivot_ref')}")
