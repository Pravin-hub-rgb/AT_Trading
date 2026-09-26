"""Download the complete Bybit BTCUSDT 5m history for the 5m-confirmation study.

The main IS ledger starts in 2023, but the original local 5m file starts in
2025. This isolated fetcher fills the missing prefix and merges it with the
existing BTCUSDT_5m.csv without touching 15m/1h data.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/bybit/BTCUSDT_5m.csv"
URL = "https://api.bybit.com/v5/market/kline"
IST = timedelta(hours=5, minutes=30)
STEP_MS = 300_000


def fetch(cur, end):
    url = f"{URL}?category=linear&symbol=BTCUSDT&interval=5&start={cur}&end={end}&limit=1000"
    req = urllib.request.Request(url, headers={"User-Agent": "AT_Trading-5m-confirmation-research/1.0"})
    for attempt in range(8):
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                payload = json.loads(response.read().decode())
            if payload.get("retCode") == 0:
                return list(reversed(payload.get("result", {}).get("list", [])))
            if payload.get("retCode") not in (10006, 10016):
                raise RuntimeError(payload)
        except Exception:
            if attempt == 7:
                raise
            time.sleep(min(60, 2 ** attempt))
    return []


def ist_to_ms(value):
    dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S") - IST
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2023-01-01 05:30:00")
    ap.add_argument("--end", default="2026-09-13 23:55:00")
    args = ap.parse_args()
    start, end = ist_to_ms(args.start), ist_to_ms(args.end)
    rows = {}
    if OUT.exists():
        for line in OUT.read_text().splitlines()[1:]:
            if line.strip():
                parts = line.split(",")
                if len(parts) >= 6:
                    rows[parts[0]] = parts[1:6]
    cur = start
    batch_no = 0
    while cur < end:
        batch = fetch(cur, min(end - 1, cur + STEP_MS * 1000 - 1))
        if not batch:
            break
        progressed = False
        for raw in batch:
            open_ms = int(raw[0])
            if not (start <= open_ms <= end):
                continue
            wall = (datetime.fromtimestamp(open_ms / 1000, tz=timezone.utc) + IST).strftime("%Y-%m-%d %H:%M:%S")
            rows[wall] = [raw[1], raw[2], raw[3], raw[4], raw[5] if len(raw) > 5 else "0"]
            progressed = True
        last = int(batch[-1][0])
        nxt = last + STEP_MS
        if not progressed or nxt <= cur:
            break
        cur = nxt
        batch_no += 1
        if batch_no % 25 == 0:
            print(f"  {len(rows):,} rows through {cur}", flush=True)
        time.sleep(0.05)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        handle.write("timestamp,open,high,low,close,volume\n")
        for stamp in sorted(rows):
            handle.write(",".join([stamp, *rows[stamp]]) + "\n")
    print(f"wrote {len(rows):,} rows -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
