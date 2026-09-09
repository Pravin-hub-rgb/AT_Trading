"""Exp1 — MAE/MFE mining on v5 FULL 442tr (net-only, no strategy change).
Recomputes excursion offline via 15m candles + 1m fine for precision.
v5 = ext-stop 1.5R + buf 0.25ATR, 0.05%+2pt, stream, 1.93M fine."""
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
from src.btc.btc_routes import _compute_swings, _load_fine_1m, _trade_costs
from src.btc.btc_engine import trade_stats
from src.btc.btc_config import load_btc_df
from src.btc.engines.htf_ltf.v5_sl_buffer import simulate_htf_ltf_sl_buffer
from src.walker import FlowCandle
from collections import defaultdict
import bisect

FEE=0.05
SLIP=2.0

def load_window(tf):
    df = load_btc_df(tf)
    c=[]; f=[]
    for row in df.itertuples():
        date=row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        c.append({"date":date,"ts":int(row.ts),"open":float(row.open),"high":float(row.high),"low":float(row.low),"close":float(row.close),"volume":0,"oi":0})
        f.append(FlowCandle(date=date,open=float(row.open),high=float(row.high),low=float(row.low),close=float(row.close)))
    return c,f,df

c1h,f1h,_ = load_window("1h")
c15,f15,_ = load_window("15m")
sw1h = _compute_swings(f1h,"continuous",min_bars=20)
sw15 = _compute_swings(f15,"continuous",min_bars=50)
t0=min(c1h[0]["ts"],c15[0]["ts"]); t1=max(c1h[-1]["ts"],c15[-1]["ts"])
fine=_load_fine_1m(t0,t1)
fine_ts=[x["ts"] for x in fine] if fine else []

nested = simulate_htf_ltf_sl_buffer(c1h,sw1h,c15,sw15,fine, htf_entry_break="flip", ltf_entry_break="decisive", sl_mode="swing", rr_target=3.0, ltf_trailing="swing", htf_breakeven=0, ltf_breakeven=0, htf_cap_days=16, ext_stop_r=1.5, sl_buf_atr=0.25)
ltf=nested["ltf_trades"]
_trade_costs(ltf,FEE,SLIP)
# build candle ts index for fast bisect
candle_ts=[c["ts"] for c in c15]

# compute MAE/MFE per trade using 1m fine if available, else 15m candles
results=[]
for tr in ltf:
    if tr["outcome"]=="open":
        continue
    entry_idx=tr["entry_idx"]
    exit_idx=tr["exit_idx"]
    entry=tr["entry_price"]
    risk=abs(entry - tr["sl"])
    if risk<=0:
        continue
    dir_ = 1 if tr["dir"]=="long" else -1
    # find fine range
    start_ts=candle_ts[entry_idx]
    # entry is at close of entry_idx, so excursion starts from next bar
    # Use fine bars from entry_ts+? to exit_ts
    entry_ts=tr["entry_ts"]
    exit_ts=tr["exit_ts"]
    # collect highs/lows in window
    if fine and fine_ts:
        f_start=bisect.bisect_left(fine_ts, entry_ts+1)  # next second after entry
        f_end=bisect.bisect_right(fine_ts, exit_ts)
        window=fine[f_start:f_end]
        highs=[x["high"] for x in window]
        lows=[x["low"] for x in window]
        if not highs:
            # fallback to 15m
            highs=[c15[i]["high"] for i in range(entry_idx+1, exit_idx+1)]
            lows=[c15[i]["low"] for i in range(entry_idx+1, exit_idx+1)]
    else:
        highs=[c15[i]["high"] for i in range(entry_idx+1, exit_idx+1)]
        lows=[c15[i]["low"] for i in range(entry_idx+1, exit_idx+1)]
    if not highs:
        mfe_r=0
        mae_r=0
        mfe_px=entry
        mae_px=entry
    else:
        if dir_==1:
            mfe_px=max(highs) if highs else entry
            mae_px=min(lows) if lows else entry
            mfe_r=(mfe_px - entry)/risk
            mae_r=(entry - mae_px)/risk  # positive means adverse
        else:
            mfe_px=min(lows) if lows else entry
            mae_px=max(highs) if highs else entry
            mfe_r=(entry - mfe_px)/risk
            mae_r=(mae_px - entry)/risk
    r_net=float(tr["r_multiple"]) - float(tr.get("cost_r",0))
    r_base=float(tr["r_multiple"])
    # time to MFE: find first bar where high reaches mfe_px (approx)
    results.append({
        "r_net": r_net,
        "r_base": r_base,
        "mfe_r": mfe_r,
        "mae_r": mae_r,
        "mfe_px": mfe_px,
        "mae_px": mae_px,
        "entry": entry,
        "sl": tr["sl"],
        "risk": risk,
        "dir": tr["dir"],
        "outcome": tr["outcome"],
        "exit_date": tr["exit_date"],
        "entry_date": tr["entry_date"],
        "bars_held": tr["bars_held"],
    })

