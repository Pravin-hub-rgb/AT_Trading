"""Per-Year Sweep: chop_thresh x sl_buf_atr — engine params per market regime.

Fixes htf_rr=3.0, ext_stop=1.5. Sweeps chop and SL buffer.
Run: python backtest/sweeps/sweep_engine_per_year.py
"""
import sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.walker import FlowCandle

SYMBOL = "BTCUSDT_BYBIT"
FIXED = {"htf_rr": 3.0, "ext_stop_r": 1.5, "cooldown_bars": 0, "max_consecutive_losses": 5, "mode": "b2_vs_flip_chop"}

CHOPS = [45.0, 50.0, 55.0, 58.0, 60.0, 65.0, 70.0]
SL_BUFS = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]

FEE_RATE = 0.055 / 100.0
ENTRY_SLIP = 0.005 / 100.0
EXIT_SLIP = 0.010 / 100.0

YEARS = [2023, 2024, 2025, 2026]
YEAR_INFO = {
    2023: {"range": "$16.5k-$44.7k", "change": "+158%", "regime": "Strong uptrend", "atr_pct": 0.28},
    2024: {"range": "$38.6k-$108.4k", "change": "+120%", "regime": "Uptrend+vol", "atr_pct": 0.37},
    2025: {"range": "$74.5k-$126.2k", "change": "-7%", "regime": "Choppy", "atr_pct": 0.29},
    2026: {"range": "$57.8k-$97.9k", "change": "-11%", "regime": "Bearish", "atr_pct": 0.30},
}


def load_window(tf):
    df = load_btc_df(tf, SYMBOL)
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({"date": date, "ts": int(row.ts), "open": float(row.open),
                        "high": float(row.high), "low": float(row.low), "close": float(row.close),
                        "volume": 0, "oi": 0})
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high),
                               low=float(row.low), close=float(row.close)))
    return candles, flow


def run_one(chop, sl_buf, c1h, sw1h, c15, sw15, fine):
    result = simulate_htf_ltf_streak_halt(
        c1h, sw1h, c15, sw15, fine_ltf=fine,
        sl_buf_atr=sl_buf, ext_stop_r=FIXED["ext_stop_r"],
        mode=FIXED["mode"], chop_thresh=chop,
        cooldown_bars=FIXED["cooldown_bars"],
        max_consecutive_losses=FIXED["max_consecutive_losses"],
        htf_rr=FIXED["htf_rr"])
    return result["ltf_trades"]


def filter_by_year(trades, year):
    return [t for t in trades if t.get("entry_date", "")[:4] == str(year)]


def calc_stats(trades):
    rs = [t["r_multiple"] for t in trades]
    n = len(rs)
    if n == 0:
        return {"n": 0, "r": 0, "wr": 0, "pf": 0, "avg": 0, "net": 0, "cost": 0, "avg_net": 0}
    tot = sum(rs)
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    wr = 100 * len(wins) / n
    pf = sum(wins) / abs(sum(losses)) if losses else float("inf")
    avg = tot / n
    cost = 0.0
    for t in trades:
        entry_px = abs(float(t.get("entry_price", 0)))
        sl_px = abs(float(t.get("sl", 0)))
        risk = abs(entry_px - sl_px)
        if risk > 0:
            cost += (entry_px * FEE_RATE * 2 + entry_px * (ENTRY_SLIP + EXIT_SLIP)) / risk
    net = tot - cost
    return {"n": n, "r": tot, "wr": wr, "pf": pf, "avg": avg, "net": net, "cost": cost, "avg_net": net / n}


def print_heatmap(results, key, fmt="+.1f", marker=None):
    col_w = 8
    print(f"{'chop / slbuf':>12}" + "".join(f"{s:>{col_w}.2f}" for s in SL_BUFS))
    print("-" * 100)
    for chop in CHOPS:
        row = f"{chop:>12.1f}"
        for sl_buf in SL_BUFS:
            r = next((x for x in results if x["chop"] == chop and x["sl_buf"] == sl_buf), None)
            if r is None:
                val = "n/a"
            else:
                val = f"{r[key]:{fmt}}"
                if marker and r["chop"] == marker[0] and r["sl_buf"] == marker[1]:
                    val += "*"
            row += f"{val:>{col_w}}"
        print(row)


