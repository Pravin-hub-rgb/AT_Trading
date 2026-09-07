"""In-sample repro on the pristine backup CSVs: stream vs legacy final."""
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, ".")
import pathlib

import pandas as pd

from src.btc.btc_engine import simulate_btc_trades
from src.btc.btc_swing import compute_btc_swings
from src.walker import FlowCandle

REPO = pathlib.Path.cwd().parent
BACKUP = REPO / "data" / "btc" / "backup_insample"


def load(tf: str):
    df = pd.read_csv(BACKUP / f"BTCUSDT_{tf}.csv")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    flow = [FlowCandle(date=r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                       open=float(r.open), high=float(r.high),
                       low=float(r.low), close=float(r.close))
            for r in df.itertuples()]
    candles = [{"date": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "ts": int(r.timestamp.value // 10**9) - 19800,
                "open": float(r.open), "high": float(r.high),
                "low": float(r.low), "close": float(r.close)}
               for r in df.itertuples()]
    return candles, flow


def run(tf: str, mb: int, selection: str):
    candles, flow = load(tf)
    sw = compute_btc_swings(flow, opts={"minBars": mb}, max_swings=len(flow) // 2)
    tr = simulate_btc_trades(candles, sw, entry_break="decisive", sl_mode="swing",
                             rr_target=3.0, trailing="swing", breakeven_r=1.0,
                             entry_selection=selection)
    closed = [t for t in tr if t["outcome"] != "open"]
    return len(closed), round(sum(t["r_multiple"] for t in closed), 2)


n50, r50 = run("5m", 20, "stream")
nf, rf = run("5m", 20, "final")
print(f"5m trail_max_r in-sample  STREAM: {n50} tr, {r50}R")
print(f"5m trail_max_r in-sample  FINAL : {nf} tr, {rf}R  (legacy 1720/+392.95)")