print(f"Exp1 — v5 FULL 442tr mined: {len(results)} closed, fine bars {len(fine)}")
# Buckets
def bucket_mae(mae):
    if mae <0.25: return "<0.25R"
    if mae <0.5: return "0.25-0.5R"
    if mae <0.75: return "0.5-0.75R"
    if mae <1.0: return "0.75-1R"
    return ">1R"

from collections import Counter
# overall MAE bucket distribution
cnt_mae=Counter(bucket_mae(r["mae_r"]) for r in results)
print("\n=== All 442tr — MAE bucket (heat) ===")
for k in ["<0.25R","0.25-0.5R","0.5-0.75R","0.75-1R",">1R"]:
    print(f"{k:10s}: {cnt_mae[k]:3d}  ({cnt_mae[k]/len(results)*100:4.1f}%)")

# runners vs losers
runners=[r for r in results if r["r_net"] >= 3.0]
big=[r for r in results if r["r_net"] >= 2.0]
losers=[r for r in results if r["r_net"] <0]
wins=[r for r in results if r["r_net"]>0]
print(f"\nRunners >=3R: {len(runners)}  >=2R: {len(big)}  Wins: {len(wins)}  Losses: {len(losers)}")
if runners:
    cnt_mae_run=Counter(bucket_mae(r["mae_r"]) for r in runners)
    print("Runners >=3R — MAE bucket:")
    for k in ["<0.25R","0.25-0.5R","0.5-0.75R","0.75-1R",">1R"]:
        print(f"  {k:10s}: {cnt_mae_run[k]:3d} ({cnt_mae_run[k]/len(runners)*100:4.1f}%)  avg MAE {sum(r['mae_r'] for r in runners if bucket_mae(r['mae_r'])==k)/max(1,cnt_mae_run[k]):.2f}R")
        # avg eventual R in bucket
if losers:
    cnt_mae_los=Counter(bucket_mae(r["mae_r"]) for r in losers)
    print("Losers — MAE bucket:")
    for k in ["<0.25R","0.25-0.5R","0.5-0.75R","0.75-1R",">1R"]:
        print(f"  {k:10s}: {cnt_mae_los[k]:3d} ({cnt_mae_los[k]/len(losers)*100:4.1f}%)")

# MFE buckets
def bucket_mfe(mfe):
    if mfe <0.5: return "<0.5R"
    if mfe <1.0: return "0.5-1R"
    if mfe <2.0: return "1-2R"
    if mfe <3.0: return "2-3R"
    if mfe <5.0: return "3-5R"
    return ">=5R"
