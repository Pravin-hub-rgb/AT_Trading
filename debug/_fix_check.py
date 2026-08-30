"""Verify the prev_pivot fix."""
import sys
sys.path.insert(0, "backend")
import pandas as pd
from src.intraday import run_backtest, DEFAULT_CFG
from src.bias import compute_bias
from src.config import DATA_DIR

df = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])
bl = compute_bias(df)

cfg = dict(DEFAULT_CFG)
cfg["sl_mode"] = "prev_pivot"
cfg["sl_pivot_buffer"] = 1.0

r = run_backtest(df, bl, cfg)
s = r["stats"]
print(f"prev_pivot buffer=1.0: {s['trades']} trades, total_r={s['total_r']}, win_rate={s['win_rate']}%")
print("\nLast 10 days with trades:")
shown = 0
for d in reversed(r["days"]):
    if d["trades"]:
        n = len(d["trades"])
        rsum = sum(t["r_multiple"] for t in d["trades"])
        outcomes = [t.get("outcome") for t in d["trades"]]
        print(f"  {d['date']} bias={d['bias']} case={d.get('case')} n={n} r={rsum:.2f} {outcomes}")
        shown += 1
        if shown >= 10:
            break
