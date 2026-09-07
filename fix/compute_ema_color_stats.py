import pandas as pd
from pathlib import Path

# Load daily
daily_path = Path(r"C:\Users\Pravin\Desktop\main\AT_Trading\data\nifty_daily.csv")
df_daily = pd.read_csv(daily_path)
df_daily["timestamp"] = pd.to_datetime(df_daily["timestamp"])
df_daily = df_daily.sort_values("timestamp")
df_daily["date_str"] = df_daily["timestamp"].dt.strftime("%Y-%m-%d")
df_daily["color"] = df_daily.apply(lambda r: "green" if float(r["close"]) > float(r["open"]) else "red" if float(r["close"]) < float(r["open"]) else "doji", axis=1)
# EMAs on close
for span in [5,10,20]:
    df_daily[f"ema{span}"] = df_daily["close"].ewm(span=span, adjust=False).mean()
    df_daily[f"hl2"] = (df_daily["high"] + df_daily["low"])/2
    df_daily[f"ema{span}_hl2"] = df_daily["hl2"].ewm(span=span, adjust=False).mean()

# 5min for daily aggregation
min5_path = Path(r"C:\Users\Pravin\Desktop\main\AT_Trading\data\nifty_5min.csv")
df5 = pd.read_csv(min5_path)
df5["timestamp"] = pd.to_datetime(df5["timestamp"])
df5 = df5.sort_values("timestamp")
# Compute 5min EMA 20 and 50 on close
for span in [20,50]:
    df5[f"ema{span}"] = df5["close"].ewm(span=span, adjust=False).mean()
# For each daily date, get last 5min close and ema of that day
df5["date_str"] = df5["timestamp"].dt.strftime("%Y-%m-%d")
# For each date, take last 5min bar's ema
g5 = df5.groupby("date_str").last().reset_index()
g5 = g5[["date_str", "close", "ema20", "ema50"]]
g5 = g5.rename(columns={"close":"close_5m_last", "ema20":"ema20_5m", "ema50":"ema50_5m"})
merged = pd.merge(df_daily, g5, on="date_str", how="left")

def print_table(df, ema_col, color_col="color", label=""):
    # 2x2 table: below vs above, red vs green
    # below = close < ema
    df = df.dropna(subset=[ema_col])
    df["below"] = df["close"] < df[ema_col]
    # For 5min ema, compare close_5m_last vs ema?
    # For daily, close vs ema
    a = len(df[(df["below"]) & (df[color_col]=="red")])
    b = len(df[(df["below"]) & (df[color_col]=="green")])
    c = len(df[(~df["below"]) & (df[color_col]=="green")])
    d = len(df[(~df["below"]) & (df[color_col]=="red")])
    total = len(df)
    print(f"\n=== {label} EMA {ema_col} vs color ===")
    print(df[[color_col, ema_col, "below"]].head().to_string())
    print(f"Table: rows=below? cols=color")
    print(f"                red    green   total")
    print(f"below      {a:4d}   {b:4d}   {a+b:4d}")
    print(f"above      {d:4d}   {c:4d}   {c+d:4d}")
    print(f"total      {a+d:4d}   {b+c:4d}   {total:4d}")
    if (a+b)>0:
        print(f"P(red|below) = {a}/{a+b} = {a/(a+b)*100:.1f}%  (if below EMA, how often red?)")
    if (c+d)>0:
        print(f"P(green|above)= {c}/{c+d} = {c/(c+d)*100:.1f}%")
    if (a+d)>0:
        print(f"P(below|red) = {a}/{a+d} = {a/(a+d)*100:.1f}%")
    if (b+c)>0:
        print(f"P(above|green)= {c}/{b+c} = {c/(b+c)*100:.1f}%")
    # Also P(below) etc
    print(f"P(below) = {a+b}/{total} = {(a+b)/total*100:.1f}%")
    # Also test predictive for next day: does below today predict red tomorrow?
    df_sorted = df.sort_values("timestamp")
    df_sorted["next_color"] = df_sorted[color_col].shift(-1)
    df_sorted["next_below"] = df_sorted["below"].shift(-1)
    # For those below today, what is next day color?
    below_today = df_sorted[df_sorted["below"]]
    # Next day red?
    next_red_given_below = len(below_today[below_today["next_color"]=="red"])
    next_green_given_below = len(below_today[below_today["next_color"]=="green"])
    total_below = len(below_today.dropna(subset=["next_color"]))
    if total_below>0:
        print(f"Predictive: P(next red | below today) = {next_red_given_below}/{total_below} = {next_red_given_below/total_below*100:.1f}%")
        print(f"Predictive: P(next green | above today) = {len(df_sorted[(~df_sorted['below']) & (df_sorted['next_color']=='green')].dropna())}/{len(df_sorted[~df_sorted['below']].dropna())*100:.1f}%")
    # Simpler
    above_today = df_sorted[~df_sorted["below"]]
    next_green_given_above = len(above_today[above_today["next_color"]=="green"])
    total_above = len(above_today.dropna(subset=["next_color"]))
    if total_above>0:
        print(f"P(next green | above today) = {next_green_given_above}/{total_above} = {next_green_given_above/total_above*100:.1f}%")

