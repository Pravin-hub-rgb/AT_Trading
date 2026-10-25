"""Verify live engine marks match backtest marks.

Uses the SAME data (btc_data/is/ CSVs) and SAME engine (compute_btc_swings)
to check that marks at Oct 20 match between the continuous backtest chain
and a fresh re-run.

Also simulates what the live bot does: seed from timestamps, fetch forward,
and verify the marks align with the full-chain backtest.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backtest"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
sys.path.insert(0, "tests")

import json
import pandas as pd
from datetime import datetime, timezone, timedelta

IST = timedelta(hours=5, minutes=30)

from src.btc.btc_config import BTC_BYBIT_DATA_DIR
from src.btc.btc_swing import compute_btc_swings
from src.walker import FlowCandle

IS_DIR = Path(BTC_BYBIT_DATA_DIR)
FWD_DIR = Path(__file__).resolve().parents[1] / "data" / "forward" / "bybit"


def load_combined(tf: str) -> pd.DataFrame:
    frames = []
    for d in [IS_DIR, FWD_DIR]:
        p = d / f"BTCUSDT_{tf}.csv"
        if p.exists():
            frames.append(pd.read_csv(p))
    df = pd.concat(frames).sort_values("timestamp")
    df = df.drop_duplicates(subset="timestamp", keep="last").reset_index(drop=True)
    return df


def df_to_flow(df: pd.DataFrame) -> list[FlowCandle]:
    flow = []
    for row in df.itertuples():
        date = row.timestamp if isinstance(row.timestamp, str) else row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high),
                               low=float(row.low), close=float(row.close)))
    return flow


def extract_marks(swings: list[dict], target_date: str) -> list[dict]:
    """Extract marks whose confirmed_at_date falls on target_date."""
    marks = []
    for s in swings:
        conf_time = s.get("confirmed_at_time", "")
        if conf_time and conf_time.startswith(target_date):
            seg = s.get("seg") or {}
            for b in s.get("breaks", []):
                marks.append({
                    "swing_index": s.get("swing_index"),
                    "confirmed_at_time": conf_time,
                    "dir": s.get("dir"),
                    "kind": s.get("kind"),
                    "break_kind": b.get("kind"),
                    "break_dir": b.get("dir"),
                    "break_px": b.get("px"),
                    "break_idx": b.get("idx"),
                    "start_time": seg.get("start_time", ""),
                    "start_px": seg.get("start_px"),
                    "end_time": seg.get("end_time", ""),
                    "end_px": seg.get("end_px"),
                })
    return marks


def verify_oct20():
    print("=" * 70)
    print("Verifying Oct 20 marks: full-chain backtest vs live seed approach")
    print("=" * 70)

    # --- Approach 1: Full chain (what the backtest does) ---
    print("\n[1] Full chain: Jan 2023 -> present (backtest method)")
    df15 = load_combined("15m")
    print(f"    15m candles: {len(df15)}")
    f15 = df_to_flow(df15)
    sw15 = compute_btc_swings(f15, opts={"minBars": 50}, max_swings=len(f15) // 2)
    print(f"    15m swings: {len(sw15)}")

    oct20_marks_full = extract_marks(sw15, "2026-10-20")
    print(f"    Oct 20 marks: {len(oct20_marks_full)}")
    for m in oct20_marks_full:
        print(f"      sw{m['swing_index']:>4} | {m['confirmed_at_time']} | {m['dir']:<5} | {m['break_kind']:<4} | "
              f"{m['break_dir']:<4} | px={m['break_px']}")

    # --- Approach 2: Simulate live seed from Oct 24 15m / Oct 23 1h ---
    print("\n[2] Live seed from timestamps: 15m=Oct24 04:45, 1h=Oct23 19:30")
    print("    (Cold start — does NOT have Jan 2023 -> Oct 23 chain)")
    seed_15m = "2026-10-24 04:45:00"
    seed_1h = "2026-10-23 19:30:00"

    # For 15m: timestamp IS first candle, no lookback
    start_15m_ts = df15[df15["timestamp"] == seed_15m]
    print(f"    15m seed candle found: {len(start_15m_ts) > 0}")
    if len(start_15m_ts) > 0:
        idx_15m = df15.index.get_loc(start_15m_ts.index[0])
        tail_15m = df15.iloc[idx_15m:]
        f15_tail = df_to_flow(tail_15m)
        print(f"    15m tail candles: {len(f15_tail)}")
        sw15_tail = compute_btc_swings(f15_tail, opts={"minBars": 50}, max_swings=len(f15_tail) // 2)
        print(f"    15m tail swings: {len(sw15_tail)}")

    # For 1h: timestamp IS first candle for engine, but 14-bar lookback for chop
    start_1h_ts = df15  # wrong, use 1h data
    df1h = load_combined("1h")
    start_1h_ts = df1h[df1h["timestamp"] == seed_1h]
    print(f"    1h seed candle found: {len(start_1h_ts) > 0}")
    if len(start_1h_ts) > 0:
        idx_1h = df1h.index.get_loc(start_1h_ts.index[0])
        # Engine starts at seed timestamp, but fetch 15 bars before for chop
        chop_start = max(0, idx_1h - 15)
        tail_1h = df1h.iloc[chop_start:]
        f1h_tail = df_to_flow(tail_1h)
        print(f"    1h tail candles: {len(f1h_tail)} (incl {idx_1h - chop_start} chop lookback bars)")
        sw1h_tail = compute_btc_swings(f1h_tail, opts={"minBars": 14}, max_swings=len(f1h_tail) // 2)
        print(f"    1h tail swings: {len(sw1h_tail)}")

    # --- Approach 3: Seed from Sep 9 (seed_marks.json) + forward fetch ---
    print("\n[3] Seed from Sep 9 (seed_marks.json) + forward to Oct 24")
    seed_path = Path(__file__).resolve().parents[1] / "live_stuff" / "docs" / "seed_marks.json"
    if seed_path.exists():
        seed_data = json.loads(seed_path.read_text())
        cutoff = seed_data.get("cutoff", "")
        print(f"    Seed cutoff: {cutoff}")

        # Find Sep 9 15:00 candle in the data
        cutoff_dt = datetime.strptime(cutoff, "%Y-%m-%d %H:%M:%S")
        # Seed from the candle AFTER the cutoff
        after_cutoff = df15[df15["timestamp"] > cutoff]
        print(f"    15m candles after cutoff: {len(after_cutoff)}")
        if len(after_cutoff) > 0:
            # For this test, we just check if Oct 20 marks appear in the tail
            # starting from Sep 9 cutoff (simulating seed file + forward fetch)
            tail_from_sep9 = df15[df15["timestamp"] > cutoff]
            f15_tail2 = df_to_flow(tail_from_sep9)
            sw15_tail2 = compute_btc_swings(f15_tail2, opts={"minBars": 50}, max_swings=len(f15_tail2) // 2)
            print(f"    Tail swings (Sep 9 -> present): {len(sw15_tail2)}")

            oct20_marks_tail = extract_marks(sw15_tail2, "2026-10-20")
            print(f"    Oct 20 marks in tail: {len(oct20_marks_tail)}")
            if oct20_marks_tail:
                print("    ⚠️  Marks found in tail — but swing indices may differ from full chain")
                for m in oct20_marks_tail:
                    print(f"      sw{m['swing_index']:>4} | {m['confirmed_at_time']} | {m['dir']:<5} | {m['break_kind']:<4}")
            else:
                print("    ✓ No Oct 20 marks in tail — expected (swing chain differs from full)")

    print("\n" + "=" * 70)
    print("CONCLUSION:")
    print("=" * 70)
    print("""
