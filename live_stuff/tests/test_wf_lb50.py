"""Walk-forward on B3-OPT+halt6 cd10 with lb=50 vs lb=14 (via CRAZE harness)."""
import sys, time
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import build_module, stats, BASE, \
    load_candles, _compute_swings, SWING, MB15, INSTRUMENT
from engine.v18_params import get_v18_params as _gvp
from src.btc.btc_routes import _load_fine_1m, _trade_costs

BP55 = dict(BASE); BP55["chop_thresh"] = 55.0
B3 = dict(b3_k=8, b3_mode="close")
H6 = dict(max_consecutive_losses=6)
P2 = dict(exp_persist=2)

_g = _gvp(INSTRUMENT)
FEE = (_g["fee_pct"], _g["entry_slip_pct"], _g["exit_slip_pct"])

def net_of(tr):
    c2, _ = _trade_costs(tr, FEE[0], 0.0, FEE[1], FEE[2])
    return sum(float(t["r_multiple"]) for t in tr) - c2

t0 = time.time()
(c15, f15), (c1h, f1h) = load_candles()
sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
sw1h10 = _compute_swings(f1h, "continuous", min_bars=10)
sim = build_module()
fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                     max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)
print("Data loaded (%0.0fs)" % (time.time() - t0))

T0 = int(c15[0]["ts"])
T1 = int(c15[-1]["ts"]) + 900

# Run both configs on full fine data
configs = {
    "B3-OPT+halt6 lb14": {**BP55, **B3, **P2, **H6, "cooldown_bars": 10},
    "B3-OPT+halt6 lb50": {**BP55, **B3, **P2, **H6, "cooldown_bars": 10, "exp31_lb": 50},
}

for tag, kw in configs.items():
    r = sim(c1h, sw1h10, c15, sw15, fine_ltf=fine, **kw)
    tr = r["ltf_trades"] if isinstance(r, dict) else r
    s = stats(tr)
    net = net_of(tr)
    print(f"\n{'='*60}")
    print(f"{tag}: {s['n']}t  NET {net:+.1f}  WR {s['wr']:.1f}%  DD {s['dd']:.1f}")
    print(f"  Per-year: {dict(sorted(s['py'].items()))}")

    # Expanding-window WF: 50/50, 66/34, 75/25
    for pct, label in [(0.50, "50/50"), (0.66, "66/34"), (0.75, "75/25")]:
        cut = T0 + (T1 - T0) * pct
        train = [t for t in tr if t["outcome"] != "open" and int(t["entry_ts"]) < cut]
        test = [t for t in tr if t["outcome"] != "open" and int(t["entry_ts"]) >= cut]
        tr_net = net_of(train) if train else 0
        te_net = net_of(test) if test else 0
        print(f"  {label}: train {len(train)}t {tr_net:+.1f}R  test {len(test)}t {te_net:+.1f}R")

print("\nTotal: %0.0fs" % (time.time() - t0))
