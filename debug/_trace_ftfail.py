"""Trace ft_fail trades on specific days: was the SL touched before/after?"""
import sys
backend_dir = sys.argv[1]
sys.path.insert(0, backend_dir)
import pandas as pd
from src.intraday import run_backtest, DEFAULT_CFG, _prep_day
from src.bias import compute_bias
from src.config import DATA_DIR

TARGET_DAYS = {"2026-07-15", "2026-07-09", "2026-07-08"}

df = pd.read_csv(DATA_DIR / "nifty_5min.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])
daily_path = DATA_DIR / "nifty_daily.csv"
daily_df = pd.read_csv(daily_path) if daily_path.exists() else None
bl = [lb for lb in compute_bias(df, daily_df) if lb["date"] in set(df["timestamp"].astype(str).str[:10])]
res = run_backtest(df, bl, cfg=dict(DEFAULT_CFG))

for d in res["days"]:
    if d["date"] not in TARGET_DAYS or not d["trades"]:
        continue
    day_df = df[df["timestamp"].astype(str).str[:10] == d["date"]]
    candles = _prep_day(day_df)
    order = [c["time"] for c in candles]
    print(f"\n##### {d['date']}  bias={d['bias']} case={d.get('case')} swing={d.get('swing_direction')}")
    for t in d["trades"]:
        print(f"  TRADE {t['dir']} entry {t['entry_time']} @{t['entry_price']} sl={t['sl']} tgt={t['target']} "
              f"dom_time={t['domination_time']} dom_low={t['dom_low']} dom_high={t['dom_high']} "
              f"validate={t['validate_until'] - t['entry_bar']}bars -> {t['outcome']} "
              f"exit {t.get('exit_time')} @{t.get('exit_price')} R={t.get('r_multiple')}")
        e_i = t["entry_bar"]
        try:
            x_i = order.index(t.get("exit_time"))
        except ValueError:
            x_i = e_i + 3
        sl_touch = None
        close_through = None
        for j in range(e_i, min(x_i + 3, len(candles))):
            c = candles[j]
            hit = (c["low"] <= t["sl"]) if t["dir"] == "long" else (c["high"] >= t["sl"])
            if hit and sl_touch is None:
                sl_touch = c["time"]
            if t["dir"] == "long" and c["close"] < t["dom_low"] and close_through is None:
                close_through = c["time"]
            if t["dir"] == "short" and c["close"] > t["dom_high"] and close_through is None:
                close_through = c["time"]
        print(f"    SL first touched: {sl_touch}   close beyond dom level: {close_through}   exit: {t.get('exit_time')}")
        for j in range(e_i, min(x_i + 3, len(candles))):
            c = candles[j]
            mark = "  <-- EXIT" if c["time"] == t.get("exit_time") else ""
            print(f"    {c['time']}  O={c['open']} H={c['high']} L={c['low']} C={c['close']}{mark}")
