"""Download PERPETUAL 1m data from Binance Futures (fapi).

Saves to data/btc-fut/BTCUSDT_1m.csv in IST wall-clock format by default.
Resumes from checkpoint if file exists.

Usage:
    python scripts/download_binance_fut_1m.py
    python scripts/download_binance_fut_1m.py --start "2023-01-01 05:30:00"
    python scripts/download_binance_fut_1m.py --symbol ETHUSDT \
        --dir data/eth-fut --start "2020-12-31 00:00:00" --sleep 0.3
"""
from __future__ import annotations
import argparse
import json
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

IST = timedelta(hours=5, minutes=30)
SYMBOL = "BTCUSDT"
FUTURES_URL = "https://fapi.binance.com/fapi/v1/klines"
DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "btc-fut"
DEFAULT_START_IST = "2023-01-01 05:30:00"
TF_MS = {"1m": 60_000}


def _fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def download_1m(symbol: str, data_dir: Path, start_ms: int,
                sleep_sec: float = 0.0) -> int:
    step_ms = TF_MS["1m"]
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    path = data_dir / f"{symbol}_1m.csv"
    header = "timestamp,open,high,low,close,x,y\n"
    rows: list[str] = []

    # Resume
    if path.exists():
        existing = path.read_text().splitlines()[1:]
        for line in existing:
            if line.strip():
                rows.append(line + "\n")
        if rows:
            last_ts = rows[-1].split(",")[0]
            dt = datetime.strptime(last_ts, "%Y-%m-%d %H:%M:%S") - IST
            cur = int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000) + step_ms
            print(f"  Resuming from {last_ts} ({len(rows)} existing candles)")
        else:
            cur = start_ms
    else:
        cur = start_ms

    total = len(rows)
    batch = 0
    t_start = time.time()

    while cur < now_ms:
        url = f"{FUTURES_URL}?symbol={symbol}&interval=1m&startTime={cur}&limit=1500"
        try:
            resp = _fetch_json(url)
        except Exception as e:
            print(f"\n  error: {e}, retrying in 2s...")
            time.sleep(2)
            continue

        if not resp:
            break

        for k in resp:
            # k = [openTime, open, high, low, close, volume, closeTime, ...]
            open_time_ms = int(k[0])
            utc_dt = datetime.fromtimestamp(open_time_ms / 1000.0, tz=timezone.utc)
            ist_dt = utc_dt + IST
            ist_str = ist_dt.strftime("%Y-%m-%d %H:%M:%S")
            o, h, lo, c = float(k[1]), float(k[2]), float(k[3]), float(k[4])
            rows.append(f"{ist_str},{o:.2f},{h:.2f},{lo:.2f},{c:.2f},0,0\n")
            total += 1

        nxt = int(resp[-1][0]) + step_ms
        if nxt <= cur:
            break
        cur = nxt
        batch += 1
        if sleep_sec > 0:
            time.sleep(sleep_sec)

        if batch % 10 == 0:
            elapsed = time.time() - t_start
            last_utc = datetime.fromtimestamp(int(resp[-1][0]) / 1000.0, tz=timezone.utc)
            pct = min(99.9, (last_utc.replace(tzinfo=None) - datetime(2023, 1, 1)).total_seconds() /
                      (datetime.now() - datetime(2023, 1, 1)).total_seconds() * 100)
            bar_len = 30
            filled = int(bar_len * pct / 100)
            bar = "#" * filled + "-" * (bar_len - filled)
            rate = batch / elapsed if elapsed > 0 else 1
            eta_sec = (100 - pct) / max(pct, 0.1) * elapsed if pct > 0 else 0
            print(f"\r  [{bar}] {pct:5.1f}% | {total:>8,} candles | {last_utc.strftime('%Y-%m-%d %H:%M')} | {rate:.1f} batch/s | ETA {eta_sec/60:.0f}m", end="", flush=True)

        if batch % 100 == 0 and batch > 0:
            unique: dict[str, str] = {}
            for line in rows:
                ts = line.split(",")[0]
                unique[ts] = line
            data_dir.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(header)
                for ts in sorted(unique):
                    f.write(unique[ts])

    print()

    unique: dict[str, str] = {}
    for line in rows:
        ts = line.split(",")[0]
        unique[ts] = line

    data_dir.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(header)
        for ts in sorted(unique):
            f.write(unique[ts])

    print(f"  wrote {len(unique)} candles -> {path}")
    return len(unique)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Download perp 1m from Binance Futures")
    ap.add_argument("--start", default=DEFAULT_START_IST, help="IST start datetime")
    ap.add_argument("--symbol", default=SYMBOL, help="futures symbol (default BTCUSDT)")
    ap.add_argument("--dir", default=None,
                    help="output dir (default data/btc-fut); relative to repo root")
    ap.add_argument("--sleep", type=float, default=0.0,
                    help="seconds to sleep between requests (rate limit)")
    args = ap.parse_args()

    start_dt = datetime.strptime(args.start, "%Y-%m-%d %H:%M:%S")
    start_ms = int(start_dt.replace(tzinfo=timezone.utc).timestamp() * 1000)

    data_dir = DATA_DIR
    if args.dir:
        root = Path(__file__).resolve().parents[1]
        data_dir = Path(args.dir)
        if not data_dir.is_absolute():
            data_dir = root / data_dir

    print(f"Downloading {args.symbol} perp 1m from Binance Futures "
          f"({args.start}... -> {data_dir})...")
    n = download_1m(args.symbol, data_dir, start_ms, sleep_sec=args.sleep)
    print(f"Done: {n} candles")
