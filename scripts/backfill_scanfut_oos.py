"""Backfill/repair data/scan-fut symbols to cover 2021-01-01 .. now (OOS era).

scan_instruments.py fetched only from 2023-01-01; the cross-sectional study
(Paradigm 2) needs the 2021-22 OOS window. Same CSV format as the original
files: IST wall-clock timestamps (UTC+5:30), header
"timestamp,open,high,low,close,x,y", x/y = 0, prices .2f.

MODES (per symbol x tf, decided from the file on disk):
  - intact file already starting <= 2021-01-03  -> already-covered, skip.
  - intact file starting later (2023+ etc.)     -> fetch [2021-01-01,
    first_existing) and merge (kept rows win collisions).
  - DAMAGED file (row not 7 valid CSV fields)   -> full re-fetch
    [2021-01-01, now), keep_existing = False.
Every candidate row set is validated (valid_rows) BEFORE the file is
replaced; a failed validation leaves the file untouched.

REPAIR NOTE (2026-09-27): the first version of this script wrote
`sorted(merged)` - a list of timestamp KEYS - instead of the full lines,
overwriting all 32 files with timestamp-only rows (OHLC lost). Caught by
the Paradigm 2 harness reading an all-NaN close column. Fixed here:
`ordered = [merged[k] for k in sorted(merged)]` + valid_rows gates. All
data is re-fetched from fapi (source of truth, full history).

Resume-safe: each file is written atomically (tmp + replace) only after
validation. Network errors retry 3x then record FAIL in the ledger.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "scan-fut"
LEDGER = DATA_DIR / "_backfill_oos_ledger.json"
FAPI_URL = "https://fapi.binance.com/fapi/v1/klines"
IST = timedelta(hours=5, minutes=30)
START_IST = "2021-01-01 00:00:00"   # UTC instant, converted below
TF_MS = {"15m": 900_000, "1h": 3_600_000}
WORKERS = 4
RETRIES = 3


def _fetch_json(url: str):
    last = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):      # no data for range/symbol -> empty
                return []
            last = e
            time.sleep(1.0 + attempt)
        except Exception as e:  # noqa: BLE001 - network only
            last = e
            time.sleep(1.0 + attempt)
    raise RuntimeError(f"fetch failed after {RETRIES}: {last}")


def ist_to_ms(s: str) -> int:
    dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S") - IST
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


def read_csv(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    header, rows = lines[0], lines[1:]
    return header, [ln for ln in rows if ln.strip()]


def fetch_range(symbol: str, tf: str, start_ms: int, end_ms: int) -> list[str]:
    step_ms = TF_MS[tf]
    out, cur = [], start_ms
    while cur < end_ms:
        url = (f"{FAPI_URL}?symbol={symbol}&interval={tf}"
               f"&startTime={cur}&endTime={end_ms}&limit=1000")
        data = _fetch_json(url)
        if not data:
            break
        for k in data:
            if k[0] >= end_ms:
                continue
            utc_dt = datetime.fromtimestamp(k[0] / 1000.0, tz=timezone.utc)
            ist_str = (utc_dt + IST).strftime("%Y-%m-%d %H:%M:%S")
            out.append(f"{ist_str},{float(k[1]):.2f},{float(k[2]):.2f},"
                       f"{float(k[3]):.2f},{float(k[4]):.2f},0,0")
        nxt = data[-1][0] + step_ms
        if nxt <= cur:
            break
        cur = nxt
        time.sleep(0.12)
    return out


def valid_rows(rows: list[str]) -> bool:
    """Every row must be timestamp + 5 numeric fields + x,y (7 CSV fields)."""
    if not rows:
        return False
    for ln in rows:
        parts = ln.split(",")
        if len(parts) != 7:
            return False
        try:
            float(parts[1]); float(parts[2]); float(parts[3]); float(parts[4])
        except ValueError:
            return False
    return True


def job(symbol: str, tf: str) -> dict:
    path = DATA_DIR / f"{symbol}_{tf}.csv"
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    if not path.exists():
        return {"symbol": symbol, "tf": tf, "status": "missing-file"}
    _, rows = read_csv(path)
    intact = valid_rows(rows)
    if intact and rows:
        first_ts = rows[0].split(",")[0]
        first_ms = int(datetime.strptime(first_ts, "%Y-%m-%d %H:%M:%S")
                       .replace(tzinfo=timezone.utc).timestamp() * 1000) - 19800 * 1000
        start_ms = ist_to_ms(START_IST)
        if first_ms <= start_ms + 2 * TF_MS[tf]:
            return {"symbol": symbol, "tf": tf, "status": "already-covered",
                    "first": first_ts}
        end_ms, keep_existing = first_ms, True
    else:
        # damaged file (timestamp-only rows from a bad merge): full re-fetch
        start_ms = ist_to_ms(START_IST)
        end_ms, keep_existing = now_ms, False
        first_ts, rows = "FULL-REFETCH", []
    new_rows = fetch_range(symbol, tf, start_ms, end_ms)
    if not new_rows and keep_existing:
        return {"symbol": symbol, "tf": tf, "status": "no-rows",
                "first": first_ts}
    if not new_rows:
        return {"symbol": symbol, "tf": tf, "status": "FAIL",
                "error": "full re-fetch returned nothing"}
    merged = {}
    if keep_existing:
        for ln in rows:
            merged[ln.split(",")[0]] = ln
    for ln in new_rows:          # kept rows win on collision
        merged.setdefault(ln.split(",")[0], ln)
    ordered = [merged[k] for k in sorted(merged)]
    if not valid_rows(ordered):
        return {"symbol": symbol, "tf": tf, "status": "FAIL",
                "error": "post-merge validation failed - file untouched"}
    tmp = path.with_suffix(".csv.tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write("timestamp,open,high,low,close,x,y\n")
        for ln in ordered:
            f.write(ln + "\n")
    tmp.replace(path)
    return {"symbol": symbol, "tf": tf,
            "status": "full-refetch" if not keep_existing else "backfilled",
            "added": len(ordered) - len(rows), "new_first": ordered[0].split(",")[0],
            "rows": len(ordered)}


def main() -> int:
    symbols = sorted({p.name.rsplit("_", 1)[0] for p in DATA_DIR.glob("*_15m.csv")})
    jobs = [(s, tf) for s in symbols for tf in ("15m", "1h")]
    print(f"backfill OOS 2021+ for {len(symbols)} symbols x 2 tf = {len(jobs)} jobs",
          flush=True)
    results = []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(job, s, tf): (s, tf) for s, tf in jobs}
        for fut in as_completed(futs):
            try:
                r = fut.result()
            except Exception as e:  # noqa: BLE001
                s, tf = futs[fut]
                r = {"symbol": s, "tf": tf, "status": "FAIL", "error": str(e)[:120]}
            results.append(r)
            print(f"  {r['symbol']:>10} {r['tf']:>4} {r['status']}"
                  f"{' added=' + str(r['added']) if 'added' in r else ''}"
                  f"{' first=' + r['new_first'] if 'new_first' in r else ''}",
                  flush=True)
    LEDGER.write_text(json.dumps(
        {"fetched_at": datetime.now(timezone.utc).isoformat(), "results": results},
        indent=1), encoding="utf-8")
    fails = [r for r in results if r["status"] == "FAIL"]
    print(f"DONE: {len(results) - len(fails)} ok, {len(fails)} FAIL"
          f" (ledger {LEDGER})", flush=True)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
