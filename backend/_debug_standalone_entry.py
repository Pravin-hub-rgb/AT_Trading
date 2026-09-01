"""Debug why _open_trade fails at bar 36 for 27 Aug SHORT entry."""
import sys
sys.path.insert(0, ".")
from src.intraday_1m_standalone import simulate_day_1min, run_backtest_1min
from src.config import DATA_DIR
from src.walker import WalkerEngine
import pandas as pd
import json

# Load 1-min data same way as standalone engine
df1 = pd.read_csv(DATA_DIR / "nifty_1min.csv")
df1["ts_str"] = df1["timestamp"].astype(str).str[:10]
day_1m = df1[df1["ts_str"] == "2026-08-27"].reset_index(drop=True)
day_1m["timestamp"] = pd.to_datetime(day_1m["timestamp"])

# Build candles list
candles = []
for _, row in day_1m.iterrows():
    candles.append({
        "open": float(row["open"]),
        "high": float(row["high"]),
        "low": float(row["low"]),
        "close": float(row["close"]),
        "ts": int(row["timestamp"].timestamp()),
        "time": str(row["timestamp"])[11:16],
    })

print(f"Total candles: {len(candles)}")
print(f"First candle: {candles[0]}")
print(f"Bar 36 (09:51): {candles[36]}")
print(f"Bar 37 (09:52): {candles[37]}")

# Use conservative config
cfg = {
    "entry_method": "pivot_break",
    "execution": "1min",
    "trade_mode": "conservative",
    "sl_mode": "prev_pivot",
    "sl_pivot_buffer": 1.0,
}

# Load bias labels
bias_file = DATA_DIR / "bias_labels.json"
if bias_file.exists():
    with open(bias_file) as f:
        all_labels = json.load(f)
    aug27_labels = [b for b in all_labels if b.get("date") == "2026-08-27"]
else:
    aug27_labels = []

print(f"Bias labels for 27 Aug: {aug27_labels}")

# Run the standalone engine
result = simulate_day_1min(candles, cfg, bias_labels=aug27_labels)
print(f"\n=== Standalone Result ===")
print(f"Case: {result.get('case')}")
print(f"Trades: {len(result.get('trades', []))}")
for ev in result.get('events', []):
    etype = ev.get('type')
    print(f"  {etype}: bar={ev.get('bar')}, time={ev.get('time')}, align={ev.get('aligned_with_bias')}, level={ev.get('level')}, reason={ev.get('reason')}, dirn={ev.get('dirn')}")

# Now analyze bar 36 in detail
print(f"\n=== Detailed bar 36 analysis ===")
bar36 = candles[36]
print(f"Bar 36: O={bar36['open']}, H={bar36['high']}, L={bar36['low']}, C={bar36['close']}")

# Build walker pivots up to bar 36
eng = WalkerEngine(n=5, min_bars=2, step=1)
for i in range(37):
    eng.add_bar(candles[i])

print(f"\nAll walker pivots (up to bar 36):")
for p in eng.pivots:
    print(f"  idx={p.idx}, px={p.px}, kind={p.kind}, time={candles[p.idx]['time']}")

normal_highs = [p for p in eng.pivots if p.kind == "high"]
normal_lows = [p for p in eng.pivots if p.kind == "low"]

eligible_highs = [p for p in normal_highs if p.idx < 36]
eligible_lows = [p for p in normal_lows if p.idx < 36]

print(f"\nnormal_highs (all): {[(p.idx, p.px, candles[p.idx]['time']) for p in normal_highs]}")
print(f"eligible_highs (idx < 36): {[(p.idx, p.px, candles[p.idx]['time']) for p in eligible_highs]}")

# Simulate _open_trade at bar 36 for SHORT
print(f"\n=== Simulating _open_trade at bar 36 (SHORT) ===")
dirn = -1  # SHORT
ref_level = 24228.2  # the pace_break level at bar 36
dbar = bar36
ref_swing_end_px = 24228.2  # fs2_end_px
ref_swing_end_dir = "buying"
est_entry = dbar['close']

print(f"dirn = {dirn} (SHORT)")
print(f"ref_level = {ref_level}")
print(f"dbar['close'] = {dbar['close']}")

# end_line check
end_line_skip = ref_swing_end_dir == "buying" and dirn == -1 and est_entry >= ref_swing_end_px
print(f"\nend_line check:")
print(f"  ref_swing_end_dir == 'buying': {ref_swing_end_dir == 'buying'}")
print(f"  dirn == -1: {dirn == -1}")
print(f"  est_entry >= ref_swing_end_px: {est_entry} >= {ref_swing_end_px} = {est_entry >= ref_swing_end_px}")
print(f"  Would SKIP? {end_line_skip}")

if end_line_skip:
    print(">>> FAIL: Would skip due to end_line check!")
else:
    print(">>> end_line check PASSES")

# SL calculation for SHORT
entry = ref_level
entry_high = dbar['high']
entry_low = dbar['low']

print(f"\nSL calculation:")
print(f"  entry = {entry}")
print(f"  entry_high = {entry_high}")
print(f"  entry_low = {entry_low}")
print(f"  pool = normal_highs")

if eligible_highs:
    pivot_ref = eligible_highs[-1]
    sl = pivot_ref.px
    risk = sl - entry
    print(f"\n  Using prev_pivot:")
    print(f"    pivot_ref = {pivot_ref.px} at idx={pivot_ref.idx} time={candles[pivot_ref.idx]['time']}")
    print(f"    sl = {sl}")
    print(f"    risk = sl - entry = {risk}")
    print(f"    risk <= 0? {risk <= 0}")
    
    if risk <= 0:
        print(f"\n>>> FAIL: risk <= 0, trade would be rejected by _open_trade!")
    else:
        print(f"\n>>> PASS: risk = {risk}, trade would be opened!")
else:
    print(f"\n  No eligible high pivots!")
    print(f">>> FAIL: No eligible pivots, trade would be rejected!")
