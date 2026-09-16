"""Per-Year Sweep: htf_rr x ext_stop_r — does optimal params change by market regime?

Runs the 2D grid for each year separately (2023, 2024, 2025, 2026).
Swings computed on full dataset (engine needs full context), trades filtered by year.

Run: python live_stuff/sweep_per_year.py
"""
import sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.walker import FlowCandle

SYMBOL = "BTCUSDT_BYBIT"
BASE = {"sl_buf_atr": 0.20, "chop_thresh": 58.0, "cooldown_bars": 0,
        "max_consecutive_losses": 5, "mode": "b2_vs_flip_chop"}

HTF_RRS = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
EXT_RS = [1.0, 1.5, 2.0, 2.5, 3.0]

# Cost model
FEE_RATE = 0.055 / 100.0
ENTRY_SLIP = 0.005 / 100.0
EXIT_SLIP = 0.010 / 100.0

YEARS = [2023, 2024, 2025, 2026]

# BTC price context per year
YEAR_INFO = {
    2023: {"range": "$16.5k-$44.7k", "change": "+158%", "regime": "Strong uptrend", "atr_pct": 0.28},
    2024: {"range": "$38.6k-$108.4k", "change": "+120%", "regime": "Uptrend + high vol", "atr_pct": 0.37},
    2025: {"range": "$74.5k-$126.2k", "change": "-7%", "regime": "Choppy/range", "atr_pct": 0.29},
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


def run_one(htf_rr, ext_r, c1h, sw1h, c15, sw15, fine):
    result = simulate_htf_ltf_streak_halt(
        c1h, sw1h, c15, sw15, fine_ltf=fine,
        sl_buf_atr=BASE["sl_buf_atr"], ext_stop_r=ext_r,
        mode=BASE["mode"], chop_thresh=BASE["chop_thresh"],
        cooldown_bars=BASE["cooldown_bars"],
        max_consecutive_losses=BASE["max_consecutive_losses"],
        htf_rr=htf_rr)
    return result["ltf_trades"]


def filter_by_year(trades, year):
    """Filter trades to a specific year based on entry_date."""
    out = []
    for t in trades:
        ed = t.get("entry_date", "")
        if ed and ed[:4] == str(year):
            out.append(t)
    return out


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
    # Cost
    cost = 0.0
    for t in trades:
        entry_px = abs(float(t.get("entry_price", 0)))
        sl_px = abs(float(t.get("sl", 0)))
        risk = abs(entry_px - sl_px)
        if risk > 0:
            cost += (entry_px * FEE_RATE * 2 + entry_px * (ENTRY_SLIP + EXIT_SLIP)) / risk
    net = tot - cost
    return {"n": n, "r": tot, "wr": wr, "pf": pf, "avg": avg, "net": net, "cost": cost, "avg_net": net / n}


def print_heatmap(results, key, label, fmt="+.1f", marker_val=None):
    col_w = 8
    hdr_label = "htf_rr / ext"
    header = f"{hdr_label:>12}" + "".join(f"{e:>{col_w}.1f}" for e in EXT_RS)
    print(header)
    print("-" * 100)
    for htf_rr in HTF_RRS:
        row = f"{htf_rr:>12.1f}"
        for ext_r in EXT_RS:
            r = next((x for x in results if x["htf_rr"] == htf_rr and x["ext_r"] == ext_r), None)
            if r is None:
                val = "n/a"
            else:
                val = f"{r[key]:{fmt}}"
                if marker_val and r["htf_rr"] == marker_val[0] and r["ext_r"] == marker_val[1]:
                    val += "*"
            row += f"{val:>{col_w}}"
        print(row)


def main():
    print("=" * 110)
    print("PER-YEAR SWEEP: htf_rr x ext_stop_r — BYBIT PERP — v18 ENGINE")
    print("=" * 110)
    print(f"  Params: chop={BASE['chop_thresh']}, cd={BASE['cooldown_bars']}, slbuf={BASE['sl_buf_atr']}, halt={BASE['max_consecutive_losses']}")
    print(f"  Grid: {len(HTF_RRS)}x{len(EXT_RS)} = {len(HTF_RRS)*len(EXT_RS)} combos x {len(YEARS)} years")
    print()

    # Load full data once
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

    # Run full grid once, filter by year
    print("  Running full grid (30 combos)... ", end="", flush=True)
    t_grid = time.time()
    all_trades = {}  # (htf_rr, ext_r) -> trades list
    total = len(HTF_RRS) * len(EXT_RS)
    done = 0
    for htf_rr in HTF_RRS:
        for ext_r in EXT_RS:
            done += 1
            trades = run_one(htf_rr, ext_r, c1h, sw1h, c15, sw15, fine)
            all_trades[(htf_rr, ext_r)] = trades
            sys.stdout.write(f"\r  Running full grid... [{done}/{total}]")
            sys.stdout.flush()
    print(f" done in {time.time()-t_grid:.1f}s")
    print()

    # Per-year analysis
    year_best = {}
    for year in YEARS:
        info = YEAR_INFO[year]
        print("=" * 110)
        print(f"  {year} | BTC {info['range']} ({info['change']}) | {info['regime']} | ATR% {info['atr_pct']}%")
        print("=" * 110)

        # Compute stats for each combo filtered to this year
        results = []
        for htf_rr in HTF_RRS:
            for ext_r in EXT_RS:
                trades = all_trades[(htf_rr, ext_r)]
                year_trades = filter_by_year(trades, year)
                stats = calc_stats(year_trades)
                stats["htf_rr"] = htf_rr
                stats["ext_r"] = ext_r
                results.append(stats)

        # NET R heatmap
        print(f"\n  NET R ({year}):")
        print_heatmap(results, "net", "Net R", "+.1f", marker_val=(3.0, 1.5))

        # Trades heatmap
        print(f"\n  TRADES ({year}):")
        print_heatmap(results, "n", "Trades", "d", marker_val=(3.0, 1.5))

        # Avg Net R heatmap
        print(f"\n  AVG NET R/TRADE ({year}):")
        print_heatmap(results, "avg_net", "AvgNet", "+.2f", marker_val=(3.0, 1.5))

        # PF heatmap
        print(f"\n  PROFIT FACTOR ({year}):")
        print_heatmap(results, "pf", "PF", ".2f", marker_val=(3.0, 1.5))

        # Best combos for this year
        sorted_net = sorted(results, key=lambda x: x["net"], reverse=True)
        sorted_eff = sorted([r for r in results if r["n"] > 0], key=lambda x: x["avg_net"], reverse=True)
        base = next((r for r in results if r["htf_rr"] == 3.0 and r["ext_r"] == 1.5), None)

        print(f"\n  {year} TOP 5 BY NET R:")
        print(f"  {'Rank':>4} {'htf_rr':>7} {'ext_r':>7} {'Trades':>7} {'GrossR':>8} {'Cost':>7} {'NetR':>8} {'PF':>6} {'AvgNet':>7}")
        print(f"  {'-'*95}")
        for i, r in enumerate(sorted_net[:5], 1):
            marker = " <--" if base and r["htf_rr"] == 3.0 and r["ext_r"] == 1.5 else ""
            print(f"  {i:>4} {r['htf_rr']:>7.1f} {r['ext_r']:>7.1f} {r['n']:>7} {r['r']:>+8.1f} {r['cost']:>-7.1f} {r['net']:>+8.1f} {r['pf']:>6.2f} {r['avg_net']:>+7.2f}{marker}")

        if base:
            print(f"\n  Best vs baseline (3.0/1.5): {sorted_net[0]['htf_rr']:.1f}/{sorted_net[0]['ext_r']:.1f} -> {sorted_net[0]['net']-base['net']:+.1f}R")
        year_best[year] = {"best_net": sorted_net[0], "best_avg": sorted_eff[0] if sorted_eff else None, "base": base}
        print()

    # --- CROSS-YEAR SUMMARY ---
    print("=" * 110)
    print("CROSS-YEAR SUMMARY: Does optimal param change by regime?")
    print("=" * 110)
    print()
    print(f"  {'Year':>6} {'Regime':<20} {'Best NetR Combo':>16} {'NetR':>8} {'Best AvgR Combo':>16} {'AvgNet':>7} {'Baseline(3.0/1.5)':>16} {'NetR':>8}")
    print(f"  {'-'*105}")
    for year in YEARS:
        info = YEAR_INFO[year]
        yb = year_best[year]
        bn = yb["best_net"]
        ba = yb["best_avg"]
        base = yb["base"]
        print(f"  {year:>6} {info['regime']:<20} {bn['htf_rr']:>6.1f}/{bn['ext_r']:<6.1f} {bn['net']:>+8.1f}R {ba['htf_rr']:>6.1f}/{ba['ext_r']:<6.1f} {ba['avg_net']:>+7.2f} {base['htf_rr']:>6.1f}/{base['ext_r']:<6.1f} {base['net']:>+8.1f}R")

    # Check consistency
    best_combos = set()
    for year in YEARS:
        yb = year_best[year]
        best_combos.add((yb["best_net"]["htf_rr"], yb["best_net"]["ext_r"]))

    print()
    if len(best_combos) == 1:
        combo = list(best_combos)[0]
        print(f"  CONSISTENT: Same best combo ({combo[0]:.1f}/{combo[1]:.1f}) across ALL years.")
        print(f"  -> Price/regime doesn't matter. Fixed params work everywhere.")
    else:
        print(f"  VARIES: Best combo changes across years ({len(best_combos)} different combos):")
        for combo in sorted(best_combos):
            years_with = [y for y in YEARS if (year_best[y]["best_net"]["htf_rr"], year_best[y]["best_net"]["ext_r"]) == combo]
            print(f"    {combo[0]:.1f}/{combo[1]:.1f} -> best in {years_with}")

    # Baseline performance across years
    print()
    print("  BASELINE (3.0/1.5) across all years:")
    for year in YEARS:
        base = year_best[year]["base"]
        print(f"    {year}: {base['n']}t {base['r']:+.1f}R gross, {base['net']:+.1f}R net, PF {base['pf']:.2f}, avg {base['avg_net']:+.2f}R")
    print()


if __name__ == "__main__":
    main()
