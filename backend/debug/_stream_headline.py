"""New honest headline: stream selection + 1m fills on 15m full window."""
import json
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, ".")

from fastapi.testclient import TestClient

from server import app

c = TestClient(app)
r = c.get("/api/btc/backtest", params={
    "tf": "15m", "mode": "continuous",
    "entry_break": "decisive", "trailing": "swing", "breakeven_r": 0,
    "min_bars": 50, "fee_pct": 0.05, "slippage_pts": 2,
    "entry_selection": "stream",
})
s = r.json()["stats"]
print("15m Decisive Trail 50 — STREAM + 1m fills + costs:")
print("  trades:", s["trades"], "| win:", s["win_rate"], "% | base:",
      s["total_r"], "R | costs:", s.get("total_costs_r"), "R | NET:",
      s.get("net_total_r"), "R | dd:", s["max_drawdown_r"], "R")
print("  outcomes:", s["outcomes"])

# legacy comparison (final selection, same everything)
r = c.get("/api/btc/backtest", params={
    "tf": "15m", "mode": "continuous",
    "entry_break": "decisive", "trailing": "swing", "breakeven_r": 0,
    "min_bars": 50, "fee_pct": 0.05, "slippage_pts": 2,
    "entry_selection": "final",
})
s2 = r.json()["stats"]
print("15m Decisive Trail 50 — FINAL + 1m fills + costs:")
print("  trades:", s2["trades"], "| win:", s2["win_rate"], "% | base:",
      s2["total_r"], "R | NET:", s2.get("net_total_r"), "R")
