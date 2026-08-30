"""Verify trade shape is correct in prev_pivot mode."""
import sys
sys.path.insert(0, "backend")
import pandas as pd
from src.config import DATA_DIR
from src.intraday import simulate_day, _prep_day, _classify_first_swing_v2, DEFAULT_CFG

df = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["ts"] = df["timestamp"].astype("int64") // 10**9

target = df["timestamp"].dt.date.iloc[-1]
day = df[df["timestamp"].dt.date == target]
candles = _prep_day(day)
swing_dir, swing_start, ev = _classify_first_swing_v2(candles, str(target))

cfg = dict(DEFAULT_CFG)
cfg["sl_mode"] = "prev_pivot"

# Scan last 5 days with correct bias_map to find which days actually have trades
from src.intraday import FALLBACK_AVG_RANGE, MIN_CANDLES

df["date"] = df["timestamp"].dt.date
dates = sorted(df["date"].unique())[-5:]

all_results = []
for d in dates:
    sub = df[df["date"] == d]
    if len(sub) < MIN_CANDLES:
        continue
    # Try both biases
    for bias in ("bullish", "bearish"):
        r = simulate_day(sub, bias=bias, cfg=cfg, ctx={"gap": "flat", "extreme": None, "avg_range": FALLBACK_AVG_RANGE})
        if r["trades"]:
            all_results.append({"date": str(d), "bias": bias, "n": len(r["trades"]), "sample": r["trades"][0]})
result = {"summary": all_results, "trades": []}
if all_results:
    # pick first with trades for shape inspection
    first_date = all_results[0]["date"]
    first_bias = all_results[0]["bias"]
    sub = df[df["date"] == pd.Timestamp(first_date).date()]
    r = simulate_day(sub, bias=first_bias, cfg=cfg, ctx={"gap": "flat", "extreme": None, "avg_range": FALLBACK_AVG_RANGE})
    result = r

with open("debug/_trade_check.txt", "w") as f:
    f.write(f"Day: {target}\n")
    f.write(f"First swing: {swing_dir} at idx {swing_start}\n")
    f.write(f"Trades: {len(result['trades'])}\n")
    for t in result["trades"]:
        f.write(f"  {t['dir']} {t['entry_time']} entry={t['entry_price']} sl={t['sl']} target={t['target']} outcome={t.get('outcome')} r={t.get('r_multiple')}\n")
        f.write(f"    sl_mode_used={t.get('sl_mode_used')} pivot_ref={t.get('pivot_ref')}\n")
        f.write(f"    exit_ts={t.get('exit_ts')} entry_ts={t.get('entry_ts')}\n")
    # Also append day-by-day summary
    f.write("\n--- per-day trade count (prev_pivot, buffer=1.0) ---\n")
    import collections
    by_day = collections.Counter()
    for d in dates:
        sub = df[df["date"] == d]
        if len(sub) < MIN_CANDLES:
            continue
        for bias in ("bullish", "bearish"):
            r = simulate_day(sub, bias=bias, cfg=cfg, ctx={"gap": "flat", "extreme": None, "avg_range": FALLBACK_AVG_RANGE})
            by_day[str(d)] += len(r["trades"])
    for d in sorted(by_day):
        f.write(f"  {d}: {by_day[d]} trades\n")
print("OK")
