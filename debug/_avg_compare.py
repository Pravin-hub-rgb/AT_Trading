"""Compare avg vs prev_pivot modes on full backtest."""
import sys
sys.path.insert(0, "backend")
import pandas as pd
from src.intraday import run_backtest, DEFAULT_CFG
from src.bias import compute_bias
from src.config import DATA_DIR

df = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])
bl = compute_bias(df)

for sl_mode in ("avg", "prev_pivot"):
    cfg = dict(DEFAULT_CFG)
    cfg["sl_mode"] = sl_mode
    if sl_mode == "prev_pivot":
        cfg["sl_pivot_buffer"] = 1.0

    r = run_backtest(df, bl, cfg)
    s = r["stats"]
    n_traded = sum(1 for d in r["days"] if d.get("trades"))
    print(f"\n=== sl_mode={sl_mode} ===")
    print(f"  trades={s['trades']}  win_rate={s['win_rate']}%  total_r={s['total_r']}  avg_r={s['avg_r']}")
    print(f"  days_traded={n_traded}/{len(r['days'])}")
    print(f"  longs={s.get('longs', 0)} shorts={s.get('shorts', 0)}")
    print(f"  outcomes={s.get('outcomes', {})}")
