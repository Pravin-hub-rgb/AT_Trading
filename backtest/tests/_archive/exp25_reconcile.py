"""Exp 25 — RECONCILIATION: re-anchor everything at PRODUCTION params (chop=58).

Root cause found: my scripts' `_p.update(V18_ENGINE)` overwrote the Bybit
chop_thresh (58.0) with the engine default (61.8). All session experiments
before this ran at chop 61.8. Production (btc_routes 914-941) = chop 58.0
-> 351t / +238.0R (fine gross), confirmed by audit v4.
This re-runs the key experiments at TRUE production params. Base = v18 351t.
"""
import sys
from pathlib import Path
from collections import Counter
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import build_module, stats, show, BASE, \
    load_candles, _compute_swings, SWING, MB15
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod

# THE FIX: production chop (58.0), not the V18_ENGINE default (61.8)
BASE_PROD = dict(BASE)
BASE_PROD["chop_thresh"] = 58.0

(c15, f15), (c1h, f1h) = load_candles()
sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
sw1h10 = _compute_swings(f1h, "continuous", min_bars=10)
sim = build_module()

# identity gate at PRODUCTION params: expect 351t / +238.03
r_ship = shipped_mod.simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15,
                                                  fine_ltf=[], **BASE_PROD)
t_ship = r_ship["ltf_trades"] if isinstance(r_ship, dict) else r_ship
s_ship = stats(t_ship)
r0 = sim(c1h, sw1h, c15, sw15, fine_ltf=[], **BASE_PROD)
s0 = stats(r0["ltf_trades"] if isinstance(r0, dict) else r0)
assert s_ship["n"] == 351, "ANCHOR MISMATCH: %dt" % s_ship["n"]
assert s0["rs"] == s_ship["rs"], "IDENTITY GATE FAILED"
print("IDENTITY GATE OK: production anchor %dt / %+.2fR coarse (chop=58; fine gross = +238.03)\n"
      % (s_ship["n"], s_ship["gross"]))

print("=== KEY EXPERIMENTS AT PRODUCTION PARAMS (coarse, base = v18 351t) ===")
show("v18 anchor (chop58)", s_ship)
runs = [
    ("B3 k8-close", dict(b3_k=8, b3_mode="close"), dict(), sw1h),
    ("halt=6", dict(max_consecutive_losses=6), dict(), sw1h),
    ("COMBO B3+halt6", dict(b3_k=8, b3_mode="close",
                            max_consecutive_losses=6), dict(), sw1h),
    ("multi-LTF alone", dict(exp_mltf=True), dict(), sw1h),
    ("their OPTIMAL (mb1h10+chop55+persist2+cd0+mltf)",
     dict(exp_mltf=True, exp_persist=2),
     dict(chop_thresh=55.0, cooldown_bars=0), sw1h10),
]
for tag, hflags, pover, s_htf in runs:
    r = sim(c1h, s_htf, c15, sw15, fine_ltf=[], **{**BASE_PROD, **pover, **hflags})
    tr = r["ltf_trades"] if isinstance(r, dict) else r
    s = stats(tr)
    show(tag, s)
    print("      exits: %s" % dict(Counter(x["outcome"] for x in tr)))
