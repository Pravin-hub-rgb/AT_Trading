"""Download the FORWARD (post-cutoff) Bybit BTCUSDT perpetual slice.

Data in data/bybit/ ends 2026-09-13; everything after that has never been used
by any experiment. This script writes ONLY that new range into an isolated
directory so forward data can never leak into IS/OOS replays.

Usage:
  python scripts/download_bybit_forward.py
  python scripts/download_bybit_forward.py --tf 15m
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
BYBIT_URL = "https://api.bybit.com/v5/market/kline"
TF_MS = {"1m": 60_000, "15m": 900_000, "1h": 3_600_000}
TF_BYBIT = {"1m": "1", "15m": "15", "1h": "60"}

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "forward" / "bybit"
MANIFEST = DATA_DIR / "_forward_manifest.json"

# Hard boundary: last 1m bar present in data/bybit/ is 2026-09-13 10:02 IST.
# Forward data starts strictly after this instant. Do not lower it.
FORWARD_START_IST = "2026-09-13 10:03:00"


def _fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def ist_to_ms(ist_wall: str) -> int:
    dt = datetime.strptime(ist_wall, "%Y-%m-%d %H:%M:%S") - IST
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


def ms_to_ist(ms: int) -> str:
    return (datetime.fromtimestamp(ms / 1000, tz=timezone.utc) + IST).strftime(
        "%Y-%m-%d %H:%M:%S")


def download_tf(tf: str, start_ms: int) -> int:
    step_ms = TF_MS[tf]
    interval = TF_BYBIT[tf]
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    path = DATA_DIR / f"{SYMBOL}_{tf}.csv"
    header = "timestamp,open,high,low,close,x,y\n"
    rows: list[str] = []
    if path.exists():
        for line in path.read_text().splitlines()[1:]:
            if line.strip():
                if ist_to_ms(line.split(",")[0]) >= start_ms:
                    rows.append(line + "\n")
    cur = (ist_to_ms(rows[-1].split(",")[0]) + step_ms) if rows else start_ms
    if rows:
        print(f"  [{tf}] resuming at {rows[-1].split(',')[0]} ({len(rows)} rows)")
    written = len(rows)
    while cur < now_ms:
        url = (f"{BYBIT_URL}?category=linear&symbol={SYMBOL}"
               f"&interval={interval}&start={cur}&limit=1000")
        try:
            resp = _fetch_json(url)
        except Exception as exc:  # network hiccup - back off, keep going
            print(f"  [{tf}] error {exc}; retry in 3s")
            time.sleep(3)
            continue
        if resp.get("retCode") != 0:
            print(f"  [{tf}] API {resp.get('retMsg')}; retry in 3s")
            time.sleep(3)
            continue
        data = resp.get("result", {}).get("list", [])
        if not data:
            break
        data.reverse()
        advanced = False
        for k in data:
            ms = int(k[0])
            if ms < start_ms or ms >= now_ms:
                continue
            wall = ms_to_ist(ms)
            rows.append(f"{wall},{k[1]},{k[2]},{k[3]},{k[4]},0,0\n")
            written += 1
            advanced = True
        if not advanced:
            break
        cur = int(data[-1][0]) + step_ms
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + "".join(rows), encoding="utf-8")
    print(f"  [{tf}] wrote {written} rows -> {path}")
    return written


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", choices=sorted(TF_MS), default="all")
    args = ap.parse_args()
    start_ms = ist_to_ms(FORWARD_START_IST)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"FORWARD SLICE: after {FORWARD_START_IST} IST -> {DATA_DIR}")
    tfs = sorted(TF_MS) if args.tf == "all" else [args.tf]
    summary = {}
    for tf in tfs:
        summary[tf] = download_tf(tf, start_ms)
    manifest = {
        "symbol": SYMBOL,
        "market": "bybit linear perpetual",
        "forward_start_ist": FORWARD_START_IST,
        "downloaded_utc": datetime.now(timezone.utc).isoformat(),
        "rows": summary,
        "note": ("Isolated post-2026-09-13 slice. Never merged into data/bybit/. "
                 "Used only by exp_forward_eval.py."),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"  wrote {MANIFEST}")


if __name__ == "__main__":
    main()
