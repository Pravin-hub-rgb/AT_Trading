"""Sweep: HTF (1h) rr_target — what R target closes the 1h window?

Tests rr_target from 1.0R to 4.0R on Bybit Perp data.
Everything else fixed: chop=58, cd=0, slbuf=0.20, ext_stop=1.5, max_loss=5.

Run: python live_stuff/sweep_htf_rr.py
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
        "max_consecutive_losses": 5, "ext_stop_r": 1.5, "mode": "b2_vs_flip_chop"}
RR_VALUES = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]


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


def run_one(rr_target, c1h, sw1h, c15, sw15, fine):
    t0 = time.time()
    result = simulate_htf_ltf_streak_halt(
        c1h, sw1h, c15, sw15, fine_ltf=fine,
        sl_buf_atr=BASE["sl_buf_atr"], ext_stop_r=BASE["ext_stop_r"],
        mode=BASE["mode"], chop_thresh=BASE["chop_thresh"],
        cooldown_bars=BASE["cooldown_bars"],
        max_consecutive_losses=BASE["max_consecutive_losses"],
        htf_rr=rr_target)
    ltf = result["ltf_trades"]
    htf = result.get("htf_trades", [])
    elapsed = time.time() - t0

    rs = [t["r_multiple"] for t in ltf]
    n = len(ltf)
    tot = sum(rs)
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    wr = 100 * len(wins) / n if n else 0
    pf = sum(wins) / abs(sum(losses)) if losses else float("inf")
    avg = tot / n if n else 0

    # Max drawdown in R
    peak = 0.0
    max_dd = 0.0
    cum = 0.0
    for r in rs:
        cum += r
        if cum > peak:
            peak = cum
        dd = peak - cum
        if dd > max_dd:
            max_dd = dd

    # Max consecutive losses
    max_run = 0
    run = 0
    for r in rs:
        if r <= 0:
            run += 1
            if run > max_run:
                max_run = run
        else:
            run = 0

    # Per-year breakdown
    years = {}
    for t in ltf:
        y = t["entry_date"][:4]
        years.setdefault(y, {"n": 0, "r": 0.0})
        years[y]["n"] += 1
        years[y]["r"] += t["r_multiple"]

    # HTF stats
    htf_n = len(htf)
    htf_rs = [t["r_multiple"] for t in htf if t.get("r_multiple") is not None]
    htf_tot = sum(htf_rs) if htf_rs else 0

    return {
        "rr": rr_target, "trades": n, "total_r": tot, "wr": wr, "pf": pf,
        "avg_r": avg, "max_dd": max_dd, "max_run": max_run,
        "htf_n": htf_n, "htf_r": htf_tot, "years": years, "time": elapsed,
    }


def main():
    print("=" * 90)
    print("HTF rr_target SWEEP — BYBIT PERP — v18 ENGINE")
    print("=" * 90)
    print(f"  Params: {BASE}")
    print(f"  Sweeping htf_rr: {RR_VALUES}")
    print(f"  Loading data...")

    c1h, f1h = load_window("1h")
    c15, f15 = load_window("15m")
    sw1h = _compute_swings(f1h, "continuous", min_bars=20)
    sw15 = _compute_swings(f15, "continuous", min_bars=50)
    t0 = min(c1h[0]["ts"], c15[0]["ts"])
    t1 = max(c1h[-1]["ts"], c15[-1]["ts"])
    fine = _load_fine_1m(t0, t1, symbol=SYMBOL)
    print(f"  Data loaded: {len(c1h)} 1h, {len(c15)} 15m, {len(sw1h)} sw1h, {len(sw15)} sw15, {len(fine)} 1m fine")
    print()

    results = []
    for rr in RR_VALUES:
        r = run_one(rr, c1h, sw1h, c15, sw15, fine)
        results.append(r)

    # --- Results table ---
    print("=" * 90)
    print(f"{'rr':>4} {'Trades':>7} {'TotalR':>8} {'Win%':>6} {'PF':>6} {'AvgR':>6} {'MaxDD':>7} {'MaxRun':>7} {'HTF_n':>6} {'HTF_R':>8} {'Time':>6}")
    print("-" * 90)
    for r in results:
        marker = " <--" if r["rr"] == 3.0 else ""
        print(f"{r['rr']:>4.1f} {r['trades']:>7} {r['total_r']:>+8.1f} {r['wr']:>5.1f}% {r['pf']:>6.2f} {r['avg_r']:>+6.2f} {r['max_dd']:>7.1f} {r['max_run']:>7} {r['htf_n']:>6} {r['htf_r']:>+8.1f} {r['time']:>5.1f}s{marker}")

    # --- Find best ---
    best_r = max(results, key=lambda x: x["total_r"])
    best_pf = max(results, key=lambda x: x["pf"])
    best_avg = max(results, key=lambda x: x["avg_r"])
    least_dd = min(results, key=lambda x: x["max_dd"])

    print()
    print("=" * 90)
    print("SUMMARY")
    print("=" * 90)
    print(f"  Best Total R:  rr={best_r['rr']:.1f}  ->  {best_r['total_r']:+.1f}R  ({best_r['trades']}t, PF {best_r['pf']:.2f})")
    print(f"  Best PF:       rr={best_pf['rr']:.1f}  ->  PF {best_pf['pf']:.2f}  ({best_pf['total_r']:+.1f}R, {best_pf['trades']}t)")
    print(f"  Best Avg R:    rr={best_avg['rr']:.1f}  ->  {best_avg['avg_r']:+.2f}R/trade")
    print(f"  Least Max DD:  rr={least_dd['rr']:.1f}  ->  {least_dd['max_dd']:.1f}R max drawdown")

    # --- Baseline comparison (rr=3.0) ---
    base = next(r for r in results if r["rr"] == 3.0)
    print()
    print("  vs Baseline (rr=3.0):")
    for r in results:
        delta = r["total_r"] - base["total_r"]
        tr_delta = r["trades"] - base["trades"]
        print(f"    rr={r['rr']:.1f}: {delta:+.1f}R ({tr_delta:+d} trades)")

    # --- Per-year for best ---
    print()
    print(f"  Per-year breakdown (best rr={best_r['rr']:.1f}):")
    for y, v in sorted(best_r["years"].items()):
        print(f"    {y}: {v['n']}t {v['r']:+.1f}R")

    print()
    print("=" * 90)


if __name__ == "__main__":
    main()
