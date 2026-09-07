import pandas as pd, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from src import bias as bias_svc, config
from src.firstswing import compute_swing_results
from src.walker import FlowCandle
from src.intraday_1m_standalone import simulate_day_1min, run_backtest_1min
from datetime import timezone, timedelta
import numpy as np
from collections import defaultdict, Counter

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

# Precompute bias and swings for tests that need them
labels = bias_svc.compute_bias(df5, daily)
bias_map_orig = {l["date"]: l["bias"] for l in labels}

# Whole day swings for opposite test
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

# Daily color for streak
daily = daily.sort_values("timestamp") if daily is not None else None
daily["date_str"] = daily["timestamp"].dt.strftime("%Y-%m-%d")
daily_map = {row["date_str"]: row for _, row in daily.iterrows()}
daily_colors = {}
for _, row in daily.iterrows():
    d = row["date_str"]
    o = float(row["open"]); c = float(row["close"])
    col = "green" if c > o else "red" if c < o else "doji"
    daily_colors[d] = col

# Helper to run backtest with custom bias_map
def run_with_bias_map(bias_map, cfg, label):
    # Use run_backtest_1min but we need to inject custom bias_map
    # run_backtest_1min internally recomputes bias_map from labels, so we can't directly
    # Instead we will call simulate_day_1min per day with custom bias
    # Replicate run_backtest logic but with custom map
    from src.intraday import EOD_EXIT
    df1_copy = df1.copy()
    # groups etc
    df1_copy["timestamp"] = pd.to_datetime(df1_copy["timestamp"])
    # need ts
    df1_copy["ts"] = (df1_copy["timestamp"].astype("int64")//1_000_000_000).astype("int64")
    df1_copy = df1_copy.sort_values("timestamp").drop_duplicates(subset="ts", keep="last")
    dates = df1_copy["timestamp"].dt.strftime("%Y-%m-%d")
    groups = {d: g for d,g in df1_copy.groupby(dates, sort=True)}
    ordered = sorted(groups)
    prev_close = {ordered[i]: float(groups[ordered[i-1]]["close"].iloc[-1]) for i in range(1,len(ordered))}
    # zone map from original labels for gap calc
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
            # need cfg gap_pct, default 0.0027
            gap_pct = cfg.get("gap_pct", 0.0027)
            gap="flat" if frac<=gap_pct else "gap-up" if gap_val>pc else "gap-down"
        ctx={"gap":gap,"extreme":_ext(zone_map.get(d)),"avg_range":avg_by_date.get(d)}
        # For weak filter test, we will add distance check inside simulate? For now generic
        days.append(simulate_day_1min(g, bias_map[d], cfg=cfg, ctx=ctx))
    all_trades=[t for dy in days for t in dy["trades"]]
    wins=[t for t in all_trades if t["r_multiple"]>0]
    from collections import Counter as C
    outcomes=C(t["outcome"] for t in all_trades)
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
    return {
        "label": label,
        "cfg": cfg,
        "trades": len(all_trades),
        "wins": len(wins),
        "win_rate": win_rate,
        "total_r": total_r,
        "avg_r": avg_r,
        "pf": pf,
        "days_traded": days_traded,
        "days_total": len(days),
        "longs": longs,
        "shorts": shorts,
        "outcomes": dict(outcomes),
        "days": days,
    }

# Baseline config (best logical from smart sweep)
base_cfg = {"execution":"1min","sl_mode":"prev_pivot","rr_target":4.0,"min_sl_pts":13,"breakeven_r":1.0,"gap_pct":0.0027,"ft_fail_enabled":True,"max_entries":2,"entry_cutoff":"15:15","second_trade_after":"always","swing_traverse":True,"need_opp_swing":True}

# T1 Baseline
t1 = run_with_bias_map(bias_map_orig, base_cfg, "T1 Baseline bias.py")

# T2 Opposite of first swing (ignore bias)
opp_map = {}
for day, lst in by_day.items():
    if not lst:
        opp_map[day] = "unbiased"
    else:
        first_dir = lst[0]["seg"]["dir"]  # B or S
        # B (buying) -> opposite short -> bearish, S -> bullish (long)
        opp_map[day] = "bearish" if first_dir=="B" else "bullish"
# For days not in by_day but in bias_map, keep original? Use opp for traded days only
# Merge with original for missing days
for day in bias_map_orig:
    if day not in opp_map:
        opp_map[day] = bias_map_orig[day]
t2 = run_with_bias_map(opp_map, base_cfg, "T2 Opposite of first swing (ignore bias)")

# T3 Weak-swing only (<35 pts) - we need to filter days where reference swing is weak
# For this test, we will modify simulate to skip if reference swing distance >35
# Instead of modifying engine, we will post-filter: if we detect that the day's reference swing (first swing) is strong >60, we skip that day (set bias to unbiased so no trade)
# But better is to check the swing that is actually traded (first swing for aggressive, second for conservative)
# For simplicity, filter based on first swing distance <35 (weak) - but we know first swing never <35, so this would filter all.
# So we need to filter based on *second* swing distance if conservative, or first swing if aggressive? Let's use the swing that we trade after.
# For now, let's implement a custom bias that sets unbiased for days where the relevant reference swing is strong >60
weak_map = {}
for day, lst in by_day.items():
    if day not in bias_map_orig:
        continue
    if not lst:
        weak_map[day] = "unbiased"
        continue
    # Determine which swing is reference for trade
    # We need to know trade_mode for that day (from bias)
    # Instead of recomputing, we approximate: if first swing opposite to bias (aggressive), reference is first swing; if same (conservative), reference is second swing
    # Let's use bias to decide
    bias = bias_map_orig[day]
    first_dir = lst[0]["seg"]["dir"]
    first_swing = "buying" if first_dir=="B" else "selling"
    # Determine trade_mode via classify_case logic (simplified)
    # We'll just use the actual trade_mode from a dummy run? For now, approximate with opposite check
    # If bias bullish and first selling => aggressive (first opposite), reference = first selling distance
    # If bias bullish and first buying => conservative, reference = second selling distance if exists
    # So we need second swing
    is_opposite = (bias=="bullish" and first_swing=="selling") or (bias=="bearish" and first_swing=="buying")
    if is_opposite:
        # aggressive, ref is first swing
        ref_dist = abs(lst[0]["seg"]["end_px"] - lst[0]["seg"]["start_px"])
    else:
        # conservative, need second swing opposite
        if len(lst) >=2:
            # Find first opposite to first
            opp = None
            for s in lst[1:]:
                if s["seg"]["dir"] != first_dir:
                    opp = s
                    break
            if opp:
                ref_dist = abs(opp["seg"]["end_px"] - opp["seg"]["start_px"])
            else:
                weak_map[day] = "unbiased"
                continue
        else:
            weak_map[day] = "unbiased"
            continue
    # Weak if <35, strong if >60 - we only allow weak
    if ref_dist < 35:
        weak_map[day] = bias_map_orig[day]  # keep original bias to allow trade
    else:
        weak_map[day] = "unbiased"  # skip strong

t3 = run_with_bias_map(weak_map, base_cfg, "T3 Weak-swing only (<35) - trade only if ref swing weak")

# T4 Daily streak 3-1-1
# Compute streak regime
# Need daily colors in order
daily_sorted = daily.sort_values("timestamp")
daily_sorted["color"] = daily_sorted.apply(lambda r: "green" if float(r["close"])>float(r["open"]) else "red" if float(r["close"])<float(r["open"]) else "doji", axis=1)
daily_sorted["date_str"] = daily_sorted["timestamp"].dt.strftime("%Y-%m-%d")
# Build regime map
regime_map = {}
regime = None  # "long" or "short" or None (pause)
streak = 0
prev_color = None
# We need to iterate daily in order and assign regime for *next* day trading
# Logic: Start with no regime. When we see 3 consecutive same colors, set regime to that direction and trade.
# On break (color != regime's color), still trade old regime for 1 day (fade), next day pause, then flip.

# Simpler: implement as described in ideas.md step-by-step
# We'll simulate day by day
colors = list(daily_sorted[["date_str","color"]].itertuples(index=False, name=None))
# colors is list of (date_str, color)
# We need to produce regime for each trading day (the day we trade, based on prior days)
# For day T, regime is determined by history up to T-1 (no lookahead)
# Let's simulate

regime_for_day = {}  # date_str -> bullish/bearish/unbiased
# Keep state
current_regime = None  # "long" or "short"
streak_count = 0
pause_next = False
prev_regime_color = None  # color of regime (green for long, red for short)

for idx, (date_str, color) in enumerate(colors):
    # The regime for *next* trading day is decided after processing today
    # For today itself, we already have a regime_for_day (computed from prior)
    # So first, assign regime_for_day for this date based on current state before processing today?
    # Actually for backtest, bias for day T is based on T-1's data, so regime for T is based on streak up to T-1.
    # So we should assign regime_for_day[date_str] = current_regime (or unbiased if pause)
    # But for the first few days, current_regime is None -> unbiased

    # To avoid off-by-one, we will iterate and set regime_for_day for *next* day after processing today
    # So we need to handle separately: for day 0, no prior, so unbiased
    pass

# Let's do proper loop: for each day index i, regime for day i is based on colors[0:i] (prior days)
# So we can compute for each i

for i in range(len(colors)):
    date_str = colors[i][0]
    # compute regime for this day based on prior colors 0..i-1
    if i == 0:
        regime_for_day[date_str] = "unbiased"
        continue
    # Build streak from prior days
    # We need to simulate the 3-1-1 logic for prior days to determine current regime
    # Instead of incremental, we can simulate the state machine for prior days 0..i-1 and see what regime it outputs for day i
    # Let's simulate from start up to i-1
    cur_reg = None
    streak = 0
    prev_col = None
    pause = False
    # We need to know what action was taken on each prior day to know streak
    # Simplify: we will simulate the exact 10-step example logic
    # For each prior day j, we know its color col_j, and we know what regime we were in before j, and whether we traded or paused on j
    # But for determining regime for day i, we only care about the state after processing day i-1

    # Let's simulate sequentially up to i-1
    for j in range(i):
        col = colors[j][1]
        if pause:
            # This day was pause, no trade, next regime will be set to col's direction
            # After pause, set regime to col's direction
            if col == "green":
                cur_reg = "long"
            elif col == "red":
                cur_reg = "short"
            else:
                cur_reg = None
            streak = 1 if cur_reg else 0  # start new streak with 1
            prev_col = col
            pause = False
            continue
        if cur_reg is None:
            # No regime yet, need 3 consecutive to establish?
            # Actually first green -> establish long, but we need 3? In example, day1 green -> from here we trade long only (so after day1, regime long)
            # So after seeing day j's color, if cur_reg is None, set it to that day's color
            if col == "green":
                cur_reg = "long"
                streak = 1
            elif col == "red":
                cur_reg = "short"
                streak = 1
            prev_col = col
            continue
        # We have a regime
        # Determine if col matches regime's color (green for long, red for short)
        regime_color = "green" if cur_reg=="long" else "red"
        if col == regime_color:
            streak += 1
            # continue regime
            prev_col = col
            # if streak was 3 and next is break, we will still trade old regime for one more day (fade)
            # That is handled when col != regime_color below
        else:
            # Break of streak
            if streak >= 3:
                # We have at least 3 in streak, so this break day we still trade old regime (fade)
                # So we do not flip yet, but next day will be pause
                # For now, keep cur_reg as is, but set pause for next day
                # Streak stays?
                # After this break day, next day is pause
                pause = True
                # streak remains? But after pause we will reset
                prev_col = col
                # Keep cur_reg for this break day (so day j was still old regime)
                # For next iteration, pause will handle
            else:
                # Streak <3, break means regime was not strong, we should maybe reset?
                # In example, they had 3 greens then red still long, then pause. If streak was only 2 and broke, what?
                # For now, if streak <3 and breaks, we just flip immediately? Or go to pause?
                # Let's go to pause as well to be safe
                pause = True
                prev_col = col
            # Note: cur_reg stays old for this day j (the break day still traded old)
            # The flip to new direction will happen after pause day
        # end loop for prior days
    # After processing up to i-1, the regime for day i is:
    # If pause is True for day i (meaning day i is pause day), then unbiased
    # Else cur_reg determines bias
    if pause:
        regime_for_day[date_str] = "unbiased"
    else:
        if cur_reg == "long":
            regime_for_day[date_str] = "bullish"
        elif cur_reg == "short":
            regime_for_day[date_str] = "bearish"
        else:
            regime_for_day[date_str] = "unbiased"

# Now we have regime_for_day for all days, use it as bias_map
streak_map = {}
for day in bias_map_orig:
    if day in regime_for_day:
        streak_map[day] = regime_for_day[day]
    else:
        streak_map[day] = "unbiased"

# Count stats for streak
from collections import Counter as C2
streak_counts = C2(regime_for_day.values())
print(f"\nStreak regime distribution: {dict(streak_counts)}")
# Also count how many days streak gave long vs short
t4 = run_with_bias_map(streak_map, base_cfg, "T4 Daily streak 3-1-1 (long/short regime)")

# Print summary for ideas.md
print("\n=== SUMMARY FOR IDEAS.MD ===")
for t in [t1, t2, t3, t4]:
    print(f"{t['label']}: Trades {t['trades']} WR {t['win_rate']}% R {t['total_r']} PF {t['pf']} Days {t['days_traded']}/{t['days_total']}")

