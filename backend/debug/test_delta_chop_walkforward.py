"""DeltaChop and walk-forward
- For each HTF interval, compute chop_before, Deltachop (change vs previous), slope3, slope5, ATR%
- Bucket by Deltachop rising/falling/stable and chop level
- Walk-forward Train 2023 Test 2024 etc with fixed 61.8
"""
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
import math, bisect
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.btc_config import load_btc_df
from src.walker import FlowCandle
from src.btc.engines.v7_timecap import simulate_btc_trades_v7
import csv

def load_window(tf):
    df = load_btc_df(tf)
    c=[]; f=[]
    for row in df.itertuples():
        date=row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        c.append({"date":date,"ts":int(row.ts),"open":float(row.open),"high":float(row.high),"low":float(row.low),"close":float(row.close),"volume":0,"oi":0})
        f.append(FlowCandle(date=date,open=float(row.open),high=float(row.high),low=float(row.low),close=float(row.close)))
    return c,f

c1h,f1h = load_window("1h")
c15,f15 = load_window("15m")
# chop 1h
def chop_series(candles, lb=14):
    n=len(candles)
    tr=[0.0]*n
    for i in range(n):
        hi=float(candles[i]["high"]); lo=float(candles[i]["low"])
        if i==0: tr[i]=hi-lo
        else:
            pc=float(candles[i-1]["close"])
            tr[i]=max(hi-lo, abs(hi-pc), abs(lo-pc))
    chop=[50.0]*n
    for i in range(lb, n):
        tr_sum=sum(tr[i-lb+1:i+1])
        hi_max=max(float(candles[j]["high"]) for j in range(i-lb+1, i+1))
        lo_min=min(float(candles[j]["low"]) for j in range(i-lb+1, i+1))
        rang=hi_max-lo_min
        if rang>0 and tr_sum>0:
            try: chop[i]=100*math.log10(tr_sum/rang)/math.log10(lb)
            except: chop[i]=50.0
    return chop

chop1h=chop_series(c1h)
c1h_ts=[c["ts"] for c in c1h]
# need HTF intervals for flip
from src.btc.btc_engine import _collect_signals
from src.btc.btc_routes import _load_fine_1m
sw1h = _compute_swings(f1h,"continuous",min_bars=20)
fine=_load_fine_1m(c1h[0]["ts"], c1h[-1]["ts"])

def intervals_for(br):
    tr=simulate_btc_trades_v7(c1h, sw1h, entry_break=br, sl_mode="swing", rr_target=3.0, trailing="off", breakeven_r=0.0, skip_first=True, fine=fine, cap_days=16)
    iv=[]
    for t in tr:
        if t["outcome"]=="open": continue
        iv.append((int(t["entry_ts"]), int(t["exit_ts"]), 1 if t["dir"]=="long" else -1, float(t["entry_price"]), float(t["sl"])))
    iv.sort(key=lambda x: x[0])
    return iv

iv_flip=intervals_for("flip")
# For each flip interval, get chop_before and delta
print(f"HTF flip intervals {len(iv_flip)}")
# Read interval CSV we already wrote
import pathlib
csv_path=Path(r"C:\Users\Pravin\AppData\Local\Temp\opencode\b2_flip_interval.csv")
rows=list(csv.DictReader(open(csv_path, encoding="utf-8")))
# Bucket by Deltachop
from collections import defaultdict
# Row has chop_before, chop_change, chop_slope3, chop_slope5
def bucket_delta(d):
    if d >2: return "rising >2"
    if d <-2: return "falling <-2"
    return "stable -2 to 2"

# For this test, we need to recompute delta per interval and compare B2 vs Flip delta
# We have ltf flip and b2 net per interval from previous CSV? The CSV has ltf_trades, ltf_R, but not per bucket yet
# Let's compute delta distribution
# Use previous interval_out2 bucket data: we have per interval delta already in CSV as delta_R (B2-Flip)
# Load and bucket by chop and delta
buckets_chop=defaultdict(list)
buckets_delta=defaultdict(list)
buckets_atr=defaultdict(list)
for r in rows:
    try:
        ch=float(r["chop_before"])
        delta=float(r["delta_R"])
        # delta is B2 net - Flip net for that interval (from previous calc, but we stored delta as B2-Flip per interval? In CSV, delta_R is B2 - Flip for same FLIP window)
        # Bucket by chop
        if ch <38.2: b="LOW <38.2"
        elif ch <61.8: b="MED 38.2-61.8"
        elif ch <75: b="HIGH 61.8-75"
        else: b="EXTREME >75"
        buckets_chop[b].append(delta)
        # delta bucket
        dchg=float(r["chop_change"])
        bd=bucket_delta(dchg)
        buckets_delta[bd].append(delta)
        # Also bucket by chop_slope3
        slope3=float(r["chop_slope3"])
        if slope3 >5: bs="rising >5"
        elif slope3 < -5: bs="falling <-5"
        else: bs="stable -5 to 5"
        buckets_atr[bs].append(delta)  # reuse
    except: pass

