"""Append new forward candles to data/forward/bybit/BTCUSDT_{tf}.csv.

Downloads candles from the Bybit REST API (UTC) and writes them in the same
IST-string CSV format that exp_forward_eval.py expects. Appends only — no
existing row is ever modified. Updates _forward_manifest.json.

Usage:
    cd backtest
    python tests/exp_append_forward_data.py --tf 15m,1h,1m
    python tests/exp_append_forward_data.py --tf 15m --start "2026-10-19 09:15"
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

IST_OFFSET_SEC = 5 * 3600 + 30 * 60
IST_OFFSET = timedelta(seconds=IST_OFFSET_SEC)
REST = "https://api.bybit.com"
TF_MAP = {"1m": ("1", 60), "15m": ("15", 900), "1h": ("60", 3600)}
FWD_DIR = Path(__file__).resolve().parents[2] / "data" / "forward" / "bybit"
MANIFEST = FWD_DIR / "_forward_manifest.json"


def _fetch(symbol: str, interval: str, start_ms: int) -> list[dict]:
    url = (f"{REST}/v5/market/kline?category=linear&symbol={symbol}"
           f"&interval={interval}&limit=1000&start={start_ms}")
    req = urllib.request.Request(url, headers={"User-Agent": "Backbencher/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode())
    if body.get("retCode") != 0:
        raise RuntimeError(f"Bybit API error: {body.get('retMsg', 'unknown')}")
    return body["result"]["list"]


def _to_ist_str(utc_ms: int) -> str:
    dt = datetime.fromtimestamp(utc_ms / 1000, tz=timezone.utc)
    dt += IST_OFFSET
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _read_last_ts(path: Path) -> str | None:
    if not path.exists():
        return None
    with open(path, newline="") as f:
        reader = list(csv.DictReader(f))
    return reader[-1]["timestamp"] if reader else None


def _last_ts_to_start_ms(last_ts: str, step_sec: int) -> int:
    """Convert the last IST CSV timestamp to the UTC epoch-ms to start fetching from."""
    dt = datetime.strptime(last_ts, "%Y-%m-%d %H:%M:%S")
    dt = dt.replace(tzinfo=timezone.utc)
    utc_epoch = int(dt.timestamp()) - IST_OFFSET_SEC
    return (utc_epoch + step_sec) * 1000


def append_forward(tf: str, start_ts: str | None = None):
    key = tf.replace("m", "") if tf != "1h" else "60"
    interval_str, step_sec = TF_MAP[tf]
    path = FWD_DIR / f"BTCUSDT_{tf}.csv"
    header = ["timestamp", "open", "high", "low", "close", "x", "y"]

    last_ts = start_ts or _read_last_ts(path)
    if last_ts is None:
        print(f"  {tf}: no existing forward CSV, aborting (need IS data path)")
        return 0

    start_ms = _last_ts_to_start_ms(last_ts, step_sec)
    print(f"  {tf}: existing last row {last_ts}, fetching from {start_ms} (UTC epoch ms)")

    all_rows = []
    cur_ms = start_ms
    fetched = 0
    while True:
        data = _fetch("BTCUSDT", interval_str, cur_ms)
        if not data:
            break
        data.sort(key=lambda k: int(k[0]))
        for k in data:
            ot = int(k[0])
            if ot < start_ms:
                continue
            ist_str = _to_ist_str(ot)
            all_rows.append({
                "timestamp": ist_str,
                "open": k[1],
                "high": k[2],
                "low": k[3],
                "close": k[4],
                "x": "0",
                "y": "0",
            })
        fetched += len(data)
        newest = max(int(k[0]) for k in data)
        nxt = newest + step_sec * 1000
        if nxt <= cur_ms or len(data) < 1000:
            break
        cur_ms = nxt
        if fetched > 50000:
            print(f"  {tf}: safety limit hit at {fetched} rows")
            break
        time.sleep(0.1)

    if not all_rows:
        print(f"  {tf}: no new rows (already at latest)")
        return 0

    existed = path.exists()
    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        if not existed:
            writer.writeheader()
        for row in all_rows:
            writer.writerow(row)
    print(f"  {tf}: appended {len(all_rows)} rows -> {all_rows[-1]['timestamp']}")
    return len(all_rows)


def update_manifest(tf: str):
    """Update manifest with new row counts."""
    if not MANIFEST.exists():
        manifest = {"symbol": "BTCUSDT", "market": "bybit linear perpetual",
                     "forward_start_ist": "2026-09-13 10:03:00",
                     "rows": {}, "downloaded_utc": datetime.now(timezone.utc).isoformat()}
    else:
        with open(MANIFEST) as f:
            manifest = json.load(f)

    manifest.setdefault("rows", {})
    for t in TF_MAP:
        p = FWD_DIR / f"BTCUSDT_{t}.csv"
        if p.exists():
            with open(p, newline="") as f:
                count = sum(1 for _ in csv.DictReader(f))
            manifest["rows"][t] = count

    manifest["downloaded_utc"] = datetime.now(timezone.utc).isoformat()
    with open(MANIFEST, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"  manifest updated: {manifest['rows']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="15m,1h,1m",
                    help="comma-separated timeframes: 1m,15m,1h")
    ap.add_argument("--start", default=None,
                    help="IST timestamp string to start fetching from (e.g. '2026-10-19 09:15:00')")
    args = ap.parse_args()

    tfs = [t.strip() for t in args.tf.split(",") if t.strip()]
    total = 0
    for tf in tfs:
        assert tf in TF_MAP, f"unknown tf: {tf}"
        n = append_forward(tf, args.start)
        total += n

    update_manifest(args.tf)
    print(f"\nDone. Appended {total} total rows across {len(tfs)} timeframes.")


if __name__ == "__main__":
    main()
