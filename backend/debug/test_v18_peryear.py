"""Streak analysis: what happens after long losing streaks?"""
import sys, statistics, math, random
from pathlib import Path
from collections import Counter
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v11_conditional_htf import simulate_htf_ltf_conditional
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

base = simulate_htf_ltf_conditional(
    c1h, sw1h, c15, sw15, fine_ltf=fine,
    sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
    cooldown_bars=20,
)
trades = base["ltf_trades"]

# A. RECOVERY ANALYSIS
print("=" * 72)
print("A. RECOVERY: What happens after N consecutive losses?")
print("=" * 72)

streaks = []
current_streak = 0
streak_start_idx = 0

for i, t in enumerate(trades):
    r = t["r_multiple"]
    if r <= 0:
        if current_streak == 0:
            streak_start_idx = i
        current_streak += 1
    else:
        if current_streak > 0:
            streaks.append({
                "length": current_streak,
                "start_idx": streak_start_idx,
                "end_idx": i - 1,
                "next_trade_r": r,
                "next_trade_date": t["entry_date"],
            })
        current_streak = 0

if current_streak > 0:
    streaks.append({
        "length": current_streak,
        "start_idx": streak_start_idx,
        "end_idx": len(trades) - 1,
        "next_trade_r": None,
        "next_trade_date": None,
    })

print(f"\nTotal streaks: {len(streaks)}")
print(f"Max streak: {max(s['length'] for s in streaks)}")

streak_groups = {}
for s in streaks:
    n = s["length"]
    if n not in streak_groups:
        streak_groups[n] = []
    streak_groups[n].append(s)

print(f"\n{'Streak':>8} {'Count':>6} {'Next AvgR':>12} {'Next Win%':>10} {'Next >1R':>10}")
print("-" * 50)
for n in sorted(streak_groups.keys()):
    group = streak_groups[n]
    next_rs = [s["next_trade_r"] for s in group if s["next_trade_r"] is not None]
    if next_rs:
        avg_next = statistics.mean(next_rs)
        win_pct = sum(1 for r in next_rs if r > 0) / len(next_rs) * 100
        big_win_pct = sum(1 for r in next_rs if r > 1) / len(next_rs) * 100
        print(f"  {n:>5}L   {len(group):>6}   {avg_next:>+12.3f}   {win_pct:>9.0f}%   {big_win_pct:>9.0f}%")
    else:
        print(f"  {n:>5}L   {len(group):>6}   (no next trade)")

# B. COOLDOWN SWEEP
print("\n" + "=" * 72)
print("B. COOLDOWN SWEEP: cd0 vs cd20 vs cd30 vs cd50")
print("=" * 72)

def run_cooldown(cd):
    result = simulate_htf_ltf_conditional(
        c1h, sw1h, c15, sw15, fine_ltf=fine,
        sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
        cooldown_bars=cd,
    )
    t = result["ltf_trades"]
    rs = [x["r_multiple"] for x in t]
    max_streak = 0
    current = 0
    for r in rs:
        if r <= 0:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    return {
        "trades": len(t),
        "net": sum(rs),
        "avg": statistics.mean(rs),
        "max_streak": max_streak,
        "winners": sum(1 for r in rs if r > 0),
    }

print(f"\n{'CD':>5} {'Trades':>7} {'Net R':>10} {'Avg R':>10} {'Max Streak':>11} {'Win%':>8}")
print("-" * 55)
for cd in [0, 10, 20, 30, 50, 80]:
    r = run_cooldown(cd)
    win_pct = r["winners"] / r["trades"] * 100 if r["trades"] > 0 else 0
    print(f"  {cd:>3}   {r['trades']:>7}   {r['net']:>+10.2f}   {r['avg']:>+10.3f}   {r['max_streak']:>11}   {win_pct:>7.1f}%")

# C. MAX LOSS HALT
print("\n" + "=" * 72)
print("C. MAX LOSS HALT: Stop after N consecutive losses")
print("=" * 72)

def run_max_loss_halt(max_losses):
    rs = [t["r_multiple"] for t in trades]
    halted_rs = []
    current_streak = 0
    halted = False
    for r in rs:
        if halted:
            if r > 0:
                halted = False
                current_streak = 0
                halted_rs.append(r)
            continue
        halted_rs.append(r)
        if r <= 0:
            current_streak += 1
            if current_streak >= max_losses:
                halted = True
        else:
            current_streak = 0
    return {
        "trades": len(halted_rs),
        "net": sum(halted_rs),
        "avg": statistics.mean(halted_rs) if halted_rs else 0,
        "skipped": len(rs) - len(halted_rs),
    }

print(f"\n{'MaxL':>5} {'Trades':>7} {'Net R':>10} {'Avg R':>10} {'Skipped':>8}")
print("-" * 45)
r_no_halt = run_max_loss_halt(999)
print(f"  {'inf':>3}   {r_no_halt['trades']:>7}   {r_no_halt['net']:>+10.2f}   {r_no_halt['avg']:>+10.3f}   {'—':>8}")
for max_l in [5, 10, 15, 21]:
    r = run_max_loss_halt(max_l)
    print(f"  {max_l:>3}   {r['trades']:>7}   {r['net']:>+10.2f}   {r['avg']:>+10.3f}   {r['skipped']:>8}")

# D. STREAK DISTRIBUTION
print("\n" + "=" * 72)
print("D. STREAK DISTRIBUTION")
print("=" * 72)

rs = [t["r_multiple"] for t in trades]
streaks_list = []
current = 0
for r in rs:
    if r <= 0:
        current += 1
    else:
        if current > 0:
            streaks_list.append(current)
        current = 0
if current > 0:
    streaks_list.append(current)

print(f"\nTotal streaks: {len(streaks_list)}")
print(f"Max streak: {max(streaks_list)}")
print(f"Avg streak: {statistics.mean(streaks_list):.1f}")

dist = Counter(streaks_list)
print(f"\n{'Streak':>8} {'Count':>6} {'Pct':>8}")
print("-" * 25)
for n in sorted(dist.keys()):
    pct = dist[n] / len(streaks_list) * 100
    print(f"  {n:>5}L   {dist[n]:>6}   {pct:>7.1f}%")

# E. MONTE CARLO
print("\n" + "=" * 72)
print("E. MONTE CARLO: Probability of 21+ streak")
print("=" * 72)

win_rate = sum(1 for r in rs if r > 0) / len(rs)
N_SIM = 10000
streak_counts = []
for _ in range(N_SIM):
    sim = [random.random() < win_rate for _ in range(414)]
    max_streak = 0
    current = 0
    for win in sim:
        if not win:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    streak_counts.append(max_streak)

streak_counts.sort()
p50 = streak_counts[5000]
p95 = streak_counts[9500]
p99 = streak_counts[9900]
count_21_plus = sum(1 for s in streak_counts if s >= 21)

print(f"\nWin rate: {win_rate:.3f}")
print(f"Simulated {N_SIM} runs of 414 trades")
print(f"Max streak p50: {p50}")
print(f"Max streak p95: {p95}")
print(f"Max streak p99: {p99}")
print(f"Runs with 21+ streak: {count_21_plus}/{N_SIM} ({count_21_plus/N_SIM*100:.1f}%)")
