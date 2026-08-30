"""Compare trade-by-trade results between direct call and server simulation."""
import sys
sys.path.insert(0, "backend")
import pandas as pd
from src.intraday import run_backtest, DEFAULT_CFG
from src.bias import compute_bias
from src.config import DATA_DIR

# Direct (script approach)
df = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])
bl_direct = compute_bias(df)
cfg = dict(DEFAULT_CFG)
cfg["sl_mode"] = "avg"
r_direct = run_backtest(df, bl_direct, cfg)

# Server (mimic what server does)
df5 = pd.read_csv(DATA_DIR / "nifty_5min.csv")
daily_df = pd.read_csv(DATA_DIR / "nifty_daily.csv")
bl_server = compute_bias(df5, daily_df)
dates = set(df5["timestamp"].astype(str).str[:10])
bl_server_filtered = [lb for lb in bl_server if lb["date"] in dates]
r_server = run_backtest(df5, bl_server_filtered, cfg=cfg, df_1min=None)

# Find days where direct traded but server didn't (and vice versa)
direct_dates = {d["date"]: d for d in r_direct["days"] if d.get("trades")}
server_dates = {d["date"]: d for d in r_server["days"] if d.get("trades")}

print(f"Direct traded days: {len(direct_dates)}")
print(f"Server traded days: {len(server_dates)}")
print(f"Common traded days: {len(set(direct_dates.keys()) & set(server_dates.keys()))}")
print(f"Only in direct: {sorted(set(direct_dates.keys()) - set(server_dates.keys()))[:20]}")
print(f"Only in server: {sorted(set(server_dates.keys()) - set(direct_dates.keys()))[:20]}")

# For common days, compare trade results
for date in sorted(set(direct_dates.keys()) & set(server_dates.keys())):
    d_trades = direct_dates[date]["trades"]
    s_trades = server_dates[date]["trades"]
    if len(d_trades) != len(s_trades):
        print(f"\n{date}: direct has {len(d_trades)} trades, server has {len(s_trades)}")
        continue
    for i, (dt, st) in enumerate(zip(d_trades, s_trades)):
        if abs(dt["sl"] - st["sl"]) > 0.01 or abs(dt["target"] - st["target"]) > 0.01 or dt["outcome"] != st["outcome"]:
            print(f"\n{date} trade #{i+1}:")
            print(f"  Direct:  dir={dt['dir']} entry={dt['entry_price']} sl={dt['sl']} t={dt['target']} out={dt['outcome']} r={dt.get('r_multiple', 0):.2f}")
            print(f"  Server:  dir={st['dir']} entry={st['entry_price']} sl={st['sl']} t={st['target']} out={st['outcome']} r={st.get('r_multiple', 0):.2f}")
