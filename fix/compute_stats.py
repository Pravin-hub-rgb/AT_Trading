import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from src import bias as bias_svc, config
from src.firstswing import compute_swing_results
from src.walker import FlowCandle
from datetime import timezone, timedelta
import numpy as np

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

# Bias
labels = bias_svc.compute_bias(df5, daily)
bias_map = {l["date"]: l for l in labels}

# Daily df for candle color
if daily is not None:
    daily = daily.sort_values("timestamp")
    daily["date_str"] = daily["timestamp"].dt.strftime("%Y-%m-%d")
    daily_map = {row["date_str"]: row for _, row in daily.iterrows()}
else:
    daily_map = {}

# 1min candles for swing
df1 = df1.sort_values("timestamp")
IST = timezone(timedelta(hours=5, minutes=30))
all_candles = []
for _, row in df1.iterrows():
    ts = int(row["timestamp"].timestamp())
    # Use IST string as engine expects
    # df timestamp is already IST? It is naive, but we treat as IST
    # Use the original string's time
    dt = row["timestamp"].strftime("%Y-%m-%dT%H:%M:%S")
    all_candles.append(FlowCandle(date=dt, open=float(row["open"]), high=float(row["high"]), low=float(row["low"]), close=float(row["close"])))

# Compute whole day swings (all swings per day)
swings = compute_swing_results(all_candles, {"timeCap": "09:29", "minBars": 14}, swing_count="whole")
from collections import defaultdict, Counter
by_day = defaultdict(list)
for s in swings:
    by_day[s["day"]].append(s)

# Sort each day's swings by swing_index
for day in by_day:
    by_day[day] = sorted(by_day[day], key=lambda x: x["swing_index"])

# Stats containers
total_days = len(by_day)
first_buy = 0
first_sell = 0
first_none = 0
second_opposite = 0
second_same = 0
second_none = 0
three_same = 0
three_consecutive_counts = Counter()
# For each day, check sequences
for day, lst in by_day.items():
    if not lst:
        first_none += 1
        second_none += 1
        continue
    first = lst[0]
    dir1 = first["seg"]["dir"]  # B or S
    if dir1 == "B":
        first_buy += 1
    else:
        first_sell += 1
    if len(lst) >= 2:
        second = lst[1]
        dir2 = second["seg"]["dir"]
        if dir2 != dir1:
            second_opposite += 1
        else:
            second_same += 1
    else:
        second_none += 1
    if len(lst) >= 3:
        d1 = lst[0]["seg"]["dir"]
        d2 = lst[1]["seg"]["dir"]
        d3 = lst[2]["seg"]["dir"]
        if d1 == d2 == d3:
            three_same += 1
        # count pattern
        pattern = f"{d1}-{d2}-{d3}"
        three_consecutive_counts[pattern] += 1

print(f"Total days with swings: {total_days}")
print(f"First swing B (buying/up): {first_buy} ({first_buy/total_days*100:.1f}%)")
print(f"First swing S (selling/down): {first_sell} ({first_sell/total_days*100:.1f}%)")
print(f"First swing none: {first_none}")
print(f"Second opposite to first: {second_opposite} ({second_opposite/total_days*100:.1f}%)")
print(f"Second same as first: {second_same} ({second_same/total_days*100:.1f}%)")
print(f"Second none: {second_none}")
print(f"Three consecutive same (1-2-3 all B or all S): {three_same} ({three_same/total_days*100:.1f}%)")
print(f"Three swing patterns:")
for pat, cnt in three_consecutive_counts.most_common():
    print(f"  {pat}: {cnt}")

# Bias vs first swing
from collections import Counter as C
bias_first = C()
bias_second_opposite = C()
bias_daily_color = C()
daily_color_stats = []
for day in sorted(by_day.keys()):
    if day not in bias_map:
        continue
    bias = bias_map[day]["bias"]  # bullish/bearish/unbiased
    lst = by_day[day]
    if not lst:
        continue
    first_dir = lst[0]["seg"]["dir"]  # B/S
    # Map B->buying, S->selling
    first_swing = "buying" if first_dir=="B" else "selling"
    bias_first[(bias, first_swing)] += 1
    if len(lst) >= 2:
        second_dir = lst[1]["seg"]["dir"]
        second_swing = "buying" if second_dir=="B" else "selling"
        # opposite?
        opp = "opposite" if second_dir != first_dir else "same"
        bias_second_opposite[(bias, opp)] += 1
    # Daily candle color
    if day in daily_map:
        row = daily_map[day]
        o = float(row["open"])
        c = float(row["close"])
        col = "green" if c > o else "red" if c < o else "doji"
        bias_daily_color[(bias, col)] += 1
        daily_color_stats.append((day, bias, col, first_swing))

