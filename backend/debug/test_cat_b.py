import sys, bisect
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt, _chop_series_1h
from src.btc.engines.v7_timecap import simulate_btc_trades_v7
from src.btc.btc_engine import _collect_signals
from src.walker import FlowCandle

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

print("running v18 (baseline)...")
tr = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=fine,
    sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
    cooldown_bars=20, max_consecutive_losses=5)["ltf_trades"]
print(f"trades={len(tr)}\n")

print("="*72)
print("B2: ENTRY PRICE = CLOSE OF BREAK CANDLE")
bad=[t for t in tr if abs(t["entry_price"]-float(c15[t["entry_idx"]]["close"]))>1e-6]
print(f"  mismatches: {len(bad)} / {len(tr)}  -> {'PASS' if not bad else 'FAIL'}")

print()
print("="*72)
print("B3: NO ENTRY WITHOUT HTF BIAS")
# every trade must sit inside a regime-selected window with matching direction
htf_flip = simulate_btc_trades_v7(c1h, sw1h, entry_break="flip", sl_mode="swing", rr_target=3.0, trailing="off", breakeven_r=0.0, skip_first=True, fine=fine, cap_days=16)
htf_b2 = simulate_btc_trades_v7(c1h, sw1h, entry_break="b2", sl_mode="swing", rr_target=3.0, trailing="off", breakeven_r=0.0, skip_first=True, fine=fine, cap_days=16)
def build(ts_):
    iv=[]
    for t in ts_:
        if t["outcome"]=="open": continue
        iv.append((int(t["entry_ts"]), int(t["exit_ts"]), 1 if t["dir"]=="long" else -1))
    iv.sort(key=lambda x:x[0])
    return iv,[x[0] for x in iv]
flip_iv,fs=build(htf_flip); b2_iv,bs=build(htf_b2)
chop=_chop_series_1h(c1h,lb=14); hts=[int(c["ts"]) for c in c1h]
no_bias=0
for t in tr:
    j=bisect.bisect_right(hts,t["entry_ts"])-1
    ch=chop[j] if j>=0 and j<len(chop) else 50.0
    iv,starts=(b2_iv,bs) if ch>61.8 else (flip_iv,fs)
    i=bisect.bisect_right(starts,t["entry_ts"])-1
    s,e,d=iv[i]
    if not (s<t["entry_ts"]<=e and d==(1 if t["dir"]=="long" else -1)):
        no_bias+=1
print(f"  trades without valid HTF bias window+direction: {no_bias} / {len(tr)}  -> {'PASS' if no_bias==0 else 'FAIL'}")

print()
print("="*72)
print("B4: COOLDOWN 20 BARS AFTER LOSS")
viol=0; checked=0; last_loss_exit=None
for t in tr:
    if last_loss_exit is not None:
        checked+=1
        if t["entry_idx"]-last_loss_exit < 20: viol+=1
    if t["r_multiple"]<0: last_loss_exit=t["exit_idx"]
print(f"  trades checked after a loss: {checked}  violations (<20 bars): {viol}  -> {'PASS' if viol==0 else 'FAIL'}")

print()
print("="*72)
print("B5: STREAK HALT AT 5 CONSECUTIVE LOSSES")
mx=cl=0; runs4=0
for t in tr:
    if t["r_multiple"]<=0:
        cl+=1
        if cl>mx: mx=cl
    else:
        if cl>=4: runs4+=1
        cl=0
if cl>=4: runs4+=1
print(f"  max consecutive losses IN TRADE LIST: {mx} (halt=5 -> 5th loss skipped, max allowed 4)  -> {'PASS' if mx<=4 else 'FAIL'}")
print("  cross-check vs halt=0 run...")
tr0 = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=fine,
    sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
    cooldown_bars=20, max_consecutive_losses=0)["ltf_trades"]
s18={t["entry_ts"] for t in tr}; s0={t["entry_ts"] for t in tr0}
diff=[t for t in tr0 if t["entry_ts"] not in s18]
losers=[t for t in diff if t["r_multiple"]<=0]
print(f"  halt=0: {len(tr0)}t {sum(t['r_multiple'] for t in tr0):+.1f}R | v18: {len(tr)}t {sum(t['r_multiple'] for t in tr):+.1f}R")
print(f"  skipped by halt: {len(diff)} trades, {len(losers)} losers ({100*len(losers)/max(1,len(diff)):.0f}%), net {sum(t['r_multiple'] for t in diff):+.1f}R")

print()
print("="*72)
print("B6: RESUME ON WINNER (post-halt)")
viol6=0; runs6=0
cl=0; last=None
for idx,t in enumerate(tr):
    if t["r_multiple"]<=0:
        cl+=1
    else:
        if cl>=4:
            runs6+=1
            if t["r_multiple"]<=0: viol6+=1
        cl=0
print(f"  loss-runs >=4 followed by a winner: checked {runs6}, violations {viol6}  -> {'PASS' if viol6==0 else 'FAIL'}")

print()
print("="*72)
print("B1: FIRST SIGNAL NEGLECT (stream selection, one-swing-one-trade)")
sigs=_collect_signals(sw15, "decisive", skip_first=True, selection="stream", candles=c15)
byswing={}
for s in sigs:
    byswing.setdefault(s["swing_no"],[]).append(s)
bybar={s["bar"]:s for s in sigs}
notsig=sum(1 for t in tr if t["entry_idx"] not in bybar)
dup=len(tr)-len({t["swing_no"] for t in tr})
notfirst=0; notfirst_ex=[]
for t in tr:
    ssig=byswing.get(t["swing_no"],[])
    if ssig:
        first_bar=min(s["bar"] for s in ssig)
        if t["entry_idx"]!=first_bar:
            same_dir_first=[s for s in ssig if s["bar"]<t["entry_idx"] and s["dir"]==t["dir"]]
            if same_dir_first:
                notfirst+=1; notfirst_ex.append(t)
print(f"  signals collected: {len(sigs)} across {len(byswing)} swings")
print(f"  trades not mapping to a collected signal: {notsig}")
print(f"  swings traded more than once (one-swing-one-trade): {dup}")
print(f"  trades NOT at the first same-dir signal of their swing: {notfirst}")
ok = notsig==0 and dup==0 and notfirst==0
print(f"  -> {'PASS' if ok else 'FAIL'}")
for t in notfirst_ex[:5]:
    ss=byswing[t["swing_no"]]
    print(f"    e.g. trade #{t['trade_no']} swing {t['swing_no']} entry bar {t['entry_idx']}, swing signals bars {[s['bar'] for s in ss]}")
print("="*72)
