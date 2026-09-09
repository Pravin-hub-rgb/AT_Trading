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

def max_dd(trades):
    eq=peak=dd=0.0
    for t in trades:
        eq+=t["r_multiple"]
        peak=max(peak,eq); dd=max(dd,peak-eq)
    return dd

def report(trades,label):
    rs=[t["r_multiple"] for t in trades]
    import statistics as st
    print(f"--- {label} ---")
    print(f"trades={len(trades)}  totalR={sum(rs):.1f}  maxDD={max_dd(trades):.1f}R  net/DD={(sum(rs)/max_dd(trades)):.2f}")
    # split halves by date
    for name,lo,hi in [("IS 2023-24","2023","2025"),("OOS 2025-26","2025","9999")]:
        seg=[t for t in trades if lo<=t["entry_date"][:4]<hi]
        s=sum(t["r_multiple"] for t in seg)
        print(f"  {name}: {len(seg)}t {s:+.1f}R  DD={max_dd(seg):.1f}R")
    # marginal edge t-stat of added cohort handled outside
    print()
    return trades

b=report(run("exit"),"BASELINE exit")
f=report(run("bias_flip"),"BIAS_FLIP")

sb={t['entry_ts']:t for t in b}; sf={t['entry_ts']:t for t in f}
only_f=[t for t in f if t['entry_ts'] not in sb]
only_b=[t for t in b if t['entry_ts'] not in sf]
import statistics as st
rf=[t['r_multiple'] for t in only_f]
mean=sum(rf)/len(rf); sd=st.stdev(rf); tstat=mean/(sd/len(rf)**0.5)
print(f"bias_flip-only cohort: {len(only_f)}t {sum(rf):+.1f}R avg {mean:+.3f} t={tstat:.2f}")
rb=[t['r_multiple'] for t in only_b]
print(f"baseline-only cohort (displaced): {len(only_b)}t {sum(rb):+.1f}R avg {sum(rb)/len(rb):+.3f}")
print()
print("2026 head-to-head (most recent regime):")
for lbl,tr in [("exit",b),("bias_flip",f)]:
    seg=[t for t in tr if t["entry_date"][:4]=="2026"]
    print(f"  {lbl}: {len(seg)}t {sum(t['r_multiple'] for t in seg):+.1f}R DD={max_dd(seg):.1f}R")
