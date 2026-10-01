"""Entry autopsy Phase 1b: fix swing quality + deeper analysis."""
import sys, os, datetime
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from run_experiment import run_one, _g, get_data
from test_experiments_craze import build_module, stats, BASE
from experiment_registry import EXPERIMENTS

print("Running champion_multi_sw10...")
data = get_data()
sim = build_module()

cfg = {**dict(BASE), **EXPERIMENTS["champion_multi_sw10"]["params"]}
result = sim(data["c1h"], data["sw20"], data["c15"], data["sw15"],
             fine_ltf=[], **cfg)
raw_trades = result["ltf_trades"]

swings = data["sw15"]
candles = data["c15"]
candle_ts = [int(c["ts"]) for c in candles]

print(f"Total trades: {len(raw_trades)}")
print(f"Total swings: {len(swings)}")

# Print a sample swing to understand its structure
if swings:
    s0 = swings[0]
    print(f"\nSample swing keys: {sorted(s0.keys())}")
    print(f"Sample swing: dir={s0.get('dir')}, seg={s0.get('seg', {}).keys() if s0.get('seg') else None}")
    if s0.get("seg"):
        print(f"  seg keys: {sorted(s0['seg'].keys())}")
        print(f"  seg start_idx={s0['seg'].get('start_idx')}, end_idx={s0['seg'].get('end_idx')}")
        print(f"  seg high={s0['seg'].get('high')}, low={s0['seg'].get('low')}")

# Build metrics for each trade
metrics = []
for t in raw_trades:
    entry_idx = int(t["entry_idx"])
    entry_px = float(t["entry_price"])
    sl = float(t["sl"])
    risk = abs(entry_px - sl)
    direction = 1 if t["dir"] == "long" else -1
    r_mult = float(t["r_multiple"])
    is_winner = r_mult > 0

    # ATR at entry
    tr_vals = []
    for j in range(max(0, entry_idx - 13), entry_idx + 1):
        c = candles[j]
        if j == 0:
            tr = float(c["high"]) - float(c["low"])
        else:
            pc = float(candles[j - 1]["close"])
            tr = max(float(c["high"]) - float(c["low"]),
                     abs(float(c["high"]) - pc),
                     abs(float(c["low"]) - pc))
        tr_vals.append(tr)
    atr15 = sum(tr_vals) / len(tr_vals) if tr_vals else 1.0

    # Swing quality from swing chain
    swing_no = int(t["swing_no"])
    swing_range = 0.0
    swing_age = 0
    swing_dir = ""
    if 0 <= swing_no < len(swings):
        sw = swings[swing_no]
        swing_dir = sw.get("dir", "")
        seg = sw.get("seg")
        if seg:
            hi = float(seg.get("high", 0))
            lo = float(seg.get("low", 0))
            swing_range = hi - lo if hi > lo else 0.0
            seg_start = int(seg.get("start_idx", 0))
            swing_age = entry_idx - seg_start
    swing_quality = swing_range / atr15 if atr15 > 0 else 0

    # Risk %
    risk_pct = (risk / entry_px) * 100 if entry_px > 0 else 0

    # Entry depth (entry distance from SL pivot in ATR units)
    entry_depth = risk / atr15 if atr15 > 0 else 0

    # Candle strength
    if 0 <= entry_idx < len(candles):
        c = candles[entry_idx]
        body = abs(float(c["close"]) - float(c["open"]))
        rng = float(c["high"]) - float(c["low"])
        candle_strength = body / rng if rng > 0 else 0
    else:
        candle_strength = 0

    # Time
    entry_ts = int(t["entry_ts"])
    dt = datetime.datetime.utcfromtimestamp(entry_ts / 1000)
    hour = dt.hour
    dow = dt.weekday()

    # Consecutive same-dir swings
    same_dir_count = 0
    if 0 <= swing_no < len(swings):
        target_dir = swings[swing_no].get("dir", "")
        for j in range(swing_no - 1, max(-1, swing_no - 6), -1):
            if j < 0 or j >= len(swings): break
            if swings[j].get("dir", "") == target_dir:
                same_dir_count += 1
            else:
                break

    metrics.append({
        "is_winner": is_winner,
        "r_multiple": r_mult,
        "risk_pct": round(risk_pct, 4),
        "swing_quality": round(swing_quality, 2),
        "swing_age": swing_age,
        "entry_depth": round(entry_depth, 2),
        "candle_strength": round(candle_strength, 2),
        "same_dir_count": same_dir_count,
        "hour": hour,
        "dow": dow,
        "break_kind": t.get("break_kind", ""),
        "direction": t["dir"],
        "bars_held": int(t["bars_held"]),
    })

