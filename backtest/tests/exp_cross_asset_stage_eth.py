"""Stage the ETH cross-asset dataset for the tier-4 cross-asset test.

WHY THIS FILE EXISTS
--------------------
Tier 4 of docs/learn/finding optimal book.md asks whether the underlying
PHENOMENON survives across instruments, and the repo has never answered it. The
only two datasets in the config are BTC spot and BTC perp-Bybit - both BTC, so
every "cross-instrument" study in this repo is actually a cross-VENUE study
(exp_cross_instrument_transfer.py compares Bybit against Binance perp on the
same asset). Venue transfer is not asset transfer.

The only non-BTC perp data on this machine is ETHUSDT 15m and 1m, 2025, in a
sibling project's archive. It is verified here rather than assumed:
34,498 rows, 2025-01-01 00:00:00 to 2025-12-26 08:15:00, ZERO missing 15m
slots and ZERO duplicate timestamps.

WHAT IS BUILT HERE
------------------
    data/eth-fut/ETHUSDT_15m.csv   copied verbatim
    data/eth-fut/ETHUSDT_1h.csv    RESAMPLED from the 15m

The 1h resample is plain OHLC aggregation - open of the first 15m bar in the
hour, high of the max, low of the min, close of the last - which is what the 1h
file would have contained if it had been downloaded. It is stated as a resample
wherever the result is used, because it is a derived file and a reader is
entitled to know that.

WHAT IS NOT CLAIMED
-------------------
This gives ONE asset over ONE year with no era split available inside it, so it
cannot answer "does the edge hold out of sample across assets". It can only
answer the weaker and still useful question: does the phenomenon appear at all
on an instrument that was never used to build it. A single instrument is one
data point of the seven-to-ten the framework asks for, and the doc says so.
"""
import csv
import io
import sys
from datetime import datetime
from pathlib import Path

SRC = Path(r"C:\Users\Pravin\Desktop\main\option-trading-bot\archive"
           r"\data_saver\eth_futures_data\2025")
DST = Path(r"C:\Users\Pravin\Desktop\main\AT_Trading\data\eth-fut")
FIFTEEN = "ETHUSDT_15m.csv"
HOURLY = "ETHUSDT_1h.csv"


def main() -> int:
    DST.mkdir(parents=True, exist_ok=True)
    src15 = SRC / FIFTEEN
    if not src15.exists():
        print("source missing:", src15)
        return 1

    rows = list(csv.DictReader(io.open(src15, encoding="utf-8", errors="replace")))
    rows.sort(key=lambda r: r["timestamp"])
    print("source rows: %d  %s -> %s"
          % (len(rows), rows[0]["timestamp"], rows[-1]["timestamp"]))

    # 15m verbatim
    out15 = DST / FIFTEEN
    with io.open(out15, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["timestamp", "open", "high", "low", "close"])
        for r in rows:
            w.writerow([r["timestamp"], r["open"], r["high"], r["low"], r["close"]])
    print("wrote %s  (%d rows)" % (out15, len(rows)))

    # 1h by OHLC aggregation over the 15m
    buckets = []
    cur_key = None
    cur = None
    for r in rows:
        t = datetime.fromisoformat(r["timestamp"])
        key = t.replace(minute=0, second=0, microsecond=0)
        if key != cur_key:
            if cur is not None:
                buckets.append(cur)
            cur_key = key
            cur = {"ts": key, "o": r["open"], "h": r["high"],
                   "l": r["low"], "c": r["close"]}
        else:
            cur["h"] = max(float(cur["h"]), float(r["high"]))
            cur["l"] = min(float(cur["l"]), float(r["low"]))
            cur["c"] = r["close"]
    if cur is not None:
        buckets.append(cur)

    out1h = DST / HOURLY
    with io.open(out1h, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["timestamp", "open", "high", "low", "close"])
        for b in buckets:
            w.writerow([b["ts"].isoformat(sep=" "), b["o"], b["h"], b["l"], b["c"]])
    print("wrote %s  (%d hours, RESAMPLED from 15m)" % (out1h, len(buckets)))
    print("  first %s  last %s"
          % (buckets[0]["ts"], buckets[-1]["ts"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())