"""Entry distance gradation analysis — respond to peer review."""
import sys, random, statistics, math
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v16_entry_dist import simulate_htf_ltf_entry_dist
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

base = simulate_htf_ltf_entry_dist(
    candles_htf=c1h, swings_htf=sw1h, candles_ltf=c15, swings_ltf=sw15, fine_ltf=fine,
    sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
    cooldown_bars=20, entry_dist_max=0.0,
)
trades = base["ltf_trades"]
n_candles = len(c15)

# ATR
tr_l = [0.0] * n_candles
for i in range(n_candles):
    c = c15[i]
    if i == 0:
        tr_l[i] = float(c["high"]) - float(c["low"])
    else:
        pc = float(c15[i-1]["close"])
        tr_l[i] = max(float(c["high"]) - float(c["low"]), abs(float(c["high"]) - pc), abs(float(c["low"]) - pc))
atr15 = [0.0] * n_candles
for i in range(n_candles):
    lo = max(0, i - 13)
    atr15[i] = sum(tr_l[lo:i+1]) / (i - lo + 1)

def get_dist_and_r(t):
    bar = t.get("entry_idx")
    if bar is None: return None, None
    sw = next((s for s in sw15 if s.get("swing_index") == t.get("swing_no")), None)
    if sw is None: return None, None
    start_idx = sw["seg"]["start_idx"]
    end_idx = sw["seg"]["end_idx"]
    swing_len = end_idx - start_idx
    if swing_len <= 0: return None, None
    dist = (bar - start_idx) / swing_len
    return dist, t["r_multiple"]

# ─── A. FINE 10% BINS ───────────────────────────────────────────────
print("=" * 72)
print("A. ENTRY DISTANCE -> R MULTIPLE (10% bins)")
print("=" * 72)
print(f"{'Bin':>8} {'N':>5} {'Mean':>8} {'Median':>8} {'Total':>8} {'SE':>8} {'95% CI':>16}")
print("-" * 72)
bins = {}
for t in trades:
    dist, r = get_dist_and_r(t)
    if dist is None: continue
    bucket = min(int(dist * 10), 9)
    if bucket not in bins: bins[bucket] = []
    bins[bucket].append((dist, r))

prev_mean = None
monotonic_violations = 0
for b in range(10):
    if b not in bins:
        print(f"  {b*10:>2}-{(b+1)*10:>2}%  {'---':>5}  (no trades)")
        continue
    data = bins[b]
    rs = [x[1] for x in data]
    n = len(rs)
    mean_r = statistics.mean(rs)
    median_r = statistics.median(rs)
    total_r = sum(rs)
    se = statistics.stdev(rs) / math.sqrt(n) if n > 1 else 0.0
    ci_lo = mean_r - 1.96 * se
    ci_hi = mean_r + 1.96 * se
    if prev_mean is not None and mean_r > prev_mean + se:
        monotonic_violations += 1
    prev_mean = mean_r
    print(f"  {b*10:>2}-{(b+1)*10:>2}%  {n:>5}  {mean_r:>+8.3f}  {median_r:>+8.3f}  {total_r:>+8.2f}  {se:>8.3f}  [{ci_lo:>+.2f}, {ci_hi:>+.2f}]")

print(f"\nMonotonic violations (mean rises after falling): {monotonic_violations}")
if monotonic_violations == 0:
    print("OK Clean monotonic degradation -- relationship is REAL, not noise")
elif monotonic_violations <= 2:
    print("~ Mostly monotonic -- likely real with some noise in small buckets")
else:
    print("XX Non-monotonic -- relationship is noisy, 30% cutoff may be overfit")

# --- B. SHUFFLE MC: MAX DRAWDOWN DISTRIBUTION ---
print("\n" + "=" * 72)
print("B. SHUFFLE-ORDER MC: Max Drawdown Distribution (net is invariant)")
print("=" * 72)
random.seed(42)
rs = [t["r_multiple"] for t in trades]

def max_drawdown(returns):
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for r in returns:
        equity += r
        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd
    return max_dd

actual_dd = max_drawdown(rs)
print(f"Actual sequence max DD:  {actual_dd:.2f}R")

N_SAMPLES = 10000
random_dds = []
for _ in range(N_SAMPLES):
    shuffled = random.sample(rs, len(rs))
    random_dds.append(max_drawdown(shuffled))
random_dds.sort()

p5 = random_dds[500]
p25 = random_dds[2500]
p50 = random_dds[5000]
p75 = random_dds[7500]
p95 = random_dds[9500]
print(f"Shuffle MC max DD distribution (N={N_SAMPLES}):")
print(f"  mean={statistics.mean(random_dds):.2f}")
print(f"  p5={p5:.2f}  p25={p25:.2f}  p50={p50:.2f}  p75={p75:.2f}  p95={p95:.2f}")

