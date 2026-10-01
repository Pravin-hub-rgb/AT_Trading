"""Live-like seed from Sep 8 2026 19:30 — no prior history.

Simulates what PersistentSwingEngine does:
1. Start at timestamp (15 bars before for chop lookback)
2. Process bars one by one
3. Show each swing as it declares + the open swing building
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from src.btc.btc_config import load_btc_df
from src.firstswing import SwingEngine
from src.walker import FlowCandle


def main():
    from src.btc.btc_config import load_btc_df
    df = load_btc_df("1h", "BTCUSDT_BYBIT")
    candles = []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({
            "date": date, "ts": int(row.ts),
            "open": float(row.open), "high": float(row.high),
            "low": float(row.low), "close": float(row.close),
        })

    # Find Sep 8 2026 19:30
    target = "2026-09-08 19:30:00"
    seed_idx = None
    for i, c in enumerate(candles):
        if c["date"] == target:
            seed_idx = i
            break

    if seed_idx is None:
        print(f"{target} not found"); return

    # 15 bars before for chop lookback (like live_loop does)
    chop_lookback = 15
    start_idx = max(0, seed_idx - chop_lookback)
    print(f"Seed: {target} (bar {seed_idx})")
    print(f"Chop lookback: {chop_lookback} bars -> start at {candles[start_idx]['date']}")
    print(f"Processing {len(candles) - start_idx} bars from {candles[start_idx]['date']} to {candles[-1]['date']}")
    print()

    # Fresh engine, like PersistentSwingEngine
    opts = {"minBars": 20}
    eng = SwingEngine(opts)
    swing_index = 0

    for i in range(start_idx, len(candles)):
        c = candles[i]
        fc = FlowCandle(date=c["date"], open=c["open"], high=c["high"],
                        low=c["low"], close=c["close"])
        eng.process_bar(fc, i - start_idx)  # g_idx relative to window

        if eng.declared:
            conf_date = c["date"]
            brks = [(b.kind, b.dir, round(b.px, 1), b.idx) for b in eng.break_marks]
            print(f"{'='*72}")
            print(f"SWING {swing_index} DECLARED @ {conf_date}")
            print(f"  dir={eng.dir} | source={eng.confirm_source}")
            print(f"  seg: {eng.start_px:.1f} (idx={eng.start_idx}) -> {eng.end_px:.1f} (idx={eng.end_idx})")
            print(f"  break_kind={eng.break_marks[-1].kind if eng.break_marks else '?'}")
            print(f"  MARKS:")
            for kind, dir_, px, idx in brks:
                md = candles[start_idx + idx]["date"] if 0 <= idx < len(candles) - start_idx else "?"
                print(f"    {kind:5s} {dir_:4s} @ {px:<10.1f} {md}")
            print()

            swing_index += 1

            # New engine, like PersistentSwingEngine does
            eng = SwingEngine(opts)
            eng.defer_same_bar_arm = True

    # Show open swing at the end
    print(f"{'='*72}")
    print(f"OPEN SWING (after {swing_index} declared, currently building)")
    print(f"  dir={eng.dir}, armed={eng.armed}, state={eng.state}")
    print(f"  bars_seen={eng.bars_seen}")
    if eng.start_idx >= 0:
        print(f"  start_px={eng.start_px:.1f}")
    print(f"  e_hi_prev: {eng.e_hi_prev.px:.1f}")
    print(f"  e_lo_prev: {eng.e_lo_prev.px:.1f}")
    print(f"  break_marks so far: {[(b.kind, b.dir, round(b.px,1)) for b in eng.break_marks]}")
    print(f"  latest_sealed_high: {eng.latest_sealed_high.px:.1f}")
    print(f"  latest_sealed_low:  {eng.latest_sealed_low.px:.1f}")
    print(f"  first_chop_cross_idx={eng.first_chop_cross_idx}")


if __name__ == "__main__":
    main()
