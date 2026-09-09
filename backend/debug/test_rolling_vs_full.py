"""D2 cross-check on REAL live data: rolling-window chain vs full-history chain.

The live engine recomputes swings over a rolling 30-day window. Verify that
recent marks from that window match the full-CSV-history chain exactly.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings
from src.walker import FlowCandle
from src.live.boot_data import fetch_klines

# --- full-history chain (backtester ground truth) ---
df15 = load_btc_df("15m")
f15 = [FlowCandle(date=str(r.timestamp), open=float(r.open), high=float(r.high),
                  low=float(r.low), close=float(r.close)) for r in df15.itertuples()]
print(f"full 15m history: {len(f15)} bars — computing chain...")
sw_full = _compute_swings(f15, "continuous", min_bars=50)

# marks keyed by bar ts for the last 3 days
cutoff_ts = f15[-1].date  # str; get last ts from candles list instead
# rebuild ts list parallel to flow
ts_full = [int(r.ts) for r in df15.itertuples()]
last3_ts = set(ts_full[-int(3 * 96):])
full_marks = {}
for s in sw_full:
    for b in s.get("breaks", []):
        bi = int(b["idx"])
        if 0 <= bi < len(ts_full) and ts_full[bi] in last3_ts:
            full_marks.setdefault(ts_full[bi], []).append(
                (b["kind"], b["dir"], round(float(b["px"]), 2)))

# --- rolling-window chain (live engine style, from live REST data) ---
live = fetch_klines("BTCUSDT", "15m", 5760)
live = live[:-1]  # drop running candle
print(f"live rolling window: {len(live)} bars ({live[0]['date']} -> {live[-1]['date']})")
fl = [FlowCandle(date=c["date"], open=c["open"], high=c["high"],
                 low=c["low"], close=c["close"]) for c in live]
sw_live = _compute_swings(fl, "continuous", min_bars=50)
live_marks = {}
for s in sw_live:
    for b in s.get("breaks", []):
        bi = int(b["idx"])
        if 0 <= bi < len(live) and live[bi]["ts"] in last3_ts:
            live_marks.setdefault(live[bi]["ts"], []).append(
                (b["kind"], b["dir"], round(float(b["px"]), 2)))

only_full = {k: v for k, v in full_marks.items() if k not in live_marks}
only_live = {k: v for k, v in live_marks.items() if k not in full_marks}
diff = {k for k in full_marks if k in live_marks and full_marks[k] != live_marks[k]}
match = len(full_marks) - len(only_full) - len(diff)
print(f"\nmarks in last 3 days: full-chain {len(full_marks)} bars with marks, "
      f"rolling-chain {len(live_marks)}")
print(f"identical bars        : {match}")
print(f"full-only bars        : {len(only_full)}")
print(f"rolling-only bars     : {len(only_live)}")
print(f"same-bar differences  : {len(diff)}")
for k in list(only_full)[:5]:
    print(f"  full-only  ts={k}: {full_marks[k]}")
for k in list(only_live)[:5]:
    print(f"  roll-only  ts={k}: {live_marks[k]}")
for k in list(diff)[:5]:
    print(f"  DIFF       ts={k}: full={full_marks[k]} roll={live_marks[k]}")
if not (only_full or only_live or diff):
    print("\n>>> D2 VALIDATED ON LIVE DATA: 30-day rolling window reproduces")
    print(">>> the full-history chain's marks exactly for recent bars.")
