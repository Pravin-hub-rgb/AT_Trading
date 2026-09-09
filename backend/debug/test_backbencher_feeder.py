"""Backbencher feeder replay test — prove the stolen aggregation core works.

Simulates live ticks from the 1m CSV (each 1m bar becomes 4 pseudo-ticks:
O,H,L,C — so intra-minute extremes are preserved), feeds the LiveAggregator,
and verifies against the OFFICIAL data/btc CSVs:

  1. every closed 15m candle == the 15m CSV row (date/ts/OHLC, exact)
  2. every closed 1h candle  == the 1h CSV row  (date/ts/OHLC, exact)
  3. per hour: exactly 4 x 15m closes + 1 x 1h close
  4. hour-boundary order: 1h close event BEFORE the 4th 15m close of that
     hour (engine must update windows before the LTF decision)
  5. IST wall-clock conversion matches the CSV date strings
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.btc.btc_config import load_btc_df
from src.live.aggregator import LiveAggregator

D0, D1 = "2023-01-03", "2023-01-06"  # replay window (IST days)

df1 = load_btc_df("1m")
df15 = load_btc_df("15m")
df1h = load_btc_df("1h")

m1 = df1[(df1.timestamp >= D0) & (df1.timestamp < D1)]
m15 = df15[(df15.timestamp >= D0) & (df15.timestamp < D1)]
m1h = df1h[(df1h.timestamp >= D0) & (df1h.timestamp < D1)]
m1 = m1.reset_index(drop=True)
print(f"replay window {D0}..{D1}: {len(m1)} 1m bars, "
      f"{len(m15)} 15m rows, {len(m1h)} 1h rows (official)")

events = []
agg = LiveAggregator(events.append)

# start at a UTC-hour boundary = IST wall time HH:30:00 (Binance buckets)
start_i = next(i for i, t in enumerate(m1.timestamp)
               if str(t).endswith(":30:00"))
print(f"feeding from {m1.timestamp[start_i]} (UTC-hour boundary)")
for row in m1.iloc[start_i:].itertuples():
    ts_ms = int(row.ts) * 1000  # csv ts == true utc epoch (see aggregator doc)
    for px in (row.open, row.high, row.low, row.close):
        agg.on_tick(float(px), ts_ms)

# the forming (never-emitted) candles cover the final bucket of each TF
last15 = agg.forming["15m"]["start_s"]
last1h = agg.forming["1h"]["start_s"]

got15 = {e["ts"]: e for e in events if e["tf"] == "15m"}
got1h = {e["ts"]: e for e in events if e["tf"] == "1h"}

errs = []
checked15 = checked1h = 0
feed_start_s = int(m1.iloc[start_i].ts)  # nothing before this was fed
for row in m15.itertuples():
    if int(row.ts) >= last15 or int(row.ts) < feed_start_s:
        continue  # forming candle / predates the feed
    e = got15.get(int(row.ts))
    if e is None:
        errs.append(f"15m MISSING {row.timestamp}")
        continue
    checked15 += 1
    if (e["date"] != str(row.timestamp) or e["open"] != row.open
            or e["high"] != row.high or e["low"] != row.low
            or e["close"] != row.close):
        errs.append(f"15m MISMATCH {row.timestamp}: got "
                    f"({e['date']}, {e['open']},{e['high']},{e['low']},{e['close']})")
for row in m1h.itertuples():
    if int(row.ts) >= last1h or int(row.ts) < feed_start_s:
        continue
    e = got1h.get(int(row.ts))
    if e is None:
        errs.append(f"1h MISSING {row.timestamp}")
        continue
    checked1h += 1
    if (e["date"] != str(row.timestamp) or e["open"] != row.open
            or e["high"] != row.high or e["low"] != row.low
            or e["close"] != row.close):
        errs.append(f"1h MISMATCH {row.timestamp}: got "
                    f"({e['date']}, {e['open']},{e['high']},{e['low']},{e['close']})")

extra15 = set(got15) - {int(r.ts) for r in m15.itertuples()}
extra1h = set(got1h) - {int(r.ts) for r in m1h.itertuples()}
if extra15:
    errs.append(f"15m EXTRA events: {len(extra15)}")
if extra1h:
    errs.append(f"1h EXTRA events: {len(extra1h)}")

# per-hour counts + boundary order
order_errs = 0
seq = [(e["tf"], e["ts"]) for e in events]
pos = {("tf", t): i for i, (tf_, t) in enumerate((x[0], x[1]) for x in seq)}
idx15, idx1h = [], []
for i, (tf_, ts) in enumerate(seq):
    (idx15 if tf_ == "15m" else idx1h).append((ts, i))
hour_15 = {}
for ts, i in idx15:
    hour_15.setdefault(ts // 3600, []).append((ts, i))
hours_full = [h for h, lst in hour_15.items() if len(lst) == 4]
for h in hours_full:
    if h * 3600 not in got1h:
        continue
    fourth_idx = max(i for _, i in hour_15[h])
    h1_idx = next(i for ts, i in idx1h if ts == h * 3600)
    if h1_idx > fourth_idx:
        order_errs += 1
        errs.append(f"ORDER: 1h close for hour {h} came AFTER 4th 15m close")

print(f"\nticks fed            : {agg.n_ticks}")
print(f"15m closes emitted   : {agg.n_closes['15m']}  (checked vs CSV: {checked15})")
print(f"1h closes emitted    : {agg.n_closes['1h']}  (checked vs CSV: {checked1h})")
print(f"full hours (4x15m)   : {len(hours_full)}")
print(f"boundary-order checks: {len(hours_full)} hours, {order_errs} violations")
print(f"errors               : {len(errs)}")
for e in errs[:10]:
    print("  " + e)
if not errs:
    print("\n>>> PASS: tick->15m->1h aggregation reproduces the official OHLC")
    print(">>> exactly, with correct hour-boundary event order.")
