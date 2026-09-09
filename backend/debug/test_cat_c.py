import sys, bisect
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.btc.engines.v7_timecap import simulate_btc_trades_v7
from src.btc.btc_engine import _collect_signals
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

tr = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=fine,
    sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
    cooldown_bars=20, max_consecutive_losses=5)["ltf_trades"]

# replicate engine ATR15 + signals exactly
n=len(c15)
tr_l=[0.0]*n
for i in range(n):
    c=c15[i]
    if i==0: tr_l[i]=float(c["high"])-float(c["low"])
    else:
        pc=float(c15[i-1]["close"])
        tr_l[i]=max(float(c["high"])-float(c["low"]), abs(float(c["high"])-pc), abs(float(c["low"])-pc))
atr15=[0.0]*n
for i in range(n):
    lo=max(0,i-13)
    atr15[i]=sum(tr_l[lo:i+1])/(i-lo+1)
sigs=_collect_signals(sw15, "decisive", skip_first=True, selection="stream", candles=c15)
bybar={s["bar"]:s for s in sigs}

print("="*72)
print("C1: SL = SWING START PIVOT +/- 0.25 ATR(14)")
bad1=[]
for t in tr:
    sig=bybar[t["entry_idx"]]
    pivot=float(sig["swing_start_px"])
    d=1 if t["dir"]=="long" else -1
    expected=pivot - 0.25*atr15[t["entry_idx"]] if d==1 else pivot + 0.25*atr15[t["entry_idx"]]
    if abs(t["sl"]-expected)>0.011: bad1.append(t)
print(f"  mismatches: {len(bad1)} / {len(tr)}  -> {'PASS' if not bad1 else 'FAIL'}")

print()
print("="*72)
print("C2: SL NOT TOO TIGHT (risk >= 0.05% of entry)")
bad2=[]
for t in tr:
    risk=abs(t["entry_price"]-t["sl"])
    if risk < 0.0005*t["entry_price"]-1e-9: bad2.append((t,risk))
print(f"  violations: {len(bad2)} / {len(tr)}  -> {'PASS' if not bad2 else 'FAIL'}")
if bad2: print("   worst:", min(bad2, key=lambda x:x[1])[1])

print()
print("="*72)
print("C3: TARGET = ENTRY +/- 3 x RISK")
bad3=[]
for t in tr:
    entry_u=float(c15[t["entry_idx"]]["close"])
    sig=bybar[t["entry_idx"]]
    pivot=float(sig["swing_start_px"])
    d=1 if t["dir"]=="long" else -1
    sl_u=pivot - 0.25*atr15[t["entry_idx"]] if d==1 else pivot + 0.25*atr15[t["entry_idx"]]
    risk_u=abs(entry_u-sl_u)
    tgt_u=entry_u+3.0*risk_u if d==1 else entry_u-3.0*risk_u
    if abs(t["target"]-tgt_u)>0.011: bad3.append(t)
print(f"  mismatches: {len(bad3)} / {len(tr)}  -> {'PASS' if not bad3 else 'FAIL'}")

print()
print("="*72)
print("C4: RISK CONSISTENCY (|entry-SL| == |target-entry|/3)")
bad4=[]
for t in tr:
    risk=abs(t["entry_price"]-t["sl"])
    trisk=abs(t["target"]-t["entry_price"])/3.0
    if abs(risk-trisk)>0.02: bad4.append(t)
print(f"  inconsistencies: {len(bad4)} / {len(tr)}  -> {'PASS' if not bad4 else 'FAIL'}")

print()
print("="*72)
print("C5: NO BREAKEVEN (SL never moves to entry)")
oc=Counter(t["outcome"] for t in tr)
print(f"  outcome set: {dict(oc)}")
has_be=oc.get("be",0)>0
bad5=[t for t in tr if t["outcome"]=="sl" and abs(t["exit_price"]-t["sl"])>0.011]
print(f"  'be' outcomes: {oc.get('be',0)}  |  sl-exits not at initial SL: {len(bad5)}  -> {'PASS' if not has_be and not bad5 else 'FAIL'}")

print()
print("="*72)
print("C6: HTF TRAILING OFF / LTF TRAILS MB50 BY DESIGN (amended test)")
htf_flip = simulate_btc_trades_v7(c1h, sw1h, entry_break="flip", sl_mode="swing", rr_target=3.0, trailing="off", breakeven_r=0.0, skip_first=True, fine=fine, cap_days=16)
htf_b2 = simulate_btc_trades_v7(c1h, sw1h, entry_break="b2", sl_mode="swing", rr_target=3.0, trailing="off", breakeven_r=0.0, skip_first=True, fine=fine, cap_days=16)
hoc=Counter(t["outcome"] for t in htf_flip+htf_b2)
print(f"  HTF (trailing=off) outcomes: {dict(hoc)}")
htf_ok = not (hoc.get("trail",0) or hoc.get("be",0))
trail_bad=0
for t in tr:
    if t["outcome"]=="trail":
        if t["dir"]=="long" and not (t["exit_price"]>t["sl"]): trail_bad+=1
        if t["dir"]=="short" and not (t["exit_price"]<t["sl"]): trail_bad+=1
print(f"  LTF trail exits beyond initial SL (SL ratcheted): violations {trail_bad} / {oc.get('trail',0)}")
ok6 = htf_ok and trail_bad==0
print(f"  -> {'PASS' if ok6 else 'FAIL'}  (HTF static SL: {'OK' if htf_ok else 'FAIL'}, LTF MB50 trail: {'OK' if trail_bad==0 else 'FAIL'})")
print("="*72)
