"""v18 parameter sweep on Bybit — CLEAN vs FULL comparison.

CLEAN sweep: only "safe" tuning params (chop, slbuf, ext, min_bars)
FULL sweep:  all params including structural (ext_stop_r, cooldown, mcl, mode)

Same engine, same data — comparison shows whether defaults are structurally
sound for Bybit or need deeper adaptation.
"""
import sys, itertools, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from src.btc.btc_routes import _compute_swings
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.walker import FlowCandle

IST_OFFSET_SEC = 5 * 3600 + 30 * 60
BYBIT_DIR = Path(__file__).resolve().parents[2] / "data" / "bybit"


def load_bybit(tf):
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


def run_v18(c1h, sw1h, c15, sw15, **kw):
    trades = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=None, **kw)["ltf_trades"]
    rs = [t["r_multiple"] for t in trades]
    n = len(rs)
    if n == 0:
        return {"trades": 0, "gross_r": 0, "net_r": 0, "wr": 0, "pf": 0, "dd": 0,
                "years": {}, "all_years_pos": False, "avg_r": 0}
    tot = sum(rs)
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    wr = 100 * len(wins) / n
    pf = sum(wins) / abs(sum(losses)) if losses else 99.9
    eq = peak = dd = 0.0
    for r in rs:
        eq += r; peak = max(peak, eq); dd = max(dd, peak - eq)
    years = {}
    for t in trades:
        y = t["entry_date"][:4]
        years.setdefault(y, [0, 0.0]); years[y][0] += 1; years[y][1] += t["r_multiple"]
    costs = []
    for t in trades:
        risk = abs(t["entry_price"] - t["sl"])
        if risk <= 0: costs.append(0); continue
        costs.append((t["entry_price"] * 0.05 / 100 * 2) / risk + (2 * 2) / risk)
    net = tot - sum(costs)
    return {"trades": n, "gross_r": round(tot, 1), "net_r": round(net, 1),
            "wr": round(wr, 1), "pf": round(pf, 2), "dd": round(dd, 1),
            "avg_r": round(tot / n, 3),
            "years": {y: (v[0], round(v[1], 1)) for y, v in sorted(years.items())},
            "all_years_pos": all(v[1] > 0 for v in years.values())}


def print_table(title, results, limit=20):
    print(f"\n{'=' * 120}")
    print(f"  {title}")
    print(f"{'=' * 120}")
    print(f"{'#':>3} {'Chop':>5} {'Mode':<22} {'CD':>3} {'MCL':>3} {'SL':>4} {'Ext':>4} {'MB15':>4} {'MB1h':>4} | {'#T':>4} {'Gross':>7} {'Net':>7} {'Avg':>6} {'PF':>5} {'DD':>5} {'Y+':>3}")
    print("-" * 120)
    for i, r in enumerate(results[:limit]):
        print(f"{i+1:>3} {r['chop']:>5.1f} {r['mode']:<22} {r['cd']:>3} {r['mcl']:>3} "
              f"{r['slbuf']:>4.2f} {r['ext']:>4.1f} {r['mb15']:>4} {r['mb1h']:>4} | "
              f"{r['trades']:>4} {r['gross_r']:>+7.1f} {r['net_r']:>+7.1f} {r['avg_r']:>+6.2f} "
              f"{r['pf']:>5.2f} {r['dd']:>5.1f} {'Y' if r['all_years_pos'] else 'N':>3}")


