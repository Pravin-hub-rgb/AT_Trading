"""Net-R check for the 'prev swing unconfirmed' trade subset (v18)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_pre_fs_marks import (c15, f15, c1h, f1h, sw1h, sw15, pre_keys, tr, fine)

print(f"trade keys: {sorted(tr[0].keys())}")
has_cost = "cost_r" in tr[0]
print(f"has cost_r: {has_cost}")

def net(ts):
    return sum(t["r_multiple"] - (t.get("cost_r", 0.0) if has_cost else 0.0) for t in ts)

in_state = []
for t in tr:
    d = 1 if t["dir"] == "long" else -1
    if (t["swing_no"], t["entry_idx"], d) in pre_keys:
        in_state.append(t)
other = [t for t in tr if t not in in_state]
print(f"\nALL    : {len(tr):>4} trades  gross {sum(t['r_multiple'] for t in tr):+8.1f}R"
      f"  net {net(tr):+8.1f}R")
print(f"PRE-FS : {len(in_state):>4} trades  gross {sum(t['r_multiple'] for t in in_state):+8.1f}R"
      f"  net {net(in_state):+8.1f}R  win {sum(1 for t in in_state if t['r_multiple']>0)}/{len(in_state)}")
print(f"REST   : {len(other):>4} trades  gross {sum(t['r_multiple'] for t in other):+8.1f}R"
      f"  net {net(other):+8.1f}R  win {sum(1 for t in other if t['r_multiple']>0)}/{len(other)}")
big = sorted(in_state, key=lambda t: -t["r_multiple"])[:5]
print("\ntop PRE-FS winners:")
for t in big:
    print(f"   #{t['trade_no']} {t['dir']:<5} sw{t['swing_no']} {t['entry_date']}  {t['r_multiple']:+.3f}R")
