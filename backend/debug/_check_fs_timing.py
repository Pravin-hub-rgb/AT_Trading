"""Check if trades enter BEFORE the FsV2 first-swing is confirmed."""
import sys
sys.path.insert(0, '.')

from datetime import datetime, timezone, timedelta
import pandas as pd

from src.intraday import run_backtest, DEFAULT_CFG, _prep_day
from src.bias import compute_bias
from src.config import DATA_DIR
from src.swing_engine import FirstSwingEngine
from src.walker import FlowCandle


def compute_fs_v2_conf_bar(candles: list[dict], day_date: str) -> tuple[int, str]:
    """Run FsV2 engine on the candles. Return (conf_bar_idx, conf_time) or (-1, '')."""
    IST = timezone(timedelta(hours=5, minutes=30))
    flow_candles: list[FlowCandle] = []
    for c in candles:
        ts = c.get("ts", 0)
        if ts:
            dt = datetime.fromtimestamp(int(ts), tz=IST).strftime("%Y-%m-%dT%H:%M:%S")
        else:
            dt = f"{day_date}T{c.get('time', '00:00')}:00"
        flow_candles.append(FlowCandle(
            date=dt, open=c["open"], high=c["high"], low=c["low"], close=c["close"],
        ))

    eng = FirstSwingEngine()
    for g_idx, fc in enumerate(flow_candles):
        eng.process_bar(fc, g_idx)

    if eng.declared:
        return eng.confirmed_at_idx, eng.confirmed_at_time
    return -1, ""


df = pd.read_csv(DATA_DIR / 'nifty_5min.csv')
df["timestamp"] = pd.to_datetime(df["timestamp"])
daily_df = pd.read_csv(DATA_DIR / 'nifty_daily.csv') if (DATA_DIR / 'nifty_daily.csv').exists() else None
bl = [lb for lb in compute_bias(df, daily_df) if lb["date"] in set(df["timestamp"].astype(str).str[:10])]
res = run_backtest(df, bl, cfg=dict(DEFAULT_CFG))

pre_fs = []
no_swing_days = []
for d in res["days"]:
    if not d["trades"]:
        continue
    day_df = df[df["timestamp"].astype(str).str[:10] == d["date"]]
    candles = _prep_day(day_df)
    fs_bar, fs_time = compute_fs_v2_conf_bar(candles, d["date"])
    if fs_bar < 0:
        no_swing_days.append(d["date"])
        continue
    for t in d["trades"]:
        entry_bar = t["entry_bar"]
        entry_time = t["entry_time"]
        if entry_bar < fs_bar:
            pre_fs.append({
                "date": d["date"],
                "entry_time": entry_time,
                "entry_bar": entry_bar,
                "fs_conf_bar": fs_bar,
                "fs_conf_time": fs_time,
                "outcome": t["outcome"],
                "r": t.get("r_multiple", 0),
                "dir": t.get("dir"),
            })

print(f"Found {len(pre_fs)} trades entering BEFORE FsV2 first-swing confirmation:")
print(f"Days where no swing declared: {len(no_swing_days)}")
print()
print(f"{'date':<12}{'entry':<10}{'entry_bar':<11}{'fs_conf':<10}{'fs_bar':<8}{'outcome':<8}{'R':>8}  dir")
for t in pre_fs:
    print(f"  {t['date']:<10} {t['entry_time']:<9} {t['entry_bar']:<10} "
          f"{t['fs_conf_time']:<9} {t['fs_conf_bar']:<7} {t['outcome']:<7} {t['r']:>7.2f}  {t['dir']}")

# Summary stats
if pre_fs:
    print("\n--- Outcome breakdown of pre-Fs trades ---")
    out_counts = {}
    for t in pre_fs:
        out_counts[t["outcome"]] = out_counts.get(t["outcome"], 0) + 1
    for o, c in sorted(out_counts.items()):
        print(f"  {o:<10} {c}")
