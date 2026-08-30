"""Diagnostic: print backtest stats for a given backend source tree (server-style: with daily bias)."""
import sys, os
backend_dir = sys.argv[1]
sys.path.insert(0, backend_dir)
import pandas as pd
from src.intraday import run_backtest, DEFAULT_CFG
from src.bias import compute_bias
from src.config import DATA_DIR

df = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])
daily_path = DATA_DIR / "nifty_daily.csv"
daily_df = pd.read_csv(daily_path) if daily_path.exists() else None
bl = compute_bias(df, daily_df)
bl = [lb for lb in bl if lb["date"] in set(df["timestamp"].astype(str).str[:10])]

cfg = dict(DEFAULT_CFG)
r = run_backtest(df, bl, cfg)
s = r["stats"]
n_traded = sum(1 for d in r["days"] if d.get("trades"))
print(f"[{os.path.basename(backend_dir)}] sl_mode={cfg['sl_mode']}")
print(f"  trades={s['trades']}  wins={s['wins']}  win_rate={s['win_rate']}%  total_r={s['total_r']}  avg_r={s['avg_r']}")
print(f"  days_traded={n_traded}/{len(r['days'])}  outcomes={s.get('outcomes', {})}")
cases = s.get("cases", {})
for c, v in sorted(cases.items()):
    print(f"  case {c}: {v}")