actual_pct = sum(1 for d in random_dds if d <= actual_dd) / len(random_dds) * 100
print(f"\nActual DD ({actual_dd:.2f}R) is at {actual_pct:.1f}th percentile of shuffled distribution")
if actual_pct < 25:
    print("OK Order matters: actual sequence is BETTER than random (good sequencing)")
elif actual_pct > 75:
    print("XX Order matters: actual sequence is WORSE than random (bad sequencing)")
else:
    print("~ Order doesn't matter much: actual DD is within random range")

# --- C. SPEARMAN CORRELATION ---
print("\n" + "=" * 72)
print("C. DISTANCE-R CORRELATION (Spearman rank)")
print("=" * 72)
dist_r_pairs = []
for t in trades:
    dist, r = get_dist_and_r(t)
    if dist is not None:
        dist_r_pairs.append((dist, r))

def rankdata(vals):
    n = len(vals)
    pairs = sorted(enumerate(vals), key=lambda x: x[1])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j < n and pairs[j][1] == pairs[i][1]:
            j += 1
        rank = (i + j - 1) / 2.0 + 1
        for k in range(i, j):
            ranks[pairs[k][0]] = rank
        i = j
    return ranks

ds = [x[0] for x in dist_r_pairs]
rs2 = [x[1] for x in dist_r_pairs]
r_d = rankdata(ds)
r_r = rankdata(rs2)
n = len(r_d)
mean_d = statistics.mean(r_d)
mean_r2 = statistics.mean(r_r)
cov = sum((r_d[i] - mean_d) * (r_r[i] - mean_r2) for i in range(n))
std_d = math.sqrt(sum((r_d[i] - mean_d) ** 2 for i in range(n)))
std_r2 = math.sqrt(sum((r_r[i] - mean_r2) ** 2 for i in range(n)))
spearman = cov / (std_d * std_r2) if std_d > 0 and std_r2 > 0 else 0

print(f"Spearman rho(distance, R) = {spearman:.4f}")
print(f"N = {len(dist_r_pairs)}")
if spearman < -0.15:
    print("OK Meaningful negative correlation -> deeper entry = worse payoff (REAL)")
elif spearman < -0.05:
    print("~ Weak negative correlation -> some relationship but noisy")
else:
    print("XX No meaningful correlation -> distance doesn't explain payoff")

# --- D. DISTANCE x VOLATILITY INTERACTION ---
print("\n" + "=" * 72)
print("D. DISTANCE x VOLATILITY INTERACTION (mean R)")
print("=" * 72)
combo = {}
for t in trades:
    bar = t.get("entry_idx")
    if bar is None or bar >= n_candles: continue
    dist, r = get_dist_and_r(t)
    if dist is None: continue
    atr_pct = atr15[bar] / float(c15[bar]["close"]) * 100
    d_tier = "early" if dist < 0.33 else ("mid" if dist < 0.66 else "late")
    v_tier = "low" if atr_pct < 0.5 else ("med" if atr_pct < 0.8 else "high")
    key = (d_tier, v_tier)
    if key not in combo: combo[key] = []
    combo[key].append(r)

print(f"{'':>10} {'Low Vol':>10} {'Med Vol':>10} {'High Vol':>10}")
for d in ["early", "mid", "late"]:
    row = f"  {d:>8}"
    for v in ["low", "med", "high"]:
        key = (d, v)
        if key in combo and combo[key]:
            rs3 = combo[key]
            row += f"  {statistics.mean(rs3):>+7.3f}({len(rs3)})"
        else:
            row += f"  {'---':>8}"
    print(row)

# --- E. SUMMARY ---
print("\n" + "=" * 72)
print("E. SUMMARY FOR PEER REVIEW RESPONSE")
print("=" * 72)
early_low = statistics.mean(combo.get(("early", "low"), [0])) if combo.get(("early", "low")) else 0
late_high = statistics.mean(combo.get(("late", "high"), [0])) if combo.get(("late", "high")) else 0
print(f"1. Fine bins: monotonic violations = {monotonic_violations}/9 transitions")
if monotonic_violations <= 2:
    print("   -> Smooth gradient supports gate hypothesis")
else:
    print("   -> Noisy -- 30% boundary is arbitrary")
print(f"2. Spearman rho = {spearman:.4f} -- {'meaningful negative' if spearman < -0.15 else 'weak' if spearman < -0.05 else 'none'}")
print(f"3. Max DD: actual = {actual_dd:.2f}R at {actual_pct:.0f}th percentile")
if actual_pct < 40:
    print("   -> Sequencing is favorable")
elif actual_pct > 60:
    print("   -> Sequencing is unfavorable")
else:
    print("   -> Neutral")
print(f"4. VolxDist: early+low={early_low:+.3f} vs late+high={late_high:+.3f}")
if early_low > late_high:
    print("   -> early+low vol is best bucket")
else:
    print("   -> mixed result")

    print("XX Non-monotonic -- relationship is noisy, 30% cutoff may be overfit")
