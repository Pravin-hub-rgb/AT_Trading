"""Aligned 15m close loader for the Binance perp stat-arb CSVs.

Data: data/btc-fut/BTCUSDT_15m.csv, data/eth-fut/ETHUSDT_15m.csv,
data/scan-fut/SOLUSDT_15m.csv (SOL starts 2023-01-01). CSV timestamps are
UTC+5:30 (IST) wall-clock strings on all three files (see the run_experiment
weekend warning), so alignment is a plain timestamp join and every window /
bucket below is expressed in that same local clock.

Era bounds are the house UTC instants shifted by +5:30:
  OOS era  [2021-01-01Z, 2023-01-01Z)   local 2021-01-01 05:30 .. 2023-01-01 05:30
  IS  era  [2023-01-01Z, 2026-09-14Z)   local 2023-01-01 05:30 .. 2026-09-14 05:30
Results windows start after the 6-month initial train (Kilo walk-forward
protocol, corrected quarter math): OOS results from 2021-07-01 05:30,
IS results from 2023-07-01 05:30.
"""
from __future__ import annotations

import csv
from datetime import datetime

TF_SEC = 900

OOS_START = datetime(2021, 1, 1, 5, 30)
OOS_RESULTS = datetime(2021, 7, 1, 5, 30)
OOS_END = datetime(2023, 1, 1, 5, 30)
IS_START = datetime(2023, 1, 1, 5, 30)
IS_RESULTS = datetime(2023, 7, 1, 5, 30)
IS_END = datetime(2026, 9, 14, 5, 30)

ERAS = {
    "oos": {"start": OOS_START, "results": OOS_RESULTS, "end": OOS_END},
    "is": {"start": IS_START, "results": IS_RESULTS, "end": IS_END},
}


def _read_csv(path):
    ts, cl = [], []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            ts.append(datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S"))
            cl.append(float(row["close"]))
    return ts, cl


def _gaps(ts):
    bad = 0
    for a, b in zip(ts, ts[1:]):
        if (b - a).total_seconds() != TF_SEC:
            bad += 1
    return bad


def load_frames(root):
    btc_ts, btc_cl = _read_csv(root / "data/btc-fut/BTCUSDT_15m.csv")
    eth_map = dict(zip(*_read_csv(root / "data/eth-fut/ETHUSDT_15m.csv")))
    sol_map = dict(zip(*_read_csv(root / "data/scan-fut/SOLUSDT_15m.csv")))

    ts2, b2, e2 = [], [], []
    for t, b in zip(btc_ts, btc_cl):
        e = eth_map.get(t)
        if e is not None:
            ts2.append(t)
            b2.append(b)
            e2.append(e)

    ts3, b3, e3, s3 = [], [], [], []
    for t, b, e in zip(ts2, b2, e2):
        s = sol_map.get(t)
        if s is not None:
            ts3.append(t)
            b3.append(b)
            e3.append(e)
            s3.append(s)

    checks = {
        "n_btc": len(btc_ts), "n_eth": len(eth_map), "n_sol": len(sol_map),
        "n_join2": len(ts2), "n_join3": len(ts3),
        "coverage2": round(len(ts2) / max(1, min(len(btc_ts), len(eth_map))), 6),
        "coverage3": round(len(ts3) / max(1, min(len(ts2), len(sol_map))), 6),
        "gaps2": _gaps(ts2), "gaps3": _gaps(ts3),
        "start2": str(ts2[0]), "end2": str(ts2[-1]),
        "start3": str(ts3[0]) if ts3 else None, "end3": str(ts3[-1]) if ts3 else None,
        "monotonic2": all(a < b for a, b in zip(ts2, ts2[1:])),
    }
    return {"ts": ts2, "btc": b2, "eth": e2, "ts3": ts3, "btc3": b3, "eth3": e3, "sol3": s3, "checks": checks}
