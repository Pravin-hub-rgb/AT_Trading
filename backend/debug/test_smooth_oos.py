"""Smooth OOS validation: discover on 2023-2024, validate on 2025-2026."""
import sys, statistics, math
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

# Enrich trades with distance and vol
enriched = []
for t in trades:
    bar = t.get("entry_idx")
    if bar is None or bar >= n_candles: continue
    sw = next((s for s in sw15 if s.get("swing_index") == t.get("swing_no")), None)
    if sw is None: continue
    start_idx = sw["seg"]["start_idx"]
    end_idx = sw["seg"]["end_idx"]
    swing_len = end_idx - start_idx
    if swing_len <= 0: continue
    dist = (bar - start_idx) / swing_len
    atr_pct = atr15[bar] / float(c15[bar]["close"]) * 100
    year = t["entry_date"][:4]
    enriched.append({"r": t["r_multiple"], "dist": dist, "atr_pct": atr_pct, "year": year})

is_trades = [t for t in enriched if t["year"] in ("2023", "2024")]
oos_trades = [t for t in enriched if t["year"] in ("2025", "2026")]
print(f"IS (2023-2024): {len(is_trades)} trades")
# --- Distance bins ---
def analyze_bins(trades_list, label):
    bins = {}
    for t in trades_list:
        d = t["dist"]
        b = min(int(d * 10), 9)
        if b not in bins: bins[b] = []
        bins[b].append(t["r"])
    
    print(f"\n{label}:")
    print(f"{'Bin':>8} {'N':>5} {'Mean':>8} {'Median':>8} {'Total':>8}")
    print("-" * 40)
    prev_mean = None
    violations = 0
    for b in range(10):
        if b not in bins:
            print(f"  {b*10:>2}-{(b+1)*10:>2}%  {'---':>5}")
            continue
        rs = bins[b]
        n = len(rs)
        mean_r = statistics.mean(rs)
        median_r = statistics.median(rs)
        total_r = sum(rs)
        se = statistics.stdev(rs) / math.sqrt(n) if n > 1 else 0
        if prev_mean is not None and mean_r > prev_mean + se:
            violations += 1
        prev_mean = mean_r
        print(f"  {b*10:>2}-{(b+1)*10:>2}%  {n:>5}  {mean_r:>+8.3f}  {median_r:>+8.3f}  {total_r:>+8.2f}")
    print(f"Monotonic violations: {violations}/9")
    return violations

print("\n" + "=" * 72)
print("ENTRY DISTANCE -> R")
print("=" * 72)
is_violations = analyze_bins(is_trades, "IS (2023-2024)")
oos_violations = analyze_bins(oos_trades, "OOS (2025-2026)")

# --- Vol bins ---
def analyze_vol_bins(trades_list, label):
    bins = {"low": [], "med": [], "high": []}
    for t in trades_list:
        v = t["atr_pct"]
        if v < 0.5:
            bins["low"].append(t["r"])
        elif v < 0.8:
            bins["med"].append(t["r"])
        else:
            bins["high"].append(t["r"])
    
    print(f"\n{label}:")
    print(f"{'Vol':>8} {'N':>5} {'Mean':>8} {'Median':>8} {'Total':>8}")
    print("-" * 40)
    for k, label_name in [("low", "Low<0.5%"), ("med", "Med<0.8%"), ("high", "High>=0.8%")]:
        rs = bins[k]
        if not rs:
            print(f"  {label_name:>8}  {'---':>5}")
            continue
        n = len(rs)
        mean_r = statistics.mean(rs)
        median_r = statistics.median(rs)
        total_r = sum(rs)
        print(f"  {label_name:>8}  {n:>5}  {mean_r:>+8.3f}  {median_r:>+8.3f}  {total_r:>+8.2f}")

print("\n" + "=" * 72)
print("VOLATILITY (ATR%) -> R")
print("=" * 72)
analyze_vol_bins(is_trades, "IS (2023-2024)")
analyze_vol_bins(oos_trades, "OOS (2025-2026)")

