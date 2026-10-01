"""PHASE 0 DIAGNOSTIC - why 1-minute swing computation dies.

THE BLOCKER (HANDOVER_SESSION.md section 7)
==========================================
    _compute_swings(fine, "continuous", min_bars=N) over the full
    1,946,026 one-minute bars did not finish in ~2 minutes and the
    process died. Reported as "memory-bound".

    The handover does not say WHICH structure blows up, so this script
    measures it instead of guessing. It runs the SAME call the 1m layer
    would run, on growing PREFIXES of the real 1m file, and reports:

      * wall time and process working set per prefix
      * time/N ratios across prefixes -> linear or superlinear?
      * swings produced, average bars per swing
      * tracemalloc's top allocating sites at the largest prefix

    WHY PREFIXES. If the cost is superlinear the full run is unreachable,
    so we never start it. The scaling curve is the diagnosis.

    NOTHING IS EDITED. This file only imports the engine and calls it.

    Run:  $env:PYTHONIOENCODING='utf-8'; python -u phase0_1m_swing_diag.py
"""
from __future__ import annotations

import gc
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

CSV_1M = ROOT / "data/bybit/BTCUSDT_1m.csv"
OUT = ROOT / "backtest/tests/_phase0_1m_swing_diag.json"

# IST -> UTC, identical to exp_s3_forensic.IST_OFFSET_SEC / btc_engine.IST_OFFSET_S
IST_OFFSET_SEC = 5 * 3600 + 30 * 60

# Growing prefixes, in bars. 1m bars: 1 day = 1440, ~1 month = 43200.
PREFIXES = (14_400, 43_200, 86_400, 172_800, 345_600)


# ----------------------------------------------------------------- memory
def working_set_mb() -> float:
    """Windows working set of this process, in MB (psutil is not installed).

    argtypes/restype MUST be declared: without them ctypes assumes c_int and
    truncates the 64-bit HANDLE, which silently returns 0 MB. That bug made
    an earlier run of this script print 0.0 for every prefix.
    """
    import ctypes
    from ctypes import wintypes

    class PMC(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    c = PMC()
    c.cb = ctypes.sizeof(c)
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    k32.GetCurrentProcess.argtypes = []
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    psapi.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
    ok = psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(),
                                    ctypes.byref(c), c.cb)
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())
    return round(c.WorkingSetSize / (1024 * 1024), 1)



