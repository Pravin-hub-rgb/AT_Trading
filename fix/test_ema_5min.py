import pandas as pd, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from src import bias as bias_svc, config
from src.firstswing import compute_swing_results
from src.walker import FlowCandle
from src.intraday_1m_standalone import simulate_day_1min
import numpy as np
from collections import defaultdict

DATA_DIR = config.DATA_DIR
p1 = DATA_DIR / "nifty_1min.csv"
p5 = DATA_DIR / "nifty_5min.csv"
pdaily = DATA_DIR / "nifty_daily.csv"

df1 = pd.read_csv(p1)
df5 = pd.read_csv(p5)
daily = pd.read_csv(pdaily) if pdaily.exists() else None
df1["timestamp"] = pd.to_datetime(df1["timestamp"])
df5["timestamp"] = pd.to_datetime(df5["timestamp"])
if daily is not None:
    daily["timestamp"] = pd.to_datetime(daily["timestamp"])

labels = bias_svc.compute_bias(df5, daily)
bias_map_orig = {l["date"]: l["bias"] for l in labels}

# Precompute swings for first swing direction (for T5 logic that uses first swing)
df1_sorted = df1.sort_values("timestamp")
from datetime import timezone, timedelta
IST = timezone(timedelta(hours=5, minutes=30))
all_candles = []
for _, row in df1_sorted.iterrows():
    dt = row["timestamp"].strftime("%Y-%m-%dT%H:%M:%S")
    all_candles.append(FlowCandle(date=dt, open=float(row["open"]), high=float(row["high"]), low=float(row["low"]), close=float(row["close"])))
swings = compute_swing_results(all_candles, {"timeCap": "09:29", "minBars": 14}, swing_count="whole")
by_day = defaultdict(list)
for s in swings:
    by_day[s["day"]].append(s)
for day in by_day:
    by_day[day] = sorted(by_day[day], key=lambda x: x["swing_index"])

# Daily EMA for T5a
daily_sorted = daily.sort_values("timestamp").copy()
daily_sorted["date_str"] = daily_sorted["timestamp"].dt.strftime("%Y-%m-%d")
daily_sorted["ema10"] = daily_sorted["close"].ewm(span=10, adjust=False).mean()
daily_sorted["color"] = daily_sorted.apply(lambda r: "green" if float(r["close"]) > float(r["open"]) else "red" if float(r["close"]) < float(r["open"]) else "doji", axis=1)
ema_daily_map = {row["date_str"]: row for _, row in daily_sorted.iterrows()}

# 5min EMA for T5b
df5_sorted = df5.sort_values("timestamp").copy()
for span in [20,50]:
    df5_sorted[f"ema{span}"] = df5_sorted["close"].ewm(span=span, adjust=False).mean()
df5_sorted["date_str"] = df5_sorted["timestamp"].dt.strftime("%Y-%m-%d")
# For each date, get last 5min ema
g5 = df5_sorted.groupby("date_str").last().reset_index()
ema5min_map = {row["date_str"]: row for _, row in g5.iterrows()}

