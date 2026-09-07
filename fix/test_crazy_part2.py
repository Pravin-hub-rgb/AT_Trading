import pandas as pd, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from src import bias as bias_svc, config
from src.firstswing import compute_swing_results
from src.walker import FlowCandle
from src.intraday_1m_standalone import simulate_day_1min
from datetime import timezone, timedelta
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

# Precompute swings for T5/T6
df1_sorted = df1.sort_values("timestamp")
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

# Daily for EMA and color
daily_sorted = daily.sort_values("timestamp").copy() if daily is not None else None
daily_sorted["date_str"] = daily_sorted["timestamp"].dt.strftime("%Y-%m-%d")
daily_sorted["ema5"] = daily_sorted["close"].ewm(span=5, adjust=False).mean()
daily_sorted["ema10"] = daily_sorted["close"].ewm(span=10, adjust=False).mean()
daily_sorted["color"] = daily_sorted.apply(lambda r: "green" if float(r["close"]) > float(r["open"]) else "red" if float(r["close"]) < float(r["open"]) else "doji", axis=1)
ema_map = {row["date_str"]: row for _, row in daily_sorted.iterrows()}

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
    print(f"cfg: {cfg}")
    print(f"Trades {len(all_trades)} Wins {len(wins)} Win% {win_rate} TotalR {total_r} Avg {avg_r} PF {pf} Days {days_traded}/{len(days)} L/S {longs}/{shorts} Outcomes {dict(outcomes)}")
    return {"label":label,"cfg":cfg,"trades":len(all_trades),"wins":len(wins),"win_rate":win_rate,"total_r":total_r,"avg_r":avg_r,"pf":pf,"days_traded":days_traded,"days_total":len(days),"longs":longs,"shorts":shorts,"outcomes":dict(outcomes)}

base_cfg = {"execution":"1min","sl_mode":"prev_pivot","rr_target":4.0,"min_sl_pts":13,"breakeven_r":1.0,"gap_pct":0.0027,"ft_fail_enabled":True,"max_entries":2,"entry_cutoff":"15:15","second_trade_after":"always","swing_traverse":True,"need_opp_swing":True}

# T5 EMA 5/10 daily filter
# Logic: if close > EMA10 (uptrend) and first swing selling -> allow long, if close < EMA10 and first buying -> allow short, else skip (unbiased)
ema_map_bias = {}
for day in bias_map_orig:
    if day not in by_day or not by_day[day] or day not in ema_map:
        ema_map_bias[day] = "unbiased"
        continue
    first_dir = by_day[day][0]["seg"]["dir"]
    first_swing = "buying" if first_dir=="B" else "selling"
    row = ema_map[day]
    close = float(row["close"])
    ema10 = float(row["ema10"])
    # Uptrend if close > ema10
    uptrend = close > ema10
    downtrend = close < ema10
    # Only allow trades that align with trend + first swing opposite logic
    # If uptrend and first selling -> long (buy), if downtrend and first buying -> short
    # else skip
    if uptrend and first_swing == "selling":
        ema_map_bias[day] = "bullish"  # will trade long
    elif downtrend and first_swing == "buying":
        ema_map_bias[day] = "bearish"  # will trade short
    elif uptrend and first_swing == "buying":
        # Uptrend but first is buying (already up), maybe wait for selling? That's also long but first is buying -> would be conservative long, need selling swing
        # In uptrend, we still want to buy, so allow it
        # Actually if uptrend and first buying, the reference is selling for long, so we still want long
        # So we can allow both first directions as long as trend is up -> long
        # For simplicity, if uptrend, set bullish regardless of first swing
        ema_map_bias[day] = "bullish"
    elif downtrend and first_swing == "selling":
        ema_map_bias[day] = "bearish"
    else:
        ema_map_bias[day] = "unbiased"

t5 = run_with_bias_map(ema_map_bias, base_cfg, "T5 EMA10 trend filter (close vs EMA10)")

# T6 Streak + weak (combine T4 and T3)
# Use streak regime but only if reference swing weak <35
# We need to compute streak regime again (same as T4) and then filter by weak
# Reuse streak logic from previous file: we need to recompute regime_for_day
daily_sorted2 = daily.sort_values("timestamp").copy()
daily_sorted2["color"] = daily_sorted2.apply(lambda r: "green" if float(r["close"]) > float(r["open"]) else "red" if float(r["close"]) < float(r["open"]) else "doji", axis=1)
daily_sorted2["date_str"] = daily_sorted2["timestamp"].dt.strftime("%Y-%m-%d")
colors = list(daily_sorted2[["date_str","color"]].itertuples(index=False, name=None))
regime_for_day = {}
for i in range(len(colors)):
    date_str = colors[i][0]
    if i == 0:
        regime_for_day[date_str] = "unbiased"
        continue
    cur_reg = None
    streak = 0
    pause = False
    for j in range(i):
        col = colors[j][1]
        if pause:
            if col == "green":
                cur_reg = "long"
            elif col == "red":
                cur_reg = "short"
            else:
                cur_reg = None
            streak = 1 if cur_reg else 0
            pause = False
            continue
        if cur_reg is None:
            if col == "green":
                cur_reg = "long"
                streak = 1
            elif col == "red":
                cur_reg = "short"
                streak = 1
            continue
        regime_color = "green" if cur_reg=="long" else "red"
        if col == regime_color:
            streak += 1
        else:
            if streak >= 3:
                pause = True
            else:
                pause = True
    if pause:
        regime_for_day[date_str] = "unbiased"
    else:
        if cur_reg == "long":
            regime_for_day[date_str] = "bullish"
        elif cur_reg == "short":
            regime_for_day[date_str] = "bearish"
        else:
            regime_for_day[date_str] = "unbiased"

# Now combine with weak filter
streak_weak_map = {}
for day in bias_map_orig:
    streak_bias = regime_for_day.get(day, "unbiased")
    if streak_bias == "unbiased":
        streak_weak_map[day] = "unbiased"
        continue
    # Check weak
    if day not in by_day or not by_day[day]:
        streak_weak_map[day] = "unbiased"
        continue
    # Determine reference swing for this day (like T3 logic)
    bias = streak_bias  # streak gives us bias
    first_dir = by_day[day][0]["seg"]["dir"]
    first_swing = "buying" if first_dir=="B" else "selling"
    is_opposite = (bias=="bullish" and first_swing=="selling") or (bias=="bearish" and first_swing=="buying")
    if is_opposite:
        ref_dist = abs(by_day[day][0]["seg"]["end_px"] - by_day[day][0]["seg"]["start_px"])
    else:
        opp = None
        for s in by_day[day][1:]:
            if s["seg"]["dir"] != first_dir:
                opp = s
                break
        if opp:
            ref_dist = abs(opp["seg"]["end_px"] - opp["seg"]["start_px"])
        else:
            streak_weak_map[day] = "unbiased"
            continue
    if ref_dist < 35:
        streak_weak_map[day] = streak_bias
    else:
        streak_weak_map[day] = "unbiased"

t6 = run_with_bias_map(streak_weak_map, base_cfg, "T6 Streak 3-1-1 + Weak (<35)")

print("\n=== SUMMARY ===")
for t in [t5, t6]:
    print(f"{t['label']}: Trades {t['trades']} WR {t['win_rate']}% R {t['total_r']} PF {t['pf']}")

