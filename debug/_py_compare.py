"""Python FsV2Engine driver — same as TS version, reads nifty_1min.csv, dumps per-bar state."""
import json
import sys
sys.path.insert(0, "backend")

import pandas as pd
from src.walker import FlowCandle
from src.swing_engine import FsV2Engine

DAY = "2026-08-28"
DATA = "c:/Users/Pravin/Desktop/main/AT_Trading/data/nifty_1min.csv"

df = pd.read_csv(DATA)
df["date"] = pd.to_datetime(df["timestamp"]).dt.strftime("%Y-%m-%dT%H:%M:%S")
day_df = df[df["date"].str.startswith(DAY)].copy()

if day_df.empty:
    print(f"No data for {DAY}", file=sys.stderr)
    sys.exit(1)

candles = []
for _, row in day_df.iterrows():
    c = FlowCandle(
        date=row["date"],
        open=float(row["open"]),
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
    )
    candles.append(c)

print(f"Loaded {len(candles)} candles for {DAY}", file=sys.stderr)

eng = FsV2Engine()
states = []
for i, c in enumerate(candles):
    eng.process_bar(c, i)
    states.append({
        "i": i,
        "t": c.date[11:16],
        "o": c.open,
        "h": c.high,
        "l": c.low,
        "c": c.close,
        "g": c.close >= c.open,
        "barsSeen": eng.bars_seen,
        "eHi": {"px": eng.e_hi.px, "idx": eng.e_hi.idx, "t": eng.e_hi.time},
        "eLo": {"px": eng.e_lo.px, "idx": eng.e_lo.idx, "t": eng.e_lo.time},
        "eHiPivot": {"px": eng.e_hi_pivot.px, "idx": eng.e_hi_pivot.idx, "t": eng.e_hi_pivot.time} if eng.e_hi_pivot else None,
        "eLoPivot": {"px": eng.e_lo_pivot.px, "idx": eng.e_lo_pivot.idx, "t": eng.e_lo_pivot.time} if eng.e_lo_pivot else None,
        "normalHighs": [{"px": l.px, "idx": l.idx, "t": l.time} for l in eng.normal_highs],
        "normalLows": [{"px": l.px, "idx": l.idx, "t": l.time} for l in eng.normal_lows],
        "microHighs": [{"px": l.px, "idx": l.idx, "t": l.time} for l in eng.micro_highs],
        "microLows": [{"px": l.px, "idx": l.idx, "t": l.time} for l in eng.micro_lows],
        "dir": eng.dir,
        "baseDir": eng.base_dir,
        "sameSideBreaks": eng.same_side_breaks,
        "oppositeSideBreaks": eng.opposite_side_breaks,
        "dirConfirmed": eng.dir_confirmed,
        "dirConfirmedIdx": eng.dir_confirmed_idx,
        "locked": eng.locked,
        "lockedLevelPx": eng.locked_level_px if eng.locked else None,
        "startIdx": eng.start_idx,
        "startPx": eng.start_px,
        "candIdx": eng.cand_idx,
        "candPx": eng.cand_px,
        "sustainStreak": eng.sustain_streak,
        "declared": eng.declared,
        "tier": eng.tier,
        "endIdx": eng.end_idx,
        "endPx": eng.end_px,
        "confirmedAtIdx": eng.confirmed_at_idx,
        "confirmSource": eng.confirm_source,
        "lastConfirmHit": eng.last_confirm_hit,
    })

out = {
    "day": DAY,
    "totalBars": len(candles),
    "final": {
        "declared": eng.declared,
        "dir": eng.dir,
        "tier": eng.tier,
        "startIdx": eng.start_idx,
        "startPx": eng.start_px,
        "endIdx": eng.end_idx,
        "endPx": eng.end_px,
        "confirmedAtIdx": eng.confirmed_at_idx,
        "confirmSource": eng.confirm_source,
        "lastConfirmHit": eng.last_confirm_hit,
    },
    "states": states,
}
with open(f"debug/_py_{DAY}.json", "w") as f:
    json.dump(out, f)
print(f"Written debug/_py_{DAY}.json", file=sys.stderr)
