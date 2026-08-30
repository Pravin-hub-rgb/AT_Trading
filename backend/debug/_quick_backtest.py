import sys
sys.path.insert(0, 'backend')
import pandas as pd
from src.config import DATA_DIR
from src.intraday import run_backtest, DEFAULT_CFG
from src.bias import compute_bias

df5 = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df5["timestamp"] = pd.to_datetime(df5["timestamp"])
import pathlib
df1_path = DATA_DIR / "nifty_1min.csv"
df1 = pd.read_csv(df1_path)
df1["timestamp"] = pd.to_datetime(df1["timestamp"])
daily = pd.read_csv(DATA_DIR / "nifty_daily.csv") if (DATA_DIR / "nifty_daily.csv").exists() else None
labels = compute_bias(df5, daily)
labels = [lb for lb in labels if lb["date"] in set(df5["timestamp"].astype(str).str[:10])]

for mode in ["none", "opposite_swing_needed"]:
    cfg = dict(DEFAULT_CFG)
    cfg["execution"] = "1min"
    cfg["swing_mode"] = mode
    r = run_backtest(df5, labels, cfg, df_1min=df1)
    s = r["stats"]
    print(f"swing_mode={mode} trades={s['trades']} WR={s['win_rate']:.1f}% R={s['total_r']:+.2f}")
    # also print second swing events for opposite mode
    if mode == "opposite_swing_needed":
        cnt = sum(1 for d in r["days"] for e in d["events"] if e["type"]=="fs2_segment")
        print(f"  fs2_segment count {cnt}")
        # check Aug 28
        for d in r["days"]:
            if d["date"] == "2026-08-28":
                print(f"  Aug28 events: {d['events']}")
                break