winners = [t for t in metrics if t["is_winner"]]
losers = [t for t in metrics if not t["is_winner"]]

def compare(metric, label, buckets):
    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"{'='*70}")
    print(f"  {'bucket':>20s}  {'n':>4s}  {'W%':>5s}  {'avgR':>7s}  {'totalR':>8s}  {'W_avg':>7s}  {'L_avg':>7s}  {'separation':>10s}")
    print(f"  {'-'*85}")

    for i in range(len(buckets) - 1):
        lo = buckets[i]
        hi = buckets[i + 1]
        subset = [t for t in metrics if lo <= t[metric] < hi]
        if not subset:
            continue
        w = [t for t in subset if t["is_winner"]]
        l = [t for t in subset if not t["is_winner"]]
        n = len(subset)
        wr = 100 * len(w) / n
        avg_r = sum(t["r_multiple"] for t in subset) / n
        total_r = sum(t["r_multiple"] for t in subset)
        w_avg = sum(t["r_multiple"] for t in w) / len(w) if w else 0
        l_avg = sum(t["r_multiple"] for t in l) / len(l) if l else 0
        # Separation: avg winner R minus |avg loser R|
        sep = w_avg - abs(l_avg) if w else 0
        marker = " <-- BEST" if sep > 3 else (" <-- WORST" if sep < 1 and n > 20 else "")
        print(f"  [{lo}, {hi})  {n:4d}  {wr:5.1f}%  {avg_r:+7.2f}  {total_r:+8.1f}  {w_avg:+7.2f}  {l_avg:+7.2f}  {sep:+7.2f}{marker}")

    # Overall
    n = len(metrics)
    wr = 100 * len(winners) / n
    avg_r = sum(t["r_multiple"] for t in metrics) / n
    total_r = sum(t["r_multiple"] for t in metrics)
    w_avg = sum(t["r_multiple"] for t in winners) / len(winners)
    l_avg = sum(t["r_multiple"] for t in losers) / len(losers)
    print(f"  {'OVERALL':>20s}  {n:4d}  {wr:5.1f}%  {avg_r:+7.2f}  {total_r:+8.1f}  {w_avg:+7.2f}  {l_avg:+7.2f}")

# Run comparisons
compare("risk_pct", "Risk % of Price (SL distance / entry)", [0, 0.3, 0.5, 0.7, 0.9, 1.2, 1.5, 3.0, 10])
compare("swing_quality", "Swing Quality (swing_range / ATR)", [0, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 10, 99])
compare("entry_depth", "Entry Depth (risk / ATR — how deep the stop is)", [0, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 99])
compare("candle_strength", "Candle Strength (body/range at signal bar)", [0, 0.15, 0.3, 0.5, 0.7, 0.9, 1.01])
compare("swing_age", "Swing Age (bars since swing start)", [0, 3, 6, 10, 15, 20, 30, 50, 200])
compare("same_dir_count", "Consecutive Same-Dir Swings", [0, 1, 2, 3, 4, 5, 20])
compare("hour", "Hour of Day (UTC)", [0, 4, 8, 12, 16, 20, 24])

# FLIP vs B2 deep dive
print(f"\n{'='*70}")
print(f"  FLIP vs B2 — detailed breakdown")
print(f"{'='*70}")
for kind in ["FLIP", "B2"]:
    subset = [t for t in metrics if t["break_kind"] == kind]
    w = [t for t in subset if t["is_winner"]]
    l = [t for t in subset if not t["is_winner"]]
    n = len(subset)
    wr = 100 * len(w) / n if n else 0
    avg_r = sum(t["r_multiple"] for t in subset) / n if n else 0
    total_r = sum(t["r_multiple"] for t in subset)
    w_avg = sum(t["r_multiple"] for t in w) / len(w) if w else 0
    l_avg = sum(t["r_multiple"] for t in l) / len(l) if l else 0
    print(f"\n  {kind}: {n}t  WR {wr:.1f}%  avgR {avg_r:+.2f}  totalR {total_r:+.1f}  W_avg {w_avg:+.2f}  L_avg {l_avg:+.2f}")

    # Sub-breakdown by candle strength
    print(f"    candle_strength breakdown:")
    for lo_c, hi_c, label in [(0, 0.3, "doji"), (0.3, 0.6, "medium"), (0.6, 1.01, "strong")]:
        sub = [t for t in subset if lo_c <= t["candle_strength"] < hi_c]
        if not sub: continue
        sw = [t for t in sub if t["is_winner"]]
        sn = len(sub)
        swr = 100 * len(sw) / sn if sn else 0
        sar = sum(t["r_multiple"] for t in sub) / sn if sn else 0
        print(f"      {label}: {sn}t  WR {swr:.1f}%  avgR {sar:+.2f}")

    # Sub-breakdown by risk %
    print(f"    risk_pct breakdown:")
    for lo_r, hi_r, label in [(0, 0.5, "tight"), (0.5, 1.0, "normal"), (1.0, 10, "wide")]:
        sub = [t for t in subset if lo_r <= t["risk_pct"] < hi_r]
        if not sub: continue
        sw = [t for t in sub if t["is_winner"]]
        sn = len(sub)
        swr = 100 * len(sw) / sn if sn else 0
        sar = sum(t["r_multiple"] for t in sub) / sn if sn else 0
        print(f"      {label}: {sn}t  WR {swr:.1f}%  avgR {sar:+.2f}")

