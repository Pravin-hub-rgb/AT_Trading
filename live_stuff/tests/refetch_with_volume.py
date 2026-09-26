"""Re-fetch Bybit klines with volume column. Run once per TF (or all).

Usage:
  python live_stuff/tests/refetch_with_volume.py           # all TFs
  python live_stuff/tests/refetch_with_volume.py 15m 1h    # selected TFs
"""
import sys
import time
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import urlopen, Request

ROOT = Path(__file__).resolve().parents[2]
BASE = "https://api.bybit.com/v5/market/kline"
SYMBOL = "BTCUSDT"
CATEGORY = "linear"
STEP = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
}
BYBIT_INTERVAL = {"1m": "1", "5m": "5", "15m": "15", "1h": "60", "4h": "240"}
LIMIT = 1000
DATA_DIR = ROOT / "data" / "bybit"
IST = timedelta(hours=5, minutes=30)
HEADER = "timestamp,open,high,low,close,volume,x,y"


def fetch_batch(tf, start_ms, end_ms):
    url = (
        f"{BASE}?category={CATEGORY}&symbol={SYMBOL}"
        f"&interval={BYBIT_INTERVAL[tf]}&start={start_ms}&end={end_ms}&limit={LIMIT}"
    )
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urlopen(req, timeout=30)
    data = json.loads(resp.read())
    if data.get("retCode") != 0:
        raise Exception(f"API error: {data}")
    return data["result"]["list"]


def ist_to_ms(ist_str):
    dt = datetime.strptime(ist_str, "%Y-%m-%d %H:%M:%S")
    return int((dt - IST).timestamp() * 1000)


def ms_to_ist(ms):
    utc = datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
    return (utc + IST).strftime("%Y-%m-%d %H:%M:%S")


def read_existing(csv):
    if not csv.exists():
        return {}, HEADER
    lines = csv.read_text(encoding="utf-8").strip().split("\n")
    header = lines[0]
    rows = {}
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.strip().split(",")
        ts = parts[0]
        # old format: ts,o,h,l,c,x,y (no volume) -> insert 0
        # new format: ts,o,h,l,c,volume,x,y
        if len(parts) >= 8:
            rows[ts] = tuple(float(x) for x in parts[1:6])
        elif len(parts) >= 7:
            rows[ts] = (float(parts[1]), float(parts[2]), float(parts[3]),
                        float(parts[4]), 0.0)
        else:
            continue
    return rows, header


def refetch_tf(tf):
    step = STEP[tf]
    csv = DATA_DIR / f"BTCUSDT_{tf}.csv"
    existing, old_header = read_existing(csv)
    if not existing:
        print(f"[{tf}] no existing CSV — skip (seed via btc_fetch first)")
        return

    sorted_ts = sorted(existing)
    first = sorted_ts[0]
    last = sorted_ts[-1]
    first_ms = ist_to_ms(first)
    last_ms = ist_to_ms(last) + step
    print(f"[{tf}] {len(existing)} rows  {first} -> {last}")
    print(f"[{tf}] fetching volume for full range...")

    fetched = {}
    cur = first_ms
    batches = 0
    errors = 0
    while cur < last_ms:
        end = min(cur + LIMIT * step, last_ms)
        try:
            rows = fetch_batch(tf, cur, end)
        except Exception as e:
            errors += 1
            print(f"[{tf}] error at {ms_to_ist(cur)}: {e}")
            if errors > 8:
                break
            time.sleep(1.5)
            continue
        if not rows:
            break
        errors = 0
        # Bybit returns newest-first — reverse so rows[-1] is oldest
        rows.reverse()
        for r in rows:
            ist = ms_to_ist(int(r[0]))
            vol = float(r[5]) if len(r) > 5 else 0.0
            fetched[ist] = (float(r[1]), float(r[2]), float(r[3]), float(r[4]), vol)
        nxt = int(rows[-1][0]) + step
        if nxt <= cur:
            # No forward progress — advance by window size to avoid infinite loop
            nxt = cur + LIMIT * step
        cur = nxt
        batches += 1
        if batches % 20 == 0:
            print(f"[{tf}] batch {batches}: fetched={len(fetched)} cur={ms_to_ist(cur)}", flush=True)
        time.sleep(0.05)

    # Merge: prefer fetched OHLC+vol; keep existing if API missed a bar
    merged = {}
    for ts, vals in existing.items():
        if ts in fetched:
            o, h, l, c, vol = fetched[ts]
            # Sanity: if API OHLC differs wildly, keep existing and only patch vol
            oo, oh, ol, oc, _ = vals
            if abs(o - oo) > 1e-9 or abs(h - oh) > 1e-9 or abs(l - ol) > 1e-9 or abs(c - oc) > 1e-9:
                merged[ts] = (oo, oh, ol, oc, vol)
            else:
                merged[ts] = (o, h, l, c, vol)
        else:
            merged[ts] = vals
    for ts, vals in fetched.items():
        if ts not in merged:
            merged[ts] = vals

    csv.parent.mkdir(parents=True, exist_ok=True)
    with open(csv, "w", encoding="utf-8") as f:
        f.write(HEADER + "\n")
        for ts in sorted(merged):
            o, h, l, c, vol = merged[ts]
            f.write(f"{ts},{o},{h},{l},{c},{vol},0,0\n")

    vol_nz = sum(1 for v in merged.values() if v[4] > 0)
    print(f"[{tf}] DONE rows={len(merged)} vol_nz={vol_nz} "
          f"({100.0*vol_nz/len(merged):.1f}% non-zero) "
          f"api_fetched={len(fetched)} batches={batches}")


def main():
    tfs = sys.argv[1:] or ["15m", "1h", "5m", "4h", "1m"]
    tfs = [t for t in tfs if t in STEP]
    if not tfs:
        print("no valid TFs")
        return
    t0 = time.time()
    for tf in tfs:
        refetch_tf(tf)
    print(f"\nall done in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
