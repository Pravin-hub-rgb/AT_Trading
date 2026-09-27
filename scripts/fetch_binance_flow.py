"""Fetch Binance Vision flow/positioning data missing from disk (BTCUSDT UM futures).

Datasets (verified availability 2026-09-27):
  1. metrics            daily  2021-01-01 -> 2026-09-25   5m rows: OI, OI value, toptrader L/S, all L/S, taker vol ratio
  2. bookDepth          daily  2023-01-01 -> 2026-09-25   ~30s rows at ±1..5% depth bands (approx 0.5MB/zip)
  3. premiumIndexKlines 1h     2020-01    -> 2026-08       premium/basis klines (carry research)
  4. fundingRate        monthly 2020-01   -> 2026-08       canonical funding (supersedes live_stuff/data json)

Skipped (too big / gone):
  - aggTrades 522MB+/month, trades 1GB+/month  (defer until CVD hypothesis needs them)
  - liquidationSnapshot = discontinued by Binance (404 on all dates)

Resume-safe: existing valid zips are skipped; per-dataset ledger written at
data/flow/_ledger.json. Run repeatedly until "ALL DONE".
"""
import csv
import io
import json
import sys
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "flow"
BASE = "https://data.binance.vision/data/futures/um"
UA = {"User-Agent": "Mozilla/5.0 (flow-data-fetch)"}
WORKERS = 8
RETRIES = 3

METRICS_FROM, METRICS_TO = date(2021, 1, 1), date(2026, 9, 25)
DEPTH_FROM, DEPTH_TO = date(2023, 1, 1), date(2026, 9, 25)


def daterange(a: date, b: date):
    d = a
    while d <= b:
        yield d
        d += timedelta(days=1)


def months(a: date, b: date):
    y, m = a.year, a.month
    while (y, m) <= (b.year, b.month):
        yield f"{y:04d}-{m:02d}"
        m += 1
        if m == 13:
            y, m = y + 1, 1


def valid_zip(p: Path) -> bool:
    if not p.exists() or p.stat().st_size < 100:
        return False
    try:
        with zipfile.ZipFile(p) as z:
            bad = z.testzip()
            if bad is not None:
                p.unlink(missing_ok=True)
                return False
            return bool(z.namelist())
    except zipfile.BadZipFile:
        p.unlink(missing_ok=True)
        return False


def fetch(url: str, dest: Path) -> tuple[str, str]:
    if valid_zip(dest):
        return "skip", dest.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    last = ""
    for attempt in range(1, RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            if data[:2] != b"PK":
                last = f"not-zip({len(data)}B)"
                time.sleep(1.0 * attempt)
                continue
            tmp.write_bytes(data)
            if valid_zip(tmp):
                tmp.replace(dest)
                return "ok", dest.name
            last = "zip-invalid"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return "404", dest.name
            last = f"http{e.code}"
        except Exception as e:  # noqa: BLE001
            last = e.__class__.__name__
        time.sleep(1.5 * attempt)
    return f"FAIL:{last}", dest.name


def job_set_metrics():
    return [(f"{BASE}/daily/metrics/BTCUSDT/BTCUSDT-metrics-{d}.zip",
             OUT / "metrics" / f"BTCUSDT-metrics-{d}.zip")
            for d in daterange(METRICS_FROM, METRICS_TO)]


def job_set_depth():
    return [(f"{BASE}/daily/bookDepth/BTCUSDT/BTCUSDT-bookDepth-{d}.zip",
             OUT / "bookDepth" / f"BTCUSDT-bookDepth-{d}.zip")
            for d in daterange(DEPTH_FROM, DEPTH_TO)]


def job_set_premium():
    return [(f"{BASE}/monthly/premiumIndexKlines/BTCUSDT/1h/BTCUSDT-1h-{m}.zip",
             OUT / "premium1h" / f"BTCUSDT-1h-{m}.zip")
            for m in months(date(2020, 1, 1), date(2026, 8, 1))]


def job_set_funding():
    return [(f"{BASE}/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-{m}.zip",
             OUT / "funding" / f"BTCUSDT-fundingRate-{m}.zip")
            for m in months(date(2020, 1, 1), date(2026, 8, 1))]


def run_set(name: str, jobs):
    stats = {"ok": 0, "skip": 0, "404": 0, "FAIL": 0}
    fails = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(fetch, u, d): d for u, d in jobs}
        for i, f in enumerate(as_completed(futs), 1):
            st, nm = f.result()
            key = "ok" if st == "ok" else ("skip" if st == "skip" else ("404" if st == "404" else "FAIL"))
            stats[key] += 1
            if key == "FAIL":
                fails.append(f"{nm} ({st})")
            if i % 250 == 0 or i == len(jobs):
                print(f"  [{name}] {i}/{len(jobs)} ok={stats['ok']} skip={stats['skip']} "
                      f"404={stats['404']} FAIL={stats['FAIL']} {time.time()-t0:.0f}s", flush=True)
    return stats, fails


def merge_metrics():
    """Concatenate daily metrics zips -> single CSV with 5m rows."""
    dest = OUT / "BTCUSDT_metrics_5m.csv"
    zips = sorted((OUT / "metrics").glob("BTCUSDT-metrics-*.zip"))
    rows, gaps = 0, []
    prev_day = None
    with open(dest, "w", newline="", encoding="utf-8") as fo:
        w = None
        for i, zp in enumerate(zips, 1):
            with zipfile.ZipFile(zp) as z:
                with z.open(z.namelist()[0]) as fh:
                    r = csv.reader(io.TextIOWrapper(fh, encoding="utf-8", errors="replace"))
                    hdr = next(r)
                    if w is None:
                        w = csv.writer(fo)
                        w.writerow(hdr)
                    day = "-".join(zp.stem.split("-")[-3:])
                    if prev_day is not None:
                        pd = date.fromisoformat(prev_day)
                        cd = date.fromisoformat(day)
                        if (cd - pd).days != 1:
                            gaps.append(f"{prev_day}->{day}")
                    prev_day = day
                    for row in r:
                        w.writerow(row)
                        rows += 1
    print(f"[merge] metrics -> {dest.name}: {rows} rows, {len(zips)} zips, gaps={len(gaps)}")
    if gaps:
        print(f"  gap sample: {gaps[:5]}")
    return rows


def main():
    targets = {
        "metrics": job_set_metrics,
        "bookDepth": job_set_depth,
        "premium1h": job_set_premium,
        "funding": job_set_funding,
    }
    summary = {}
    all_fails = []
    for name, fn in targets.items():
        jobs = fn()
        print(f"== {name}: {len(jobs)} files", flush=True)
        stats, fails = run_set(name, jobs)
        summary[name] = {**stats, "total": len(jobs)}
        all_fails += fails

    print("\n== summary")
    for k, v in summary.items():
        print(f"  {k:12s} {v}")
    if all_fails:
        print("FAILURES:", len(all_fails))
        for f in all_fails[:20]:
            print("  ", f)

    if summary["metrics"]["FAIL"] == 0 and summary["metrics"]["404"] == 0:
        merge_metrics()

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "_ledger.json").write_text(json.dumps(
        {"fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"), "summary": summary,
         "failures": all_fails}, indent=1), encoding="utf-8")
    print("ALL DONE" if not all_fails else "DONE WITH FAILURES (re-run to retry)")


if __name__ == "__main__":
    sys.exit(main())
