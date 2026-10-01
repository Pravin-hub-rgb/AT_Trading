"""Deep-dive: proper sweep with FIXED code."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from test_experiments import load_window, simulate_v18_experiments, run_and_report, PARAMS
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.walker import FlowCandle

SYMBOL = "BTCUSDT_BYBIT"

def load_window_swing(tf, symbol=SYMBOL):
    from src.btc.btc_config import load_btc_df
    df = load_btc_df(tf, symbol)
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({"date": date, "ts": int(row.ts), "open": float(row.open),
                        "high": float(row.high), "low": float(row.low), "close": float(row.close),
                        "volume": 0, "oi": 0})
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high),
                               low=float(row.low), close=float(row.close)))
    return candles, flow

c1h, f1h = load_window_swing("1h")
c15, f15 = load_window_swing("15m")
fine_ts_range = (min(c1h[0]["ts"], c15[0]["ts"]), max(c1h[-1]["ts"], c15[-1]["ts"]))
fine = _load_fine_1m(fine_ts_range[0], fine_ts_range[1], symbol=SYMBOL)

kw = dict(sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=58.0,
          cooldown_bars=10, max_consecutive_losses=3)

sw1h = _compute_swings(f1h, "continuous", min_bars=20)
sw15 = _compute_swings(f15, "continuous", min_bars=50)
base_tr = simulate_v18_experiments(c1h, sw1h, c15, sw15, fine, **kw)["ltf_trades"]
base = run_and_report("BASE", base_tr)

print("STEP 1: Multi-LTF cooldown sweep (exp_multi_ltf_cd)")
print("=" * 90)
print(f"BASE: {base['total_r']:+.1f}R  {base['trades']}t  WR {base['wr']:.1f}%  PF {base['pf']:.2f}")
print()
for cd in [0, 3, 5, 8, 10, 15, 20, 30, 50]:
    tr = simulate_v18_experiments(c1h, sw1h, c15, sw15, fine,
        sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=58.0,
        cooldown_bars=10, max_consecutive_losses=3,
        exp_multi_ltf=True, exp_multi_ltf_cd=cd)["ltf_trades"]
    r = run_and_report(f"cd={cd}", tr)
    d = r["total_r"] - base["total_r"]
    print(f"  cd={cd:2d}  {r['trades']:4d}t  {r['total_r']:+8.1f}R  "
          f"WR {r['wr']:5.1f}%  PF {r['pf']:5.2f}  ({d:+.1f}R)")

print()
print("STEP 2: Persist sweep (at best cd)")
print("=" * 90)
for p in [0, 1, 2, 3, 4, 5, 6, 7, 8, 10]:
    tr = simulate_v18_experiments(c1h, sw1h, c15, sw15, fine, **kw,
        exp_multi_ltf=True, exp_multi_ltf_cd=10,
        exp_regime_persist=p)["ltf_trades"]
    r = run_and_report(f"Persist={p}", tr)
    d = r["total_r"] - base["total_r"]
    print(f"  Persist={p:2d}  {r['trades']:4d}t  {r['total_r']:+8.1f}R  "
          f"WR {r['wr']:5.1f}%  PF {r['pf']:5.2f}  ({d:+.1f}R)")

print()
print("STEP 3: Min_bars sweep (15m and 1h)")
print("=" * 90)
print("Using multi-LTF + persist=5, cd=10 (best from steps 1-2)")
print()
for mb_15 in [30, 40, 50, 60, 75, 100]:
    for mb_1h in [15, 20, 25, 30]:
        sw15x = _compute_swings(f15, "continuous", min_bars=mb_15)
        sw1hx = _compute_swings(f1h, "continuous", min_bars=mb_1h)
        tr = simulate_v18_experiments(c1h, sw1hx, c15, sw15x, fine,
            sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=58.0,
            cooldown_bars=10, max_consecutive_losses=3,
            exp_multi_ltf=True, exp_multi_ltf_cd=10,
            exp_regime_persist=5)["ltf_trades"]
        r = run_and_report(f"1h={mb_1h} 15m={mb_15}", tr)
        if r["total_r"] > base["total_r"] or mb_15 == 50 and mb_1h == 20:
            d = r["total_r"] - base["total_r"]
            marker = " <-- BASELINE" if mb_15 == 50 and mb_1h == 20 else ""
            print(f"  1h={mb_1h:2d}  15m={mb_15:3d}  {r['trades']:4d}t  {r['total_r']:+8.1f}R  "
                  f"WR {r['wr']:5.1f}%  PF {r['pf']:5.2f}  ({d:+.1f}R){marker}")
