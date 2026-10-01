"""Per-Year Sweep: cooldown_bars x max_consecutive_losses — streak protection per regime.

Fixes htf_rr=3.0, ext_stop=1.5, chop=58, sl_buf=0.20. Sweeps cooldown and halt.
Run: python backtest/sweeps/sweep_cooldown_per_year.py
"""
import sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.walker import FlowCandle

SYMBOL = "BTCUSDT_BYBIT"
FIXED = {"htf_rr": 3.0, "ext_stop_r": 1.5, "chop_thresh": 58.0, "sl_buf_atr": 0.20, "mode": "b2_vs_flip_chop"}

COOLDOWNS = [0, 5, 10, 15, 20, 30]
HALTS = [3, 5, 7, 10, 15]

FEE_RATE = 0.055 / 100.0
ENTRY_SLIP = 0.005 / 100.0
EXIT_SLIP = 0.010 / 100.0

YEARS = [2023, 2024, 2025, 2026]
YEAR_INFO = {
    2023: {"range": "$16.5k-$44.7k", "change": "+158%", "regime": "Strong uptrend"},
    2024: {"range": "$38.6k-$108.4k", "change": "+120%", "regime": "Uptrend+vol"},
    2025: {"range": "$74.5k-$126.2k", "change": "-7%", "regime": "Choppy"},
    2026: {"range": "$57.8k-$97.9k", "change": "-11%", "regime": "Bearish"},
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


def run_one(cd, halt, c1h, sw1h, c15, sw15, fine):
    result = simulate_htf_ltf_streak_halt(
        c1h, sw1h, c15, sw15, fine_ltf=fine,
        sl_buf_atr=FIXED["sl_buf_atr"], ext_stop_r=FIXED["ext_stop_r"],
        mode=FIXED["mode"], chop_thresh=FIXED["chop_thresh"],
        cooldown_bars=cd, max_consecutive_losses=halt, htf_rr=FIXED["htf_rr"])
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
    print(f"{'cd / halt':>12}" + "".join(f"{h:>{col_w}}" for h in HALTS))
    print("-" * 70)
    for cd in COOLDOWNS:
        row = f"{cd:>12}"
        for halt in HALTS:
            r = next((x for x in results if x["cd"] == cd and x["halt"] == halt), None)
            if r is None:
                val = "n/a"
            else:
                val = f"{r[key]:{fmt}}"
                if marker and r["cd"] == marker[0] and r["halt"] == marker[1]:
                    val += "*"
            row += f"{val:>{col_w}}"
        print(row)


def main():
    print("=" * 80)
    print("PER-YEAR COOLDOWN x HALT SWEEP — BYBIT PERP")
    print("=" * 80)
    print(f"  Fixed: htf_rr={FIXED['htf_rr']}, ext_stop={FIXED['ext_stop_r']}, chop={FIXED['chop_thresh']}, slbuf={FIXED['sl_buf_atr']}")
    print(f"  Grid: {len(COOLDOWNS)}x{len(HALTS)} = {len(COOLDOWNS)*len(HALTS)} combos x {len(YEARS)} years")
    print()

    t_load = time.time()
    c1h, f1h = load_window("1h")
    c15, f15 = load_window("15m")
    sw1h = _compute_swings(f1h, "continuous", min_bars=20)
    sw15 = _compute_swings(f15, "continuous", min_bars=50)
    t0 = min(c1h[0]["ts"], c15[0]["ts"])
    t1 = max(c1h[-1]["ts"], c15[-1]["ts"])
    fine = _load_fine_1m(t0, t1, symbol=SYMBOL)
    print(f"  Data loaded in {time.time()-t_load:.1f}s")
    print()

    print("  Running full grid... ", end="", flush=True)
    t_grid = time.time()
    all_trades = {}
    total = len(COOLDOWNS) * len(HALTS)
    done = 0
    for cd in COOLDOWNS:
        for halt in HALTS:
            done += 1
            all_trades[(cd, halt)] = run_one(cd, halt, c1h, sw1h, c15, sw15, fine)
            sys.stdout.write(f"\r  Running full grid... [{done}/{total}]")
            sys.stdout.flush()
    print(f" done in {time.time()-t_grid:.1f}s")
    print()

    year_best = {}
    for year in YEARS:
        info = YEAR_INFO[year]
        print(f"{'='*80}")
        print(f"  {year} | BTC {info['range']} ({info['change']}) | {info['regime']}")
        print(f"{'='*80}")

        results = []
        for cd in COOLDOWNS:
            for halt in HALTS:
                trades = filter_by_year(all_trades[(cd, halt)], year)
                stats = calc_stats(trades)
                stats["cd"] = cd
                stats["halt"] = halt
                results.append(stats)

        print(f"\n  NET R ({year}):")
        print_heatmap(results, "net", "+.1f", marker=(0, 5))

        print(f"\n  TRADES ({year}):")
        print_heatmap(results, "n", "d", marker=(0, 5))

        print(f"\n  AVG NET R/TRADE ({year}):")
        print_heatmap(results, "avg_net", "+.2f", marker=(0, 5))

        sorted_net = sorted(results, key=lambda x: x["net"], reverse=True)
        base = next((r for r in results if r["cd"] == 0 and r["halt"] == 5), None)

        print(f"\n  {year} TOP 5:")
        print(f"  {'Rank':>4} {'cd':>4} {'halt':>5} {'Trades':>7} {'NetR':>8} {'PF':>6} {'AvgNet':>7}")
        print(f"  {'-'*50}")
        for i, r in enumerate(sorted_net[:5], 1):
            marker = " <--" if base and r["cd"] == 0 and r["halt"] == 5 else ""
            print(f"  {i:>4} {r['cd']:>4} {r['halt']:>5} {r['n']:>7} {r['net']:>+8.1f} {r['pf']:>6.2f} {r['avg_net']:>+7.2f}{marker}")

        if base:
            gap = sorted_net[0]["net"] - base["net"]
            print(f"\n  Best vs baseline (cd=0/halt=5): {sorted_net[0]['cd']}/{sorted_net[0]['halt']} -> {gap:+.1f}R")
        year_best[year] = {"best": sorted_net[0], "base": base}
        print()

    # Summary
    print("=" * 80)
    print("CROSS-YEAR SUMMARY: Do cooldown/halt need to change by regime?")
    print("=" * 80)
    print()
    print(f"  {'Year':>6} {'Regime':<16} {'Best Cd':>7} {'Best Halt':>9} {'NetR':>8} {'Baseline(0/5)':>14} {'NetR':>8} {'Gap':>6}")
    print(f"  {'-'*75}")
    for year in YEARS:
        info = YEAR_INFO[year]
        yb = year_best[year]
        b = yb["best"]
        base = yb["base"]
        gap = b["net"] - base["net"]
        print(f"  {year:>6} {info['regime']:<16} {b['cd']:>7} {b['halt']:>9} {b['net']:>+8.1f} {'0/5':>14} {base['net']:>+8.1f} {gap:>+6.1f}")

    best_cds = set(yb["best"]["cd"] for yb in year_best.values())
    best_halts = set(yb["best"]["halt"] for yb in year_best.values())
    print()
    if len(best_cds) == 1 and len(best_halts) == 1:
        print(f"  CONSISTENT: Same best cooldown/halt across ALL years.")
    else:
        if len(best_cds) > 1:
            print(f"  cooldown VARIES: {sorted(best_cds)}")
        else:
            print(f"  cooldown CONSISTENT: {list(best_cds)[0]}")
        if len(best_halts) > 1:
            print(f"  halt VARIES: {sorted(best_halts)}")
        else:
            print(f"  halt CONSISTENT: {list(best_halts)[0]}")

    total_base = sum(yb["base"]["net"] for yb in year_best.values())
    total_best = sum(yb["best"]["net"] for yb in year_best.values())
    print(f"\n  Total baseline (cd=0/halt=5): {total_base:+.1f}R")
    print(f"  Total best-per-year:          {total_best:+.1f}R")
    print(f"  Gap:                          {total_best - total_base:+.1f}R")
    print()


if __name__ == "__main__":
    main()
