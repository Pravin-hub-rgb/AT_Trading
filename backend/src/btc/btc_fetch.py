"""Fetch new candles and APPEND to BTC CSVs — all exchanges.

Supports:
  - spot:   Binance Spot  (api.binance.com/api/v3)     -> data/btc/
  - perp:   Binance Perp  (fapi.binance.com/fapi/v1)    -> data/btc-fut/
  - bybit:  Bybit Perp    (api.bybit.com/v5/market/kline) -> data/bybit/
"""
from __future__ import annotations

import json
import time
import urllib.request
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path

warnings.filterwarnings("ignore")

IST = timedelta(hours=5, minutes=30)
SYMBOL = "BTCUSDT"
TF_MS = {
    "1m": 60_000, "5m": 300_000, "15m": 900_000,
    "1h": 3_600_000, "4h": 14_400_000,
}
TF_BYBIT = {"1m": "1", "5m": "5", "15m": "15", "1h": "60", "4h": "240"}
SEED_IST = "2025-01-01 05:30:00"

EXCHANGES = {
    "spot": {
        "label": "Binance Spot",
        "url": "https://api.binance.com/api/v3/klines",
        "dir": "btc",
        "limit": 1000,
    },
    "perp": {
        "label": "Binance Perp",
        "url": "https://fapi.binance.com/fapi/v1/klines",
        "dir": "btc-fut",
        "limit": 1500,
    },
    "bybit": {
        "label": "Bybit Perp",
        "url": "https://api.bybit.com/v5/market/kline",
        "dir": "bybit",
        "limit": 1000,
    },
}


def _data_dir(exchange: str) -> Path:
    """Path to data/<exchange>/ (project root, three levels up from backend/src/btc/)."""
    cfg = EXCHANGES[exchange]
    return Path(__file__).resolve().parents[3] / "data" / cfg["dir"]


def _fetch_json(url: str) -> list | dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def last_ts(exchange: str, tf: str) -> str | None:
    path = _data_dir(exchange) / f"BTCUSDT_{tf}.csv"
    if not path.exists():
        return None
    last = ""
    with open(path, encoding="utf-8") as f:
        f.readline()  # header
        for line in f:
            if line.strip():
                last = line.split(",", 1)[0]
    return last or None


def ts_to_ms(ist_wall: str) -> int:
    """IST wall-clock string -> UTC epoch ms."""
    dt = datetime.strptime(ist_wall, "%Y-%m-%d %H:%M:%S") - IST
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


def fetch_tf(exchange: str, tf: str, since_ms: int) -> dict[str, tuple[float, float, float, float]]:
    """{ist_wall: (o, h, l, c)} for all candles from since_ms to now."""
    cfg = EXCHANGES[exchange]
    step_ms = TF_MS[tf]
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    out: dict[str, tuple[float, float, float, float]] = {}
    cur = since_ms + step_ms  # start AFTER the last stored candle
    retries = 0

    while cur < now_ms:
        # Build URL
        if exchange == "bybit":
            bybit_interval = TF_BYBIT.get(tf, tf)
            url = (
                f"{cfg['url']}?category=linear&symbol={SYMBOL}"
                f"&interval={bybit_interval}&start={cur}&limit={cfg['limit']}"
            )
        else:
            url = (
                f"{cfg['url']}?symbol={SYMBOL}&interval={tf}"
                f"&startTime={cur}&limit={cfg['limit']}"
            )

        try:
            resp = _fetch_json(url)
        except Exception as e:
            retries += 1
            if retries > 5:
                break
            time.sleep(2)
            continue

        # Parse response
        if exchange == "bybit":
            if resp.get("retCode") != 0:
                retries += 1
                if retries > 5:
                    break
                time.sleep(2)
                continue
            rows = resp.get("result", {}).get("list", [])
            rows.reverse()  # Bybit returns newest first
        else:
            rows = resp
            if not rows:
                break

        if not rows:
            break

        retries = 0
        for k in rows:
            open_time_ms = int(k[0])
            utc = datetime.fromtimestamp(open_time_ms / 1000.0, tz=timezone.utc)
            ist = (utc + IST).strftime("%Y-%m-%d %H:%M:%S")
            out[ist] = (float(k[1]), float(k[2]), float(k[3]), float(k[4]))

        nxt = int(rows[-1][0]) + step_ms
        if nxt <= cur:
            break
        cur = nxt
    return out


def merge_csv(exchange: str, tf: str,
              new_rows: dict[str, tuple[float, float, float, float]],
              seed: bool = False) -> int:
    """Append new timestamps to the main CSV; returns rows written."""
    path = _data_dir(exchange) / f"BTCUSDT_{tf}.csv"
    existing: dict[str, str] = {}
    header = "timestamp,open,high,low,close,x,y\n"
    if path.exists() and not seed:
        with open(path, encoding="utf-8") as f:
            header = f.readline()
            for line in f:
                if line.strip():
                    existing[line.split(",", 1)[0]] = line
    # count new rows BEFORE adding them to existing
    new_count = sum(1 for k in new_rows if k not in existing)
    for k in new_rows:
        if k in existing:
            continue
        o, h, l, c = new_rows[k]
        existing[k] = f"{k},{o},{h},{l},{c},0,0\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(header)
        for k in sorted(existing):
            f.write(existing[k])
    return new_count


def refresh_tf(exchange: str, tf: str) -> dict:
    """Fetch + append for one TF. Returns a status dict."""
    if tf not in TF_MS:
        return {"tf": tf, "ok": False, "error": f"unknown tf {tf}"}

    last = last_ts(exchange, tf)
    seeding = last is None
    if seeding:
        since_ms = ts_to_ms(SEED_IST)
        start_ms = since_ms
        note = f"seeding from {SEED_IST}"
    else:
        since_ms = ts_to_ms(last)
        start_ms = since_ms
        note = f"appending after {last}"

    new_rows = fetch_tf(exchange, tf, start_ms)
    added = merge_csv(exchange, tf, new_rows, seed=seeding)

    new_last = last_ts(exchange, tf)
    return {
        "tf": tf,
        "ok": True,
        "seeded": seeding,
        "note": note,
        "fetched": len(new_rows),
        "appended": added,
        "last_ts": new_last,
    }


def refresh_all(exchange: str, tfs: list[str] | None = None) -> dict:
    """Refresh all (or specified) TFs. Returns per-tf status list."""
    targets = ["1m", "5m", "15m", "1h", "4h"] if tfs is None else tfs
    results = []
    for tf in targets:
        try:
            results.append(refresh_tf(exchange, tf))
        except Exception as e:
            results.append({"tf": tf, "ok": False, "error": str(e)})
    return {"results": results}
