"""Exp 26 fine — NET for the grand-sweep top candidates (production params)."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import build_module, stats, BASE, \
    load_candles, _compute_swings, SWING, MB15, INSTRUMENT
from engine.v18_params import get_v18_params as _gvp
from src.btc.btc_routes import _load_fine_1m, _trade_costs

BP = dict(BASE)
BP["chop_thresh"] = 58.0
_g = _gvp(INSTRUMENT)
FEE = dict(fee_pct=_g["fee_pct"], entry_slip_pct=_g["entry_slip_pct"],
           exit_slip_pct=_g["exit_slip_pct"])

(c15, f15), (c1h, f1h) = load_candles()
sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
sw1h10 = _compute_swings(f1h, "continuous", min_bars=10)
sim = build_module()
print("loading fine 1m...")
fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                     max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)


def net_of(tr):
    c2, _ = _trade_costs(tr, FEE["fee_pct"], 0.0,
                         FEE["entry_slip_pct"], FEE["exit_slip_pct"])
    return sum(float(t["r_multiple"]) for t in tr) - c2


B3 = dict(b3_k=8, b3_mode="close")
print("=== FINE NETs (production params) ===")
print("  references: anchor 351t NET +163.7 | their-OPTIMAL 515t NET +348.0")
for tag, hflags, pover, s_htf in [
        ("S15 B3+OPTIMAL", {**B3, "exp_mltf": True, "exp_persist": 2},
         dict(chop_thresh=55.0, cooldown_bars=0), sw1h10),
        ("S6 mltf+persist5", dict(exp_mltf=True, exp_persist=5), dict(), sw1h),
        ("S9 mltf+mb1h10+chop55", dict(exp_mltf=True),
         dict(chop_thresh=55.0), sw1h10),
        ("S19 OPTIMAL+halt6", dict(exp_mltf=True, exp_persist=2),
         dict(chop_thresh=55.0, cooldown_bars=0, max_consecutive_losses=6), sw1h10)]:
    r = sim(c1h, s_htf, c15, sw15, fine_ltf=fine, **{**BP, **pover, **hflags})
    tr = r["ltf_trades"] if isinstance(r, dict) else r
    s = stats(tr)
    print("  %-20s %4dt gross %+8.1f  NET %+8.1f  WR %4.1f%%  DD %5.1f  H1 %+7.1f H2 %+7.1f"
          % (tag, s["n"], s["gross"], net_of(tr), s["wr"], s["dd"], s["h1"], s["h2"]))
    print("      per-year: %s" % {k: round(v, 1) for k, v in sorted(s["py"].items())})
print("(exp26 fine done)")
