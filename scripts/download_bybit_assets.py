"""Download isolated Bybit linear-perpetual OHLCV for cross-asset studies.

Files are written to data/bybit-assets/<SYMBOL>_<TF>.csv in the repository's
IST wall-clock convention. Existing BTC/Binance datasets are never modified.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "bybit-assets"
BYBIT_URL = "https://api.bybit.com/v5/market/kline"
IST = timedelta(hours=5, minutes=30)
STEP_MS = {"1m": 60_000, "15m": 900_000, "1h": 3_600_000}
INTERVAL = {"1m": "1", "15m": "15", "1h": "60"}
HEADER = "timestamp,open,high,low,close,volume,turnover,x,y\n"


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "AT_Trading-cross-asset-research/1.0"})
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.loads(response.read())


def ist_to_ms(value: str) -> int:
    dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S") - IST
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


def ms_to_ist(value: int) -> str:
    return (datetime.fromtimestamp(value / 1000.0, tz=timezone.utc) + IST).strftime("%Y-%m-%d %H:%M:%S")


def download(symbol: str, tf: str, start_ms: int, end_ms: int) -> int:
    step = STEP_MS[tf]
    path = OUT_DIR / f"{symbol}_{tf}.csv"
    rows: dict[str, tuple[str, ...]] = {}
    if path.exists():
        with path.open(encoding="utf-8") as handle:
            next(handle, None)
            for line in handle:
                if not line.strip():
                    continue
                parts = line.rstrip("\n").split(",")
                if len(parts) >= 9:
                    rows[parts[0]] = tuple(parts[1:9])

    cur = start_ms
    if rows:
        last = max(rows)
        # Only resume from an existing file when it actually covers the requested
        # start. A previous Bybit response may have been the newest page rather
        # than the oldest page; do not silently build a partial study from it.
        first_existing = min(rows)
        if ist_to_ms(first_existing) > start_ms + step:
            rows.clear()
        else:
            last = max(rows)
            cur = ist_to_ms(last) + step
    total_batches = 0
    while cur < end_ms:
        window_end = min(end_ms, cur + step * 1000 - 1)
        url = (
            f"{BYBIT_URL}?category=linear&symbol={symbol}"
            f"&interval={INTERVAL[tf]}&start={cur}&end={window_end}&limit=1000"
        )
        payload = None
        for attempt in range(8):
            try:
                payload = fetch_json(url)
            except Exception:
                payload = {"retCode": 10006, "retMsg": "network/rate-limit retry"}
            if payload.get("retCode") == 0:
                break
            if payload.get("retCode") not in (10006, 10016) or attempt == 7:
                raise RuntimeError(f"Bybit {symbol} {tf}: {payload}")
            time.sleep(min(60.0, 2.0 * (2 ** attempt)))
        if payload is None or payload.get("retCode") != 0:
            raise RuntimeError(f"Bybit {symbol} {tf}: {payload}")
        batch = list(payload.get("result", {}).get("list", []))
        if not batch:
            break
        batch.reverse()
        progressed = False
        for raw in batch:
            open_ms = int(raw[0])
            if open_ms < start_ms or open_ms + step > end_ms:
                continue
            if not (cur <= open_ms <= window_end):
                continue
            ts = ms_to_ist(open_ms)
            rows[ts] = (
                f"{float(raw[1]):.10g}", f"{float(raw[2]):.10g}",
                f"{float(raw[3]):.10g}", f"{float(raw[4]):.10g}",
                f"{float(raw[5]) if len(raw) > 5 else 0.0:.10g}",
                f"{float(raw[6]) if len(raw) > 6 else 0.0:.10g}", "0", "0",
            )
            progressed = True
        if not progressed:
            break
        last_open = max(int(raw[0]) for raw in batch)
        next_cur = last_open + step
        if next_cur <= cur:
            break
        cur = next_cur
        total_batches += 1
        if total_batches % 25 == 0:
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8", newline="") as handle:
                handle.write(HEADER)
                for ts in sorted(rows):
                    handle.write(ts + "," + ",".join(rows[ts]) + "\n")
            print(f"  {symbol} {tf}: {len(rows):,} candles, batch {total_batches}", flush=True)
        time.sleep(0.08)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(HEADER)
        for ts in sorted(rows):
            handle.write(ts + "," + ",".join(rows[ts]) + "\n")
    print(f"  wrote {len(rows):,} candles -> {path}", flush=True)
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", default=["ETHUSDT", "SOLUSDT"])
    parser.add_argument("--tf", nargs="+", default=["15m", "1h", "1m"], choices=sorted(STEP_MS))
    parser.add_argument("--start", default="2023-01-01 05:30:00")
    parser.add_argument("--end", default=None, help="IST wall-clock end; default now")
    args = parser.parse_args()
    start_ms = ist_to_ms(args.start)
    end_ms = ist_to_ms(args.end) if args.end else int(datetime.now(timezone.utc).timestamp() * 1000)
    for symbol in args.symbols:
        for tf in args.tf:
            print(f"Downloading Bybit linear perp {symbol} {tf}: {args.start} -> end {end_ms}", flush=True)
            download(symbol, tf, start_ms, end_ms)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
