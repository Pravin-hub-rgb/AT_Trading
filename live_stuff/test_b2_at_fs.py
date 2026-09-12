"""Check: how often does B2/FLIP fire at the exact bar as prev swing's confirmed_at_idx?"""
import sys
sys.path.insert(0, r"C:\Users\Pravin\Desktop\main\AT_Trading\backend")

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m, _trade_costs
from src.btc.btc_engine import trade_stats, _collect_signals
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.walker import FlowCandle


def to_cf(df):
    c, f = [], []
    for row in df.itertuples():
        d = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        c.append({"date":d,"ts":int(row.ts),"open":float(row.open),"high":float(row.high),
                   "low":float(row.low),"close":float(row.close),"volume":0,"oi":0})
        f.append(FlowCandle(date=d,open=float(row.open),high=float(row.high),
                            low=float(row.low),close=float(row.close)))
    return c, f


def main():
    print("=" * 80)
    print("B2/FLIP AT PREV SWING'S FS BAR — Edge Case Analysis")
    print("=" * 80)

    # Load Bybit perp data
    df1h = load_btc_df("1h", "BTCUSDT_BYBIT")
    df15 = load_btc_df("15m", "BTCUSDT_BYBIT")
    c1h, f1h = to_cf(df1h)
    c15, f15 = to_cf(df15)
    sw1h = _compute_swings(f1h, "continuous", min_bars=20)
    sw15 = _compute_swings(f15, "continuous", min_bars=50)

    print(f"\n15m swings: {len(sw15)}")
    print(f"1h swings: {len(sw1h)}")

    # Count marks where bidx == prev swing's confirmed_at_idx
    print(f"\n{'='*80}")
    print("15m SWINGS — Marks at prev FS bar")
    print(f"{'='*80}")

    at_fs_count = 0
    at_fs_details = []

    for si in range(1, len(sw15)):
        prev_confirmed = int(sw15[si - 1].get("confirmed_at_idx", -1))
        if prev_confirmed < 0:
            continue
        for b in sw15[si].get("breaks", []):
            bidx = int(b.get("idx", -1))
            if bidx == prev_confirmed:
                at_fs_count += 1
                at_fs_details.append({
                    "swing_no": sw15[si].get("swing_index", si),
                    "prev_swing_no": sw15[si-1].get("swing_index", si-1),
                    "kind": b["kind"],
                    "dir": b["dir"],
                    "px": float(b["px"]),
                    "bidx": bidx,
                    "prev_confirmed": prev_confirmed,
                    "time": b.get("time", "?"),
                })

    print(f"  Total marks at prev FS bar: {at_fs_count}")
    for d in at_fs_details:
        print(f"  sw{d['swing_no']}: {d['kind']} {d['dir']} @ {d['px']:.2f} "
              f"bidx={d['bidx']} prev_fs={d['prev_confirmed']} ({d['time']})")

    # Same for 1h
    print(f"\n{'='*80}")
    print("1h SWINGS — Marks at prev FS bar")
    print(f"{'='*80}")

    at_fs_1h = 0
    for si in range(1, len(sw1h)):
        prev_confirmed = int(sw1h[si - 1].get("confirmed_at_idx", -1))
        if prev_confirmed < 0:
            continue
        for b in sw1h[si].get("breaks", []):
            bidx = int(b.get("idx", -1))
            if bidx == prev_confirmed:
                at_fs_1h += 1
                print(f"  sw{sw1h[si].get('swing_index', si)}: {b['kind']} {b['dir']} "
                      f"@ {float(b['px']):.2f} bidx={bidx} prev_fs={prev_confirmed} ({b.get('time','?')})")

    print(f"  Total: {at_fs_1h}")

    # Now check: what about bidx == prev_confirmed for ALL breaks (not just one per swing)?
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"  15m: {at_fs_count} marks fire at prev swing's FS bar out of {len(sw15)} swings")
    print(f"  1h:  {at_fs_1h} marks fire at prev swing's FS bar out of {len(sw1h)} swings")

    # Now also check: marks where bidx < prev_confirmed (these are filtered)
    filtered_15m = 0
    for si in range(1, len(sw15)):
        prev_confirmed = int(sw15[si - 1].get("confirmed_at_idx", -1))
        if prev_confirmed < 0:
            continue
        for b in sw15[si].get("breaks", []):
            bidx = int(b.get("idx", -1))
            if bidx < prev_confirmed:
                filtered_15m += 1

    print(f"\n  15m marks FILTERED (bidx < prev_fs): {filtered_15m}")
    print(f"  15m marks AT prev_fs bar (bidx == prev_fs): {at_fs_count}")
    print(f"  15m marks PASSING (bidx > prev_fs): check engine...")

    # Run full engine and check how many trades have bidx == prev_confirmed
    print(f"\n{'='*80}")
    print("ENGINE OUTPUT — Trades from bidx == prev_confirmed signals")
    print(f"{'='*80}")

    t0 = min(c1h[0]["ts"], c15[0]["ts"])
    t1 = max(c1h[-1]["ts"], c15[-1]["ts"])
    fine = _load_fine_1m(t0, t1, symbol="BTCUSDT_BYBIT")

    result = simulate_htf_ltf_streak_halt(
        c1h, sw1h, c15, sw15, fine_ltf=fine,
        sl_buf_atr=0.20, ext_stop_r=1.5,
        mode="b2_vs_flip_chop", chop_thresh=58.0,
        cooldown_bars=0, max_consecutive_losses=5,
    )
    trades = result["ltf_trades"]
    closed = [t for t in trades if t["outcome"] != "open"]

    # For each trade, find its signal bar and check against prev swing's confirmed_at_idx
    at_fs_trades = 0
    for t in closed:
        entry_ts = int(t["entry_ts"])
        # Find which 15m bar this is
        bar_idx = -1
        for i, c in enumerate(c15):
            if c["ts"] == entry_ts:
                bar_idx = i
                break
        if bar_idx < 0:
            continue
        # Find which swing this signal belongs to
        for si, sw in enumerate(sw15):
            for b in sw.get("breaks", []):
                if int(b.get("idx", -1)) == bar_idx:
                    # Found the signal's swing
                    if si > 0:
                        prev_conf = int(sw15[si-1].get("confirmed_at_idx", -1))
                        if prev_conf >= 0 and bar_idx == prev_conf:
                            at_fs_trades += 1
                            print(f"  Trade: {t['dir']} sw{sw.get('swing_index',si)} "
                                  f"entry={float(t['entry_price']):.2f} R={float(t['r_multiple']):+.2f} "
                                  f"bidx={bar_idx} prev_fs={prev_conf} ({t.get('entry_date','')})")

    print(f"\n  Trades from bidx == prev_fs: {at_fs_trades} out of {len(closed)} total")
    if at_fs_trades > 0:
        # Get their R
        at_fs_r = []
        for t in closed:
            entry_ts = int(t["entry_ts"])
            bar_idx = -1
            for i, c in enumerate(c15):
                if c["ts"] == entry_ts:
                    bar_idx = i
                    break
            if bar_idx < 0:
                continue
            for si, sw in enumerate(sw15):
                for b in sw.get("breaks", []):
                    if int(b.get("idx", -1)) == bar_idx and si > 0:
                        prev_conf = int(sw15[si-1].get("confirmed_at_idx", -1))
                        if prev_conf >= 0 and bar_idx == prev_conf:
                            at_fs_r.append(float(t["r_multiple"]))
        print(f"  Their R: {at_fs_r}")
        print(f"  Sum R: {sum(at_fs_r):+.2f}")
    else:
        print("  (none found)")

    print(f"\n{'='*80}")
    print("DONE")
    print("=" * 80)


if __name__ == "__main__":
    main()