# Combined filter candidates
print(f"\n{'='*70}")
print(f"  COMBINED FILTER CANDIDATES")
print(f"{'='*70}")

# Test: FLIP + strong candle + normal risk
combo1 = [t for t in metrics if t["break_kind"] == "FLIP" and t["candle_strength"] >= 0.4 and 0.4 <= t["risk_pct"] <= 1.2]
w1 = [t for t in combo1 if t["is_winner"]]
n1 = len(combo1)
if n1:
    wr1 = 100 * len(w1) / n1
    ar1 = sum(t["r_multiple"] for t in combo1) / n1
    tr1 = sum(t["r_multiple"] for t in combo1)
    print(f"  FLIP + candle>=0.4 + risk 0.4-1.2%: {n1}t  WR {wr1:.1f}%  avgR {ar1:+.2f}  totalR {tr1:+.1f}")

# Test: FLIP + strong candle only
combo2 = [t for t in metrics if t["break_kind"] == "FLIP" and t["candle_strength"] >= 0.5]
w2 = [t for t in combo2 if t["is_winner"]]
n2 = len(combo2)
if n2:
    wr2 = 100 * len(w2) / n2
    ar2 = sum(t["r_multiple"] for t in combo2) / n2
    tr2 = sum(t["r_multiple"] for t in combo2)
    print(f"  FLIP + candle>=0.5: {n2}t  WR {wr2:.1f}%  avgR {ar2:+.2f}  totalR {tr2:+.1f}")

# Test: FLIP only
combo3 = [t for t in metrics if t["break_kind"] == "FLIP"]
w3 = [t for t in combo3 if t["is_winner"]]
n3 = len(combo3)
wr3 = 100 * len(w3) / n3
ar3 = sum(t["r_multiple"] for t in combo3) / n3
tr3 = sum(t["r_multiple"] for t in combo3)
print(f"  FLIP only: {n3}t  WR {wr3:.1f}%  avgR {ar3:+.2f}  totalR {tr3:+.1f}")

# Test: not-FLIP (B2) with doji candle
combo4 = [t for t in metrics if t["break_kind"] == "B2" and t["candle_strength"] < 0.3]
w4 = [t for t in combo4 if t["is_winner"]]
n4 = len(combo4)
if n4:
    wr4 = 100 * len(w4) / n4
    ar4 = sum(t["r_multiple"] for t in combo4) / n4
    tr4 = sum(t["r_multiple"] for t in combo4)
    print(f"  B2 + doji (<0.3): {n4}t  WR {wr4:.1f}%  avgR {ar4:+.2f}  totalR {tr4:+.1f}")
else:
    print(f"  B2 + doji (<0.3): 0t")

# Test: wide risk (>1.5%) on B2
combo5 = [t for t in metrics if t["break_kind"] == "B2" and t["risk_pct"] > 1.2]
w5 = [t for t in combo5 if t["is_winner"]]
n5 = len(combo5)
if n5:
    wr5 = 100 * len(w5) / n5
    ar5 = sum(t["r_multiple"] for t in combo5) / n5
    tr5 = sum(t["r_multiple"] for t in combo5)
    print(f"  B2 + wide risk (>1.2%): {n5}t  WR {wr5:.1f}%  avgR {ar5:+.2f}  totalR {tr5:+.1f}")

# Overall for reference
print(f"\n  OVERALL: {len(metrics)}t  WR {100*len(winners)/len(metrics):.1f}%  avgR {sum(t['r_multiple'] for t in metrics)/len(metrics):+.2f}  totalR {sum(t['r_multiple'] for t in metrics):+.1f}")

print("\n" + "=" * 70)
print("PHASE 1b COMPLETE")
print("=" * 70)
