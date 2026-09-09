import sys, bisect
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.walker import FlowCandle
from collections import Counter

def load_window(tf):
    df = load_btc_df(tf)
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({"date": date, "ts": int(row.ts), "open": float(row.open), "high": float(row.high), "low": float(row.low), "close": float(row.close), "volume": 0, "oi": 0})
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high), low=float(row.low), close=float(row.close)))
    return candles, flow

c1h, f1h = load_window("1h")
c15, f15 = load_window("15m")
sw1h = _compute_swings(f1h, "continuous", min_bars=20)
sw15 = _compute_swings(f15, "continuous", min_bars=50)
t0 = min(c1h[0]["ts"], c15[0]["ts"])
t1 = max(c1h[-1]["ts"], c15[-1]["ts"])
fine = _load_fine_1m(t0, t1)
fine_by_ts={int(c["ts"]):c for c in fine}

tr = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=fine,
    sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
    cooldown_bars=20, max_consecutive_losses=5)["ltf_trades"]
rs=[t["r_multiple"] for t in tr]

print("="*72)
print("D1: EXIT AT SL — LOSERS NEVER LOSE MORE THAN -1R")
sl_exit_bad=[t for t in tr if t["outcome"]=="sl" and abs(t["exit_price"]-t["sl"])>0.011]
beyond=[t for t in tr if t["r_multiple"]<-1.001]
print(f"  sl-exits not at initial SL: {len(sl_exit_bad)} / 112")
print(f"  trades worse than -1R: {len(beyond)}  (worst: {min(rs):.3f}R)")
print(f"  -> {'PASS' if not sl_exit_bad and not beyond else 'FAIL'}")

print()
print("="*72)
print("D2: WINNERS EXIT VIA MB50 TRAIL (amended — 3R target is HTF-side only)")
oc=Counter(t["outcome"] for t in tr)
winners=[t for t in tr if t["r_multiple"]>0]
win_bad=[t for t in winners if t["outcome"]!="trail"]
win_dir_bad=[t for t in winners if (t["dir"]=="long" and t["exit_price"]<=t["entry_price"]) or (t["dir"]=="short" and t["exit_price"]>=t["entry_price"])]
print(f"  outcome set: {dict(oc)}  (target exits: {oc.get('target',0)} — HTF-only, correct)")
print(f"  winners: {len(winners)}  not trail-exited: {len(win_bad)}  exited against direction: {len(win_dir_bad)}")
print(f"  -> {'PASS' if not win_bad and not win_dir_bad else 'FAIL'}")

print()
print("="*72)
print("D3: NO OPEN TRADES")
opens=[t for t in tr if t["outcome"]=="open"]
print(f"  open trades: {len(opens)} / {len(tr)}  -> {'PASS' if not opens else 'FAIL'}")

print()
print("="*72)
print("D4: EXIT TIMESTAMP AFTER ENTRY")
bad4=[t for t in tr if int(t["exit_ts"])<=int(t["entry_ts"])]
print(f"  exit_ts <= entry_ts: {len(bad4)} / {len(tr)}  (min bars_held: {min(t['bars_held'] for t in tr)})  -> {'PASS' if not bad4 else 'FAIL'}")

print()
print("="*72)
print("D5: 1M PRECISION — EXIT PRICE IS A REAL 1M PRINT")
missing=0; outofrange=[]
for t in tr:
    c=fine_by_ts.get(int(t["exit_ts"]))
    if c is None: missing+=1; continue
    lo,hi=float(c["low"]),float(c["high"])
    if not (lo-1e-6 <= t["exit_price"] <= hi+1e-6): outofrange.append(t)
print(f"  exit_ts not found in 1m data: {missing}")
print(f"  exit_price outside 1m bar range: {len(outofrange)} / {len(tr)}  -> {'PASS' if missing==0 and not outofrange else 'FAIL'}")
print("="*72)
