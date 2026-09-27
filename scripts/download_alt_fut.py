"""Download engine-grade ETHUSDT/SOLUSDT perp candles (Binance fapi) to data/alt-fut/.

Purpose (Paradigm 6, Stage CrossAssetBinance): the frozen v18 lanes need
full-precision OHLC on instruments/venue never seen by any engine run.
data/eth-fut and data/scan-fut are SHARED stat-arb inputs (written with
:.2f rounding) and are therefore NEVER mutated here - this script writes a
clean copy under data/alt-fut/ with RAW fapi precision (SOL native is 4dp;
2dp is lossy below ~$10 price).

Format: same as the rest of the repo - header
"timestamp,open,high,low,close,x,y", IST wall-clock open-time stamps.
Resumes from checkpoint if file exists.

Usage:
    python scripts/download_alt_fut.py --symbol ETHUSDT --tf 15m
    python scripts/download_alt_fut.py --symbol SOLUSDT --tf 1m --sleep 0.3
"""
from __future__ import annotations
import argparse
import json
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

IST = timedelta(hours=5, minutes=30)
FUTURES_URL = "https://fapi.binance.com/fapi/v1/klines"
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "alt-fut"
DEFAULT_START_IST = "2020-12-31 00:00:00"
TF_MS = {"1m": 60_000, "15m": 900_000, "1h": 3_600_000}
TF_LIMIT = {"1m": 1500, "15m": 1000, "1h": 1000}


def _fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def download(symbol: str, tf: str, start_ms: int, sleep_sec: float) -> int:
    step_ms = TF_MS[tf]
    limit = TF_LIMIT[tf]
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    path = DATA_DIR / f"{symbol}_{tf}.csv"
    header = "timestamp,open,high,low,close,x,y\n"
    rows: list[str] = []

    if path.exists():
        existing = path.read_text(encoding="utf-8").splitlines()[1:]
        rows = [ln + "\n" for ln in existing if ln.strip()]
    if rows:
        last_ts = rows[-1].split(",")[0]
        dt = datetime.strptime(last_ts, "%Y-%m-%d %H:%M:%S") - IST
        cur = int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000) + step_ms
        print(f"  resuming {symbol}/{tf} from {last_ts} ({len(rows)} rows)")
    else:
        cur = start_ms

    total = len(rows)
    batch = 0
    t0 = time.time()
    while cur < now_ms:
        url = (f"{FUTURES_URL}?symbol={symbol}&interval={tf}"
               f"&startTime={cur}&limit={limit}")
        try:
            resp = _fetch_json(url)
        except Exception as e:  # noqa: BLE001 - rate limit / transient
            print(f"\n  error: {e}; retry in 3s...", flush=True)
            time.sleep(3)
            continue
        if not resp:
            break

        for k in resp:
            open_ms = int(k[0])
            ist_dt = datetime.fromtimestamp(open_ms / 1000.0, tz=timezone.utc) + IST
            rows.append("%s,%s,%s,%s,%s,0,0\n" % (
                ist_dt.strftime("%Y-%m-%d %H:%M:%S"),
                k[1], k[2], k[3], k[4]))
            total += 1

        nxt = int(resp[-1][0]) + step_ms
        if nxt <= cur:
            break
        cur = nxt
        batch += 1
        if sleep_sec > 0:
            time.sleep(sleep_sec)

        if batch % 50 == 0:
            last_utc = datetime.fromtimestamp(int(resp[-1][0]) / 1000.0,
                                              tz=timezone.utc)
            rate = batch / max(time.time() - t0, 1e-9)
            print(f"  [{symbol}/{tf}] {batch} batches, {total} rows, "
                  f"last {last_utc:%Y-%m-%d %H:%M}, {rate:.1f} batch/s",
                  flush=True)

        if batch % 100 == 0 and batch > 0:
            _write(path, header, rows)

    _write(path, header, rows)
    print(f"  wrote {len({r.split(',', 1)[0] for r in rows})} candles -> {path}")
    return total


def _write(path: Path, header: str, rows: list[str]) -> None:
    unique: dict[str, str] = {}
    for line in rows:
        unique[line.split(",", 1)[0]] = line
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(header)
        for ts in sorted(unique):
            f.write(unique[ts])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Download ETH/SOL perp klines "
                                             "(raw precision) to data/alt-fut")
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--tf", required=True, choices=list(TF_MS))
    ap.add_argument("--start", default=DEFAULT_START_IST)
    ap.add_argument("--sleep", type=float, default=0.15)
    args = ap.parse_args()

    start_dt = datetime.strptime(args.start, "%Y-%m-%d %H:%M:%S")
    start_ms = int(start_dt.replace(tzinfo=timezone.utc).timestamp() * 1000)
    print(f"alt-fut: {args.symbol} {args.tf} from {args.start} "
          f"(raw precision, sleep {args.sleep}s)")
    n = download(args.symbol, args.tf, start_ms, args.sleep)
    print(f"Done: {n} rows")
