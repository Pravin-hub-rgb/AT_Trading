"""Final comprehensive sweep: best mb + cd + persist + params."""
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

sw1h = _compute_swings(f1h, "continuous", min_bars=10)
sw15 = _compute_swings(f15, "continuous", min_bars=50)

print("PHASE 1: Persist x cd matrix (15m=50, 1h=10)")
print("=" * 95)
print(f"{'Persist':>8} {'cd':>4} {'Trades':>7} {'R':>9} {'WR':>6} {'PF':>6}")
print("-" * 95)

best_r = -999
best_combo = None

for p in [0, 1, 2, 3, 4, 5, 6, 7, 8, 10]:
    for cd in [0, 3, 5, 8, 10, 15]:
        tr = simulate_v18_experiments(c1h, sw1h, c15, sw15, fine,
            sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=58.0,
            cooldown_bars=cd, max_consecutive_losses=3,
            exp_multi_ltf=True, exp_multi_ltf_cd=cd,
            exp_regime_persist=p)["ltf_trades"]
        r = run_and_report(f"p{p}cd{cd}", tr)
        marker = ""
        if r["total_r"] > best_r:
            best_r = r["total_r"]
            best_combo = (p, cd)
        if p in [0, 3, 5, 7, 10] or r["total_r"] > 270:
            print(f"  {p:>5}   {cd:>3} {r['trades']:>7} {r['total_r']:>+9.1f} {r['wr']:>5.1f}% {r['pf']:>5.2f}")
    print()

print(f"BEST: persist={best_combo[0]} cd={best_combo[1]}  =>  {best_r:+.1f}R")

print()
print("PHASE 2: sl_buf sweep at best combo")
print("=" * 95)
p_best, cd_best = best_combo
for sl in [0.001, 0.005, 0.008, 0.01, 0.015, 0.02, 0.05]:
    tr = simulate_v18_experiments(c1h, sw1h, c15, sw15, fine,
        sl_buf_atr=sl, ext_stop_r=1.5, chop_thresh=58.0,
        cooldown_bars=cd_best, max_consecutive_losses=3,
        exp_multi_ltf=True, exp_multi_ltf_cd=cd_best,
        exp_regime_persist=p_best)["ltf_trades"]
    r = run_and_report(f"sl={sl}", tr)
    print(f"  sl={sl:.3f}  {r['trades']:>5}t  {r['total_r']:>+8.1f}R  WR {r['wr']:>5.1f}%  PF {r['pf']:>5.2f}")

print()
print("PHASE 3: Chop sweep at best combo + best sl")
print("=" * 95)
for ch in [50, 55, 58, 62, 65, 68, 70, 75]:
    tr = simulate_v18_experiments(c1h, sw1h, c15, sw15, fine,
        sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=ch,
        cooldown_bars=cd_best, max_consecutive_losses=3,
        exp_multi_ltf=True, exp_multi_ltf_cd=cd_best,
        exp_regime_persist=p_best)["ltf_trades"]
    r = run_and_report(f"ch={ch}", tr)
    print(f"  ch={ch:>3}  {r['trades']:>5}t  {r['total_r']:>+8.1f}R  WR {r['wr']:>5.1f}%  PF {r['pf']:>5.2f}")

print()
print("PHASE 4: ext_stop_r sweep at best combo + best sl + best chop")
print("=" * 95)
for es in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]:
    tr = simulate_v18_experiments(c1h, sw1h, c15, sw15, fine,
        sl_buf_atr=0.01, ext_stop_r=es, chop_thresh=58.0,
        cooldown_bars=cd_best, max_consecutive_losses=3,
        exp_multi_ltf=True, exp_multi_ltf_cd=cd_best,
        exp_regime_persist=p_best)["ltf_trades"]
    r = run_and_report(f"es={es}", tr)
    print(f"  es={es:.1f}  {r['trades']:>5}t  {r['total_r']:>+8.1f}R  WR {r['wr']:>5.1f}%  PF {r['pf']:>5.2f}")

print()
print("PHASE 5: max_consecutive_losses sweep")
print("=" * 95)
for mcl in [2, 3, 4, 5, 7, 10]:
    tr = simulate_v18_experiments(c1h, sw1h, c15, sw15, fine,
        sl_buf_atr=0.01, ext_stop_r=1.5, chop_thresh=58.0,
        cooldown_bars=cd_best, max_consecutive_losses=mcl,
        exp_multi_ltf=True, exp_multi_ltf_cd=cd_best,
        exp_regime_persist=p_best)["ltf_trades"]
    r = run_and_report(f"mcl={mcl}", tr)
    print(f"  mcl={mcl:>2}  {r['trades']:>5}t  {r['total_r']:>+8.1f}R  WR {r['wr']:>5.1f}%  PF {r['pf']:>5.2f}")