def main():
    print("=" * 110)
    print("PER-YEAR ENGINE SWEEP: chop_thresh x sl_buf_atr — BYBIT PERP")
    print("=" * 110)
    print(f"  Fixed: htf_rr={FIXED['htf_rr']}, ext_stop={FIXED['ext_stop_r']}, cd={FIXED['cooldown_bars']}, halt={FIXED['max_consecutive_losses']}")
    print(f"  Grid: {len(CHOPS)}x{len(SL_BUFS)} = {len(CHOPS)*len(SL_BUFS)} combos x {len(YEARS)} years")
    print()

    t_load = time.time()
    c1h, f1h = load_window("1h")
    c15, f15 = load_window("15m")
    sw1h = _compute_swings(f1h, "continuous", min_bars=20)
    sw15 = _compute_swings(f15, "continuous", min_bars=50)
    t0 = min(c1h[0]["ts"], c15[0]["ts"])
    t1 = max(c1h[-1]["ts"], c15[-1]["ts"])
    fine = _load_fine_1m(t0, t1, symbol=SYMBOL)
    print(f"  Data loaded in {time.time()-t_load:.1f}s: {len(c1h)} 1h, {len(c15)} 15m, {len(fine)} 1m")
    print()

    # Run full grid once
    print("  Running full grid... ", end="", flush=True)
    t_grid = time.time()
    all_trades = {}
    total = len(CHOPS) * len(SL_BUFS)
    done = 0
    for chop in CHOPS:
        for sl_buf in SL_BUFS:
            done += 1
            trades = run_one(chop, sl_buf, c1h, sw1h, c15, sw15, fine)
            all_trades[(chop, sl_buf)] = trades
            sys.stdout.write(f"\r  Running full grid... [{done}/{total}]")
            sys.stdout.flush()
    print(f" done in {time.time()-t_grid:.1f}s")
    print()

    year_best = {}
    for year in YEARS:
        info = YEAR_INFO[year]
        print("=" * 110)
        print(f"  {year} | BTC {info['range']} ({info['change']}) | {info['regime']} | ATR% {info['atr_pct']}%")
        print("=" * 110)

        results = []
        for chop in CHOPS:
            for sl_buf in SL_BUFS:
                trades = all_trades[(chop, sl_buf)]
                year_trades = filter_by_year(trades, year)
                stats = calc_stats(year_trades)
                stats["chop"] = chop
                stats["sl_buf"] = sl_buf
                results.append(stats)

        print(f"\n  NET R ({year}):")
        print_heatmap(results, "net", "+.1f", marker=(58.0, 0.20))

        print(f"\n  TRADES ({year}):")
        print_heatmap(results, "n", "d", marker=(58.0, 0.20))

        print(f"\n  AVG NET R/TRADE ({year}):")
        print_heatmap(results, "avg_net", "+.2f", marker=(58.0, 0.20))

        print(f"\n  PROFIT FACTOR ({year}):")
        print_heatmap(results, "pf", ".2f", marker=(58.0, 0.20))

        sorted_net = sorted(results, key=lambda x: x["net"], reverse=True)
        base = next((r for r in results if r["chop"] == 58.0 and r["sl_buf"] == 0.20), None)

        print(f"\n  {year} TOP 5 BY NET R:")
        print(f"  {'Rank':>4} {'chop':>6} {'slbuf':>6} {'Trades':>7} {'GrossR':>8} {'Cost':>7} {'NetR':>8} {'PF':>6} {'AvgNet':>7}")
        print(f"  {'-'*75}")
        for i, r in enumerate(sorted_net[:5], 1):
            marker = " <--" if base and r["chop"] == 58.0 and r["sl_buf"] == 0.20 else ""
            print(f"  {i:>4} {r['chop']:>6.1f} {r['sl_buf']:>6.2f} {r['n']:>7} {r['r']:>+8.1f} {r['cost']:>-7.1f} {r['net']:>+8.1f} {r['pf']:>6.2f} {r['avg_net']:>+7.2f}{marker}")

        if base:
            delta = sorted_net[0]["net"] - base["net"]
            print(f"\n  Best vs baseline (58/0.20): {sorted_net[0]['chop']:.0f}/{sorted_net[0]['sl_buf']:.2f} -> {delta:+.1f}R")
        year_best[year] = {"best": sorted_net[0], "base": base}
        print()

    # Cross-year summary
    print("=" * 110)
    print("CROSS-YEAR SUMMARY: Do engine params need to change by regime?")
    print("=" * 110)
    print()
    print(f"  {'Year':>6} {'Regime':<16} {'Best Chop':>9} {'Best SlBuf':>10} {'NetR':>8} {'Baseline(58/0.20)':>18} {'NetR':>8} {'Gap':>6}")
    print(f"  {'-'*85}")
    for year in YEARS:
        info = YEAR_INFO[year]
        yb = year_best[year]
        b = yb["best"]
        base = yb["base"]
        gap = b["net"] - base["net"]
        print(f"  {year:>6} {info['regime']:<16} {b['chop']:>9.0f} {b['sl_buf']:>10.2f} {b['net']:>+8.1f} {base['chop']:>9.0f}/{base['sl_buf']:<6.2f} {base['net']:>+8.1f} {gap:>+6.1f}")

    # Check consistency
    best_chops = set(yb["best"]["chop"] for yb in year_best.values())
    best_slbufs = set(yb["best"]["sl_buf"] for yb in year_best.values())

    print()
    if len(best_chops) == 1 and len(best_slbufs) == 1:
        print(f"  CONSISTENT: Same best params across ALL years.")
        print(f"  -> Price/regime doesn't matter for engine params.")
    else:
        if len(best_chops) > 1:
            print(f"  chop_thresh VARIES: {sorted(best_chops)}")
        else:
            print(f"  chop_thresh CONSISTENT: {list(best_chops)[0]}")
        if len(best_slbufs) > 1:
            print(f"  sl_buf_atr VARIES: {sorted(best_slbufs)}")
        else:
            print(f"  sl_buf_atr CONSISTENT: {list(best_slbufs)[0]}")

    # Baseline vs best total
    total_base = sum(yb["base"]["net"] for yb in year_best.values())
    total_best = sum(yb["best"]["net"] for yb in year_best.values())
    print(f"\n  Total baseline (58/0.20): {total_base:+.1f}R")
    print(f"  Total best-per-year:      {total_best:+.1f}R")
    print(f"  Gap:                      {total_best - total_base:+.1f}R")
    print()


if __name__ == "__main__":
    main()
