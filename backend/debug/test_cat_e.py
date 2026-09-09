import sys, bisect
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.btc.btc_engine import _collect_signals
from src.walker import FlowCandle

# allow loading a wider window than trades need, for the sanity bounds
c1h, f1h = load_window = None, None

def load_window(tf):
    df = load_btc_df(tf)
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({"date": date, "ts": int(row.ts), "open": float(row.open), "high": float(row.high), "low": float(row.low), "close": float(row.close), "volume": 0, "oi": 0})
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high), low=float(row.low), close=float(row.close)))
    return candles, flow

from src.btc.btc_config import load_btc_df
c1h, f1h = load_window("1h")
c15, f15 = load_window("15m")
sw1h = _compute_swings(f1h, "continuous", min_bars=20)
sw15 = _compute_swings(f15, "continuous", min_bars=50)
t0 = min(c1h[0]["ts"], c15[0]["ts"])
t1 = max(c1h[-1]["ts"], c15[-1]["ts"])
fine = _load_fine_1m(t0, t1)

tr = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=fine,
    sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
    cooldown_bars=20, max_consecutive_losses=5)["ltf_trades"]

print("="*72)
print("E1: NO DUPLICATE TRADES (same entry timestamp)")
dups=len(tr)-len({t["entry_ts"] for t in tr})
print(f"  duplicate entry timestamps: {dups} / {len(tr)}  -> {'PASS' if dups==0 else 'FAIL'}")

print()
print("="*72)
print("E2: NO OVERLAPPING TRADES (next entry after previous exit)")
viol=0
for a,b in zip(tr,tr[1:]):
    if b["entry_idx"] <= a["exit_idx"]: viol+=1
print(f"  overlapping pairs: {viol} / {len(tr)-1}  -> {'PASS' if viol==0 else 'FAIL'}")

print()
print("="*72)
print("E3: MAX STREAK <= 5 CONSECUTIVE LOSSES")
mx=cl=0
for t in tr:
    if t["r_multiple"]<=0: cl+=1; mx=max(mx,cl)
    else: cl=0
print(f"  max consecutive losses: {mx} (<=5)  -> {'PASS' if mx<=5 else 'FAIL'}")

print()
print("="*72)
print("E4: FIRST SWING SKIP (skip_first=True -> first swing is bias-only)")
sigs_all=_collect_signals(sw15, "decisive", skip_first=False, selection="stream", candles=c15)
first_swing=min(s["swing_no"] for s in sigs_all)
traded_swings={t["swing_no"] for t in tr}
bad=traded_swings & {first_swing}
print(f"  first LTF swing_no: {first_swing}  |  min traded swing_no: {min(traded_swings)}")
print(f"  trades on the first swing: {len(bad)}  -> {'PASS' if not bad else 'FAIL'}")

print()
print("="*72)
print("E5: WEEKEND GAPS / DATA CONTINUITY (BTC is 24/7)")
ts15=[int(c["ts"]) for c in c15]
gaps=[(ts15[i]-ts15[i-1]) for i in range(1,len(ts15)) if ts15[i]-ts15[i-1] != 900]
maxgap=max(gaps)/3600 if gaps else 0
expected=(ts15[-1]-ts15[0])//900+1
contpct=100*len(c15)/expected
print(f"  15m bars: {len(c15)} (expected {expected}, continuity {contpct:.2f}%)  gaps: {len(gaps)}  max gap: {maxgap:.1f}h")
# no trade may straddle a data hole > 24h
big=[(ts15[i-1],ts15[i]) for i in range(1,len(ts15)) if ts15[i]-ts15[i-1] > 86400]
straddle=0
for a,b in zip(tr,tr[1:]):
    for g0,g1 in big:
        if a["exit_ts"] < g0 and b["entry_ts"] > g1: straddle+=1
inrange=all(t0<=int(t["entry_ts"])<=t1 and t0<=int(t["exit_ts"])<=t1 for t in tr)
print(f"  data holes > 24h: {len(big)}  trades straddling them: {straddle}  all ts in range: {inrange}")
print(f"  -> {'PASS' if inrange and straddle==0 else 'FAIL'}")

print()
print("="*72)
print("E6: PRICE SANITY")
gmin=min(float(c["low"]) for c in c15); gmax=max(float(c["high"]) for c in c15)
bad_entry=[t for t in tr if not (float(c15[t["entry_idx"]]["low"])-1e-6 <= t["entry_price"] <= float(c15[t["entry_idx"]]["high"])+1e-6)]
bad_exit=[t for t in tr if not (float(c15[t["exit_idx"]]["low"])-1e-6 <= t["exit_price"] <= float(c15[t["exit_idx"]]["high"])+1e-6)]
out_of_world=[t for t in tr if not all(5000<=p<=500000 for p in (t["entry_price"],t["sl"],t["target"],t["exit_price"]))]
print(f"  global BTC range in data: {gmin:.0f} - {gmax:.0f}")
print(f"  entry outside its 15m bar range: {len(bad_entry)}")
print(f"  exit outside its 15m bar range: {len(bad_exit)}")
print(f"  prices outside sane BTC world [5k, 500k]: {len(out_of_world)}")
ok = not bad_entry and not bad_exit and not out_of_world
print(f"  -> {'PASS' if ok else 'FAIL'}")
print("="*72)