# ----------------------------------------------------------------- loading
def load_1m_flow(limit: int | None = None) -> tuple[list, float]:
    """The 1m flow exactly as exp_s3_forensic._candles builds it.

    Only the FlowCandle half - the swing engine consumes FlowCandle, and
    the dict half would double the peak for no Phase 0 benefit.
    """
    import pandas as pd
    from src.walker import FlowCandle

    t0 = time.time()
    df = pd.read_csv(CSV_1M, usecols=["timestamp", "open", "high", "low", "close"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = (df.sort_values("timestamp")
            .drop_duplicates(subset="timestamp", keep="last")
            .reset_index(drop=True))
    flow = []
    for r in df.itertuples(index=False):
        flow.append(FlowCandle(
            date=r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            open=float(r.open), high=float(r.high),
            low=float(r.low), close=float(r.close)))
        if limit is not None and len(flow) >= limit:
            break
    load_s = time.time() - t0
    del df
    gc.collect()
    return flow, load_s


# ----------------------------------------------------------------- the call
def swings_continuous(flow: list, min_bars: int) -> list:
    """Byte-for-byte what btc_routes._compute_swings(flow, "continuous", n) does.

    Replicated rather than imported because btc_routes drags in FastAPI and
    the whole route layer. `verify_matches_routes()` proves the two agree.
    """
    from src.btc.btc_swing import compute_btc_swings
    opts = {"minBars": max(2, int(min_bars))}
    cap = max(1, len(flow) // 2)
    return compute_btc_swings(flow, opts=opts, max_swings=cap)


def verify_matches_routes(flow: list, min_bars: int) -> bool:
    """Control gate: our thin wrapper == the real _compute_swings."""
    try:
        from src.btc.btc_routes import _compute_swings as real
    except Exception as e:  # noqa: BLE001
        print(f"  [skip] routes import failed: {e}")
        return False
    return swings_continuous(flow, min_bars) == real(flow, "continuous",
                                                     min_bars=min_bars)


def main() -> None:
    full_mode = "--full" in sys.argv
    print("=" * 74)
    print("PHASE 0 - 1m swing scaling diagnostic")
    print("=" * 74)
    report: dict = {"prefixes": [], "min_bars": 10, "full_mode": full_mode}


    full, load_s = load_1m_flow()
    print(f"1m bars available : {len(full):,}")
    print(f"load time         : {load_s:.1f}s")
    print(f"working set       : {working_set_mb()} MB after load")
    print(f"first / last      : {full[0].date}  ->  {full[-1].date}")
    report.update({
        "bars_available": len(full), "load_s": round(load_s, 1),
        "ws_after_load_mb": working_set_mb(),
        "first_date": full[0].date, "last_date": full[-1].date,
    })

    mb = 10
    ctrl = verify_matches_routes(full[:14_400], mb)
    print(f"\ncontrol gate (wrapper == btc_routes._compute_swings): {ctrl}")
    report["wrapper_matches_routes"] = ctrl

    print(f"\n{'bars':>10} {'swings':>9} {'time_s':>9} {'us/bar':>9} "
          f"{'ws_MB':>8} {'bars/swing':>11}")
    print("-" * 74)

    prev = None
    prefixes = (len(full),) if full_mode else PREFIXES
    for n in prefixes:
        if n > len(full):
            continue
        sub = full[:n]
        gc.collect()
        ws0 = working_set_mb()
        t0 = time.time()
        sw = swings_continuous(sub, mb)
        el = time.time() - t0
        ws1 = working_set_mb()
        row = {
            "bars": n, "swings": len(sw), "seconds": round(el, 2),
            "us_per_bar": round(el / n * 1e6, 3), "ws_mb": ws1,
            "ws_delta_mb": round(ws1 - ws0, 1),
            "bars_per_swing": round(n / len(sw), 1) if sw else None,
        }
        if prev and prev["seconds"] > 0:
            row["time_ratio_vs_prev"] = round(el / prev["seconds"], 2)
            row["n_ratio_vs_prev"] = round(n / prev["bars"], 2)
            row["superlinear"] = (row["time_ratio_vs_prev"]
                                  > 1.3 * row["n_ratio_vs_prev"])
        report["prefixes"].append(row)
        print(f"{n:>10,} {len(sw):>9,} {el:>9.2f} {row['us_per_bar']:>9.2f} "
              f"{ws1:>8.0f} {(row['bars_per_swing'] or 0):>11.1f}")
        if "time_ratio_vs_prev" in row:
            print(f"{'':>10}   time x{row['time_ratio_vs_prev']} for "
                  f"x{row['n_ratio_vs_prev']} bars  -> "
                  f"{'SUPERLINEAR' if row['superlinear'] else 'linear'}")
        prev = row
        del sw, sub
        gc.collect()

    # Where does the memory actually live, at the largest prefix?
    import tracemalloc
    largest = max((r["bars"] for r in report["prefixes"]), default=0)
    if largest:
        gc.collect()
        tracemalloc.start()
        sub = full[:largest]
        sw = swings_continuous(sub, mb)
        cur, peak = tracemalloc.get_traced_memory()
        top = tracemalloc.take_snapshot().statistics("lineno")[:8]
        tracemalloc.stop()
        report["tracemalloc_at_max_prefix"] = {
            "bars": largest, "swings": len(sw),
            "current_mb": round(cur / 1e6, 1), "peak_mb": round(peak / 1e6, 1),
            "top_sites": [
                {"mb": round(s.size / 1e6, 2), "count": s.count,
                 "line": s.traceback[0].filename.split("AT_Trading")[-1]
                         + ":" + str(s.traceback[0].lineno)}
                for s in top
            ],
        }
        print(f"\ntracemalloc @ {largest:,} bars -> peak {peak/1e6:.1f} MB, "
              f"current {cur/1e6:.1f} MB")
        for s in report["tracemalloc_at_max_prefix"]["top_sites"]:
            print(f"   {s['mb']:8.2f} MB  n={s['count']:<9} {s['line']}")
        del sw, sub

    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nreport -> {OUT}")


if __name__ == "__main__":
    main()
