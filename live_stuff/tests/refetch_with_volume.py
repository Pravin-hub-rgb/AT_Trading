"""Re-fetch Bybit 15m data with volume column. Run once."""
import sys, time, json
from pathlib import Path
from urllib.request import urlopen, Request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend/src"))

BASE = "https://api.bybit.com/v5/market/kline"
SYMBOL = "BTCUSDT"
CATEGORY = "linear"
TF = "15m"
STEP_MS = 15 * 60 * 1000
LIMIT = 1000

DATA_DIR = ROOT / "data" / "bybit"
CSV = DATA_DIR / f"BTCUSDT_{TF}.csv"


def fetch_batch(start_ms, end_ms):
    url = f"{BASE}?category={CATEGORY}&symbol={SYMBOL}&interval={TF}&start={start_ms}&end={end_ms}&limit={LIMIT}"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urlopen(req, timeout=30)
    data = json.loads(resp.read())
    if data.get("retCode") != 0:
        raise Exception(f"API error: {data}")
    return data["result"]["list"]


def main():
    # Read existing CSV to get current range
    lines = CSV.read_text(encoding="utf-8").strip().split("\n")
    header = lines[0]
    print(f"Current CSV: {len(lines)-1} rows")
    print(f"Header: {header}")

    # Parse existing timestamps to find gaps
    existing = set()
    for line in lines[1:]:
        ts = line.split(",")[0]
        existing.add(ts)

    # Find first and last timestamps
    sorted_existing = sorted(existing)
    first = sorted_existing[0]
    last = sorted_existing[-1]
    print(f"Range: {first} to {last}")

    # Convert to ms (these are IST wall times, need to convert to UTC ms)
    from datetime import datetime, timezone, timedelta
    IST = timedelta(hours=5, minutes=30)

    def ist_to_ms(ist_str):
        dt = datetime.strptime(ist_str, "%Y-%m-%d %H:%M:%S")
        utc = dt - IST
        return int(utc.timestamp() * 1000)

    first_ms = ist_to_ms(first)
    last_ms = ist_to_ms(last) + STEP_MS

    # Fetch in batches from start to end
    print(f"\nFetching full range with volume...")
    print(f"From: {first} ({first_ms}ms)")
    print(f"To:   {last} ({last_ms}ms)")

    all_rows = {}
    cur = first_ms
    batch_count = 0
    total_fetched = 0

    while cur < last_ms:
        end = min(cur + LIMIT * STEP_MS, last_ms)
        try:
            rows = fetch_batch(cur, end)
            if not rows:
                break
            for r in rows:
                ts_ms = int(r[0])
                utc = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
                ist = (utc + IST).strftime("%Y-%m-%d %H:%M:%S")
                o = float(r[1])
                h = float(r[2])
                l = float(r[3])
                c = float(r[4])
                vol = float(r[5]) if len(r) > 5 else 0.0
                all_rows[ist] = (o, h, l, c, vol)
                total_fetched += 1

            nxt = int(rows[-1][0]) + STEP_MS
            if nxt <= cur:
                break
            cur = nxt
            batch_count += 1
            if batch_count % 10 == 0:
                print(f"  batch {batch_count}: {total_fetched} rows fetched, cur={ist}")
            time.sleep(0.1)  # rate limit
        except Exception as e:
            print(f"  error at {cur}: {e}")
            time.sleep(1)
            continue

    print(f"\nFetched {total_fetched} rows total")

    # Merge with existing CSV
    print("Merging with existing CSV...")
    merged = {}
    for line in lines[1:]:
        if line.strip():
            parts = line.split(",")
            ts = parts[0]
            if ts in all_rows:
                # Update with volume
                o, h, l, c, vol = all_rows[ts]
                merged[ts] = f"{ts},{o},{h},{l},{c},{vol},0,0\n"
            else:
                merged[ts] = line + "\n"

    # Add new rows from fetch
    for ts in all_rows:
        if ts not in merged:
            o, h, l, c, vol = all_rows[ts]
            merged[ts] = f"{ts},{o},{h},{l},{c},{vol},0,0\n"

    # Write
    CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(CSV, "w", encoding="utf-8") as f:
        f.write("timestamp,open,high,low,close,volume,x,y\n")
        for ts in sorted(merged):
            f.write(merged[ts].rstrip("\n") + "\n")

    final_lines = CSV.read_text(encoding="utf-8").strip().split("\n")
    print(f"Done! CSV now has {len(final_lines)-1} rows with volume data")


if __name__ == "__main__":
    main()
