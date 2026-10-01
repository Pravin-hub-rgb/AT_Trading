"""Smoke test: prove the REAL v18 engine runs inside backtest.

Uses the ACTUAL backend functions (compute_btc_swings, simulate_htf_ltf_streak_halt)
NOT a toy reimplementation.

Run: python backtest/tests/test_smoke.py
Pass criteria: 351 trades, +211.7R (+-0.5), all years positive.
(Bybit Perp with C14+C15 causal fixes + trail ratchet fix 2026-09-20 + pre-FS filter.
 Post-ratchet fine+58 anchor: 351t +211.6R gross — was +238.0 pre-fix; pin updated.)
FCFS: first tradeable mark per swing decides -- pass or fail, no second chances.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.walker import FlowCandle

SYMBOL = "BTCUSDT_BYBIT"
PARAMS = {"sl_buf_atr": 0.01, "chop_thresh": 58.0, "cooldown_bars": 10,
          "max_consecutive_losses": 3}


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


def main():
    c1h, f1h = load_window("1h")
    c15, f15 = load_window("15m")
    sw1h = _compute_swings(f1h, "continuous", min_bars=20)
    sw15 = _compute_swings(f15, "continuous", min_bars=50)
    t0 = min(c1h[0]["ts"], c15[0]["ts"])
    t1 = max(c1h[-1]["ts"], c15[-1]["ts"])
    fine = _load_fine_1m(t0, t1, symbol=SYMBOL)

    tr = simulate_htf_ltf_streak_halt(
        c1h, sw1h, c15, sw15, fine_ltf=fine,
        sl_buf_atr=PARAMS["sl_buf_atr"], ext_stop_r=1.5, mode="b2_vs_flip_chop",
        chop_thresh=PARAMS["chop_thresh"],
        cooldown_bars=PARAMS["cooldown_bars"],
        max_consecutive_losses=PARAMS["max_consecutive_losses"])["ltf_trades"]

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
    print("BACKBENCHER SMOKE TEST -- BYBIT PERP -- REAL v18 ENGINE")
    print("=" * 72)
    print(f"  trades: {n}  -> {'PASS' if n == 351 else 'FAIL'}")
    print(f"  total R: {tot:+.1f}  (|delta| = {abs(tot - 211.7):.2f})  -> {'PASS' if abs(tot - 211.7) < 0.5 else 'FAIL'}")
    print(f"  win rate: {wr:.1f}%  ({len(wins)}W/{len(losses)}L)")
    print(f"  PF: {pf:.2f}")
    for y, v in sorted(years.items()):
        print(f"  {y}: {v[0]}t {v[1]:+.1f}R")
    print(f"  all years positive: {'PASS' if allyes else 'FAIL'}")
    print("=" * 72)

    assert n == 351, f"Expected 351 trades, got {n}"
    assert abs(tot - 211.7) < 0.5, f"Expected +211.7R (post-ratchet fine+58), got {tot:+.1f}R"
    assert allyes, "Not all years positive"
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