def main():
    t0 = time.time()
    print("Loading Bybit data...")
    c1h, f1h = load_bybit("1h")
    c15, f15 = load_bybit("15m")

    mb15_opts = [40, 50, 60]
    mb1h_opts = [15, 20]
    print("Pre-computing swing chains...")
    swing_15m = {mb: _compute_swings(f15, "continuous", min_bars=mb) for mb in mb15_opts}
    swing_1h = {mb: _compute_swings(f1h, "continuous", min_bars=mb) for mb in mb1h_opts}
    for mb in mb15_opts: print(f"  15m mb={mb}: {len(swing_15m[mb])} swings")
    for mb in mb1h_opts: print(f"  1h  mb={mb}: {len(swing_1h[mb])} swings")

    # CLEAN: only chop, slbuf, ext, min_bars — mode/cd/mcl FIXED at defaults
    clean_grid = list(itertools.product(
        [50.0, 55.0, 58.0, 60.0, 61.8, 63.0, 68.0],    # chop
        [0.18, 0.20, 0.25, 0.28],                         # slbuf
        [0.8, 1.0, 1.2, 1.5],                             # ext
        mb15_opts, mb1h_opts,
    ))
    print(f"\nCLEAN: {len(clean_grid)} combos (fixed: mode=b2, cd=20, mcl=5)")
    clean_results = []
    for idx, (chop, slbuf, ext, mb15, mb1h) in enumerate(clean_grid):
        r = run_v18(c1h, swing_1h[mb1h], c15, swing_15m[mb15],
                    sl_buf_atr=slbuf, ext_stop_r=ext, chop_thresh=chop,
                    mode="b2_vs_flip_chop", cooldown_bars=20, max_consecutive_losses=5)
        clean_results.append({"chop": chop, "mode": "b2_vs_flip_chop", "cd": 20,
                              "mcl": 5, "slbuf": slbuf, "ext": ext, "mb15": mb15, "mb1h": mb1h, **r})
        if (idx + 1) % 200 == 0:
            best = max((x["net_r"] for x in clean_results), default=0)
            print(f"  CLEAN [{idx+1}/{len(clean_grid)}] {time.time()-t0:.0f}s, best={best:+.1f}R")
    clean_results.sort(key=lambda x: x["net_r"], reverse=True)

    # Save intermediate results
    partial_path = Path(__file__).resolve().parent / "sweep_bybit_partial.json"

    # FULL: all params free — same process as Binance spot sweep
    full_grid = list(itertools.product(
        [50.0, 55.0, 58.0, 60.0, 61.8, 65.0, 68.0],       # chop (7)
        ["b2_vs_flip_chop", "chop", "decisive_vs_flip_chop"],  # mode (3)
        [0, 20],                                              # cd (2)
        [0, 5],                                               # mcl (2)
        [0.20, 0.25],                                         # slbuf (2)
        [0.8, 1.0, 1.2, 1.5],                                # ext (4)
        [40, 50, 60],                                         # mb15 (3)
        [15, 20],                                             # mb1h (2)
    ))
    print(f"\nFULL: {len(full_grid)} combos (all params free)")
    full_results = []
    for idx, (chop, mode, cd, mcl, slbuf, ext, mb15, mb1h) in enumerate(full_grid):
        r = run_v18(c1h, swing_1h[mb1h], c15, swing_15m[mb15],
                    sl_buf_atr=slbuf, ext_stop_r=ext, chop_thresh=chop,
                    mode=mode, cooldown_bars=cd, max_consecutive_losses=mcl)
        full_results.append({"chop": chop, "mode": mode, "cd": cd,
                             "mcl": mcl, "slbuf": slbuf, "ext": ext, "mb15": mb15, "mb1h": mb1h, **r})
        if (idx + 1) % 200 == 0:
            best = max((x["net_r"] for x in full_results), default=0)
            print(f"  FULL [{idx+1}/{len(full_grid)}] {time.time()-t0:.0f}s, best={best:+.1f}R")
            partial_path.write_text(json.dumps(full_results))
    full_results.sort(key=lambda x: x["net_r"], reverse=True)

    # BASELINE
    b = run_v18(c1h, swing_1h[20], c15, swing_15m[50],
                sl_buf_atr=0.25, ext_stop_r=1.5, chop_thresh=61.8,
                mode="b2_vs_flip_chop", cooldown_bars=20, max_consecutive_losses=5)

    print(f"\n{'=' * 120}")
    print(f"  BASELINE: chop=61.8, b2_vs_flip, cd=20, mcl=5, slbuf=0.25, ext=1.5, mb15=50, mb1h=20")
    print(f"  Trades={b['trades']}, Net={b['net_r']:+.1f}R, Avg={b['avg_r']:+.2f}R, PF={b['pf']}, DD={b['dd']}R, AllY+={'Y' if b['all_years_pos'] else 'N'}")
    print(f"  Yearly: {b['years']}")

    print_table("CLEAN SWEEP — TOP 25 BY NET R (mode/cd/mcl fixed)", clean_results, 25)
    clean_good = [r for r in clean_results if r["all_years_pos"] and r["dd"] <= 12]
    if clean_good:
        print_table("CLEAN — TOP 15 (all years +, DD<=12R)", clean_good, 15)

    print_table("FULL SWEEP — TOP 25 BY NET R (all params free)", full_results, 25)
    full_good = [r for r in full_results if r["all_years_pos"] and r["dd"] <= 12]
    if full_good:
        print_table("FULL — TOP 15 (all years +, DD<=12R)", full_good, 15)

    cb, fb = clean_results[0], full_results[0]
    print(f"\n{'=' * 120}")
    print(f"  CLEAN BEST vs FULL BEST vs BASELINE")
    print(f"{'=' * 120}")
    print(f"  {'':30} {'Baseline':>12} {'Clean Best':>12} {'Full Best':>12}")
    for label, bv, cv, fv in [
        ("Net R", b['net_r'], cb['net_r'], fb['net_r']),
        ("Avg R", b['avg_r'], cb['avg_r'], fb['avg_r']),
        ("Trades", b['trades'], cb['trades'], fb['trades']),
        ("DD", b['dd'], cb['dd'], fb['dd']),
        ("PF", b['pf'], cb['pf'], fb['pf']),
    ]:
        fmt = "+.1f" if label != "Trades" else "d"
        print(f"  {label:30} {bv:>12{fmt}} {cv:>12{fmt}} {fv:>12{fmt}}")
    print(f"  {'All Years +':30} {'Y' if b['all_years_pos'] else 'N':>12} {'Y' if cb['all_years_pos'] else 'N':>12} {'Y' if fb['all_years_pos'] else 'N':>12}")
    print(f"\n  CLEAN: chop={cb['chop']}, slbuf={cb['slbuf']}, ext={cb['ext']}, mb15={cb['mb15']}, mb1h={cb['mb1h']}")
    print(f"  FULL:  chop={fb['chop']}, mode={fb['mode']}, cd={fb['cd']}, mcl={fb['mcl']}, slbuf={fb['slbuf']}, ext={fb['ext']}, mb15={fb['mb15']}, mb1h={fb['mb1h']}")
    delta = fb['net_r'] - cb['net_r']
    print(f"\n  Full vs Clean: {delta:+.1f}R")
    if delta > 20:
        print(f"  >> Structural changes add {delta:.0f}R -- Bybit needs different strategy logic")
    elif delta > 5:
        print(f"  >> Structural changes add {delta:.0f}R -- mild structural adaptation helps")
    else:
        print(f"  >> Structural changes add only {delta:.0f}R -- defaults are structurally sound")
    print(f"\nTotal: {len(clean_grid) + len(full_grid)} combos, {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
