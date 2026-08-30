"""Verify 29 May long trade details."""
import sys
sys.path.insert(0, "backend")
import pandas as pd
from src.intraday import simulate_day, _prep_day, DEFAULT_CFG, FALLBACK_AVG_RANGE
from src.config import DATA_DIR

df = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["date"] = df["timestamp"].dt.date
sub = df[df["date"] == pd.Timestamp("2026-05-29").date()].copy()

cfg = dict(DEFAULT_CFG)
cfg["sl_mode"] = "prev_pivot"
cfg["sl_pivot_buffer"] = 1.0
r = simulate_day(sub, bias="bullish", cfg=cfg, ctx={"gap": "flat", "extreme": None, "avg_range": FALLBACK_AVG_RANGE})
print(f"bullish: {len(r['trades'])} trades")
for t in r["trades"]:
    print(f"  {t['dir']} {t['entry_time']} entry={t['entry_price']} sl={t['sl']} target={t['target']} outcome={t.get('outcome')} r={t.get('r_multiple'):.2f}")
    print(f"    pivot_ref={t.get('pivot_ref')}")

# Show 9:30 candle (entry time was 09:45 for first trade; check pivots available)
candles = _prep_day(sub)
print("\n9:30-9:50 candles:")
for c in candles[3:8]:
    print(f"  {c['time']} H={c['high']} L={c['low']} C={c['close']}")
