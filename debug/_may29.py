"""Inspect 29 May 2026 trade with prev_pivot mode."""
import sys
sys.path.insert(0, "backend")
import pandas as pd
from src.intraday import simulate_day, _prep_day, _classify_first_swing_v2, DEFAULT_CFG, FALLBACK_AVG_RANGE, MIN_CANDLES
from src.config import DATA_DIR

df = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["date"] = df["timestamp"].dt.date

# 29 May 2026
target = pd.Timestamp("2026-05-29").date()
sub = df[df["date"] == target].copy()
print(f"Date: {target}, rows: {len(sub)}")
print(f"Range: {sub['timestamp'].iloc[0]} to {sub['timestamp'].iloc[-1]}")

# First show the 9:55 candle (idx 9:30 + ... find by time)
nine55 = sub[sub["timestamp"].dt.strftime("%H:%M") == "09:55"]
print("\n9:55 candle:")
print(nine55.to_string())

candles = _prep_day(sub)
swing_dir, swing_start, ev = _classify_first_swing_v2(candles, str(target))
print(f"\nFirst swing: {swing_dir} at idx {swing_start}")

cfg = dict(DEFAULT_CFG)
cfg["sl_mode"] = "prev_pivot"
cfg["sl_pivot_buffer"] = 1.0

# Try both biases to see which one is in play
for bias in ("bullish", "bearish", "unbiased"):
    r = simulate_day(sub, bias=bias, cfg=cfg, ctx={"gap": "flat", "extreme": None, "avg_range": FALLBACK_AVG_RANGE})
    print(f"\nbias={bias} -> effective_bias={r['effective_bias']} case={r['case']} trades={len(r['trades'])}")
    for t in r["trades"]:
        print(f"  {t['dir']} {t['entry_time']} entry={t['entry_price']} sl={t['sl']} target={t['target']} outcome={t.get('outcome')} r={t.get('r_multiple')}")
        print(f"    sl_mode_used={t.get('sl_mode_used')} pivot_ref={t.get('pivot_ref')}")
