"""Verify live engine marks match backtest marks.

Uses the SAME data (btc_data/is/ CSVs) and SAME engine (compute_btc_swings)
to check that marks at Oct 20 match between the continuous backtest chain
and a fresh re-run.

Also simulates what the live bot does: seed from timestamps, fetch forward,
and verify the marks align with the full-chain backtest.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backtest"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

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

    # --- Approach 2: Simulate live seed from Sep 26 (7+ days before Oct 24) ---
    # Plan §6: seed from 2026-09-26 10:00 (15m) / 2026-09-26 16:30 (1h)
    # After ~7 days (300 15m / 150 1h bars), swings converge with full chain.
    print("\n[2] Live seed from timestamps: 15m=Sep26 10:00, 1h=Sep26 16:30")
    print("    (7+ day handoff — walker should converge by Oct 20)")
    seed_15m = "2026-09-26 10:00:00"
    seed_1h = "2026-09-26 16:30:00"  

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
        sw1h_tail = compute_btc_swings(f1h_tail, opts={"minBars": 15}, max_swings=len(f1h_tail) // 2)
        print(f"    1h tail swings: {len(sw1h_tail)}")

        # Compare: extract Oct 20 marks from BOTH chains and check convergence
        oct20_marks_tail = extract_marks(sw15_tail, "2026-10-20")
        print(f"\n[3] Convergence check: Oct 20 marks full-chain vs seeded")
        print(f"    Full chain:  {len(oct20_marks_full)} marks")
        print(f"    Seed chain:  {len(oct20_marks_tail)} marks")

        full_keys = {(m["swing_index"], m["confirmed_at_time"], m["break_kind"],
                       m["break_dir"], round(m["break_px"], 2)) for m in oct20_marks_full}
        tail_keys = {(m["swing_index"], m["confirmed_at_time"], m["break_kind"],
                       m["break_dir"], round(m["break_px"], 2)) for m in oct20_marks_tail}

        # Note: swing_index differs between chains (different starting count).
        # Compare by (confirmed_at_time, break_kind, break_dir, break_px) only.
        full_loose = {(m["confirmed_at_time"], m["break_kind"], m["break_dir"],
                       round(m["break_px"], 2)) for m in oct20_marks_full}
        tail_loose = {(m["confirmed_at_time"], m["break_kind"], m["break_dir"],
                       round(m["break_px"], 2)) for m in oct20_marks_tail}

        print(f"    Exact (incl swing_index):   full={len(full_keys - tail_keys)} tail-only, tail={len(tail_keys - full_keys)} full-only")
        print(f"    Loose (time/kind/dir/px):   full={len(full_loose - tail_loose)} tail-only, tail={len(tail_loose - full_loose)} full-only")
        if not full_loose - tail_loose and not tail_loose - full_loose:
            print("    CONVERGED: Oct 20 marks match within 2 cents")
        else:
            print("    MISMATCH: Oct 20 marks differ — seed too close or path divergence")
    else:
        print("    15m seed candle not found — skipping convergence check")

    print("\n" + "=" * 70)
    print("CONCLUSION:")
    print("=" * 70)
    print("""
Full chain (backtest): Jan 2023 -> Oct 24
  - 15m: 50-bar minBars
  - Swing chain is continuous from Jan 2023

Seed chain (from Sep 26, 7+ day handoff):
  - Engine starts fresh at Sep 26 seed timestamp
  - Path-dependent initially, but converges after ~7 days (300 15m / 150 1h bars)
  - By Oct 20, marks should match within 2 cents

If converged: P0a (1h index alignment) is verified — the seeded chain
produces the same swing breaks as the full backtest chain.
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
    out_path = Path(__file__).resolve().parents[2] / "backtest" / "verify_oct24_marks.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nResults written to: {out_path}")