print("\n=== DeltaChop bucket: B2-Flip per HTF interval (FLIP window as base) ===")
for b in ["LOW <38.2","MED 38.2-61.8","HIGH 61.8-75"]:
    lst=buckets_chop[b]
    if lst:
        avg=sum(lst)/len(lst)
        win=sum(1 for x in lst if x>0)
        print(f"{b:15s} | intervals {len(lst):3d} | avg delta {avg:+6.2f} | B2 wins {win}/{len(lst)} ({win/len(lst)*100:.1f}%) | median {sorted(lst)[len(lst)//2]:+.2f}")

print("\n=== DeltaChop change bucket (chop_before - previous) ===")
for b in ["rising >2","stable -2 to 2","falling <-2"]:
    lst=buckets_delta[b]
    if lst:
        avg=sum(lst)/len(lst)
        win=sum(1 for x in lst if x>0)
        print(f"{b:15s} | n {len(lst):3d} | avg delta {avg:+6.2f} | B2 wins {win}/{len(lst)}")

print("\n=== Chop slope 3 bars bucket ===")
for b in ["rising >5","stable -5 to 5","falling <-5"]:
    lst=buckets_atr[b]
    if lst:
        avg=sum(lst)/len(lst)
        print(f"{b:15s} | n {len(lst):3d} | avg delta {avg:+6.2f}")

# Walk-forward with fixed 61.8
print("\n=== Walk-forward with fixed 61.8 (HIGH->B2 else Flip) ===")
# We already have per year net for flip, b2, cond from cond_out
# Let's compute walk-forward:
# Train 2023 to pick best threshold? For walk-forward, we fix 61.8 beforehand, not re-optimized
# So we just show Train 2023 (2023 net for each mode) and Test 2024 net for same mode
# From cond_out: flip 2023 -7.2, b2 -15.3, cond -7.5, decisive +37.7
# For walk-forward, we need to simulate Train 2023 to choose best HTF mode based on 2023 net, then Test that mode on 2024
# Let's do that logic:
# For each train window, find best HTF mode among flip/b2/decisive based on train net, then apply that mode's test net
from collections import defaultdict as dd
# Hardcode per-year nets from earlier runs (from cond_out and perm_out)
# For HTF flip/b2/decisive on 15m LTF decisive, we have:
per_year={
    "flip": {"2023":-7.2,"2024":40.1,"2025":101.5,"2026":33.7, "total":168.1},
    "b2": {"2023":-15.3,"2024":-1.2,"2025":63.4,"2026":2.9, "total":49.8},
    "decisive": {"2023":37.7,"2024":-16.9,"2025":35.3,"2026":66.5, "total":122.6},
    "cond_b2_vs_flip": {"2023":-7.5,"2024":62.3,"2025":99.5,"2026":43.0, "total":197.2},
    "cond_chop_or_atr": {"2023":21.4,"2024":25.7,"2025":55.4,"2026":70.0, "total":172.5},
}
for train, test in [("2023","2024"), ("2023-2024","2025"), ("2023-2025","2026")]:
    if train=="2023":
        train_nets={k: per_year[k]["2023"] for k in ["flip","b2","decisive"]}
    elif train=="2023-2024":
        train_nets={k: per_year[k]["2023"]+per_year[k]["2024"] for k in ["flip","b2","decisive"]}
    else:
        train_nets={k: per_year[k]["2023"]+per_year[k]["2024"]+per_year[k]["2025"] for k in ["flip","b2","decisive"]}
    best_train=max(train_nets, key=train_nets.get)
    # Test net for that best_train mode on test year
    test_net=per_year[best_train][test] if test in per_year[best_train] else 0
    # Also cond net on test year
    cond_net=per_year["cond_b2_vs_flip"][test]
    # Also cond_chop_or_atr
    cond2_net=per_year["cond_chop_or_atr"][test]
    print(f"Train {train:10s} best HTF = {best_train:8s} ({train_nets[best_train]:5.1f} in train) -> Test {test} net: Flip {per_year['flip'][test]:5.1f} B2 {per_year['b2'][test]:5.1f} Decisive {per_year['decisive'][test]:5.1f} | Cond b2_vs_flip {cond_net:5.1f} | Cond chop_or_atr {cond2_net:5.1f} | Best train pick {test_net:5.1f}")

print("\nIf we had followed Train best pick, would we beat pure Flip/Cond?")
# Also test if we had used cond's fixed 61.8 rule (b2_vs_flip) vs pure Flip per test year
for test in ["2024","2025","2026"]:
    print(f"Test {test}: Flip {per_year['flip'][test]:5.1f} vs Cond b2_vs_flip {per_year['cond_b2_vs_flip'][test]:5.1f} diff {per_year['cond_b2_vs_flip'][test]-per_year['flip'][test]:+5.1f} vs Cond chop_or_atr {per_year['cond_chop_or_atr'][test]:5.1f} diff {per_year['cond_chop_or_atr'][test]-per_year['flip'][test]:+5.1f}")

print("\nDone walk-forward")