cnt_mfe=Counter(bucket_mfe(r["mfe_r"]) for r in results)
print("\n=== All — MFE bucket (favourable) ===")
for k in ["<0.5R","0.5-1R","1-2R","2-3R","3-5R",">=5R"]:
    print(f"{k:10s}: {cnt_mfe[k]:3d} ({cnt_mfe[k]/len(results)*100:4.1f}%)")

# For each MAE bucket, what's eventual outcome
print("\n=== MAE bucket -> eventual outcome (avg net R, win%, runner freq) ===")
for k in ["<0.25R","0.25-0.5R","0.5-0.75R","0.75-1R",">1R"]:
    bucket=[r for r in results if bucket_mae(r["mae_r"])==k]
    if not bucket:
        continue
    avg=sum(r["r_net"] for r in bucket)/len(bucket)
    win=len([r for r in bucket if r["r_net"]>0])/len(bucket)*100
    runner=len([r for r in bucket if r["r_net"]>=3])/len(bucket)*100
    avg_mfe=sum(r["mfe_r"] for r in bucket)/len(bucket)
    print(f"{k:10s}: n={len(bucket):3d} win{win:4.1f}% runner{runner:4.1f}% avgR {avg:+5.2f} avgMFE {avg_mfe:4.1f}R")

# Giveback for winners: mfe - r_net
winners=[r for r in results if r["r_net"]>0]
if winners:
    avg_give=sum(r["mfe_r"]-r["r_net"] for r in winners)/len(winners)
    print(f"\nWinners avg giveback (mfe - r_net): {avg_give:.2f}R  (mfe mean {sum(r['mfe_r'] for r in winners)/len(winners):.1f}R, r mean {sum(r['r_net'] for r in winners)/len(winners):.1f}R)")
    # top 10 winners detail
    top10=sorted(winners, key=lambda x: x["r_net"], reverse=True)[:10]
    print("Top10 winners (net, mfe, mae, outcome, bars):")
    for r in top10:
        print(f"  net {r['r_net']:+5.2f} mfe {r['mfe_r']:4.1f} mae {r['mae_r']:4.2f} {r['outcome']:5s} bars {r['bars_held']:3d} {r['exit_date'][:10]}")
    # runners heat
    print("\nRunners >=3R heat (mae, mfe, net):")
    for r in sorted(runners, key=lambda x: x["r_net"], reverse=True)[:15]:
        print(f"  net {r['r_net']:+5.2f} mfe {r['mfe_r']:4.1f} mae {r['mae_r']:4.2f} giveback {r['mfe_r']-r['r_net']:4.1f} bars {r['bars_held']:3d} {r['exit_date'][:10]} {r['dir']}")

# losers cheap test: what if SL was 0.75R tighter? would runners survive?
# Count runners with mae >0.5, >0.75 etc
for thr in [0.25,0.5,0.75,1.0]:
    killed=sum(1 for r in runners if r["mae_r"] > thr)
    print(f"Runners killed if SL tightened to {thr}R: {killed}/{len(runners)} ({killed/len(runners)*100:.1f}%)")

# 2023 split
res2023=[r for r in results if r["exit_date"][:4]=="2023"]
if res2023:
    print(f"\n2023 split {len(res2023)}tr: avg net {sum(r['r_net'] for r in res2023)/len(res2023):+.2f} avg mae {sum(r['mae_r'] for r in res2023)/len(res2023):.2f} mfe {sum(r['mfe_r'] for r in res2023)/len(res2023):.2f}")
    # also print 2025 for comparison
    for y in ["2023","2024","2025","2026"]:
        b=[r for r in results if r["exit_date"][:4]==y]
        if b:
            print(f"  {y}: {len(b)}tr net {sum(r['r_net'] for r in b):+6.1f} avg {sum(r['r_net'] for r in b)/len(b):+.2f} mae {sum(r['mae_r'] for r in b)/len(b):.2f} mfe {sum(r['mfe_r'] for r in b)/len(b):.2f} win {len([x for x in b if x['r_net']>0])/len(b)*100:.1f}%")
