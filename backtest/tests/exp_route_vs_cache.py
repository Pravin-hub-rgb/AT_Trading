"""Compare the route's own inputs against the harness cache, field by field.

The route builds its inputs at btc_routes.py:696-718:
  candles      = _load_window("15m")   -> _compute_swings(flow, min_bars=50)
  candles_htf  = _load_window("1h")    -> _compute_swings(hflow, min_bars=10)
  fine         = _load_fine_1m(candles[0].ts .. candles[-1].ts)

The harness reads the same five objects out of %TEMP%/at_datacache.pkl. If any of
them differs, the two paths cannot produce the same trades no matter what the
pivot rule is.

Run: python -u exp_route_vs_cache.py
"""
import sys, os, pickle, types
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

with open(Path(os.environ["TEMP"]) / "at_datacache.pkl", "rb") as f:
    d = pickle.load(f)

lines = []
win, err = _load_window("15m", None, SYMBOL)
candles, flow = win
sw15 = _compute_swings(flow, "continuous", min_bars=50)

hwin, herr = _load_window("1h", None, SYMBOL)
c1h, hflow = hwin
sw10 = _compute_swings(hflow, "continuous", min_bars=10)

fine = _load_fine_1m(candles[0]["ts"], candles[-1]["ts"], SYMBOL)


def cmp(name, a, b):
    same = (a == b)
    span = ""
    if not same and a and b:
        span = f"  route[{a[0].get('date')} .. {a[-1].get('date')}]" \
               f"  cache[{b[0].get('date')} .. {b[-1].get('date')}]"
    lines.append(f"  {name:12s} route={len(a) if a else 0:<8d} "
                 f"cache={len(b) if b else 0:<8d} identical={same}{span}")


cmp("candles15", candles, d.get("c15"))
cmp("candles1h", c1h, d.get("c1h"))
cmp("swings15", sw15, d.get("sw15"))
cmp("swings10", sw10, d.get("sw10"))
cmp("fine1m", fine or [], d.get("fine"))

# If the candle lists match but the swings do not, the min_bars the cache was
# built with is not 50. Recover it by searching for the value that reproduces it.
if candles == d.get("c15") and sw15 != d.get("sw15"):
    lines.append("")
    lines.append("  candles match, swings differ -> searching for the cache min_bars:")
    target = len(d["sw15"])
    for mb in range(2, 121):
        s = _compute_swings(flow, "continuous", min_bars=mb)
        if len(s) == target:
            lines.append(f"    min_bars={mb:<4d} -> {len(s)} swings, identical={s == d['sw15']}")
            if s == d["sw15"]:
                break

out = "\n".join(lines)
print(out)
Path(ROOT / "backtest" / "tests" / "_rvc.txt").write_text(out, encoding="utf-8")

