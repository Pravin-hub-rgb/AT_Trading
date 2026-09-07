"""Backfill Binance 2023-01-01 -> 2025-01-01 candles into data/btc CSVs (prepend).
Properly sorted merge (unlike the append-only fetch script). Progress printed.
"""
import json
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT.parent / "data" / "btc"
IST = timedelta(hours=5, minutes=30)
SYMBOL = "BTCUSDT"
TF_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000,
         "1h": 3_600_000, "4h": 14_400_000}
ORDER = ["4h", "1h", "15m", "5m", "1m"]  # fast frames first
START_UTC = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
END_IST = "2025-01-01 05:30:00"  # first bar already in the CSVs (exclusive)


def fetch_range(tf, start_ms, end_ms):
    step = TF_MS[tf]
    out = {}
    cur = start_ms
    reqs = 0
    while cur < end_ms:
        url = (f"https://api.binance.com/api/v3/klines?symbol={SYMBOL}"
               f"&interval={tf}&limit=1000&startTime={cur}&endTime={end_ms}")
        rows = None
        for attempt in range(4):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    rows = json.loads(r.read().decode())
                break
            except Exception as e:
                print(f"    retry {attempt + 1} ({tf}): {e}", flush=True)
                time.sleep(2 * (attempt + 1))
        if rows is None:
            raise RuntimeError(f"fetch failed permanently for {tf} at {cur}")
        if not rows:
            break
        for k in rows:
            utc = datetime.fromtimestamp(k[0] / 1000.0, tz=timezone.utc)
            ist = (utc + IST).strftime("%Y-%m-%d %H:%M:%S")
            out[ist] = (float(k[1]), float(k[2]), float(k[3]), float(k[4]))
        reqs += 1
        if reqs % 100 == 0:
            at = datetime.fromtimestamp(cur / 1000.0, tz=timezone.utc)
            print(f"    {tf}: req={reqs} candles={len(out)} cursor={at:%Y-%m-%d}", flush=True)
        nxt = rows[-1][0] + step
        if nxt <= cur:
            break
        cur = nxt
        if len(rows) < 1000:
            break
    return out, reqs


def merge_sorted(tf, new_rows):
    path = DATA_DIR / f"BTCUSDT_{tf}.csv"
    existing = {}
    header = "timestamp,open,high,low,close,x,y\n"
    with open(path, encoding="utf-8") as f:
        header = f.readline()
        for line in f:
            if line.strip():
                existing[line.split(",", 1)[0]] = line
    all_rows = dict(existing)
    added = 0
    for t, (o, h, lo, c) in new_rows.items():
        if t not in all_rows:
            all_rows[t] = f"{t},{o:.2f},{h:.2f},{lo:.2f},{c:.2f},0,0\n"
            added += 1
    tmp = path.with_suffix(".csv.tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(header)
        for t in sorted(all_rows):
            f.write(all_rows[t])
    tmp.replace(path)
    return len(existing), added


def main():
    end_ms = int((datetime.strptime(END_IST, "%Y-%m-%d %H:%M:%S") - IST)
                 .replace(tzinfo=timezone.utc).timestamp() * 1000)
    for tf in ORDER:
        print(f"[{tf}] backfilling {START_UTC:%Y-%m-%d} -> {END_IST} ...", flush=True)
        t0 = time.time()
        rows, reqs = fetch_range(tf, int(START_UTC.timestamp() * 1000), end_ms)
        n_exist, added = merge_sorted(tf, rows)
        print(f"[{tf}] DONE: fetched={len(rows)} new_rows={added} existing={n_exist} "
              f"total={n_exist + added} | {time.time() - t0:.0f}s", flush=True)
    print("BACKFILL COMPLETE", flush=True)


if __name__ == "__main__":
    main()
