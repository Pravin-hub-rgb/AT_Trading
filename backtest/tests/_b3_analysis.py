import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings
from src.walker import FlowCandle
from replay_harness import load_candles

# Load IS data
(c15, f15), (c1h, f1h) = load_candles()

# Compute swings on 1h
swings = _compute_swings(f1h, "continuous", min_bars=20)
print(f"Total 1h swings: {len(swings)}")

# Analyze break sequences
from collections import Counter
break_kinds = Counter()
break_sequences = []
for s in swings:
    breaks = s.get("breaks", [])
    kinds = [b["kind"] for b in breaks]
    break_kinds.update(kinds)
    if len(breaks) >= 3:
        break_sequences.append((s["swing_index"], kinds))

print(f"\nBreak kind counts: {dict(break_kinds)}")
print(f"Swings with 3+ breaks: {len(break_sequences)}")

# Show first 20 multi-break sequences
print("\nFirst 20 swings with 3+ breaks:")
for idx, kinds in break_sequences[:20]:
    print(f"  swing {idx}: {kinds}")

# Count swings by number of breaks
from collections import Counter
n_breaks = Counter(len(s.get("breaks", [])) for s in swings)
print(f"\nSwings by break count: {dict(sorted(n_breaks.items()))}")

# For 3+ break swings, what's the last break kind?
last_kinds = Counter()
for s in swings:
    breaks = s.get("breaks", [])
    if len(breaks) >= 3:
        last_kinds[breaks[-1]["kind"]] += 1
print(f"\nLast break kind for 3+ break swings: {dict(last_kinds)}")