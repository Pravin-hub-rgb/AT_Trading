"""Smoke test the simplified BTC API: single dataset, fees, net stats, summary."""
import os
import pathlib
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, ".")

REPO = pathlib.Path.cwd().parent

# _oos.csv files must be gone; one CSV per tf
stray = sorted(p.name for p in (REPO / "data" / "btc").glob("*_oos.csv"))
print("stray oos csvs:", stray)

from fastapi.testclient import TestClient  # noqa: E402

from server import app  # noqa: E402

c = TestClient(app)
fail = 0


def check(name, cond, extra=""):
    global fail
    print(("PASS" if cond else "FAIL"), name, extra)
    if not cond:
        fail += 1


# 1. status — simple shape
r = c.get("/api/btc/status")
st = r.json()
check("status 200", r.status_code == 200)
check("status legacy tfs", "5m" in st.get("tfs", {}))
t5 = st["tfs"]["5m"]
print("   5m:", t5)
check("status 5m covers 2026", t5["exists"] and t5["last_ts"].startswith("2026-09"))
check("no datasets key", "datasets" not in st)

# 2. chart — no dataset param anywhere
r = c.get("/api/btc/chart", params={"tf": "15m", "mode": "continuous", "limit": 3000})
ch = r.json()
check("chart 200", r.status_code == 200)
check("chart count", ch.get("count") == 3000, str(ch.get("count")))
check("chart last is 2026", str(ch.get("last_ts", "")).startswith("2026-09"), str(ch.get("last_ts")))
check("chart no dataset key", "dataset" not in ch)
idxs = [s["seg"]["start_idx"] for s in ch["swings"]]
check("chart idx in window", all(0 <= i < ch["count"] for i in idxs if i >= 0))

# 3. validation still works
r = c.get("/api/btc/chart", params={"tf": "5m", "mode": "bogus"})
check("chart bad mode 400", r.status_code == 400, str(r.status_code))
r = c.get("/api/btc/chart", params={"tf": "9m"})
check("chart bad tf 400", r.status_code == 400, str(r.status_code))

# 4. backtest with fees — Flip Trail 50 on the merged 15m series (OOS window incl.)
r = c.get("/api/btc/backtest", params={
    "tf": "15m", "mode": "continuous",
    "entry_break": "flip", "trailing": "swing", "breakeven_r": 0, "min_bars": 50,
    "fee_pct": 0.05, "slippage_pts": 2,
})
bt = r.json()
check("backtest 200", r.status_code == 200)
s = bt["stats"]
check("backtest net stats", "net_total_r" in s and "total_costs_r" in s)
print("   flip50 merged-15m: tr", s["trades"], "win%", s["win_rate"],
      "baseR", s["total_r"], "netR", s["net_total_r"])
check("trade cost_r present", "cost_r" in bt["trades"][0])
check("params no dataset", "dataset" not in bt["params"])

# 5. fee validation
r = c.get("/api/btc/backtest", params={"tf": "5m", "fee_pct": 5})
check("backtest bad fee 400", r.status_code == 400, str(r.status_code))

# 6. summary — all 8 presets on the same window, ranked by net R
r = c.get("/api/btc/summary", params={"tf": "15m", "mode": "continuous",
                                      "fee_pct": 0.05, "slippage_pts": 2})
sm = r.json()
check("summary 200", r.status_code == 200)
rows = sm.get("rows", [])
check("summary 12 rows", len(rows) == 12, str(len(rows)))
check("summary ranked", all("rank" in x for x in rows))
check("summary best set", sm.get("best") is not None)
for x in rows:
    print(f"   {x['rank']}. {x['label']:26s} tr={x['trades']:5d} "
          f"win={x['win_rate']:5.1f}% base={x['base_r']:8.2f} "
          f"costs={x['costs_r']:7.2f} NET={x['net_r']:8.2f}")

# 7. daily-mode regression intact
r = c.get("/api/btc/chart", params={"tf": "5m", "mode": "daily", "limit": 3000})
ch2 = r.json()
check("daily mode ok", r.status_code == 200)
bad = [x for x in ch2["swings"]
       if x["seg"]["start_idx"] >= 0 and not (0 <= x["seg"]["start_idx"] < ch2["count"])]
check("daily idx fix intact", not bad, str(len(bad)))

# 8. in-sample headline repro — engine numbers must match the recorded sweep.
#    NOTE 1: the old 1720/+392.95 was recorded under the OLD retrospective
#      "final" entry_selection + signal-TF fills (that +392.95 was an illusion —
#      the look-ahead bug the Jan-10 audit found).
#    NOTE 2: the opposite-direction SL fix (prev-leg END pivot, not START)
#      made live-visible B2/FLIP signals tradeable (e.g. the 10-Jan 17:00
#      SHORT). On this 5m in-sample config that moved the honest stream number
#      to 1963 trades / +122.05R. Assert THAT stays stable.
#    (ran against the preserved in-sample CSVs, not the merged ones)
import pandas as pd  # noqa: E402

from src.btc.btc_config import BTC_DATA_DIR  # noqa: E402
from src.btc.btc_engine import simulate_btc_trades  # noqa: E402
from src.btc.btc_swing import compute_btc_swings  # noqa: E402
from src.walker import FlowCandle  # noqa: E402

df = pd.read_csv(BTC_DATA_DIR / "backup_insample" / "BTCUSDT_5m.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values("timestamp").reset_index(drop=True)
flow = [FlowCandle(date=x.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                   open=float(x.open), high=float(x.high),
                   low=float(x.low), close=float(x.close))
        for x in df.itertuples()]
candles = [
    {"date": x.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
     "ts": int(x.timestamp.value // 10**9) - 19800,
     "open": float(x.open), "high": float(x.high),
     "low": float(x.low), "close": float(x.close)}
    for x in df.itertuples()
]
sw = compute_btc_swings(flow, opts={"minBars": 20}, max_swings=len(flow) // 2)
tr = simulate_btc_trades(candles, sw, entry_break="decisive", sl_mode="swing",
                         rr_target=3.0, trailing="swing", breakeven_r=1.0,
                         entry_selection="stream")
closed = [t for t in tr if t["outcome"] != "open"]
total = sum(t["r_multiple"] for t in closed)
print(f"   in-sample repro (stream): tr={len(closed)} R={total:.2f}")
check("in-sample headline repro (2034 / +82.24 stream)",
      len(closed) == 2034 and abs(total - 82.24) < 0.5,
      f"tr={len(closed)} R={total:.2f}")

print()
print("FAILURES:", fail)
sys.exit(1 if fail else 0)

ch = r.json()
check("chart 200", r.status_code == 200)
check("chart count", ch.get("count") == 3000, str(ch.get("count")))
check("chart last is 2026", str(ch.get("last_ts", "")).startswith("2026-09"), str(ch.get("last_ts")))
check("chart no dataset key", "dataset" not in ch)
idxs = [s["seg"]["start_idx"] for s in ch["swings"]]
check("chart idx in window", all(0 <= i < ch["count"] for i in idxs if i >= 0))

# 3. validation still works
r = c.get("/api/btc/chart", params={"tf": "5m", "mode": "bogus"})
check("chart bad mode 400", r.status_code == 400, str(r.status_code))
r = c.get("/api/btc/chart", params={"tf": "9m"})
check("chart bad tf 400", r.status_code == 400, str(r.status_code))
