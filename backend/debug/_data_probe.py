import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.btc.btc_config import load_btc_df
from src.live.boot_data import fetch_klines

TS = [1788538500, 1788624900, 1788628500]
df = load_btc_df("15m")
by_ts = {int(r.ts): r for r in df.itertuples()}
live = {c["ts"]: c for c in fetch_klines("BTCUSDT", "15m", 2880)}
for ts in TS:
    c, l = by_ts.get(ts), live.get(ts)
    if c is None:
        print(f"ts={ts}: NOT IN CSV")
    else:
        print(f"ts={ts} CSV : {c.timestamp} O {c.open} H {c.high} L {c.low} C {c.close}")
    if l:
        print(f"       LIVE: {l['date']} O {l['open']} H {l['high']} L {l['low']} C {l['close']}")
print("\nCSV last row:", df.iloc[-1].timestamp)
