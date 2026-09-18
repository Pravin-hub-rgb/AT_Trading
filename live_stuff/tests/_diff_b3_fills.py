"""CRAZE: diff k8-close trades coarse vs fine — is the fine path actually
changing fills? If bit-identical, find out WHY before trusting the result."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import build_module, BASE, load_candles, _compute_swings, SWING, INSTRUMENT, MB15
from src.btc.btc_routes import _load_fine_1m

(c15, f15), (c1h, f1h) = load_candles()
sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
sim = build_module()
KW = {**BASE, "b3_k": 8, "b3_mode": "close"}

rc = sim(c1h, sw1h, c15, sw15, fine_ltf=[], **KW)
tc = rc["ltf_trades"] if isinstance(rc, dict) else rc
print("coarse: %dt gross %+.2f" % (len(tc), sum(float(t["r_multiple"]) for t in tc)))

fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                     max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)
rf = sim(c1h, sw1h, c15, sw15, fine_ltf=fine, **KW)
tf = rf["ltf_trades"] if isinstance(rf, dict) else rf
print("fine  : %dt gross %+.2f" % (len(tf), sum(float(t["r_multiple"]) for t in tf)))

if len(tc) == len(tf):
    diffs = 0
    for a, b in zip(tc, tf):
        if (a["exit_price"] != b["exit_price"] or a["exit_ts"] != b["exit_ts"]
                or a["r_multiple"] != b["r_multiple"]):
            diffs += 1
            if diffs <= 5:
                print("  DIFF #%s: coarse exit %s @ %s r=%s | fine exit %s @ %s r=%s"
                      % (a["trade_no"], a["exit_date"], a["exit_price"], a["r_multiple"],
                         b["exit_date"], b["exit_price"], b["r_multiple"]))
    print("trades with differing fills: %d / %d" % (diffs, len(tc)))
else:
    print("TRADE COUNT MISMATCH")