def run_with_bias_map(bias_map, cfg, label):
    from src.intraday import EOD_EXIT
    df1_copy = df1.copy()
    df1_copy["timestamp"] = pd.to_datetime(df1_copy["timestamp"])
    df1_copy["ts"] = (df1_copy["timestamp"].astype("int64")//1_000_000_000).astype("int64")
    df1_copy = df1_copy.sort_values("timestamp").drop_duplicates(subset="ts", keep="last")
    dates = df1_copy["timestamp"].dt.strftime("%Y-%m-%d")
    groups = {d: g for d,g in df1_copy.groupby(dates, sort=True)}
    ordered = sorted(groups)
    prev_close = {ordered[i]: float(groups[ordered[i-1]]["close"].iloc[-1]) for i in range(1,len(ordered))}
    zone_map = {l["date"]: (l.get("overview") or {}).get("zone") for l in labels}
    def _ext(z): return "highs" if z in ("new_high","highs_extreme") else "lows" if z in ("new_low","lows_extreme") else None
    def _q(g):
        rows=g.reset_index(drop=True)
        return [float(r["high"])-float(r["low"]) for _,r in rows.iloc[1:].iterrows() if r["timestamp"].strftime("%H:%M") < EOD_EXIT]
    day_ranges = {d: _q(groups[d]) for d in ordered}
    avg_by_date = {}
    for idx,d in enumerate(ordered):
        flat=[]
        for j in range(max(0, idx-10), idx):
            flat.extend(day_ranges[ordered[j]])
        avg_by_date[d]= sum(flat)/len(flat) if flat else None
    traded = set(groups) & set(bias_map.keys())
    days=[]
    for d in sorted(traded):
        g = groups[d]
        gap_val = float(g["open"].iloc[0])
        pc = prev_close.get(d)
        gap="flat"
        if pc:
            frac=abs(gap_val-pc)/pc
            gap="flat" if frac<=cfg["gap_pct"] else "gap-up" if gap_val>pc else "gap-down"
        ctx={"gap":gap,"extreme":_ext(zone_map.get(d)),"avg_range":avg_by_date.get(d)}
        days.append(simulate_day_1min(g, bias_map[d], cfg=cfg, ctx=ctx))
    all_trades=[t for dy in days for t in dy["trades"]]
    wins=[t for t in all_trades if t["r_multiple"]>0]
    from collections import Counter
    outcomes=Counter(t["outcome"] for t in all_trades)
    total_r = round(sum(t["r_multiple"] for t in all_trades),2)
    avg_r = round(total_r/len(all_trades),2) if all_trades else 0
    win_rate = round(len(wins)/len(all_trades)*100,1) if all_trades else 0
    gross_win = sum(r for r in [t["r_multiple"] for t in all_trades] if r>0)
    gross_loss = sum(-r for r in [t["r_multiple"] for t in all_trades] if r<0)
    pf = gross_win/gross_loss if gross_loss>0 else 999 if gross_win>0 else 0
    pf=round(pf,2)
    longs = sum(1 for t in all_trades if t["dir"]=="long")
    shorts = sum(1 for t in all_trades if t["dir"]=="short")
    days_traded = sum(1 for dy in days if dy["trades"])
    print(f"\n=== {label} ===")
    print(f"Trades {len(all_trades)} Wins {len(wins)} Win% {win_rate} TotalR {total_r} Avg {avg_r} PF {pf} Days {days_traded}/{len(days)} L/S {longs}/{shorts} Outcomes {dict(outcomes)}")
    return {"label":label,"cfg":cfg,"trades":len(all_trades),"wins":len(wins),"win_rate":win_rate,"total_r":total_r,"avg_r":avg_r,"pf":pf}

base_cfg = {"execution":"1min","sl_mode":"prev_pivot","rr_target":4.0,"min_sl_pts":13,"breakeven_r":1.0,"gap_pct":0.0027,"ft_fail_enabled":True,"max_entries":2,"entry_cutoff":"15:15","second_trade_after":"always","swing_traverse":True,"need_opp_swing":True}

# T5a Daily EMA10 (already done, but re-run for consistency)
ema_daily_bias = {}
for day in bias_map_orig:
    if day not in ema_daily_map:
        ema_daily_bias[day] = "unbiased"
        continue
    row = ema_daily_map[day]
    close = float(row["close"])
    ema10 = float(row["ema10"])
    if close > ema10:
        ema_daily_bias[day] = "bullish"
    elif close < ema10:
        ema_daily_bias[day] = "bearish"
    else:
        ema_daily_bias[day] = "unbiased"
t5a = run_with_bias_map(ema_daily_bias, base_cfg, "T5a Daily EMA10 (close vs EMA10)")

# T5b 5min EMA20 (intraday)
ema_5min_bias = {}
for day in bias_map_orig:
    if day not in ema5min_map:
        ema_5min_bias[day] = "unbiased"
        continue
    row = ema5min_map[day]
    # Use last 5min close vs EMA20_5m
    close_5m = float(row["close"])
    ema20 = float(row["ema20"])
    if close_5m > ema20:
        ema_5min_bias[day] = "bullish"
    elif close_5m < ema20:
        ema_5min_bias[day] = "bearish"
    else:
        ema_5min_bias[day] = "unbiased"
t5b = run_with_bias_map(ema_5min_bias, base_cfg, "T5b 5min EMA20 (5m close vs EMA20)")

# T5c 5min cross 20>50
ema_cross_bias = {}
for day in bias_map_orig:
    if day not in ema5min_map:
        ema_cross_bias[day] = "unbiased"
        continue
    row = ema5min_map[day]
    ema20 = float(row["ema20"])
    ema50 = float(row["ema50"])
    if ema20 > ema50:
        ema_cross_bias[day] = "bullish"
    elif ema20 < ema50:
        ema_cross_bias[day] = "bearish"
    else:
        ema_cross_bias[day] = "unbiased"
t5c = run_with_bias_map(ema_cross_bias, base_cfg, "T5c 5min EMA20>50 cross")

# T5d Both daily and 5min agree
both_bias = {}
for day in bias_map_orig:
    d = ema_daily_bias.get(day, "unbiased")
    m = ema_5min_bias.get(day, "unbiased")
    # Also need cross?
    c = ema_cross_bias.get(day, "unbiased")
    # Require daily and 5min cross agree
    if d == c and d != "unbiased":
        both_bias[day] = d
    else:
        both_bias[day] = "unbiased"
t5d = run_with_bias_map(both_bias, base_cfg, "T5d Both Daily EMA10 + 5min Cross agree (else unbiased)")

print("\n=== SUMMARY ===")
for t in [t5a, t5b, t5c, t5d]:
    print(f"{t['label']}: Trades {t['trades']} WR {t['win_rate']}% R {t['total_r']} PF {t['pf']}")

