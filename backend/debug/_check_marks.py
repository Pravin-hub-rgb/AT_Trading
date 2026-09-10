import sys
sys.path.insert(0, '.')
from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings
from src.walker import FlowCandle

df = load_btc_df('15m')
candles = []
for row in df.itertuples():
    date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    candles.append({"date": date, "ts": int(row.ts), "open": float(row.open), "high": float(row.high), "low": float(row.low), "close": float(row.close)})

flow = [FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"]) for c in candles]
swings = _compute_swings(flow, "continuous", min_bars=50)

for s in swings:
    for b in s.get("breaks", []):
        idx = b.get("idx", -1)
        if 0 <= idx < len(candles):
            t = candles[idx]["date"]
            if "2026-09-09" in t or "2026-09-10" in t:
                print(f"  {t} | {b['kind']:<4} {b['dir']:<4} sw{s['swing_index']} @ {b['px']:.2f}")

