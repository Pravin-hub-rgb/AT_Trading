"""C16 pivot cost measured on the ROUTE's data window, not the harness cache.

The route and the harness were never measuring the same period:

  route  2023-01-01 05:30 .. 2026-09-10 16:00   129403 x 15m
  cache  2023-01-01 00:15 .. 2026-09-13 10:00   129736 x 15m

so their trade counts differed for reasons that had nothing to do with the stop
rule. This script rebuilds the route's inputs with the route's own helpers and
the book's own parameters, then runs both rules over that one window. The
origin-to-leg delta is then directly comparable.

Run: python -u exp_v19_matrix_route.py     (about 4 min, two engine passes)
"""
import sys, os, types
from pathlib import Path

m = types.ModuleType("websockets")
m.connect = lambda *a, **k: None
m.WebSocketClientProtocol = object
m.exceptions = types.ModuleType("websockets.exceptions")
sys.modules.setdefault("websockets", m)
sys.modules.setdefault("websockets.exceptions", m.exceptions)

SYMBOL = os.environ.get("VENUE", "BTCUSDT_BYBIT")
ROOT = Path(r"C:/Users/Pravin/Desktop/main/AT_Trading")
sys.path.insert(0, str(ROOT / "backend"))
sys.path.append(str(ROOT / "backend" / "src"))

from src.btc.btc_routes import _load_window, _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v19_champion import simulate_htf_ltf_streak_halt as V19

FEE, ES, XS, FUND = 0.055, 0.005, 0.01, 0.01

# Books params, frontend/src/lib/books.ts V19.
LTF_MIN_BARS, HTF_MIN_BARS = 50, 10

# _load_window returns ((candles, flow), error) - two levels of unpacking.
win, err = _load_window("15m", None, SYMBOL)
assert err is None, err
candles, flow = win
swings = _compute_swings(flow, "continuous", min_bars=LTF_MIN_BARS)
hwin, herr = _load_window("1h", None, SYMBOL)
assert herr is None, herr
candles_htf, hflow = hwin
swings_htf = _compute_swings(hflow, "continuous", min_bars=HTF_MIN_BARS)
fine = _load_fine_1m(candles[0]["ts"], candles[-1]["ts"], SYMBOL)


def costs(cl):
    tot = 0.0
    for x in cl:
        rk = abs(float(x["entry_price"]) - float(x["sl"]))
        if rk <= 0:
            continue
        e = abs(float(x["entry_price"]))
        xp = abs(float(x.get("exit_price", x["entry_price"])))
        tot += ((e + xp) * (FEE / 100.0) + e * (ES / 100.0) + xp * (XS / 100.0)) / rk \
            + e * (FUND / 100.0) / 32.0 * int(x.get("bars_held", 0)) / rk
    return tot


rows = []
print(f"  window {candles[0]['date']} .. {candles[-1]['date']}   "
      f"{len(candles)} x 15m, {len(fine or [])} x 1m")
for rule in ("origin", "leg"):
    r = V19(candles_htf, swings_htf, candles, swings, fine_ltf=fine,
            pivot_rule=rule, sl_buf_atr=0.01, ext_stop_r=3.0, mode="atr_high",
            chop_thresh=58.0, cooldown_bars=8, max_consecutive_losses=3,
            htf_rr=3.0, window_end="exit")["ltf_trades"]
    cl = [x for x in r if x.get("outcome") != "open"]
    g = sum(float(x["r_multiple"]) for x in cl)
    c = costs(cl)
    rows.append((rule, len(cl), g, c, g - c))
    print(f"  {rule:7s} n={len(cl):<5d} gross {g:+9.2f}R  cost {c:7.2f}R  net {g-c:+9.2f}R")

o, l = rows
print(f"\n  C16 cost on the route window: {l[4]-o[4]:+.2f}R over {l[1]-o[1]:+d} trades")
print("  harness window, same rules   : -86.67R over -1 trades")

