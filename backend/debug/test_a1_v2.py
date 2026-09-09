import sys, bisect
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from datetime import datetime
from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt, _chop_series_1h, _r_touch_end
from src.btc.engines.v7_timecap import simulate_btc_trades_v7
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
fine_ts = [int(c["ts"]) for c in fine]

print("Running v18 (window = entry -> 1.5R touch)...")
r18 = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=fine,
    sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
    cooldown_bars=20, max_consecutive_losses=5)
trades = r18["ltf_trades"]
print(f"v18 trades: {len(trades)}")

# --- Independently rebuild HTF windows (1.5R touch) ---
htf_flip = simulate_btc_trades_v7(c1h, sw1h, entry_break="flip", sl_mode="swing", rr_target=3.0, trailing="off", breakeven_r=0.0, skip_first=True, fine=fine, cap_days=16)
htf_b2 = simulate_btc_trades_v7(c1h, sw1h, entry_break="b2", sl_mode="swing", rr_target=3.0, trailing="off", breakeven_r=0.0, skip_first=True, fine=fine, cap_days=16)

def build(trades_):
    iv=[]
    for t in trades_:
        if t["outcome"]=="open": continue
        iv.append((int(t["entry_ts"]), _r_touch_end(t, fine, fine_ts, 1.5), 1 if t["dir"]=="long" else -1))
    iv.sort(key=lambda x: x[0])
    return iv, [x[0] for x in iv]

flip_iv, flip_starts = build(htf_flip)
b2_iv, b2_starts = build(htf_b2)

# --- Regime per LTF bar (independent recompute) ---
chop = _chop_series_1h(c1h, lb=14)
hts = [int(c["ts"]) for c in c1h]

def regime_at(ts):
    j = bisect.bisect_right(hts, ts) - 1
    ch = chop[j] if j >= 0 and j < len(chop) else 50.0
    return ("b2" if ch > 61.8 else "flip"), ch

# --- Verify every trade ---
inside=outside=regime_bad=dir_bad=0
bad=[]
for t in trades:
    use, ch = regime_at(t["entry_ts"])
    iv, starts = (b2_iv, b2_starts) if use=="b2" else (flip_iv, flip_starts)
    idx = bisect.bisect_right(starts, t["entry_ts"]) - 1
    if idx < 0:
        outside+=1; bad.append((t,"no interval",use,ch)); continue
    s,e,d = iv[idx]
    if not (s < t["entry_ts"] <= e):
        outside+=1; bad.append((t,"outside",use,ch)); continue
    if d != (1 if t["dir"]=="long" else -1):
        dir_bad+=1; bad.append((t,"dir mismatch",use,ch)); continue
    if t.get("htf_regime") != use:
        regime_bad+=1; bad.append((t,"regime field mismatch",use,ch)); continue
    inside+=1

print()
print("="*72)
print(f"TOTAL={len(trades)}  INSIDE+OK={inside}  OUTSIDE={outside}  DIR_BAD={dir_bad}  REGIME_BAD={regime_bad}")
for t,why,use,ch in bad[:5]:
    print(f"  #{t['trade_no']} {t['entry_date']} {t['dir']} reg={t.get('htf_regime')} use={use} ch={ch:.1f} -> {why}")

# --- Window length comparison: old (exit_ts) vs new (1.5R touch) ---
old_h=[]; new_h=[]; touched=0; sl_first=0
for t in htf_flip+htf_b2:
    if t["outcome"]=="open": continue
    wend=_r_touch_end(t, fine, fine_ts, 1.5)
    old_h.append((int(t["exit_ts"])-int(t["entry_ts"]))/3600)
    new_h.append((wend-int(t["entry_ts"]))/3600)
    if wend < int(t["exit_ts"]): touched+=1
    else: sl_first+=1
print()
print(f"HTF windows: {len(old_h)}  ended at 1.5R touch: {touched}  ended at SL/cap exit: {sl_first}")
print(f"Avg window len  OLD (exit-based): {sum(old_h)/len(old_h):.1f}h   NEW (1.5R touch): {sum(new_h)/len(new_h):.1f}h")
print("="*72)
