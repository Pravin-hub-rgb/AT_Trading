"""Swing-engine parity diagnostic: compute_btc_swings vs PersistentSwingEngine.

Feeds identical candles; reports swing-count, first divergence, and root cause.
Run: python backtest/tests/exp_swing_parity_diag.py
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backtest/tests"))

from persistence.database import Database
from src.btc.btc_swing import compute_btc_swings
from src.live.persistent_swing import PersistentSwingEngine
from src.walker import FlowCandle
from engine.v18_params import SWING


def load_flow_15m():
    """Load 15m candles as FlowCandle list (same source as backtest experiments)."""
    from src.btc.btc_config import load_btc_df
    df = load_btc_df("15m", "BTCUSDT_BYBIT")
    rows = []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        rows.append(FlowCandle(
            date=date, open=float(row.open), high=float(row.high),
            low=float(row.low), close=float(row.close),
        ))
    return rows, "load_btc_df(15m, BTCUSDT_BYBIT)"


def swing_key(s):
    seg = s.get("seg", {})
    return (
        s.get("dir"),
        round(float(seg.get("start_px", 0)), 2),
        round(float(seg.get("end_px", 0)), 2),
        int(seg.get("start_idx", -1)),
        int(seg.get("end_idx", -1)),
    )


def main():
    print("=" * 100)
    print("  SWING PARITY DIAG — compute_btc_swings vs PersistentSwingEngine")
    print("=" * 100)

    flow, src = load_flow_15m()
    # Use a 40-day 15m slice (audit used 40d): 40*96 = 3840 bars
    N = min(len(flow), 40 * 96)
    flow = flow[-N:]
    # reindex dates only (g_idx will be 0..n-1)
    print(f"  source: {src}")
    print(f"  slice:  {N} bars  {flow[0].date} -> {flow[-1].date}")
    min_bars = int(SWING.get("min_bars_15m", 14))
    print(f"  minBars: {min_bars}  timeCap backtest=00:00")

    # ---- backtest path ----
    bt = compute_btc_swings(flow, opts={"minBars": min_bars}, max_swings=len(flow) // 2)
    print(f"\n  compute_btc_swings: {len(bt)} swings")

    # ---- live path (replay_harness style, timeCap forced 00:00) ----
    state_db = Database(os.path.join(tempfile.mkdtemp(prefix="sw_parity_"), "s.db"))
    state_db.connect()
    state_db.create_tables()
    pse = PersistentSwingEngine("15m", state_db, {"minBars": min_bars, "timeCap": "00:00"})
    live = []
    for g_idx, c in enumerate(flow):
        r = pse.process_bar(c, g_idx)
        if r:
            live.append(r)
    print(f"  PersistentSwingEngine: {len(live)} swings")

    n = min(len(bt), len(live))
    first_div = None
    matches = 0
    for i in range(n):
        kb, kl = swing_key(bt[i]), swing_key(live[i])
        if kb == kl:
            matches += 1
        elif first_div is None:
            first_div = (i, bt[i], live[i])

    print(f"\n  key-matches among first {n}: {matches}/{n}")
    if first_div is not None:
        i, b, l = first_div
        print(f"\n  FIRST DIVERGENCE at swing index {i}:")
        print(f"    BT   dir={b['dir']} seg={b['seg']} conf={b.get('confirmed_at_time')}")
        print(f"    LIVE dir={l['dir']} seg={l['seg']} conf={l.get('confirmed_at_time')}")
        if i > 0:
            print(f"    prev BT   swing {i-1}: {swing_key(bt[i-1])}")
            print(f"    prev LIVE swing {i-1}: {swing_key(live[i-1])}")
            # stitch analysis: where did next engine start?
            prev_end = int(bt[i - 1]["seg"]["end_idx"])
            print(f"\n  stitch analysis after swing {i-1}:")
            print(f"    end_idx={prev_end} -> BT next engine starts at {prev_end + 1}")
            print(f"    BT swing {i} start_idx={b['seg']['start_idx']} (re-fed from end+1)")
            print(f"    LIVE swing {i} start_idx={l['seg']['start_idx']}")
            # gap: bars LIVE never fed to new engine
            live_start = int(l["seg"]["start_idx"])
            if live_start > prev_end + 1:
                skipped = live_start - (prev_end + 1)
                print(f"    LIVE skipped {skipped} bars [{prev_end + 1} .. {live_start - 1}] "
                      f"that BT re-feeds to the new engine  << ROOT CAUSE")
            else:
                print(f"    LIVE start <= BT start — divergence is engine-state, not stitch gap")
    elif len(bt) != len(live):
        print(f"\n  chains match for {n} swings but counts differ ({len(bt)} vs {len(live)})")
        if len(bt) > len(live):
            print(f"  BT-only tail: {len(bt) - len(live)} swings (live missing tail / early stop)")
        else:
            print(f"  LIVE-only tail: {len(live) - len(bt)} swings")
    else:
        print("\n  PERFECT PARITY — all swings match")

    # also try live with default timeCap to show C11 impact (fresh DB)
    state_db2 = Database(os.path.join(tempfile.mkdtemp(prefix="sw_parity2_"), "s.db"))
    state_db2.connect()
    state_db2.create_tables()
    pse2 = PersistentSwingEngine("15m", state_db2, {"minBars": min_bars, "timeCap": "09:29"})
    live2 = []
    for g_idx, c in enumerate(flow):
        r = pse2.process_bar(c, g_idx)
        if r:
            live2.append(r)
    # drain any queued emissions beyond stream end
    m2 = sum(1 for i in range(min(len(bt), len(live2))) if swing_key(bt[i]) == swing_key(live2[i]))
    print(f"\n  control — live timeCap=09:29: {len(live2)} swings, key-matches {m2}/{min(len(bt), len(live2))}")

    print("\n(done)")


if __name__ == "__main__":
    main()
