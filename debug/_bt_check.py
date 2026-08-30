"""Run full run_backtest with both sl_modes and compare trade counts."""
import sys
sys.path.insert(0, "backend")
import pandas as pd
from src.intraday import run_backtest, DEFAULT_CFG
from src.bias import compute_bias
from src.config import DATA_DIR

df_5min = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df_5min["timestamp"] = pd.to_datetime(df_5min["timestamp"])

bias_labels = compute_bias(df_5min)

cfg_pp = dict(DEFAULT_CFG)
cfg_pp["sl_mode"] = "prev_pivot"
cfg_pp["sl_pivot_buffer"] = 1.0

print("=== prev_pivot, buffer=1.0 ===")
res = run_backtest(df_5min, bias_labels, cfg_pp)
print(f"trades: {res['stats']['trades']}, days_traded: {res['stats']['days_traded']}/{res['stats']['days_total']}")
print(f"total_r: {res['stats']['total_r']}, win_rate: {res['stats']['win_rate']}")
print("trades per case:")
for c, s in (res.get("stats", {}).get("by_case") or {}).items():
    print(f"  {c}: {s}")
# Show last 10 days with trades
print("\nLast 10 days with trades:")
shown = 0
for d in reversed(res["days"]):
    if d["trades"]:
        n = len(d["trades"])
        rsum = sum(t["r_multiple"] for t in d["trades"])
        print(f"  {d['date']} bias={d['bias']} case={d.get('case')} n={n} r={rsum:.2f}")
        shown += 1
        if shown >= 10:
            break

cfg_avg = dict(DEFAULT_CFG)
cfg_avg["sl_mode"] = "avg"
print("\n=== avg ===")
res2 = run_backtest(df_5min, bias_labels, cfg_avg)
print(f"trades: {res2['stats']['trades']}, days_traded: {res2['stats']['days_traded']}/{res2['stats']['days_total']}")
print(f"total_r: {res2['stats']['total_r']}, win_rate: {res2['stats']['win_rate']}")
print("Last 10 days with trades:")
shown = 0
for d in reversed(res2["days"]):
    if d["trades"]:
        n = len(d["trades"])
        rsum = sum(t["r_multiple"] for t in d["trades"])
        print(f"  {d['date']} bias={d['bias']} case={d.get('case')} n={n} r={rsum:.2f}")
        shown += 1
        if shown >= 10:
            break
