"""Download historical Bybit linear-perpetual OHLCV for the unseen OOS set.

Supports 1m, 5m, 15m, and 1h. Files are written to
 data/unseen/bybit/<SYMBOL>_<TF>.csv in the project's IST wall-clock
convention. Existing files are resumed, never overwritten with another
symbol, and API pagination is chronological.
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
BYBIT_URL = "https://api.bybit.com/v5/market/kline"
TF_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "1h": 3_600_000}
TF_BYBIT = {"1m": "1", "5m": "5", "15m": "15", "1h": "60"}
DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "unseen" / "bybit"
DEFAULT_START_IST = "2021-01-01 05:30:00"
DEFAULT_END_IST = "2022-12-31 23:59:59"


def _fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def ist_to_ms(ist_wall: str) -> int:
    dt = datetime.strptime(ist_wall, "%Y-%m-%d %H:%M:%S") - IST
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


def download_tf(tf: str, symbol: str, data_dir: Path, start_ms: int, end_ms: int) -> int:
    """Download all candles for a timeframe within the date range. Returns rows written."""
    step_ms = TF_MS[tf]
    bybit_interval = TF_BYBIT[tf]

    path = data_dir / f"{symbol}_{tf}.csv"
    header = "timestamp,open,high,low,close,x,y\n"
    rows: list[str] = []

    # Resume from checkpoint if file exists
    if path.exists():
        existing = path.read_text().splitlines()[1:]  # skip header
        for line in existing:
            if line.strip():
                rows.append(line + "\n")
        if rows:
            last_ts = rows[-1].split(",")[0]
            # Convert IST wall clock back to ms
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
    total_batches_est = max(1, (end_ms - start_ms) // (step_ms * 1000))

    while cur < end_ms:
        url = f"{BYBIT_URL}?category=linear&symbol={symbol}&interval={bybit_interval}&start={cur}&limit=1000"
        try:
            resp = _fetch_json(url)
        except Exception as e:
            print(f"\n  error at {cur}: {e}, retrying in 2s...")
            time.sleep(2)
            continue

        if resp.get("retCode") != 0:
            print(f"\n  API error at {cur}: {resp.get('retMsg', 'unknown')}, retrying in 2s...")
            time.sleep(2)
            continue

        data = resp.get("result", {}).get("list", [])
        if not data:
            break

        data.reverse()

        for k in data:
            open_time_ms = int(k[0])
            # Skip candles beyond our end date
            if open_time_ms > end_ms:
                continue
            utc_dt = datetime.fromtimestamp(open_time_ms / 1000.0, tz=timezone.utc)
            ist_dt = utc_dt + IST
            ist_str = ist_dt.strftime("%Y-%m-%d %H:%M:%S")
            o, h, lo, c = float(k[1]), float(k[2]), float(k[3]), float(k[4])
            rows.append(f"{ist_str},{o:.2f},{h:.2f},{lo:.2f},{c:.2f},0,0\n")
            total += 1

        nxt = int(data[-1][0]) + step_ms
        if nxt <= cur:
            break
        cur = nxt
        batch += 1

        if batch % 10 == 0:
            elapsed = time.time() - t_start
            rate = batch / elapsed if elapsed > 0 else 1
            last_utc = datetime.fromtimestamp(int(data[-1][0]) / 1000.0, tz=timezone.utc)
            pct = min(99.9, (last_utc.replace(tzinfo=None) - datetime(2022, 1, 1)).total_seconds() /
                      (datetime(2022, 12, 31) - datetime(2022, 1, 1)).total_seconds() * 100)
            bar_len = 30
            filled = int(bar_len * pct / 100)
            bar = "#" * filled + "-" * (bar_len - filled)
            eta_sec = (100 - pct) / max(pct, 0.1) * elapsed if pct > 0 else 0
            eta_min = eta_sec / 60
            print(f"\r  [{bar}] {pct:5.1f}% | {total:>8,} candles | {last_utc.strftime('%Y-%m-%d %H:%M')} | {rate:.0f} batch/s | ETA {eta_min:.0f}m", end="", flush=True)

        if batch % 100 == 0 and batch > 0:
            # Checkpoint
            unique: dict[str, str] = {}
            for line in rows:
                ts = line.split(",")[0]
                unique[ts] = line
            data_dir.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(header)
                for ts in sorted(unique):
                    f.write(unique[ts])

    print()  # newline after progress bar

    # Final save
    unique: dict[str, str] = {}
    for line in rows:
        ts = line.split(",")[0]
        unique[ts] = line

    data_dir.mkdir(parents=True, exist_ok=True)
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
    ap.add_argument("--start", default=DEFAULT_START_IST,
                    help="IST start time, e.g. '2022-01-01 05:30:00'")
    ap.add_argument("--end", default=DEFAULT_END_IST,
                    help="IST end time, e.g. '2022-12-31 23:59:59'")
    args = ap.parse_args()

    start_ms = ist_to_ms(args.start)
    end_ms = ist_to_ms(args.end)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for tf in args.tf:
        print(f"Downloading {SYMBOL} perp {tf} from Bybit ({args.start} to {args.end})...")
        print(f"  Saving to: {DATA_DIR}")
        n = download_tf(tf, SYMBOL, DATA_DIR, start_ms, end_ms)
        print(f"  Done: {n} candles\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