print("\nBias vs First Swing:")
for k,v in bias_first.items():
    print(f"  bias {k[0]:8s} first {k[1]:7s}: {v}")

print("\nBias vs Second opposite/same:")
for k,v in bias_second_opposite.items():
    print(f"  bias {k[0]:8s} second {k[1]:8s}: {v}")

print("\nBias vs Daily candle color (daily open->close):")
for k,v in bias_daily_color.items():
    print(f"  bias {k[0]:8s} daily {k[1]:5s}: {v}")

# Weak vs strong swings
# Compute start-end distance pts for each swing
distances = []
for day, lst in by_day.items():
    for s in lst:
        seg = s["seg"]
        dist = abs(seg["end_px"] - seg["start_px"])
        distances.append(dist)

if distances:
    arr = np.array(distances)
    print(f"\nSwing distance pts stats (all swings {len(distances)}):")
    print(f"  mean {arr.mean():.1f} median {np.median(arr):.1f} p25 {np.percentile(arr,25):.1f} p75 {np.percentile(arr,75):.1f} p90 {np.percentile(arr,90):.1f} min {arr.min():.1f} max {arr.max():.1f}")
    # define weak < 15 pts, strong > 30 pts? Let's see distribution
    weak_thr = 15
    strong_thr = 30
    weak = (arr < weak_thr).sum()
    strong = (arr > strong_thr).sum()
    mid = len(arr) - weak - strong
    print(f"  weak <{weak_thr}: {weak} ({weak/len(arr)*100:.1f}%)")
    print(f"  mid {weak_thr}-{strong_thr}: {mid} ({mid/len(arr)*100:.1f}%)")
    print(f"  strong >{strong_thr}: {strong} ({strong/len(arr)*100:.1f}%)")

    # For first swings only
    first_dists = []
    for day, lst in by_day.items():
        if lst:
            seg = lst[0]["seg"]
            first_dists.append(abs(seg["end_px"] - seg["start_px"]))
    if first_dists:
        arr2 = np.array(first_dists)
        print(f"\nFirst swing distance:")
        print(f"  mean {arr2.mean():.1f} median {np.median(arr2):.1f} p25 {np.percentile(arr2,25):.1f} p75 {np.percentile(arr2,75):.1f}")
        print(f"  weak <15: {(arr2<15).sum()} ({(arr2<15).sum()/len(arr2)*100:.1f}%)")
        print(f"  strong >30: {(arr2>30).sum()} ({(arr2>30).sum()/len(arr2)*100:.1f}%)")

# Check: after weak first swing, is next opposite bigger?
weak_next_bigger = 0
weak_next_total = 0
strong_next_bigger = 0
strong_next_total = 0
for day, lst in by_day.items():
    if len(lst) >= 2:
        d1 = abs(lst[0]["seg"]["end_px"] - lst[0]["seg"]["start_px"])
        d2 = abs(lst[1]["seg"]["end_px"] - lst[1]["seg"]["start_px"])
        if d1 < 15:
            weak_next_total += 1
            if d2 > d1:
                weak_next_bigger += 1
        elif d1 > 30:
            strong_next_total += 1
            if d2 > d1:
                strong_next_bigger += 1

if weak_next_total:
    print(f"\nAfter weak first (<15, n={weak_next_total}), second bigger than first: {weak_next_bigger} ({weak_next_bigger/weak_next_total*100:.1f}%)")
if strong_next_total:
    print(f"After strong first (>30, n={strong_next_total}), second bigger than first: {strong_next_bigger} ({strong_next_bigger/strong_next_total*100:.1f}%)")

