import pandas as pd, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from src import bias as b, config
from src.intraday_1m_standalone import run_backtest_1min
import pandas as pd

p1=config.DATA_DIR/'nifty_1min.csv'
p5=config.DATA_DIR/'nifty_5min.csv'
pdaily=config.DATA_DIR/'nifty_daily.csv'
df1=pd.read_csv(p1)
df5=pd.read_csv(p5)
daily=pd.read_csv(pdaily) if pdaily.exists() else None

def run_with_bias(bias_map, label):
    from src.intraday import EOD_EXIT
    df1_copy=df1.copy()
    df1_copy["timestamp"]=pd.to_datetime(df1_copy["timestamp"])
    df1_copy["ts"]=(df1_copy["timestamp"].astype("int64")//1_000_000_000).astype("int64")
    df1_copy=df1_copy.sort_values("timestamp").drop_duplicates(subset="ts", keep="last")
    dates=df1_copy["timestamp"].dt.strftime("%Y-%m-%d")
    groups={d:g for d,g in df1_copy.groupby(dates, sort=True)}
    ordered=sorted(groups)
    prev_close={ordered[i]: float(groups[ordered[i-1]]["close"].iloc[-1]) for i in range(1,len(ordered))}
    # zone map not needed for this test, use empty
    zone_map={}
    def _ext(z): return None
    def _q(g):
        rows=g.reset_index(drop=True)
        return [float(r["high"])-float(r["low"]) for _,r in rows.iloc[1:].iterrows() if r["timestamp"].strftime("%H:%M") < EOD_EXIT]
    day_ranges={d: _q(groups[d]) for d in ordered}
    avg_by_date={}
    for idx,d in enumerate(ordered):
        flat=[]
        for j in range(max(0, idx-10), idx):
            flat.extend(day_ranges[ordered[j]])
        avg_by_date[d]= sum(flat)/len(flat) if flat else None
    base_cfg={"execution":"1min","sl_mode":"prev_pivot","rr_target":4.0,"min_sl_pts":13,"breakeven_r":1.0,"gap_pct":0.0027,"ft_fail_enabled":True,"max_entries":2,"entry_cutoff":"15:15","second_trade_after":"always","swing_traverse":True,"need_opp_swing":True}
    from src.intraday import resolve_cfg
    cfg=resolve_cfg(base_cfg)
    traded=set(groups) & set(bias_map.keys())
    days=[]
    for d in sorted(traded):
        g=groups[d]
        gap_val=float(g["open"].iloc[0])
        pc=prev_close.get(d)
        gap="flat"
        if pc:
            frac=abs(gap_val-pc)/pc
            gap="flat" if frac<=cfg["gap_pct"] else "gap-up" if gap_val>pc else "gap-down"
        ctx={"gap":gap,"extreme":None,"avg_range":avg_by_date.get(d)}
        days.append(__import__('src.intraday_1m_standalone', fromlist=['simulate_day_1min']).simulate_day_1min(g, bias_map[d], cfg=cfg, ctx=ctx))
    all_trades=[t for dy in days for t in dy["trades"]]
    wins=[t for t in all_trades if t["r_multiple"]>0]
    from collections import Counter
    outcomes=Counter(t["outcome"] for t in all_trades)
    total_r=round(sum(t["r_multiple"] for t in all_trades),2)
    win_rate=round(len(wins)/len(all_trades)*100,1) if all_trades else 0
    print(f"{label}: Trades {len(all_trades)} WR {win_rate}% R {total_r} PF {round(sum(r for r in [t['r_multiple'] for t in all_trades] if r>0)/max(1, -sum(r for r in [t['r_multiple'] for t in all_trades] if r<0)),2)} Days {sum(1 for dy in days if dy['trades'])}/{len(days)}")

# Build bias maps for daily EMA10 trend vs inverse (no far band)
daily_sorted=pd.read_csv(pdaily)
daily_sorted["timestamp"]=pd.to_datetime(daily_sorted["timestamp"])
daily_sorted=daily_sorted.sort_values("timestamp")
daily_sorted["ema10"]=daily_sorted["close"].ewm(span=10, adjust=False).mean()
daily_sorted["date_str"]=daily_sorted["timestamp"].dt.strftime("%Y-%m-%d")

# Trend: close > EMA -> bullish (long)
trend_map={}
inv_map={}
for i in range(1, len(daily_sorted)):
    today=daily_sorted.iloc[i]["date_str"]
    prev_close=float(daily_sorted.iloc[i-1]["close"])
    prev_ema=float(daily_sorted.iloc[i-1]["ema10"])
    if prev_close > prev_ema:
        trend_map[today]="bullish"
        inv_map[today]="bearish"  # inverse: above -> short
    elif prev_close < prev_ema:
        trend_map[today]="bearish"
        inv_map[today]="bullish"
    else:
        trend_map[today]=inv_map[today]="unbiased"
# Next day placeholder
last_next=(pd.Timestamp(daily_sorted.iloc[-1]["timestamp"])+pd.tseries.offsets.BDay(1)).strftime("%Y-%m-%d")
trend_map[last_next]="unbiased"
inv_map[last_next]="unbiased"

print("Testing daily EMA10 trend vs inverse (no far band, always fade if above/below)")
run_with_bias(trend_map, "Daily EMA10 TREND (close>EMA -> long)")
run_with_bias(inv_map, "Daily EMA10 INVERSE (close>EMA -> short, below -> long) - YOUR QUESTION")

# Also test with 5min cross inverse?
# For 5min cross, trend is EMA20>50 -> bullish, inverse would be opposite
df5["timestamp"]=pd.to_datetime(df5["timestamp"])
df5_sorted=df5.sort_values("timestamp")
df5_sorted["ema20"]=df5_sorted["close"].ewm(span=20, adjust=False).mean()
df5_sorted["ema50"]=df5_sorted["close"].ewm(span=50, adjust=False).mean()
df5_sorted["date_str"]=df5_sorted["timestamp"].dt.strftime("%Y-%m-%d")
# Group by date last bar
g5=df5_sorted.groupby("date_str")
ordered5=sorted(g5.groups.keys())
trend5={}
inv5={}
for i in range(1, len(ordered5)):
    today=ordered5[i]
    prev=ordered5[i-1]
    last_row=g5.get_group(prev).iloc[-1]
    ef=float(last_row["ema20"])
    es=float(last_row["ema50"])
    if ef > es:
        trend5[today]="bullish"
        inv5[today]="bearish"
    elif ef < es:
        trend5[today]="bearish"
        inv5[today]="bullish"
    else:
        trend5[today]=inv5[today]="unbiased"
trend5[last_next]="unbiased"
inv5[last_next]="unbiased"
print("\nTesting 5min EMA20>50 cross trend vs inverse")
run_with_bias(trend5, "5min EMA20>50 TREND")
run_with_bias(inv5, "5min EMA20>50 INVERSE")
