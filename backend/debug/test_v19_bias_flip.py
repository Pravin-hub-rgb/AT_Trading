import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
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

def run(we):
    return simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=fine,
        sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
        cooldown_bars=20, max_consecutive_losses=5, window_end=we)["ltf_trades"]

def stats(trades, label):
    n=len(trades); rs=[t["r_multiple"] for t in trades]; tot=sum(rs)
    wins=[r for r in rs if r>0]; losses=[r for r in rs if r<=0]
    print(f"--- {label} ---")
    print(f"trades={n}  totalR={tot:.1f}  avgR={tot/n if n else 0:.3f}  wins={len(wins)} ({100*len(wins)/n:.1f}%)")
    if wins: print(f"avg win={sum(wins)/len(wins):.2f}R  gross={sum(wins):.1f}R", end="  ")
    if losses: print(f"avg loss={sum(losses)/len(losses):.2f}R  gross={sum(losses):.1f}R")
    from collections import Counter
    print("outcomes:", dict(Counter(t['outcome'] for t in trades)))
    years={}
    for t in trades:
        y=t["entry_date"][:4]; years.setdefault(y,[0,0.0]); years[y][0]+=1; years[y][1]+=t["r_multiple"]
    print("per year:", {y: f"{v[0]}t {v[1]:+.1f}R" for y,v in sorted(years.items())})
    ml=cl=0
    for r in rs:
        cl=cl+1 if r<=0 else 0; ml=max(ml,cl)
    print(f"maxConsecL={ml}  worst={min(rs):.2f}R  best={max(rs):.2f}R")
    print()
    return tot

base = run("exit")
tot_b = stats(base, "BASELINE window_end='exit' (current best)")
bias = run("bias_flip")
tot_f = stats(bias, "EXPERIMENT window_end='bias_flip' (window until opposite HTF entry)")

sb={t['entry_ts']:t for t in base}; sf={t['entry_ts']:t for t in bias}
only_b=[t for t in base if t['entry_ts'] not in sf]
only_f=[t for t in bias if t['entry_ts'] not in sb]
print(f"DELTA: {tot_f-tot_b:+.1f}R | trades {len(bias)} vs {len(base)} ({len(bias)-len(base):+d})")
if only_b: print(f"trades only in baseline: {len(only_b)} -> {sum(t['r_multiple'] for t in only_b):+.1f}R (avg {sum(t['r_multiple'] for t in only_b)/len(only_b):+.2f})")
if only_f: print(f"trades only in bias_flip: {len(only_f)} -> {sum(t['r_multiple'] for t in only_f):+.1f}R (avg {sum(t['r_multiple'] for t in only_f)/len(only_f):+.2f})")
