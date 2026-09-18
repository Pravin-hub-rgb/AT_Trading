"""Focused grid: chop=62-70 × halt=3-7 × sl=0.005-0.02 × cd=8-15"""
import sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.walker import FlowCandle

SYMBOL = "BTCUSDT_BYBIT"

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

def run_engine(c1h, sw1h, c15, sw15, fine, params):
    tr = simulate_htf_ltf_streak_halt(
        c1h, sw1h, c15, sw15, fine_ltf=fine,
        sl_buf_atr=params["sl_buf_atr"], ext_stop_r=1.5,
        mode="b2_vs_flip_chop",
        chop_thresh=params["chop_thresh"],
        cooldown_bars=params["cooldown_bars"],
        max_consecutive_losses=params["max_consecutive_losses"])["ltf_trades"]
    rs = [t["r_multiple"] for t in tr]
    n = len(rs)
    tot = sum(rs)
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    wr = 100 * len(wins) / n if n else 0
    pf = sum(wins) / abs(sum(losses)) if losses else float("inf")
    years = {}
    for t in tr:
        y = t["entry_date"][:4]
        years.setdefault(y, [0, 0.0])
        years[y][0] += 1
        years[y][1] += t["r_multiple"]
    allyes = all(v[1] > 0 for v in years.values())
    return n, tot, wr, pf, years, allyes

def main():
    c1h, f1h = load_window("1h")
    c15, f15 = load_window("15m")
    sw1h = _compute_swings(f1h, "continuous", min_bars=20)
    sw15 = _compute_swings(f15, "continuous", min_bars=50)
    t0 = min(c1h[0]["ts"], c15[0]["ts"])
    t1 = max(c1h[-1]["ts"], c15[-1]["ts"])
    fine = _load_fine_1m(t0, t1, symbol=SYMBOL)

    print("=" * 110)
    print("FOCUSED GRID SWEEP")
    print("=" * 110)

    chop_vals = [58, 60, 62, 65, 68, 70]
    halt_vals = [0, 3, 5, 7]
    sl_vals = [0.005, 0.01, 0.02]
    cd_vals = [0, 5, 10, 15]

    results = []
    total = len(chop_vals) * len(halt_vals) * len(sl_vals) * len(cd_vals)
    done = 0
    tstart = time.time()

    for ch in chop_vals:
        for ht in halt_vals:
            for sl in sl_vals:
                for cd in cd_vals:
                    p = {"sl_buf_atr": sl, "chop_thresh": ch,
                         "cooldown_bars": cd, "max_consecutive_losses": ht,
                         "ext_stop_r": 1.5}
                    n, tot, wr, pf, years, allyes = run_engine(c1h, sw1h, c15, sw15, fine, p)
                    results.append((tot, n, wr, pf, allyes, p, years))
                    done += 1
                    if done % 20 == 0:
                        elapsed = time.time() - tstart
                        eta = elapsed / done * (total - done)
                        print(f"  [{done}/{total}] {elapsed:.0f}s elapsed, ~{eta:.0f}s remaining...")

    elapsed = time.time() - tstart
    print(f"\n  Completed {total} combos in {elapsed:.1f}s\n")

    results.sort(key=lambda x: -x[0])

    print("=" * 110)
    print("  TOP 15 (by gross R)")
    print("=" * 110)
    for tot, n, wr, pf, allyes, p, years in results[:15]:
        flag = "OK" if allyes else "NEG"
        yr = " ".join(f"{y}:{v[1]:+.0f}" for y, v in sorted(years.items()))
        print(f"  {n:4d}t  {tot:+8.1f}R  WR {wr:5.1f}%  PF {pf:5.2f}  {flag}  {p}  [{yr}]")

    print()
    print("=" * 110)
    print("  TOP 15 by RISK-ADJUSTED (highest PF among >+220R)")
    print("=" * 110)
    profitable = [r for r in results if r[0] > 220]
    profitable.sort(key=lambda x: -x[3])  # sort by PF
    for tot, n, wr, pf, allyes, p, years in profitable[:15]:
        flag = "OK" if allyes else "NEG"
        print(f"  {n:4d}t  {tot:+8.1f}R  WR {wr:5.1f}%  PF {pf:5.2f}  {flag}  {p}")

    print()
    print("=" * 110)
    print("  BOTTOM 5")
    print("=" * 110)
    for tot, n, wr, pf, allyes, p, years in results[-5:]:
        flag = "OK" if allyes else "NEG"
        print(f"  {n:4d}t  {tot:+8.1f}R  WR {wr:5.1f}%  PF {pf:5.2f}  {flag}  {p}")

    # Stability check: group by top param combos and count occurrences
    print()
    print("=" * 110)
    print("  STABILITY ANALYSIS")
    print("=" * 110)
    top20 = results[:20]
    from collections import Counter
    chop_c = Counter(r[5]["chop_thresh"] for r in top20)
    halt_c = Counter(r[5]["max_consecutive_losses"] for r in top20)
    sl_c = Counter(r[5]["sl_buf_atr"] for r in top20)
    cd_c = Counter(r[5]["cooldown_bars"] for r in top20)
    print(f"  Top 20 chop distribution: {dict(chop_c.most_common())}")
    print(f"  Top 20 halt distribution: {dict(halt_c.most_common())}")
    print(f"  Top 20 sl_buf distribution: {dict(sl_c.most_common())}")
    print(f"  Top 20 cd distribution: {dict(cd_c.most_common())}")

    # Baseline comparison
    print()
    bl = {"sl_buf_atr": 0.01, "chop_thresh": 58.0, "cooldown_bars": 10,
          "max_consecutive_losses": 3, "ext_stop_r": 1.5}
    bl_match = [r for r in results if r[5] == bl]
    if bl_match:
        bl_r = bl_match[0]
        print(f"  BASELINE: {bl_r[1]}t / {bl_r[0]:+.1f}R / WR {bl_r[2]:.1f}% / PF {bl_r[3]:.2f}")
    best = results[0]
    print(f"  BEST:     {best[1]}t / {best[0]:+.1f}R / WR {best[2]:.1f}% / PF {best[3]:.2f}")
    print(f"  DELTA:    {best[1]-bl_match[0][1]:+d}t / {best[0]-bl_match[0][0]:+.1f}R")
    print(f"  BEST PARAMS: {best[5]}")

if __name__ == "__main__":
    main()