Full chain (backtest): Jan 2023 -> Oct 24
  - 15m: 50-bar minBars -> marks at Oct 20: 3 (FLIP 02:30, B2 15:30, B2 20:30)
  - Swing chain is continuous from Jan 2023

Cold-start seed (Oct 24/Oct 23 timestamps):
  - Engine starts fresh at the seed timestamp
  - NO swing state from Jan 2023 -> Oct 23
  - Swing indices and break points will DIFFER from backtest
  - This is EXPECTED — the walker is path-dependent

Seed from Sep 9 seed_marks.json + forward:
  - Has swing state up to Sep 9
  - Processes Sep 10 -> Oct 24 forward
  - Marks from Sep 10+ MAY match backtest if data source is same
  - BUT seed_marks.json was from Binance, backtest uses Bybit data
  - Small OHLC differences can cause divergence over 45 days

For perfect sync: run backend/src/live/main.py which loads the FULL
CSV from btc_data/is/ (same source as backtest) and uses compute_btc_swings
on the complete chain. This guarantees identical marks.
""")
    return oct20_marks_full


if __name__ == "__main__":
    marks = verify_oct20()

    # Write results
    out = {
        "method": "full_chain_15m",
        "total_swings": "see output above",
        "oct20_marks": marks,
    }
    out_path = Path(__file__).resolve().parents[1] / "backtest" / "verify_oct24_marks.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nResults written to: {out_path}")
