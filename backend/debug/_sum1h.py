"""1h full-window strategy summary (All = Jan-2025 -> Sep-2026)."""
import json
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, ".")

from fastapi.testclient import TestClient

from server import app

c = TestClient(app)
j = c.get("/api/btc/summary", params={"tf": "1h", "fee_pct": 0.05,
                                      "slippage_pts": 2}).json()
print("window bars:", j["count"], "| fill_tf:", j["fill_tf"])
for x in j["rows"]:
    print(f"{x['rank']}. {x['label']:26s} key={x['key']:12s} tr={x['trades']:5d} "
          f"win={x['win_rate']:5.1f} base={x['base_r']:8.2f} NET={x['net_r']:8.2f}")
