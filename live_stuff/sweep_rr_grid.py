"""2D Sweep: htf_rr × ext_stop_r — the two R targets that control trade flow.

htf_rr:       when the 1h window closes (HTF trade target)
ext_stop_r:   when LTF entries are blocked (1h leg unrealized R gate)

Run: python live_stuff/sweep_rr_grid.py
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

# Cost model (Bybit taker + asymmetric slippage)
FEE_RATE = 0.055 / 100.0       # 0.055% per side
ENTRY_SLIP = 0.005 / 100.0     # 0.005% entry slippage
EXIT_SLIP = 0.010 / 100.0      # 0.010% exit slippage

HTF_RRS = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
EXT_RS = [1.0, 1.5, 2.0, 2.5, 3.0]


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
    ltf = result["ltf_trades"]
    rs = [t["r_multiple"] for t in ltf]
    n = len(ltf)
    tot = sum(rs)
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    wr = 100 * len(wins) / n if n else 0
    pf = sum(wins) / abs(sum(losses)) if losses else float("inf")
    avg = tot / n if n else 0

    # Cost model: fees + slippage per trade
    total_cost = 0.0
    for t in ltf:
        entry_px = abs(float(t.get("entry_price", 0)))
        sl_px = abs(float(t.get("sl", 0)))
        risk = abs(entry_px - sl_px)
        if risk > 0:
            fee_r = (entry_px * FEE_RATE + entry_px * FEE_RATE) / risk  # entry+exit fee
            slip_r = (entry_px * ENTRY_SLIP + entry_px * EXIT_SLIP) / risk
            total_cost += fee_r + slip_r
    net = tot - total_cost
    avg_cost = total_cost / n if n else 0
    avg_net = net / n if n else 0

    return {"htf_rr": htf_rr, "ext_r": ext_r, "n": n, "r": tot, "wr": wr, "pf": pf,
            "avg": avg, "cost": total_cost, "net": net, "avg_cost": avg_cost, "avg_net": avg_net}


def main():
    print("=" * 95)
    print("2D SWEEP: htf_rr × ext_stop_r — BYBIT PERP — v18 ENGINE")
    print("=" * 95)
    print(f"  Params: chop={BASE['chop_thresh']}, cd={BASE['cooldown_bars']}, slbuf={BASE['sl_buf_atr']}, halt={BASE['max_consecutive_losses']}")
    print(f"  htf_rr:    {HTF_RRS}")
    print(f"  ext_stop_r: {EXT_RS}")
    print(f"  Grid: {len(HTF_RRS)}×{len(EXT_RS)} = {len(HTF_RRS)*len(EXT_RS)} runs")
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

    results = []
    total = len(HTF_RRS) * len(EXT_RS)
    done = 0
    for htf_rr in HTF_RRS:
        for ext_r in EXT_RS:
            done += 1
            r = run_one(htf_rr, ext_r, c1h, sw1h, c15, sw15, fine)
            results.append(r)
            sys.stdout.write(f"\r  [{done}/{total}] htf_rr={htf_rr:.1f} ext_stop={ext_r:.1f} -> {r['n']}t {r['r']:+.1f}R PF={r['pf']:.2f}")
            sys.stdout.flush()
    print("\n")

    # --- TOTAL R HEATMAP ---
    print("=" * 100)
    print("GROSS R (higher = better)")
    print("=" * 100)
    col_w = 8
    hdr_label = "htf_rr / ext"
    header = f"{hdr_label:>12}" + "".join(f"{e:>{col_w}.1f}" for e in EXT_RS)
    print(header)
    print("-" * 100)
    for htf_rr in HTF_RRS:
        row = f"{htf_rr:>12.1f}"
        for ext_r in EXT_RS:
            r = next(x for x in results if x["htf_rr"] == htf_rr and x["ext_r"] == ext_r)
            val = f"{r['r']:+.1f}"
            if htf_rr == 3.0 and ext_r == 1.5:
                val += "*"
            row += f"{val:>{col_w}}"
        print(row)

    # --- NET R HEATMAP (after fees + slippage) ---
    print()
    print("=" * 100)
    print("NET R (after fees + slippage: 0.055%/side taker + 0.005% entry + 0.010% exit)")
    print("=" * 100)
    header = f"{hdr_label:>12}" + "".join(f"{e:>{col_w}.1f}" for e in EXT_RS)
    print(header)
    print("-" * 100)
    for htf_rr in HTF_RRS:
        row = f"{htf_rr:>12.1f}"
        for ext_r in EXT_RS:
            r = next(x for x in results if x["htf_rr"] == htf_rr and x["ext_r"] == ext_r)
            val = f"{r['net']:+.1f}"
            if htf_rr == 3.0 and ext_r == 1.5:
                val += "*"
            row += f"{val:>{col_w}}"
        print(row)

    # --- COST PER TRADE HEATMAP ---
    print()
    print("=" * 100)
    print("AVG COST PER TRADE (R)")
    print("=" * 100)
    header = f"{hdr_label:>12}" + "".join(f"{e:>{col_w}.1f}" for e in EXT_RS)
    print(header)
    print("-" * 100)
    for htf_rr in HTF_RRS:
        row = f"{htf_rr:>12.1f}"
        for ext_r in EXT_RS:
            r = next(x for x in results if x["htf_rr"] == htf_rr and x["ext_r"] == ext_r)
            val = f"{r['avg_cost']:.3f}"
            if htf_rr == 3.0 and ext_r == 1.5:
                val += "*"
            row += f"{val:>{col_w}}"
        print(row)

    # --- TRADES HEATMAP ---
    print()
    print("=" * 100)
    print("TRADE COUNT")
    print("=" * 100)
    header = f"{hdr_label:>12}" + "".join(f"{e:>{col_w}.1f}" for e in EXT_RS)
    print(header)
    print("-" * 100)
    for htf_rr in HTF_RRS:
        row = f"{htf_rr:>12.1f}"
        for ext_r in EXT_RS:
            r = next(x for x in results if x["htf_rr"] == htf_rr and x["ext_r"] == ext_r)
            val = f"{r['n']}"
            if htf_rr == 3.0 and ext_r == 1.5:
                val += "*"
            row += f"{val:>{col_w}}"
        print(row)

    # --- PF HEATMAP ---
    print()
    print("=" * 100)
    print("PROFIT FACTOR (higher = better)")
    print("=" * 100)
    header = f"{hdr_label:>12}" + "".join(f"{e:>{col_w}.1f}" for e in EXT_RS)
    print(header)
    print("-" * 100)
    for htf_rr in HTF_RRS:
        row = f"{htf_rr:>12.1f}"
        for ext_r in EXT_RS:
            r = next(x for x in results if x["htf_rr"] == htf_rr and x["ext_r"] == ext_r)
            val = f"{r['pf']:.2f}"
            if htf_rr == 3.0 and ext_r == 1.5:
                val += "*"
            row += f"{val:>{col_w}}"
        print(row)

    # --- AVG NET R HEATMAP ---
    print()
    print("=" * 100)
    print("AVG NET R PER TRADE (after costs)")
    print("=" * 100)
    header = f"{hdr_label:>12}" + "".join(f"{e:>{col_w}.1f}" for e in EXT_RS)
    print(header)
    print("-" * 100)
    for htf_rr in HTF_RRS:
        row = f"{htf_rr:>12.1f}"
        for ext_r in EXT_RS:
            r = next(x for x in results if x["htf_rr"] == htf_rr and x["ext_r"] == ext_r)
            val = f"{r['avg_net']:+.2f}"
            if htf_rr == 3.0 and ext_r == 1.5:
                val += "*"
            row += f"{val:>{col_w}}"
        print(row)

    # --- TOP 10 BY NET R ---
    print()
    print("=" * 100)
    print("TOP 10 BY NET R (after costs)")
    print("=" * 100)
    sorted_net = sorted(results, key=lambda x: x["net"], reverse=True)
    print(f"{'Rank':>4} {'htf_rr':>7} {'ext_r':>7} {'Trades':>7} {'GrossR':>8} {'Cost':>7} {'NetR':>8} {'PF':>6} {'AvgNet':>7}")
    print("-" * 100)
    for i, r in enumerate(sorted_net[:10], 1):
        marker = " <--" if r["htf_rr"] == 3.0 and r["ext_r"] == 1.5 else ""
        print(f"{i:>4} {r['htf_rr']:>7.1f} {r['ext_r']:>7.1f} {r['n']:>7} {r['r']:>+8.1f} {r['cost']:>-7.1f} {r['net']:>+8.1f} {r['pf']:>6.2f} {r['avg_net']:>+7.2f}{marker}")

    # --- TOP 10 BY NET R / TRADE (efficiency) ---
    print()
    print("=" * 100)
    print("TOP 10 BY NET R PER TRADE (efficiency)")
    print("=" * 100)
    sorted_eff = sorted(results, key=lambda x: x["avg_net"], reverse=True)
    print(f"{'Rank':>4} {'htf_rr':>7} {'ext_r':>7} {'Trades':>7} {'GrossR':>8} {'Cost':>7} {'NetR':>8} {'PF':>6} {'AvgNet':>7}")
    print("-" * 100)
    for i, r in enumerate(sorted_eff[:10], 1):
        marker = " <--" if r["htf_rr"] == 3.0 and r["ext_r"] == 1.5 else ""
        print(f"{i:>4} {r['htf_rr']:>7.1f} {r['ext_r']:>7.1f} {r['n']:>7} {r['r']:>+8.1f} {r['cost']:>-7.1f} {r['net']:>+8.1f} {r['pf']:>6.2f} {r['avg_net']:>+7.2f}{marker}")

    # --- TOP 10 BY PF ---
    print()
    print("=" * 100)
    print("TOP 10 BY PROFIT FACTOR")
    print("=" * 100)
    sorted_pf = sorted(results, key=lambda x: x["pf"], reverse=True)
    print(f"{'Rank':>4} {'htf_rr':>7} {'ext_r':>7} {'Trades':>7} {'GrossR':>8} {'Cost':>7} {'NetR':>8} {'PF':>6} {'AvgNet':>7}")
    print("-" * 100)
    for i, r in enumerate(sorted_pf[:10], 1):
        marker = " <--" if r["htf_rr"] == 3.0 and r["ext_r"] == 1.5 else ""
        print(f"{i:>4} {r['htf_rr']:>7.1f} {r['ext_r']:>7.1f} {r['n']:>7} {r['r']:>+8.1f} {r['cost']:>-7.1f} {r['net']:>+8.1f} {r['pf']:>6.2f} {r['avg_net']:>+7.2f}{marker}")

    # --- FEWEST TRADES WITH GOOD NET R ---
    print()
    print("=" * 100)
    print("FEWEST TRADES (net >=250R)")
    print("=" * 100)
    good = [r for r in results if r["net"] >= 250]
    sorted_n = sorted(good, key=lambda x: x["n"])
    print(f"{'Rank':>4} {'htf_rr':>7} {'ext_r':>7} {'Trades':>7} {'GrossR':>8} {'Cost':>7} {'NetR':>8} {'PF':>6} {'AvgNet':>7}")
    print("-" * 100)
    for i, r in enumerate(sorted_n[:10], 1):
        marker = " <--" if r["htf_rr"] == 3.0 and r["ext_r"] == 1.5 else ""
        print(f"{i:>4} {r['htf_rr']:>7.1f} {r['ext_r']:>7.1f} {r['n']:>7} {r['r']:>+8.1f} {r['cost']:>-7.1f} {r['net']:>+8.1f} {r['pf']:>6.2f} {r['avg_net']:>+7.2f}{marker}")

    # --- BASELINE COMPARISON ---
    base = next(x for x in results if x["htf_rr"] == 3.0 and x["ext_r"] == 1.5)
    print()
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"  Baseline: htf_rr=3.0 ext_stop=1.5 -> {base['n']}t gross {base['r']:+.1f}R  cost {base['cost']:.1f}R  NET {base['net']:+.1f}R  PF={base['pf']:.2f}")
    print()
    best_net = sorted_net[0]
    best_eff = sorted_eff[0]
    best_pf = sorted_pf[0]
    print(f"  Best NET R:    {best_net['htf_rr']:.1f}/{best_net['ext_r']:.1f} -> {best_net['n']}t NET {best_net['net']:+.1f}R ({best_net['net']-base['net']:+.1f}R vs baseline)")
    print(f"  Best Avg NET:  {best_eff['htf_rr']:.1f}/{best_eff['ext_r']:.1f} -> {best_eff['n']}t Avg {best_eff['avg_net']:+.2f}R/trade")
    print(f"  Best PF:       {best_pf['htf_rr']:.1f}/{best_pf['ext_r']:.1f} -> {best_pf['n']}t PF {best_pf['pf']:.2f} NET {best_pf['net']:+.1f}R")
    if sorted_n:
        print(f"  Fewest >=250R: {sorted_n[0]['htf_rr']:.1f}/{sorted_n[0]['ext_r']:.1f} -> {sorted_n[0]['n']}t NET {sorted_n[0]['net']:+.1f}R PF={sorted_n[0]['pf']:.2f}")
    print()


if __name__ == "__main__":
    main()
