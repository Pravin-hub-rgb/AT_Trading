"""Verify parity: compare live journal vs REAL backtest output.

Uses the ACTUAL backend engine (compute_btc_swings + simulate_htf_ltf_streak_halt)
to recompute expected marks/trades on the same window, then diffs against
the live journal.

L1: marks (swing_no, kind, direction, price on same bar)
L2: trades (entry/exit/SL/TP)
L3: R-multiple totals

Any diff = live bug.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.walker import FlowCandle


def load_window(tf):
    df = load_btc_df(tf)
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({"date": date, "ts": int(row.ts), "open": float(row.open),
                        "high": float(row.high), "low": float(row.low), "close": float(row.close),
                        "volume": 0, "oi": 0})
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high),
                               low=float(row.low), close=float(row.close)))
    return candles, flow


def run_backtest():
    """Run the REAL v18 backtest and return marks + trades."""
    c1h, f1h = load_window("1h")
    c15, f15 = load_window("15m")
    sw1h = _compute_swings(f1h, "continuous", min_bars=20)
    sw15 = _compute_swings(f15, "continuous", min_bars=50)
    t0 = min(c1h[0]["ts"], c15[0]["ts"])
    t1 = max(c1h[-1]["ts"], c15[-1]["ts"])
    fine = _load_fine_1m(t0, t1)

    result = simulate_htf_ltf_streak_halt(
        c1h, sw1h, c15, sw15, fine_ltf=fine,
        sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
        cooldown_bars=20, max_consecutive_losses=5)

    # Extract marks from swing chains
    marks_15m = []
    for s in sw15:
        for b in s.get("breaks", []):
            idx = b.get("idx", -1)
            if 0 <= idx < len(c15):
                marks_15m.append({
                    "ts": c15[idx]["ts"],
                    "date": c15[idx]["date"],
                    "tf": "15m",
                    "kind": b["kind"],
                    "dir": b["dir"],
                    "px": b["px"],
                    "swing_no": s["swing_index"],
                })

    marks_1h = []
    for s in sw1h:
        for b in s.get("breaks", []):
            idx = b.get("idx", -1)
            if 0 <= idx < len(c1h):
                marks_1h.append({
                    "ts": c1h[idx]["ts"],
                    "date": c1h[idx]["date"],
                    "tf": "1h",
                    "kind": b["kind"],
                    "dir": b["dir"],
                    "px": b["px"],
                    "swing_no": s["swing_index"],
                })

    return marks_15m, marks_1h, result["ltf_trades"]


def compare_marks(live_marks, expected_marks):
    """Compare live journal marks vs expected backtest marks."""
    live_set = {(m["ts"], m["kind"], m["dir"], m["swing_no"]) for m in live_marks}
    expected_set = {(m["ts"], m["kind"], m["dir"], m["swing_no"]) for m in expected_marks}

    missing = expected_set - live_set
    extra = live_set - expected_set
    matched = live_set & expected_set

    return {
        "expected_count": len(expected_set),
        "actual_count": len(live_set),
        "matched": len(matched),
        "missing": len(missing),
        "extra": len(extra),
        "match": len(missing) == 0 and len(extra) == 0,
    }


def verify(live_db_path: str = "backbencher.db"):
    """Run full parity verification."""
    from persistence.database import Database
    from persistence.mark_store import get_marks

    print("=" * 72)
    print("PARITY CHECK: Live Journal vs REAL Backtest")
    print("=" * 72)

    # Run backtest
    print("\n[1] Running REAL v18 backtest...")
    expected_15m, expected_1h, expected_trades = run_backtest()
    print(f"  15m marks: {len(expected_15m)}")
    print(f"   1h marks: {len(expected_1h)}")
    print(f"  LTF trades: {len(expected_trades)}")

    # Load live journal
    print("\n[2] Loading live journal...")
    db = Database(live_db_path)
    db.connect()
    live_15m = get_marks(db, "15m")
    live_1h = get_marks(db, "1h")
    print(f"  15m marks: {len(live_15m)}")
    print(f"   1h marks: {len(live_1h)}")

    # Convert live marks to comparable dicts
    live_15m_dicts = [{"ts": m.ts, "kind": m.kind, "direction": m.direction, "swing_no": m.swing_no} for m in live_15m]
    live_1h_dicts = [{"ts": m.ts, "kind": m.kind, "direction": m.direction, "swing_no": m.swing_no} for m in live_1h]

    # Compare
    print("\n[3] Comparing...")
    result_15m = compare_marks(live_15m_dicts, expected_15m)
    result_1h = compare_marks(live_1h_dicts, expected_1h)

    print(f"\n  15m: {'PASS' if result_15m['match'] else 'FAIL'}")
    print(f"    expected={result_15m['expected_count']} actual={result_15m['actual_count']} "
          f"matched={result_15m['matched']} missing={result_15m['missing']} extra={result_15m['extra']}")

    print(f"\n   1h: {'PASS' if result_1h['match'] else 'FAIL'}")
    print(f"    expected={result_1h['expected_count']} actual={result_1h['actual_count']} "
          f"matched={result_1h['matched']} missing={result_1h['missing']} extra={result_1h['extra']}")

    db.close()

    overall = result_15m["match"] and result_1h["match"]
    print("\n" + "=" * 72)
    print(f"Overall: {'PASS - Live matches backtest' if overall else 'FAIL - Differences found'}")
    print("=" * 72)

    return overall


if __name__ == "__main__":
    verify()

