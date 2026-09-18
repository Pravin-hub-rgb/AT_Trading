"""Run the TRUE optimal combo: all best params chained."""
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

print("CHAINING: persist=2, cd=0, chop=55")
print("Then sweeping sl_buf, ext_stop_r, mcl on TOP of those")
print("=" * 95)

# Phase A: sl_buf at persist=2, cd=0, chop=55
print("\nPHASE A: sl_buf at persist=2, cd=0, chop=55, es=1.5, mcl=3")
print("-" * 95)
best_a_r, best_a_sl = -999, 0.01
for sl in [0.001, 0.003, 0.005, 0.008, 0.01, 0.015, 0.02, 0.05]:
    tr = simulate_v18_experiments(c1h, sw1h, c15, sw15, fine,
        sl_buf_atr=sl, ext_stop_r=1.5, chop_thresh=55.0,
        cooldown_bars=0, max_consecutive_losses=3,
        exp_multi_ltf=True, exp_multi_ltf_cd=0,
        exp_regime_persist=2)["ltf_trades"]
    r = run_and_report(f"sl={sl}", tr)
    print(f"  sl={sl:.3f}  {r['trades']:>5}t  {r['total_r']:>+8.1f}R  WR {r['wr']:>5.1f}%  PF {r['pf']:>5.2f}")
    if r["total_r"] > best_a_r:
        best_a_r, best_a_sl = r["total_r"], sl

print(f"  Best sl_buf: {best_a_sl}")

# Phase B: ext_stop_r at persist=2, cd=0, chop=55, best sl
print(f"\nPHASE B: ext_stop_r at persist=2, cd=0, chop=55, sl={best_a_sl}")
print("-" * 95)
best_b_r, best_b_es = -999, 1.5
for es in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]:
    tr = simulate_v18_experiments(c1h, sw1h, c15, sw15, fine,
        sl_buf_atr=best_a_sl, ext_stop_r=es, chop_thresh=55.0,
        cooldown_bars=0, max_consecutive_losses=3,
        exp_multi_ltf=True, exp_multi_ltf_cd=0,
        exp_regime_persist=2)["ltf_trades"]
    r = run_and_report(f"es={es}", tr)
    print(f"  es={es:.1f}  {r['trades']:>5}t  {r['total_r']:>+8.1f}R  WR {r['wr']:>5.1f}%  PF {r['pf']:>5.2f}")
    if r["total_r"] > best_b_r:
        best_b_r, best_b_es = r["total_r"], es

print(f"  Best ext_stop_r: {best_b_es}")

# Phase C: mcl at persist=2, cd=0, chop=55, best sl, best es
print(f"\nPHASE C: max_consecutive_losses at persist=2, cd=0, chop=55, sl={best_a_sl}, es={best_b_es}")
print("-" * 95)
best_c_r, best_c_mcl = -999, 3
for mcl in [1, 2, 3, 4, 5, 7, 10]:
    tr = simulate_v18_experiments(c1h, sw1h, c15, sw15, fine,
        sl_buf_atr=best_a_sl, ext_stop_r=best_b_es, chop_thresh=55.0,
        cooldown_bars=0, max_consecutive_losses=mcl,
        exp_multi_ltf=True, exp_multi_ltf_cd=0,
        exp_regime_persist=2)["ltf_trades"]
    r = run_and_report(f"mcl={mcl}", tr)
    print(f"  mcl={mcl:>2}  {r['trades']:>5}t  {r['total_r']:>+8.1f}R  WR {r['wr']:>5.1f}%  PF {r['pf']:>5.2f}")
    if r["total_r"] > best_c_r:
        best_c_r, best_c_mcl = r["total_r"], mcl

print(f"  Best mcl: {best_c_mcl}")

# FINAL: Everything chained
print(f"\n{'=' * 95}")
print("FINAL OPTIMAL COMBO:")
print(f"  15m min_bars=50, 1h min_bars=10")
print(f"  persist=2, cd=0, chop=55, sl={best_a_sl}, es={best_b_es}, mcl={best_c_mcl}")
print("-" * 95)
tr = simulate_v18_experiments(c1h, sw1h, c15, sw15, fine,
    sl_buf_atr=best_a_sl, ext_stop_r=best_b_es, chop_thresh=55.0,
    cooldown_bars=0, max_consecutive_losses=best_c_mcl,
    exp_multi_ltf=True, exp_multi_ltf_cd=0,
    exp_regime_persist=2)["ltf_trades"]
r = run_and_report("FINAL", tr)
print(f"  {r['trades']}t  {r['total_r']:+.1f}R  WR {r['wr']:.1f}%  PF {r['pf']:.2f}")
print(f"  vs baseline: {r['total_r'] - 238.0:+.1f}R")

# Also test cd=5 for more conservative option
print(f"\nCONSERVATIVE (cd=5, same other params):")
print("-" * 95)
tr2 = simulate_v18_experiments(c1h, sw1h, c15, sw15, fine,
    sl_buf_atr=best_a_sl, ext_stop_r=best_b_es, chop_thresh=55.0,
    cooldown_bars=5, max_consecutive_losses=best_c_mcl,
    exp_multi_ltf=True, exp_multi_ltf_cd=5,
    exp_regime_persist=2)["ltf_trades"]
r2 = run_and_report("CONSERVATIVE", tr2)
print(f"  {r2['trades']}t  {r2['total_r']:+.1f}R  WR {r2['wr']:.1f}%  PF {r2['pf']:.2f}")
print(f"  vs baseline: {r2['total_r'] - 238.0:+.1f}R")

# Also test persist=5 for more conservative option
print(f"\nPERSIST-5 (cd=0, persist=5, same other params):")
print("-" * 95)
tr3 = simulate_v18_experiments(c1h, sw1h, c15, sw15, fine,
    sl_buf_atr=best_a_sl, ext_stop_r=best_b_es, chop_thresh=55.0,
    cooldown_bars=0, max_consecutive_losses=best_c_mcl,
    exp_multi_ltf=True, exp_multi_ltf_cd=0,
    exp_regime_persist=5)["ltf_trades"]
r3 = run_and_report("PERSIST5", tr3)
print(f"  {r3['trades']}t  {r3['total_r']:+.1f}R  WR {r3['wr']:.1f}%  PF {r3['pf']:.2f}")
print(f"  vs baseline: {r3['total_r'] - 238.0:+.1f}R")
