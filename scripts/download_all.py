"""Unified BTC download — Binance Spot, Binance Perp, Bybit Perp.

Downloads 1m/15m/1h klines from 2023-01-01 to now. Resumes from checkpoint.
Saves to data/<folder>/BTCUSDT_<tf>.csv in IST wall-clock format.

Usage:
    python scripts/download_all.py                          # all 3 exchanges, 1m+15m+1h
    python scripts/download_all.py --exchange spot          # Binance Spot only
    python scripts/download_all.py --exchange perp          # Binance Perp only
    python scripts/download_all.py --exchange bybit         # Bybit Perp only
    python scripts/download_all.py --tf 1m                  # all exchanges, 1m only
    python scripts/download_all.py --exchange spot --tf 15m # Binance Spot 15m only
    python scripts/download_all.py --start "2024-01-01 05:30:00"
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
DEFAULT_START_IST = "2023-01-01 05:30:00"
TF_MS = {"1m": 60_000, "15m": 900_000, "1h": 3_600_000}

EXCHANGES = {
    "spot": {
        "label": "Binance Spot",
        "url": "https://api.binance.com/api/v3/klines",
        "dir": "btc",
        "interval_param": True,  # interval=<tf>
        "limit": 1000,
    },
    "perp": {
        "label": "Binance Perp",
        "url": "https://fapi.binance.com/fapi/v1/klines",
        "dir": "btc-fut",
        "interval_param": True,
        "limit": 1500,
    },
    "bybit": {
        "label": "Bybit Perp",
        "url": "https://api.bybit.com/v5/market/kline",
        "dir": "bybit",
        "interval_param": False,  # uses Bybit interval codes
        "limit": 1000,
    },
}

TF_BYBIT = {"1m": "1", "15m": "15", "1h": "60"}


def _fetch_json(url: str) -> list | dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def ist_to_ms(ist_wall: str) -> int:
    dt = datetime.strptime(ist_wall, "%Y-%m-%d %H:%M:%S") - IST
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


def download_tf(exchange: str, tf: str, start_ms: int) -> int:
    """Download all candles for one exchange + timeframe. Returns count."""
    cfg = EXCHANGES[exchange]
    data_dir = Path(__file__).resolve().parents[1] / "data" / cfg["dir"]
    step_ms = TF_MS[tf]
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    path = data_dir / f"{SYMBOL}_{tf}.csv"
    header = "timestamp,open,high,low,close,x,y\n"
    rows: list[str] = []

    # Resume from checkpoint
    if path.exists():
        existing = path.read_text().splitlines()[1:]
        for line in existing:
            if line.strip():
                rows.append(line + "\n")
        if rows:
            last_ts = rows[-1].split(",")[0]
            dt = datetime.strptime(last_ts, "%Y-%m-%d %H:%M:%S") - IST
            cur = int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000) + step_ms
            print(f"  Resuming from {last_ts} ({len(rows):,} existing candles)")
        else:
            cur = start_ms
    else:
        cur = start_ms

    total = len(rows)
    batch = 0
    t_start = time.time()

    while cur < now_ms:
        # Build URL
        if cfg["interval_param"]:
            bybit_interval = tf
            url = f"{cfg['url']}?symbol={SYMBOL}&interval={bybit_interval}&startTime={cur}&limit={cfg['limit']}"
        else:
            bybit_interval = TF_BYBIT[tf]
            url = f"{cfg['url']}?category=linear&symbol={SYMBOL}&interval={bybit_interval}&start={cur}&limit={cfg['limit']}"

        try:
            resp = _fetch_json(url)
        except Exception as e:
            print(f"\n  error: {e}, retrying in 2s...")
            time.sleep(2)
            continue

        # Parse response
        if exchange == "bybit":
            if resp.get("retCode") != 0:
                print(f"\n  API error: {resp.get('retMsg', 'unknown')}, retrying...")
                time.sleep(2)
                continue
            data = resp.get("result", {}).get("list", [])
            data.reverse()  # Bybit returns newest first
        else:
            data = resp
            if not data:
                break

        if not data:
            break

        for k in data:
            if exchange == "bybit":
                open_time_ms = int(k[0])
                o, h, lo, c = float(k[1]), float(k[2]), float(k[3]), float(k[4])
            else:
                open_time_ms = int(k[0])
                o, h, lo, c = float(k[1]), float(k[2]), float(k[3]), float(k[4])

            utc_dt = datetime.fromtimestamp(open_time_ms / 1000.0, tz=timezone.utc)
            ist_dt = utc_dt + IST
            ist_str = ist_dt.strftime("%Y-%m-%d %H:%M:%S")
            rows.append(f"{ist_str},{o:.2f},{h:.2f},{lo:.2f},{c:.2f},0,0\n")
            total += 1

        nxt = int(data[-1][0]) + step_ms
        if nxt <= cur:
            break
        cur = nxt
        batch += 1

        # Progress bar every 10 batches
        if batch % 10 == 0:
            elapsed = time.time() - t_start
            last_utc = datetime.fromtimestamp(int(data[-1][0]) / 1000.0, tz=timezone.utc)
            pct = min(99.9, (last_utc.replace(tzinfo=None) - datetime(2023, 1, 1)).total_seconds() /
                      (datetime.now() - datetime(2023, 1, 1)).total_seconds() * 100)
            bar_len = 30
            filled = int(bar_len * pct / 100)
            bar = "#" * filled + "-" * (bar_len - filled)
            rate = batch / elapsed if elapsed > 0 else 1
            eta_sec = (100 - pct) / max(pct, 0.1) * elapsed if pct > 0 else 0
            print(f"\r  [{bar}] {pct:5.1f}% | {total:>8,} candles | {last_utc.strftime('%Y-%m-%d %H:%M')} | {rate:.1f} batch/s | ETA {eta_sec/60:.0f}m", end="", flush=True)

        # Checkpoint every 100 batches
        if batch % 100 == 0 and batch > 0:
            _save(path, header, rows)

    print()

    # Final save
    count = _save(path, header, rows)
    print(f"  [{tf}] wrote {count:,} candles -> {path}")
    return count


def _save(path: Path, header: str, rows: list[str]) -> int:
    unique: dict[str, str] = {}
    for line in rows:
        ts = line.split(",")[0]
        unique[ts] = line
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(header)
        for ts in sorted(unique):
            f.write(unique[ts])
    return len(unique)


def main() -> int:
    ap = argparse.ArgumentParser(description="Unified BTC kline downloader")
    ap.add_argument("--exchange", nargs="+", default=["spot", "perp", "bybit"],
                    choices=sorted(EXCHANGES), help="Exchange(s) to download")
    ap.add_argument("--tf", nargs="+", default=["1m", "15m", "1h"],
                    choices=sorted(TF_MS), help="Timeframe(s)")
    ap.add_argument("--start", default=DEFAULT_START_IST,
                    help="IST start datetime (default: 2023-01-01 05:30:00)")
    args = ap.parse_args()

    start_ms = ist_to_ms(args.start)
    total_candles = 0

    for exchange in args.exchange:
        cfg = EXCHANGES[exchange]
        print(f"\n{'='*60}")
        print(f"  {cfg['label']} ({cfg['dir']}/)")
        print(f"{'='*60}")
        for tf in args.tf:
            print(f"\n  Downloading {SYMBOL} {tf} from {args.start}...")
            n = download_tf(exchange, tf, start_ms)
            total_candles += n

    print(f"\n{'='*60}")
    print(f"  TOTAL: {total_candles:,} candles downloaded")
    print(f"{'='*60}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
