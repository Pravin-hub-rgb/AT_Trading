"""Fetch new Binance candles and APPEND to the main BTC CSVs.

Reusable backend module — same logic as debug/_btc_fetch_update.py but
exposed as a function the /api/btc/fetch route can call.
"""
from __future__ import annotations

import json
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
SEED_IST = "2025-01-01 05:30:00"


def _data_dir() -> Path:
    """Path to data/btc/ (project root, three levels up from backend/src/btc/)."""
    return Path(__file__).resolve().parents[3] / "data" / "btc"


def _fetch_json(url: str) -> list:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def last_ts(tf: str) -> str | None:
    path = _data_dir() / f"BTCUSDT_{tf}.csv"
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


def fetch_tf(tf: str, since_ms: int) -> dict[str, tuple[float, float, float, float]]:
    """{ist_wall: (o, h, l, c)} for all Binance candles from since_ms to now."""
    step_ms = TF_MS[tf]
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    out: dict[str, tuple[float, float, float, float]] = {}
    cur = since_ms + step_ms  # start AFTER the last stored candle
    while cur < now_ms:
        url = (
            f"https://api.binance.com/api/v3/klines?symbol={SYMBOL}"
            f"&interval={tf}&limit=1000&startTime={cur}"
        )
        rows = _fetch_json(url)
        if not rows:
            break
        for k in rows:
            utc = datetime.fromtimestamp(k[0] / 1000.0, tz=timezone.utc)
            ist = (utc + IST).strftime("%Y-%m-%d %H:%M:%S")
            out[ist] = (float(k[1]), float(k[2]), float(k[3]), float(k[4]))
        nxt = rows[-1][0] + step_ms
        if nxt <= cur:
            break
        cur = nxt
    return out


def merge_csv(tf: str, new_rows: dict[str, tuple[float, float, float, float]],
              seed: bool = False) -> int:
    """Append new timestamps to the main CSV; returns rows written."""
    path = _data_dir() / f"BTCUSDT_{tf}.csv"
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
    with open(path, "w", encoding="utf-8") as f:
        f.write(header)
        for k in sorted(existing):
            f.write(existing[k])
    return new_count


def refresh_tf(tf: str) -> dict:
    """Fetch + append for one TF. Returns a status dict."""
    if tf not in TF_MS:
        return {"tf": tf, "ok": False, "error": f"unknown tf {tf}"}

    last = last_ts(tf)
    seeding = last is None
    if seeding:
        since_ms = ts_to_ms(SEED_IST)
        start_ms = since_ms
        note = f"seeding from {SEED_IST}"
    else:
        since_ms = ts_to_ms(last)
        start_ms = since_ms
        note = f"appending after {last}"

    new_rows = fetch_tf(tf, start_ms)
    added = merge_csv(tf, new_rows, seed=seeding)

    new_last = last_ts(tf)
    return {
        "tf": tf,
        "ok": True,
        "seeded": seeding,
        "note": note,
        "fetched": len(new_rows),
        "appended": added,
        "last_ts": new_last,
    }


def refresh_all(tfs: list[str] | None = None) -> dict:
    """Refresh all (or specified) TFs. Returns per-tf status list."""
    targets = tms = ["1m", "5m", "15m", "1h", "4h"] if tfs is None else tfs
    results = []
    for tf in targets:
        try:
            results.append(refresh_tf(tf))
        except Exception as e:
            results.append({"tf": tf, "ok": False, "error": str(e)})
    return {"results": results}
