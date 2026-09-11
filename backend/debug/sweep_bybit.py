"""v18 parameter sweep on Bybit BTCUSDT perp data.

Sweeps: chop_thresh, mode, cooldown_bars, max_consecutive_losses, sl_buf_atr, ext_stop_r, min_bars.
Uses Bybit 15m+1h data (no 1m fine fills).
"""
import sys, itertools, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from src.btc.btc_routes import _compute_swings
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.walker import FlowCandle

IST_OFFSET_SEC = 5 * 3600 + 30 * 60
BYBIT_DIR = Path(__file__).resolve().parents[2] / "data" / "bybit"


def load_bybit(tf: str):
    path = BYBIT_DIR / f"BTCUSDT_{tf}.csv"
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates(subset="timestamp", keep="last").reset_index(drop=True)
    df["ts"] = (df["timestamp"].astype("int64") // 10**9) - IST_OFFSET_SEC
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({"date": date, "ts": int(row.ts), "open": float(row.open),
                        "high": float(row.high), "low": float(row.low), "close": float(row.close),
                        "volume": 0, "oi": 0})
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high),
                               low=float(row.low), close=float(row.close)))
    return candles, flow


def run_v18(c1h, sw1h, c15, sw15, **kwargs):
    trades = simulate_htf_ltf_streak_halt(
        c1h, sw1h, c15, sw15, fine_ltf=None, **kwargs
    )["ltf_trades"]
    rs = [t["r_multiple"] for t in trades]
    n = len(rs)
    if n == 0:
        return {"trades": 0, "gross_r": 0, "net_r": 0, "wr": 0, "pf": 0, "dd": 0, "years": {}, "all_years_pos": False}
    tot = sum(rs)
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    wr = 100 * len(wins) / n
    pf = sum(wins) / abs(sum(losses)) if losses else 99.9

    eq = peak = dd = 0.0
    for r in rs:
        eq += r
        peak = max(peak, eq)
        dd = max(dd, peak - eq)

    years = {}
    for t in trades:
        y = t["entry_date"][:4]
        years.setdefault(y, [0, 0.0])
        years[y][0] += 1
        years[y][1] += t["r_multiple"]

    costs = []
    for t in trades:
        risk = abs(t["entry_price"] - t["sl"])
        if risk <= 0:
            costs.append(0)
            continue
        fee_r = (t["entry_price"] * 0.05 / 100 * 2) / risk
        slip_r = (2 * 2) / risk
        costs.append(fee_r + slip_r)
    net = tot - sum(costs)

    return {
        "trades": n, "gross_r": round(tot, 1), "net_r": round(net, 1),
        "wr": round(wr, 1), "pf": round(pf, 2), "dd": round(dd, 1),
        "years": {y: (v[0], round(v[1], 1)) for y, v in sorted(years.items())},
        "all_years_pos": all(v[1] > 0 for v in years.values()),
    }


