"""Smoke test: v18 still produces its pinned trade count after pivot_rule threading.

v18 is the LIVE engine (live_loop.py:35). Its pin is 351 trades, count band
[346, 356], net >= 120.0R, PF >= 1.80, every calendar year >= 0
(backend/tests/test_v18_causal_integrity.py).

v18 previously reached _collect_signals with no pivot_rule argument, so it took
the default "leg". It now passes "leg" explicitly. The default was deliberately
NOT changed, so behaviour should be identical - this proves it rather than
assuming it.

Run: python -u exp_v18_smoke.py     (about 3 min)
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
for p in ("backend", "backtest", "backtest/engine", "backtest/sweeps"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from src.btc.btc_routes import _load_window, _compute_swings, _load_fine_1m, _trade_costs
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt as V18
from engine.v18_params import SWING, get_v18_params, V18_ENGINE

# Same construction the pin test uses (test_v18_causal_integrity._bp / _run).
BP = dict(get_v18_params(SYMBOL))
BP.update(V18_ENGINE)
BP["chop_thresh"] = 58.0          # production; V18_ENGINE's 61.8 must not clobber it
LTF_MB = SWING["min_bars_15m"]
HTF_MB = SWING["min_bars_1h"]

win, err = _load_window("15m", None, SYMBOL)
candles, flow = win
swings = _compute_swings(flow, "continuous", min_bars=LTF_MB)
hwin, herr = _load_window("1h", None, SYMBOL)
candles_htf, hflow = hwin
swings_htf = _compute_swings(hflow, "continuous", min_bars=HTF_MB)
fine = _load_fine_1m(candles[0]["ts"], candles[-1]["ts"], SYMBOL)

KEEP = ["sl_buf_atr", "ext_stop_r", "chop_thresh", "atr_low_thresh",
        "atr_high_thresh", "mode", "cooldown_bars", "max_consecutive_losses",
        "htf_rr", "window_end"]
kw = {k: BP[k] for k in KEEP if k in BP}

out = []
r = V18(candles_htf, swings_htf, candles, swings, fine_ltf=fine, **kw)
tr = r["ltf_trades"] if isinstance(r, dict) else []
rs = [float(t["r_multiple"]) for t in tr]
fee = BP.get("fee_pct", 0.055)
c2, _ = _trade_costs(tr, fee, 0.0, BP.get("entry_slip_pct", 0.005),
                     BP.get("exit_slip_pct", 0.010))
gross = sum(rs)
net = gross - c2
w = [x for x in rs if x > 0]
l = [x for x in rs if x < 0]
pf = (sum(w) / abs(sum(l))) if l else 9.0

out.append(f"  window {candles[0]['date']} .. {candles[-1]['date']}  "
           f"min_bars {LTF_MB}/{HTF_MB}  fine={len(fine or [])}")
out.append(f"  v18 leg/leg    n={len(tr):<5d} gross {gross:+9.2f}R  net {net:+9.2f}R  "
           f"PF {pf:.3f}  WR {100*len(w)/len(tr) if tr else 0:.1f}%")
out.append("")
out.append(f"  pin says        n=351        gross +211.72R  net +137.33R  PF 1.907  WR 27.6%")
out.append(f"  band            n in [346,356]  net >= 120.0  PF >= 1.80")
out.append("")
ok_n = 346 <= len(tr) <= 356
ok_net = net >= 120.0
ok_pf = pf >= 1.80
out.append(f"  count band : {'PASS' if ok_n else 'FAIL'} ({len(tr)})")
out.append(f"  net floor  : {'PASS' if ok_net else 'FAIL'} ({net:.2f} vs 120.0)")
out.append(f"  PF floor   : {'PASS' if ok_pf else 'FAIL'} ({pf:.3f} vs 1.80)")

txt = "\n".join(out)
print(txt)
Path(ROOT / "backtest" / "tests" / "_v18.txt").write_text(txt, encoding="utf-8")

