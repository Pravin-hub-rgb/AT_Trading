"""Extract Oct 20 2026 swing marks from the forward-tested swing chain.

Loads IS + forward 15m data (combined), recomputes the continuous swing chain
exactly as exp_forward_eval.py does, then dumps all swing marks whose
confirmed_at_time falls on 2026-10-20 IST.

The output CSV (forward_oct20_marks.csv) is meant to be opened alongside
TradingView's BTCUSDT.P chart (timezone IST) for cross-checking.

Contract:
  - Swings are computed on the 15m chart itself (not lower-tf projected).
  - min_bars=50 for 15m (as configured in exp_forward_eval.py).
  - timeCap="00:00" (24/7, BTC has no session gate).
  - Engine is parity-tested: same src/firstswing.py, src/walker.py in both
    backtest and live paths.
"""
from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, "..")
sys.path.insert(0, "tests")

from test_experiments_craze import _compute_swings
from src.btc.btc_config import BTC_BYBIT_DATA_DIR

IS_DIR = Path(BTC_BYBIT_DATA_DIR)
FWD_DIR = Path(__file__).resolve().parents[2] / "data" / "forward" / "bybit"
IST_OFFSET_SEC = 5 * 3600 + 30 * 60
OUT_CSV = Path(__file__).resolve().parent.parent / "forward_oct20_marks.csv"
OUT_JSON = Path(__file__).resolve().parent.parent / "forward_oct20_marks.json"
TARGET_DATE = "2026-10-20"
MB15 = 50


def _read_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def _concat_tf(dirs, tf: str) -> pd.DataFrame:
    frames = [_read_csv(d / f"BTCUSDT_{tf}.csv") for d in dirs
              if (d / f"BTCUSDT_{tf}.csv").exists()]
    df = pd.concat(frames).sort_values("timestamp")
    return df.drop_duplicates(subset="timestamp", keep="last").reset_index(drop=True)


def _to_flow(df: pd.DataFrame):
    from src.walker import FlowCandle
    flow = []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high),
                               low=float(row.low), close=float(row.close)))
    return flow


def main():
    print("Loading combined IS + forward 15m data...")
    t0 = time.time()
    df15 = _concat_tf([IS_DIR, FWD_DIR], "15m")
    f15 = _to_flow(df15)
    print(f"  total 15m candles: {len(f15)}  ({time.time()-t0:.1f}s)")

    print("Computing continuous swing chain (minBars=50)...")
    t0 = time.time()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    print(f"  total swings: {len(sw15)}  ({time.time()-t0:.1f}s)")

    # Filter to Oct 20 confirmed marks
    oct20 = []
    for s in sw15:
        conf_time = s.get("confirmed_at_time", "")
        if conf_time.startswith(TARGET_DATE):
            oct20.append(s)

    print(f"\nOct 20 confirmed swing marks: {len(oct20)}")

    if not oct20:
        print("  (none found — check date range)")
        return

    rows = []
    for s in oct20:
        seg = s.get("seg") or {}
        rows.append({
            "swing_index": s.get("swing_index", ""),
            "confirmed_at_time": s.get("confirmed_at_time", ""),
            "confirmed_at_idx": s.get("confirmed_at_idx", ""),
            "dir": s.get("dir", ""),
            "kind": s.get("kind", ""),
            "break_kind": s.get("break_kind", ""),
            "start_time": f15[seg.get("start_idx", 0)].date if seg.get("start_idx", 0) < len(f15) else "",
            "start_px": seg.get("start_px", ""),
            "end_time": f15[seg.get("end_idx", 0)].date if seg.get("end_idx", 0) < len(f15) else "",
            "end_px": seg.get("end_px", ""),
            "fs_at_time": s.get("fs_at_time", ""),
            "source": s.get("source", ""),
        })

    # Write swing-level CSV + JSON
    with open(OUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} swing marks to:  {OUT_CSV}")

    print("\n--- Oct 20 Mark Summary ---")
    for r in rows:
        print(f"  swing#{r['swing_index']:3} | {r['confirmed_at_time']} | {r['dir']:5} | {r['kind']:3} | {r['break_kind']:5} | "
              f"start={r['start_px']:>10} @ {r['start_time']} | end={r['end_px']:>10} @ {r['end_time']}")

    # Build per-bar table for Oct 20 with OHLC + mark indicators
    # Map each swing's confirmation index to its mark info
    mark_by_idx = {}
    for s in oct20:
        seg = s.get("seg") or {}
        conf_idx = s.get("confirmed_at_idx", -1)
        if conf_idx >= 0 and conf_idx < len(f15):
            dir_marker = "B2+" if s.get("break_kind") == "B2" and s.get("dir") == "up" else (
                "B2-" if s.get("break_kind") == "B2" and s.get("dir") == "down" else s.get("break_kind", "")
            )
            mark_by_idx[conf_idx] = {
                "swing_index": s.get("swing_index", ""),
                "dir": s.get("dir", ""),
                "kind": s.get("kind", ""),
                "break_kind": s.get("break_kind", ""),
                "dir_marker": dir_marker,
            }

    # Find the first Oct 20 candle index
    oct20_start_idx = None
    for i, c in enumerate(f15):
        if c.date.startswith(TARGET_DATE):
            oct20_start_idx = i
            break

    if oct20_start_idx is not None:
        per_bar = []
        i = oct20_start_idx
        while i < len(f15) and f15[i].date.startswith(TARGET_DATE):
            c = f15[i]
            mark = mark_by_idx.get(i)
            per_bar.append({
                "bar": i - oct20_start_idx + 1,
                "time": c.date,
                "open": round(c.open, 1),
                "high": round(c.high, 1),
                "low": round(c.low, 1),
                "close": round(c.close, 1),
                "mark": f"{mark['dir_marker']} {mark['break_kind']}" if mark else "",
                "swing_index": mark.get("swing_index", "") if mark else "",
            })
            i += 1

        # Write per-bar CSV
        bar_csv = Path(__file__).resolve().parent.parent / "forward_oct20_bars.csv"
        with open(bar_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(per_bar[0].keys()))
            writer.writeheader()
            writer.writerows(per_bar)

        # Write combined JSON
        combined = {"swings": rows, "per_bar": per_bar,
                     "target_date": TARGET_DATE, "timezone": "IST"}
        with open(OUT_JSON, "w") as f:
            json.dump(combined, f, indent=2)

        print(f"\n  Per-bar table: {len(per_bar)} candles on Oct 20")
        print(f"  Per-bar CSV: {bar_csv}")

        # Print the per-bar table
        print("\n--- Oct 20 Per-Bar Marks ---")
        print(f"  {'Bar':>3} | {'time':<20} | {'open':>9} | {'high':>9} | {'low':>9} | {'close':>9} | mark")
        print(f"  {'-'*4}-+-{'-'*20}-+-{'-'*9}-+-{'-'*9}-+-{'-'*9}-+-{'-'*9}--+------------------")
        for r2 in per_bar:
            mark_str = r2["mark"] if r2["mark"] else "  -"
            print(f"  {r2['bar']:>3} | {r2['time']:<20} | {r2['open']:>9.1f} | {r2['high']:>9.1f} | {r2['low']:>9.1f} | {r2['close']:>9.1f} | {mark_str}")


if __name__ == "__main__":
    main()