def main():
    t0 = time.time()
    print("Loading Bybit data...")
    c1h, f1h = load_bybit("1h")
    c15, f15 = load_bybit("15m")

    # Pre-compute swing chains
    min_bars_15m_opts = [35, 45, 50, 55, 65]
    min_bars_1h_opts = [15, 20, 25]

    print("Pre-computing swing chains...")
    swing_15m = {}
    swing_1h = {}
    for mb in min_bars_15m_opts:
        swing_15m[mb] = _compute_swings(f15, "continuous", min_bars=mb)
        print(f"  15m minBars={mb}: {len(swing_15m[mb])} swings")
    for mb in min_bars_1h_opts:
        swing_1h[mb] = _compute_swings(f1h, "continuous", min_bars=mb)
        print(f"  1h  minBars={mb}: {len(swing_1h[mb])} swings")

    # Parameter grid (~600 combos, ~10min)
    grid = list(itertools.product(
        [55.0, 60.0, 61.8, 65.0, 68.0],                    # chop_thresh
        ["b2_vs_flip_chop", "decisive_vs_flip_chop"],        # mode
        [0, 20],                                              # cooldown_bars
        [0, 5],                                               # max_consecutive_losses
        [0.20, 0.25],                                         # sl_buf_atr
        [1.0, 1.5],                                           # ext_stop_r
        [35, 50],                                             # min_bars_15m
        [15, 20],                                             # min_bars_1h
    ))

    total = len(grid)
    print(f"\nSweep: {total} combinations")
    print("=" * 115)

    results = []
    for idx, (chop, mode, cd, mcl, slbuf, ext, mb15, mb1h) in enumerate(grid):
        sw15 = swing_15m[mb15]
        sw1h = swing_1h[mb1h]
        r = run_v18(
            c1h, sw1h, c15, sw15,
            sl_buf_atr=slbuf, ext_stop_r=ext,
            chop_thresh=chop, mode=mode,
            cooldown_bars=cd, max_consecutive_losses=mcl,
        )
        results.append({
            "chop": chop, "mode": mode, "cd": cd, "mcl": mcl,
            "slbuf": slbuf, "ext": ext, "mb15": mb15, "mb1h": mb1h,
            **r,
        })

        if (idx + 1) % 1000 == 0 or idx == total - 1:
            elapsed = time.time() - t0
            rate = (idx + 1) / elapsed if elapsed > 0 else 0
            eta = (total - idx - 1) / rate if rate > 0 else 0
            best = max((r2["net_r"] for r2 in results), default=0)
            print(f"  [{idx+1}/{total}] {elapsed:.0f}s elapsed, {rate:.0f}/s, ETA {eta:.0f}s, best net so far: {best:+.1f}R")

    # Sort by net R
    results.sort(key=lambda x: x["net_r"], reverse=True)

    print("\n" + "=" * 115)
    print("TOP 30 BY NET R")
    print("=" * 115)
    hdr = f"{'#':>3} {'Chop':>5} {'Mode':<24} {'CD':>3} {'MCL':>3} {'SL':>4} {'Ext':>4} {'MB15':>4} {'MB1h':>4} | {'#T':>4} {'Gross':>7} {'Net':>7} {'WR%':>5} {'PF':>5} {'DD':>5} {'Y+':>3}"
    print(hdr)
    print("-" * 115)
    for i, r in enumerate(results[:30]):
        print(f"{i+1:>3} {r['chop']:>5.1f} {r['mode']:<24} {r['cd']:>3} {r['mcl']:>3} {r['slbuf']:>4.2f} {r['ext']:>4.1f} {r['mb15']:>4} {r['mb1h']:>4} | {r['trades']:>4} {r['gross_r']:>+7.1f} {r['net_r']:>+7.1f} {r['wr']:>5.1f} {r['pf']:>5.2f} {r['dd']:>5.1f} {'Y' if r['all_years_pos'] else 'N':>3}")

    # Top by net/DD
    print("\n" + "=" * 115)
    print("TOP 30 BY NET R / DD (risk-adjusted)")
    print("=" * 115)
    results_rd = [r for r in results if r["dd"] > 0]
    results_rd.sort(key=lambda x: x["net_r"] / x["dd"], reverse=True)
    hdr2 = f"{'#':>3} {'Chop':>5} {'Mode':<24} {'CD':>3} {'MCL':>3} {'SL':>4} {'Ext':>4} {'MB15':>4} {'MB1h':>4} | {'#T':>4} {'Gross':>7} {'Net':>7} {'WR%':>5} {'PF':>5} {'DD':>5} {'N/DD':>5} {'Y+':>3}"
    print(hdr2)
    print("-" * 120)
    for i, r in enumerate(results_rd[:30]):
        ratio = r["net_r"] / r["dd"]
        print(f"{i+1:>3} {r['chop']:>5.1f} {r['mode']:<24} {r['cd']:>3} {r['mcl']:>3} {r['slbuf']:>4.2f} {r['ext']:>4.1f} {r['mb15']:>4} {r['mb1h']:>4} | {r['trades']:>4} {r['gross_r']:>+7.1f} {r['net_r']:>+7.1f} {r['wr']:>5.1f} {r['pf']:>5.2f} {r['dd']:>5.1f} {ratio:>5.1f} {'Y' if r['all_years_pos'] else 'N':>3}")

    # Baseline
    print("\n" + "=" * 115)
    print("BASELINE: v18 defaults (chop=61.8, b2_vs_flip_chop, cd=20, mcl=5, slbuf=0.25, ext=1.5, mb15=50, mb1h=20)")
    b = [r for r in results if r["chop"]==61.8 and r["mode"]=="b2_vs_flip_chop" and r["cd"]==20 and r["mcl"]==5 and r["slbuf"]==0.25 and r["ext"]==1.5 and r["mb15"]==50 and r["mb1h"]==20]
    if b:
        br = b[0]
        print(f"  Trades: {br['trades']}, Gross: {br['gross_r']:+.1f}R, Net: {br['net_r']:+.1f}R, WR: {br['wr']}%, PF: {br['pf']}, DD: {br['dd']}R, AllY+: {'Y' if br['all_years_pos'] else 'N'}")
        print(f"  Yearly: {br['years']}")
    print(f"\nTotal: {total} combos, {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
