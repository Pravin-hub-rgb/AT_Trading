"""Test that opposite_first bias always trades opposite of first swing"""
import pandas as pd
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src import bias as b, config
from src.intraday_1m_standalone import run_backtest_1min
from src.firstswing import compute_swing_results
from src.walker import FlowCandle

def test_opposite_first_direction():
    p1 = config.DATA_DIR / "nifty_1min.csv"
    p5 = config.DATA_DIR / "nifty_5min.csv"
    pdaily = config.DATA_DIR / "nifty_daily.csv"
    df1 = pd.read_csv(p1)
    df5 = pd.read_csv(p5)
    daily = pd.read_csv(pdaily) if pdaily.exists() else None
    df1["timestamp"] = pd.to_datetime(df1["timestamp"])
    df1_sorted = df1.sort_values("timestamp")
    # Get first swings per day
    all_cands = []
    for _, row in df1_sorted.iterrows():
        dt = row["timestamp"].strftime("%Y-%m-%dT%H:%M:%S")
        all_cands.append(FlowCandle(date=dt, open=float(row["open"]), high=float(row["high"]), low=float(row["low"]), close=float(row["close"])))
    swings = compute_swing_results(all_cands, {"timeCap": "09:29", "minBars": 14}, swing_count=1)
    first_map = {s["day"]: s["seg"]["dir"] for s in swings}  # B or S

    labels = b.compute_bias_with_mode(df5, daily, df1, mode="opposite_first")
    cfg = {"execution":"1min","sl_mode":"avg","rr_target":2.0,"min_sl_pts":13,"breakeven_r":0,"gap_pct":0.0027,"ft_fail_enabled":True,"max_entries":2,"entry_cutoff":"15:15","second_trade_after":"always","bias_mode":"opposite_first"}
    res = run_backtest_1min(df1, labels, cfg=cfg)
    mismatches = []
    for day in res["days"]:
        d = day["date"]
        if not day["trades"]:
            continue
        first_dir = first_map.get(d)
        if not first_dir:
            continue
        expected = "short" if first_dir == "B" else "long"
        for t in day["trades"]:
            if t["dir"] != expected:
                mismatches.append((d, first_dir, expected, t["dir"], t["entry_time"]))
                break
    if mismatches:
        print(f"FAIL: {len(mismatches)} days where trade not opposite of first swing:")
        for m in mismatches[:10]:
            print(f"  {m[0]} first {m[1]} expected {m[2]} got {m[3]} at {m[4]}")
        assert False, f"{len(mismatches)} mismatches"
    else:
        print(f"PASS: All {len([d for d in res['days'] if d['trades']])} traded days correctly opposite of first swing")

if __name__ == "__main__":
    test_opposite_first_direction()
