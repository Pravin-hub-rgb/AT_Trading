"""Run Python FsV2Engine on multiple days and save final results to JSON."""
import sys, json
sys.path.insert(0, "backend")
import pandas as pd
from src.walker import FlowCandle
from src.swing_engine import FsV2Engine

DATA = "c:/Users/Pravin/Desktop/main/AT_Trading/data/nifty_1min.csv"
df = pd.read_csv(DATA)
df["date"] = pd.to_datetime(df["timestamp"]).dt.strftime("%Y-%m-%dT%H:%M:%S")

for day in ["2026-08-24", "2026-08-25", "2026-08-26", "2026-08-27"]:
    day_df = df[df["date"].str.startswith(day)].copy()
    if day_df.empty:
        print(f"NO DATA: {day}", flush=True)
        continue
    candles = [FlowCandle(date=r["date"], open=float(r["open"]), high=float(r["high"]),
                          low=float(r["low"]), close=float(r["close"]))
               for _, r in day_df.iterrows()]
    eng = FsV2Engine()
    for i, c in enumerate(candles):
        eng.process_bar(c, i)
    out = {
        "day": day, "totalBars": len(candles),
        "final": {"declared": eng.declared, "dir": eng.dir, "tier": eng.tier,
                  "startIdx": eng.start_idx, "startPx": eng.start_px,
                  "endIdx": eng.end_idx, "endPx": eng.end_px,
                  "confirmedAtIdx": eng.confirmed_at_idx, "confirmSource": eng.confirm_source,
                  "lastConfirmHit": eng.last_confirm_hit},
        "states": [],
    }
    with open(f"debug/_py_{day}.json", "w") as f:
        json.dump(out, f)
    print(f"{day}: declared={eng.declared} dir={eng.dir} startIdx={eng.start_idx} endIdx={eng.end_idx} confirmedAt={eng.confirmed_at_idx} source={eng.confirm_source}", flush=True)
print("DONE", flush=True)
