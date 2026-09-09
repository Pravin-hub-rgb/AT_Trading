import sys, bisect
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt, _chop_series_1h
from src.btc.engines.v7_timecap import simulate_btc_trades_v7
from src.walker import FlowCandle

CUT = "2023-01-13"   # show everything before this date

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

print(f"ts unit check: first 1h ts={c1h[0]['ts']} date={c1h[0]['date']}")
print()
print(f"=== 1h SWINGS + BREAKS (mb20) up to {CUT} ===")
for i in range(1, len(sw1h)):
    prev, curr = sw1h[i-1], sw1h[i]
    conf_idx = curr.get("confirmed_at_idx", -1)
    if conf_idx < 0: continue
    conf_date = c1h[conf_idx]["date"]
    if conf_date >= CUT: break
    btype = "FLIP" if curr["dir"] != prev["dir"] else ("B2" if sum(1 for j in range(i-1,-1,-1) if sw1h[j]["dir"]==curr["dir"]) >= 2 else "B1")
    si = curr.get("start_idx", -1)
    sd = c1h[si]["date"] if 0 <= si < len(c1h) else "?"
    ei = curr.get("end_idx", -1)
    ed = c1h[ei]["date"] if 0 <= ei < len(c1h) else "?"
    print(f"  swing[{i:2d}] {btype:5s} dir={curr['dir']:5s} swing={sd} -> {ed}  confirmed={conf_date}")

print()
print(f"=== HTF windows (v7) up to {CUT} ===")
htf_flip = simulate_btc_trades_v7(c1h, sw1h, entry_break="flip", sl_mode="swing", rr_target=3.0, trailing="off", breakeven_r=0.0, skip_first=True, fine=fine, cap_days=16)
htf_b2 = simulate_btc_trades_v7(c1h, sw1h, entry_break="b2", sl_mode="swing", rr_target=3.0, trailing="off", breakeven_r=0.0, skip_first=True, fine=fine, cap_days=16)
print("-- FLIP windows:")
for i, t in enumerate(htf_flip):
    if t["entry_date"] >= CUT: break
    print(f"  [{i}] {t['dir']:5s} entry={t['entry_date']} exit={t['exit_date']} outcome={t['outcome']}")
print("-- B2 windows:")
for i, t in enumerate(htf_b2):
    if t["entry_date"] >= CUT: break
    print(f"  [{i}] {t['dir']:5s} entry={t['entry_date']} exit={t['exit_date']} outcome={t['outcome']}")

print()
print(f"=== CHOP per 1h bar, Jan 5-8 (regime at each bar) ===")
chop = _chop_series_1h(c1h, lb=14)
for j, c in enumerate(c1h):
    if c["date"] < "2023-01-05" or c["date"] >= "2023-01-09": continue
    if j >= len(chop) or chop[j] is None: continue
    print(f"  {c['date']}  chop={chop[j]:.1f}  regime={'B2' if chop[j]>61.8 else 'flip'}")

print()
print(f"=== FIRST v18 LTF TRADES (up to {CUT}) ===")
r18 = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=fine,
    sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
    cooldown_bars=20, max_consecutive_losses=5)
trades = r18["ltf_trades"]
for t in trades:
    if t["entry_date"] >= CUT: break
    print(f"  #{t['trade_no']} {t['entry_date']} {t['dir']:5s} kind={t.get('kind','?')} regime={t.get('htf_regime','?')} outcome={t['outcome']} r={t.get('r',0):+.3f}")
    print(f"      keys: {[k for k in t.keys() if k in ('entry','sl','target','exit','exit_price','swing_no','entry_price')]}")
    for k in ("entry","entry_price","sl","target","exit_price"):
        if k in t: print(f"      {k}={t[k]:.2f}", end="")
    print()
