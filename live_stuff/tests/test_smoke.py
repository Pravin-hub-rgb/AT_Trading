"""Smoke test: prove the REAL v18 engine runs inside live_stuff.

Copies test_cat_f.py recipe verbatim but lives in live_stuff/tests/.
Uses the ACTUAL backend functions (compute_btc_swings, simulate_htf_ltf_streak_halt)
NOT a toy reimplementation.

Run: python live_stuff/tests/test_smoke.py
Pass criteria: 313 trades, +289.9R (+-0.2), all years positive.
(BTC Spot with pre-FS filter applied)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.walker import FlowCandle


def load_window(tf):
    df = load_btc_df(tf)
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({"date": date, "ts": int(row.ts), "open": float(row.open),
                        "high": float(row.high), "low": float(row.low), "close": float(row.close),
                        "volume": 0, "oi": 0})
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high),
                               low=float(row.low), close=float(row.close)))
    return candles, flow


def main():
    c1h, f1h = load_window("1h")
    c15, f15 = load_window("15m")
    sw1h = _compute_swings(f1h, "continuous", min_bars=20)
    sw15 = _compute_swings(f15, "continuous", min_bars=50)
    t0 = min(c1h[0]["ts"], c15[0]["ts"])
    t1 = max(c1h[-1]["ts"], c15[-1]["ts"])
    fine = _load_fine_1m(t0, t1)

    tr = simulate_htf_ltf_streak_halt(
        c1h, sw1h, c15, sw15, fine_ltf=fine,
        sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
        cooldown_bars=20, max_consecutive_losses=5)["ltf_trades"]

    rs = [t["r_multiple"] for t in tr]
    n = len(tr)
    tot = sum(rs)
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    wr = 100 * len(wins) / n
    pf = sum(wins) / abs(sum(losses)) if losses else float("inf")

    years = {}
    for t in tr:
        y = t["entry_date"][:4]
        years.setdefault(y, [0, 0.0])
        years[y][0] += 1
        years[y][1] += t["r_multiple"]

    allyes = all(v[1] > 0 for v in years.values())

    print("=" * 72)
    print("BACKBENCHER SMOKE TEST -- REAL v18 ENGINE")
    print("=" * 72)
    print(f"  trades: {n}  -> {'PASS' if n == 313 else 'FAIL'}")
    print(f"  total R: {tot:+.1f}  (|delta| = {abs(tot - 289.9):.2f})  -> {'PASS' if abs(tot - 289.9) < 0.2 else 'FAIL'}")
    print(f"  win rate: {wr:.1f}%  ({len(wins)}W/{len(losses)}L)")
    print(f"  PF: {pf:.2f}")
    for y, v in sorted(years.items()):
        print(f"  {y}: {v[0]}t {v[1]:+.1f}R")
    print(f"  all years positive: {'PASS' if allyes else 'FAIL'}")
    print("=" * 72)

    assert n == 313, f"Expected 313 trades, got {n}"
    assert abs(tot - 289.9) < 0.2, f"Expected +289.9R, got {tot:+.1f}R"
    assert allyes, "Not all years positive"
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
