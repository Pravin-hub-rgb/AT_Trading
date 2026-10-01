"""Min_bars sweep — full matrix output."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from test_experiments import load_window, simulate_v18_experiments, run_and_report
from src.btc.btc_routes import _compute_swings, _load_fine_1m

SYMBOL = "BTCUSDT_BYBIT"
def load_swing(tf):
    from src.btc.btc_config import load_btc_df
    from src.walker import FlowCandle
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

c1h, f1h = load_swing("1h")
c15, f15 = load_swing("15m")
fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                     max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=SYMBOL)

print("FULL MIN_BARS MATRIX: 15m x 1h")
print("All combos: 15m in [20,25,30,40,50,60,75,100] x 1h in [10,15,20,25,30]")
print("=" * 95)
print(f"{'15m':>5} {'1h':>5} {'Trades':>7} {'R':>9} {'WR':>6} {'PF':>6} {'Delta':>8}")
print("-" * 95)

best_r = -999
best_combo = None
results = []

for mb_15 in [20, 25, 30, 40, 50, 60, 75, 100]:
    for mb_1h in [10, 15, 20, 25, 30]:
        sw15x = _compute_swings(f15, "continuous", min_bars=mb_15)
        sw1hx = _compute_swings(f1h, "continuous", min_bars=mb_1h)
        tr = simulate_v18_experiments(c1h, sw1hx, c15, sw15x, fine,
            sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=58.0,
            cooldown_bars=10, max_consecutive_losses=3,
            exp_multi_ltf=True, exp_multi_ltf_cd=5,
            exp_regime_persist=5)["ltf_trades"]
        r = run_and_report(f"{mb_15}/{mb_1h}", tr)
        d = r["total_r"] - 238.0
        results.append((mb_15, mb_1h, r["trades"], r["total_r"], r["wr"], r["pf"], d))
        if r["total_r"] > best_r:
            best_r = r["total_r"]
            best_combo = (mb_15, mb_1h)

for mb_15, mb_1h, t, tr, wr, pf, d in results:
    marker = " <-- BEST" if (mb_15, mb_1h) == best_combo else ""
    marker += " <-- BASE" if mb_15 == 50 and mb_1h == 20 else ""
    print(f"{mb_15:>5} {mb_1h:>5} {t:>7} {tr:>+9.1f} {wr:>5.1f}% {pf:>5.2f} {d:>+7.1f}R{marker}")

print()
print(f"BEST: 15m={best_combo[0]} 1h={best_combo[1]}  =>  {best_r:+.1f}R")