# Daily EMAs
for span in [5,10,20]:
    print_table(df_daily, f"ema{span}", label=f"Daily close vs EMA{span}")

for span in [5,10,20]:
    print_table(df_daily, f"ema{span}_hl2", label=f"Daily hl2 vs EMA{span}_hl2")

# 5min EMAs merged
# For 5min, we need to compare 5min last close vs 5min EMA, vs daily color?
# Let's see correlation between 5min trend and daily color
merged = merged.dropna(subset=["ema20_5m","ema50_5m"])
merged["below_20_5m"] = merged["close_5m_last"] < merged["ema20_5m"]
merged["below_50_5m"] = merged["close_5m_last"] < merged["ema50_5m"]
merged["ema_cross_5m"] = merged["ema20_5m"] > merged["ema50_5m"]  # uptrend if 20>50

print("\n=== 5min EMA20 vs daily color ===")
a = len(merged[(merged["below_20_5m"]) & (merged["color"]=="red")])
b = len(merged[(merged["below_20_5m"]) & (merged["color"]=="green")])
c = len(merged[(~merged["below_20_5m"]) & (merged["color"]=="green")])
d = len(merged[(~merged["below_20_5m"]) & (merged["color"]=="red")])
total=len(merged)
print(f"below_20_5m & red {a}, below & green {b}, above & green {c}, above & red {d}, total {total}")
if (a+b)>0:
    print(f"P(red|below_20_5m) = {a/(a+b)*100:.1f}%")
if (c+d)>0:
    print(f"P(green|above_20_5m)= {c/(c+d)*100:.1f}%")

print("\n=== 5min EMA cross 20>50 vs daily color ===")
a = len(merged[(merged["ema_cross_5m"]) & (merged["color"]=="green")])
b = len(merged[(merged["ema_cross_5m"]) & (merged["color"]=="red")])
c = len(merged[(~merged["ema_cross_5m"]) & (merged["color"]=="red")])
d = len(merged[(~merged["ema_cross_5m"]) & (merged["color"]=="green")])
total=len(merged)
print(f"cross up (20>50) & green {a}, cross up & red {b}, cross down & red {c}, cross down & green {d}")
if (a+b)>0:
    print(f"P(green|cross up) = {a/(a+b)*100:.1f}%")
if (c+d)>0:
    print(f"P(red|cross down) = {c/(c+d)*100:.1f}%")

# Also check P(next day color | 5min cross)
merged_sorted = merged.sort_values("timestamp")
merged_sorted["next_color"] = merged_sorted["color"].shift(-1)
# cross up today, next day green?
cross_up = merged_sorted[merged_sorted["ema_cross_5m"]]
next_green = len(cross_up[cross_up["next_color"]=="green"].dropna())
total_cross_up = len(cross_up.dropna(subset=["next_color"]))
if total_cross_up>0:
    print(f"P(next green | cross up today) = {next_green}/{total_cross_up} = {next_green/total_cross_up*100:.1f}%")
cross_down = merged_sorted[~merged_sorted["ema_cross_5m"]]
next_red = len(cross_down[cross_down["next_color"]=="red"].dropna())
total_cross_down = len(cross_down.dropna(subset=["next_color"]))
if total_cross_down>0:
    print(f"P(next red | cross down today) = {next_red}/{total_cross_down} = {next_red/total_cross_down*100:.1f}%")

print("\nDone")
