"""All master presets, stream semantics, on 15m and 1h full windows."""
import json
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, ".")

from fastapi.testclient import TestClient

from server import app

c = TestClient(app)
out = {}
for tf in ("15m", "1h"):
    j = c.get("/api/btc/summary", params={
        "tf": tf, "fee_pct": 0.05, "slippage_pts": 2,
        "entry_selection": "stream",
    }).json()
    out[tf] = {"count": j["count"], "rows": j["rows"], "best": j["best"]}
    print(f"=== {tf} ({j['count']} bars) — stream + 1m fills + costs ===")
    for x in j["rows"]:
        print(f"  {x['rank']:2d}. {x['label']:28s} tr={x['trades']:5d} "
              f"win={x['win_rate']:5.1f}% base={x['base_r']:8.2f} "
              f"costs={x['costs_r']:7.2f} NET={x['net_r']:8.2f}")
with open("debug/_summary_stream.json", "w") as f:
    json.dump(out, f, indent=1)
print("\nsaved debug/_summary_stream.json")
