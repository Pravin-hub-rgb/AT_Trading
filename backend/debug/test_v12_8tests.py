"""8 robustness tests on v12+cd20 base (the best config)."""
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))

import random
import statistics
from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m, _trade_costs
from src.btc.engines.htf_ltf.v15_recover_1r import simulate_htf_ltf_recover_1r
from src.walker import FlowCandle

def load_window(tf):
    df = load_btc_df(tf)
    candles = []
    flow = []
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

base = simulate_htf_ltf_recover_1r(
    candles_htf=c1h, swings_htf=sw1h, candles_ltf=c15, swings_ltf=sw15, fine_ltf=fine,
    sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop", cooldown_bars=20, recover_1r=False,
)
trades = base["ltf_trades"]
print(f"=== v12+cd20 base: {len(trades)} trades ===")

# === 1. Entry distance into 15m swing ===
print("\n=== 1. ENTRY DISTANCE INTO SWING ===")
buckets = {"0-30%": [], "30-50%": [], "50-70%": [], "70-100%": []}
for t in trades:
    entry_idx = t["entry_idx"]
    swing_no = t["swing_no"]
    sw = next((s for s in sw15 if s.get("swing_index") == swing_no), None)
    if sw is None:
        continue
    start_idx = sw["seg"]["start_idx"]
    end_idx = sw["seg"]["end_idx"]
    swing_len = end_idx - start_idx
    if swing_len <= 0:
        continue
    dist = (entry_idx - start_idx) / swing_len
    r = t["r_multiple"]
    if dist < 0.3:
        buckets["0-30%"].append(r)
    elif dist < 0.5:
        buckets["30-50%"].append(r)
    elif dist < 0.7:
        buckets["50-70%"].append(r)
    else:
        buckets["70-100%"].append(r)
for k, v in buckets.items():
    if v:
        print(f"  {k}: n={len(v)} avg={statistics.mean(v):.3f} net={sum(v):.2f}")

# === 2. Runner durability (cap winners) ===
print("\n=== 2. RUNNER DURABILITY (cap winners) ===")
for cap in [3, 5, 10, 15, 20, 999]:
    capped = [min(t["r_multiple"], cap) for t in trades]
    print(f"  cap={cap}: net={sum(capped):.2f}")

# === 3. Trim-the-top robustness ===
print("\n=== 3. TRIM-THE-TOP ROBUSTNESS ===")
sorted_trades = sorted(trades, key=lambda t: t["r_multiple"], reverse=True)
for trim in [0, 1, 2, 3, 5, 10]:
    remaining = sorted_trades[trim:]
    net = sum(t["r_multiple"] for t in remaining)
    print(f"  trim top {trim}: n={len(remaining)} net={net:.2f}")

# === 4. Volatility at entry ===
print("\n=== 4. VOLATILITY AT ENTRY ===")
vol_buckets = {"low": [], "med": [], "high": []}
for t in trades:
    r = t["r_multiple"]
    entry = t["entry_price"]
    sl = t["sl"]
    risk = abs(entry - sl)
    atr_pct = risk / entry * 100
    if atr_pct < 0.7:
        vol_buckets["low"].append(r)
    elif atr_pct < 1.2:
        vol_buckets["med"].append(r)
    else:
        vol_buckets["high"].append(r)
for k, v in vol_buckets.items():
    if v:
        print(f"  {k}: n={len(v)} avg={statistics.mean(v):.3f} net={sum(v):.2f}")

# === 5. HTF interval age ===
print("\n=== 5. HTF INTERVAL AGE ===")
age_buckets = {"early": [], "mid": [], "late": []}
for t in trades:
    r = t["r_multiple"]
    entry_idx = t["entry_idx"]
    for ht in base["htf_trades"]:
        if ht["entry_idx"] <= entry_idx < ht["exit_idx"]:
            htf_len = ht["exit_idx"] - ht["entry_idx"]
            if htf_len > 0:
                age = (entry_idx - ht["entry_idx"]) / htf_len
                if age < 0.5:
                    age_buckets["early"].append(r)
                elif age < 0.75:
                    age_buckets["mid"].append(r)
                else:
                    age_buckets["late"].append(r)
            break
for k, v in age_buckets.items():
    if v:
        print(f"  {k}: n={len(v)} avg={statistics.mean(v):.3f} net={sum(v):.2f}")

# === 6. Bootstrap confidence ===
print("\n=== 6. BOOTSTRAP CONFIDENCE (10000 samples) ===")
random.seed(42)
rs = [t["r_multiple"] for t in trades]
boot_nets = []
for _ in range(10000):
    sample = [random.choice(rs) for _ in range(len(rs))]
    boot_nets.append(sum(sample))
boot_nets.sort()
print(f"  mean={statistics.mean(boot_nets):.2f}")
print(f"  p5={boot_nets[500]:.2f}  p25={boot_nets[2500]:.2f}  p50={boot_nets[5000]:.2f}  p75={boot_nets[7500]:.2f}  p95={boot_nets[9500]:.2f}")
print(f"  95% CI: [{boot_nets[250]:.2f}, {boot_nets[9750]:.2f}]")

# === 7. Trade-level MC (shuffle order) ===
print("\n=== 7. TRADE-LEVEL MC (shuffle order, 10000 samples) ===")
mc_nets = []
for _ in range(10000):
    shuffled = random.sample(rs, len(rs))
    mc_nets.append(sum(shuffled))
mc_nets.sort()
print(f"  mean={statistics.mean(mc_nets):.2f}")
print(f"  p5={mc_nets[500]:.2f}  p25={mc_nets[2500]:.2f}  p50={mc_nets[5000]:.2f}  p75={mc_nets[7500]:.2f}  p95={mc_nets[9500]:.2f}")

# === 8. Per-year breakdown ===
print("\n=== 8. PER-YEAR BREAKDOWN ===")
year_buckets = {}
for t in trades:
    year = t["entry_date"][:4]
    if year not in year_buckets:
        year_buckets[year] = []
    year_buckets[year].append(t["r_multiple"])
for year in sorted(year_buckets.keys()):
    v = year_buckets[year]
    print(f"  {year}: n={len(v)} net={sum(v):.2f} avg={statistics.mean(v):.3f}")

print("\n=== DONE ===")