# EMA stats
# Use daily close for EMA
if daily is not None and len(daily) > 20:
    daily_sorted = daily.sort_values("timestamp")
    daily_sorted["ema5"] = daily_sorted["close"].ewm(span=5, adjust=False).mean()
    daily_sorted["ema10"] = daily_sorted["close"].ewm(span=10, adjust=False).mean()
    # For each day, check if close below ema5, ema10 etc and bias
    ema_stats = Counter()
    for _, row in daily_sorted.iterrows():
        d = row["date_str"]
        if d not in bias_map or d not in by_day or not by_day[d]:
            continue
        close = float(row["close"])
        ema5 = float(row["ema5"])
        ema10 = float(row["ema10"])
        bias = bias_map[d]["bias"]
        first_dir = by_day[d][0]["seg"]["dir"]
        first_swing = "buying" if first_dir=="B" else "selling"
        # EMA relation
        below5 = close < ema5
        below10 = close < ema10
        ema_stats[(bias, first_swing, below5, below10)] += 1
    print("\nEMA vs Bias vs First Swing (sample):")
    for k,v in list(ema_stats.items())[:10]:
        print(f"  bias {k[0]:8s} first {k[1]:7s} below5 {k[2]} below10 {k[3]}: {v}")
    # Also overall below stats
    below5_count = (daily_sorted["close"] < daily_sorted["ema5"]).sum()
    below10_count = (daily_sorted["close"] < daily_sorted["ema10"]).sum()
    print(f"\nDaily close below EMA5: {below5_count}/{len(daily_sorted)} ({below5_count/len(daily_sorted)*100:.1f}%)")
    print(f"Daily close below EMA10: {below10_count}/{len(daily_sorted)} ({below10_count/len(daily_sorted)*100:.1f}%)")

# Additional crazy stats: how many days there are 5+ swings?
swing_counts = Counter(len(lst) for lst in by_day.values())
print("\nSwing counts per day:")
for cnt in sorted(swing_counts):
    print(f"  {cnt} swings: {swing_counts[cnt]} days")

# How many days first and second same and third opposite etc
# Already did three_same, now more: first buying then selling then buying etc
# Let's compute 4-swing streaks
four_same = 0
for day,lst in by_day.items():
    if len(lst) >=4:
        dirs = [s["seg"]["dir"] for s in lst[:4]]
        if len(set(dirs))==1:
            four_same+=1
print(f"\nFour consecutive same direction (first 4 all B or all S): {four_same} days")

# Bias vs actual daily direction vs first swing opposite trade idea
# "we don't care about bias, just trade opposite of first swing"
# Let's compute win rate if we always trade opposite of first swing (ignoring bias) using simple backtest logic? We can approximate with our 1min engine but with bias forced to opposite?
# For now just count how many days opposite trade would be long/short
opp_long = 0
opp_short = 0
for day,lst in by_day.items():
    if not lst:
        continue
    first_dir = lst[0]["seg"]["dir"]
    # opposite trade
    # if first is B (buying/up), opposite is S (selling) -> trade short? Wait per entry theory: buying first -> need selling swing to buy? Actually entry theory: for buying -> wait for selling swing then buy. So opposite trade is in direction of bias? Let's define: first buying -> trade long (buy), first selling -> trade short. That's trading *with* the reversal, not with first swing direction.
    # The user says: first swing is selling so we trade buying (long). So opposite of first swing direction = trade direction.
    # So first B -> trade short? No, B is buying swing (up), then we wait for selling swing to buy? That's confusing. Let's use the doc: for buying -> wait for selling swing then buy. So first swing buying -> trade long. So trade is same as first swing? No, first buying -> trade long (same). Wait first buying is up, trade long is up, same.
    # Actually per entry theory.md: for buying -> wait for selling swing then buy. So if first swing is buying, we are already in buying, but we wait for selling? So first swing buying -> second selling -> trade long. So trade is not opposite of first, it's opposite of second? This is confusing.
    # Let's just count: trade opposite of first swing means if first is B, trade short; if first is S, trade long. That's the "opposite of first swing" idea.
    if first_dir=="B":
        opp_short+=1
    else:
        opp_long+=1
print(f"\nOpposite of first swing trade (B->short, S->long): long {opp_long} days, short {opp_short} days")

# How many days where bias matches opposite trade vs not
bias_match = 0
bias_mismatch = 0
for day,lst in by_day.items():
    if day not in bias_map or not lst:
        continue
    bias = bias_map[day]["bias"]
    first_dir = lst[0]["seg"]["dir"]
    # opposite trade direction
    opp_dir = "bearish" if first_dir=="B" else "bullish"  # B->short->bearish, S->long->bullish
    if bias == opp_dir:
        bias_match+=1
    elif bias == "unbiased":
        pass
    else:
        bias_mismatch+=1
print(f"Bias matches opposite trade: {bias_match} days, mismatches: {bias_mismatch} days")

# Gap stats
gap_stats = Counter()
for day in by_day:
    if day in bias_map:
        # bias_map's overview has gap? Actually bias_map's details has gap via ctx? Let's use labels' overview zone?
        # We need to recompute gap for each day using 5min open vs prev close like in run_backtest
        pass

print("\nDone stats")
