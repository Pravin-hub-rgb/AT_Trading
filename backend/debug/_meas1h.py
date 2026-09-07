"""Measure the two missing 1h sweep configs with 1m-precise fills."""
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, ".")

from fastapi.testclient import TestClient

from server import app

c = TestClient(app)
configs = [
    ("decisive mb30 swing BE0", {"entry_break": "decisive", "min_bars": 30,
                                 "trailing": "swing", "breakeven_r": 0}),
    ("flip mb20 swing BE0", {"entry_break": "flip", "min_bars": 20,
                             "trailing": "swing", "breakeven_r": 0}),
    ("flip mb20 fixed-3R BE0 (=#3)", {"entry_break": "flip", "min_bars": 20,
                                      "trailing": "off", "breakeven_r": 0}),
    ("flip mb30 swing BE0 (=#4)", {"entry_break": "flip", "min_bars": 30,
                                   "trailing": "swing", "breakeven_r": 0}),
]
for name, p in configs:
    r = c.get("/api/btc/backtest", params={
        "tf": "1h", "fee_pct": 0.05, "slippage_pts": 2, **p,
    })
    s = r.json()["stats"]
    print(f"{name:32s} tr={s['trades']:4d} win={s['win_rate']:5.1f}% "
          f"base={s['total_r']:8.2f} NET={s['net_total_r']:8.2f}")
