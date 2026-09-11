"""Download BTCUSDT PERPETUAL FUTURES data from Binance.

Fetches 15m and 1h klines from fapi.binance.com for 2023-01-01 to now.
Saves to data/btc-fut/BTCUSDT_15m.csv and BTCUSDT_1h.csv (same IST wall-clock format).

Usage:
    python scripts/download_fut_data.py          # download both 15m and 1h
    python scripts/download_fut_data.py --tf 15m # download only 15m
"""
from __future__ import annotations
import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

IST = timedelta(hours=5, minutes=30)
SYMBOL = "BTCUSDT"
FAPI_URL = "https://fapi.binance.com/fapi/v1/klines"
TF_MS = {"15m": 900_000, "1h": 3_600_000, "4h": 14_400_000}
DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "btc-fut"
START_IST = "2023-01-01 05:30:00"  # 2023-01-01 00:00 UTC = 05:30 IST


def _fetch_json(url: str) -> list:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def ist_to_ms(ist_wall: str) -> int:
    dt = datetime.strptime(ist_wall, "%Y-%m-%d %H:%M:%S") - IST
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


def download_tf(tf: str, symbol: str, data_dir: Path) -> int:
    """Download all candles for a timeframe. Returns rows written."""
    step_ms = TF_MS[tf]
    start_ms = ist_to_ms(START_IST)
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    path = data_dir / f"{symbol}_{tf}.csv"
    header = "timestamp,open,high,low,close,x,y\n"
    rows: list[str] = []

    cur = start_ms
    batch = 0
    total = 0
    while cur < now_ms:
        url = f"{FAPI_URL}?symbol={SYMBOL}&interval={tf}&startTime={cur}&limit=1000"
        try:
            data = _fetch_json(url)
        except Exception as e:
            print(f"  error at {cur}: {e}, retrying in 2s...")
            time.sleep(2)
            continue

        if not data:
            break

        for k in data:
            utc_dt = datetime.fromtimestamp(k[0] / 1000.0, tz=timezone.utc)
            ist_dt = utc_dt + IST
            ist_str = ist_dt.strftime("%Y-%m-%d %H:%M:%S")
            o, h, lo, c = float(k[1]), float(k[2]), float(k[3]), float(k[4])
            rows.append(f"{ist_str},{o:.2f},{h:.2f},{lo:.2f},{c:.2f},0,0\n")
            total += 1

        nxt = data[-1][0] + step_ms
        if nxt <= cur:
            break
        cur = nxt
        batch += 1

        if batch % 50 == 0:
            print(f"  [{tf}] batch {batch}, {total} candles, last={ist_str}")
            time.sleep(0.5)  # rate limit headroom

    # Deduplicate by timestamp and sort
    unique: dict[str, str] = {}
    for line in rows:
        ts = line.split(",")[0]
        unique[ts] = line

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(header)
        for ts in sorted(unique):
            f.write(unique[ts])

    print(f"  [{tf}] wrote {len(unique)} candles -> {path}")
    return len(unique)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", nargs="+", default=["15m", "1h"],
                    choices=sorted(TF_MS))
    args = ap.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for tf in args.tf:
        print(f"Downloading {SYMBOL} futures {tf} from {START_IST}...")
        n = download_tf(tf)
        print(f"  Done: {n} candles\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