# --- Distance x Vol grid ---
def analyze_grid(trades_list, label):
    grid = {}
    for t in trades_list:
        d = t["dist"]
        v = t["atr_pct"]
        d_tier = "early" if d < 0.33 else ("mid" if d < 0.66 else "late")
        v_tier = "low" if v < 0.5 else ("med" if v < 0.8 else "high")
        key = (d_tier, v_tier)
        if key not in grid: grid[key] = []
        grid[key].append(t["r"])
    
    print(f"\n{label}:")
    print(f"{'':>10} {'Low Vol':>10} {'Med Vol':>10} {'High Vol':>10}")
    for d in ["early", "mid", "late"]:
        row = f"  {d:>8}"
        for v in ["low", "med", "high"]:
            key = (d, v)
            if key in grid and grid[key]:
                rs = grid[key]
                row += f"  {statistics.mean(rs):>+7.3f}({len(rs)})"
            else:
                row += f"  {'---':>8}"
        print(row)
    return grid

print("\n" + "=" * 72)
print("DISTANCE x VOL GRID (mean R)")
print("=" * 72)
is_grid = analyze_grid(is_trades, "IS (2023-2024)")
oos_grid = analyze_grid(oos_trades, "OOS (2025-2026)")

# --- OOS validation: does IS best bucket hold? ---
print("\n" + "=" * 72)
print("OOS VALIDATION: Does the IS best bucket hold?")
print("=" * 72)

best_is_bucket = None
best_is_mean = -999
for key, rs in is_grid.items():
    if len(rs) >= 20:
        m = statistics.mean(rs)
        if m > best_is_mean:
            best_is_mean = m
            best_is_bucket = key

if best_is_bucket:
    d_label = {"early": "entry<33%", "mid": "33-66%", "late": ">66%"}[best_is_bucket[0]]
    v_label = {"low": "ATR<0.5%", "med": "ATR<0.8%", "high": "ATR>=0.8%"}[best_is_bucket[1]]
    is_rs = is_grid[best_is_bucket]
    oos_rs = oos_grid.get(best_is_bucket, [])
    
    print(f"\nBest IS bucket: {d_label} + {v_label}")
    print(f"  IS:  n={len(is_rs)}, mean={statistics.mean(is_rs):+.3f}, total={sum(is_rs):+.2f}")
    if oos_rs:
        print(f"  OOS: n={len(oos_rs)}, mean={statistics.mean(oos_rs):+.3f}, total={sum(oos_rs):+.2f}")
        oos_mean = statistics.mean(oos_rs)
        is_mean = statistics.mean(is_rs)
        if oos_mean > 0:
            ratio = oos_mean / is_mean
            print(f"  OOS/IS ratio: {ratio:.2f}", end="")
            if ratio > 0.5:
                print(" <- HOLDS UP")
            else:
                print(" <- DECAYS")
    else:
        print("  OOS: no trades in this bucket")

# --- Smoothness summary ---
print("\n" + "=" * 72)
print("SMOOTHNESS SUMMARY")
print("=" * 72)
print(f"IS monotonic violations:  {is_violations}/9")
print(f"OOS monotonic violations: {oos_violations}/9")

if is_violations <= 2 and oos_violations <= 2:
    print("BOTH smooth -> relationship is REAL")
elif is_violations <= 2 and oos_violations > 2:
    print("IS smooth but OOS noisy -> partially overfit")
elif is_violations > 2 and oos_violations <= 2:
    print("IS noisy but OOS smooth -> needs more data")
else:
    print("BOTH noisy -> NOT smooth, gate is overfit")

print(f"\nIS net:  {sum(t['r'] for t in is_trades):+.2f}")
print(f"OOS net: {sum(t['r'] for t in oos_trades):+.2f}")

print(f"OOS (2025-2026): {len(oos_trades)} trades")
