"""Final verification: dropdown order + backend summary."""
import io
import re
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, ".")

s = io.open("../frontend/src/lib/btcMaster.ts", encoding="utf-8").read()
labels = re.findall(r'label: "([^"]+)"', s)
print("dropdown order (%d presets):" % len(labels))
for l in labels:
    print(" ", l)
dm = re.search(r'BTC_MASTER_DEFAULT = "([^"]+)"', s)
print("default:", dm.group(1) if dm else "NOT FOUND")

from fastapi.testclient import TestClient  # noqa: E402

from server import app  # noqa: E402

c = TestClient(app)
j = c.get("/api/btc/summary", params={
    "tf": "15m", "fee_pct": 0.05, "slippage_pts": 2,
    "entry_selection": "stream",
}).json()
print("\n15m stream summary (12 presets):")
for x in j["rows"]:
    print(f"  {x['rank']}. {x['label']} tr={x['trades']} NET={x['net_r']}")
print("best:", j["best"], "| entry_selection:", j.get("entry_selection", "stream"))
