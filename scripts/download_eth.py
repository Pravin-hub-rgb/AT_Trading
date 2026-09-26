"""Download ETHUSDT PERPETUAL FUTURES data from Binance.
Saves to data/eth-fut/ETHUSDT_{tf}.csv (IST wall-clock format).
"""
from __future__ import annotations
import json
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

IST = timedelta(hours=5, minutes=30)
SYMBOL = "ETHUSDT"
FAPI_URL = "https://fapi.binance.com/fapi/v1/klines"
TF_MS = {"15m": 900_000, "1h": 3_600_000}
DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "eth-fut"
START_IST = "2021-01-01 05:30:00"


def _fetch_json(url: str) -> list:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def ist_to_ms(ist_wall: str) -> int:
    dt = datetime.strptime(ist_wall, "%Y-%m-%d %H:%M:%S") - IST
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


def download_tf(tf: str) -> int:
    step_ms = TF_MS[tf]
    start_ms = ist_to_ms(START_IST)
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    path = DATA_DIR / f"{SYMBOL}_{tf}.csv"
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
            print(f"  error: {e}, retry in 2s...")
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
            time.sleep(0.5)
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


for tf in ["15m", "1h"]:
    print(f"Downloading {SYMBOL} futures {tf} from {START_IST}...")
    download_tf(tf)
    print()
