"""Resolve halt3 lb14 vs lb50 discrepancy."""
import sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import build_module, stats, BASE, load_candles, _compute_swings, MB15, INSTRUMENT
from src.btc.btc_routes import _load_fine_1m, _trade_costs

BP = dict(BASE)
BP["chop_thresh"] = 58.0

def net_of(tr):
    c2, _ = _trade_costs(tr, 0.055, 0.0, 0.005, 0.010, 0.01)
    return sum(float(t["r_multiple"]) for t in tr) - c2

t0 = time.time()
(c15, f15), (c1h, f1h) = load_candles()
sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
sw1h10 = _compute_swings(f1h, "continuous", min_bars=10)
fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                     max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)
sim = build_module()
print("Loaded (%0.0fs)" % (time.time() - t0))

B3 = dict(b3_k=8, b3_mode="close")

# B3-OPT halt3 cd10 lb14
kw14 = {**BP, "chop_thresh": 55.0, **B3, "exp_persist": 2,
        "max_consecutive_losses": 3, "cooldown_bars": 10}
r14 = sim(c1h, sw1h10, c15, sw15, fine_ltf=fine, **kw14)
tr14 = r14["ltf_trades"]
s14 = stats(tr14)
n14 = net_of(tr14)
print("\nB3-OPT halt3 cd10 lb14: %dt gross%+.1f NET%+.1f WR%.1f%% DD%.1f" % (
    s14["n"], s14["gross"], n14, s14["wr"], s14["dd"]))

# B3-OPT halt3 cd10 lb50
kw50 = {**BP, "chop_thresh": 55.0, **B3, "exp_persist": 2,
        "max_consecutive_losses": 3, "cooldown_bars": 10, "exp31_lb": 50}
r50 = sim(c1h, sw1h10, c15, sw15, fine_ltf=fine, **kw50)
tr50 = r50["ltf_trades"]
s50 = stats(tr50)
n50 = net_of(tr50)
print("B3-OPT halt3 cd10 lb50: %dt gross%+.1f NET%+.1f WR%.1f%% DD%.1f" % (
    s50["n"], s50["gross"], n50, s50["wr"], s50["dd"]))

# B3-OPT halt6 cd10 lb14
kw_h6 = {**BP, "chop_thresh": 55.0, **B3, "exp_persist": 2,
         "max_consecutive_losses": 6, "cooldown_bars": 10}
r_h6 = sim(c1h, sw1h10, c15, sw15, fine_ltf=fine, **kw_h6)
tr_h6 = r_h6["ltf_trades"]
s_h6 = stats(tr_h6)
n_h6 = net_of(tr_h6)
print("B3-OPT halt6 cd10 lb14: %dt gross%+.1f NET%+.1f WR%.1f%% DD%.1f" % (
    s_h6["n"], s_h6["gross"], n_h6, s_h6["wr"], s_h6["dd"]))

# B3-OPT halt6 cd10 lb50
kw_h6_50 = {**BP, "chop_thresh": 55.0, **B3, "exp_persist": 2,
            "max_consecutive_losses": 6, "cooldown_bars": 10, "exp31_lb": 50}
r_h6_50 = sim(c1h, sw1h10, c15, sw15, fine_ltf=fine, **kw_h6_50)
tr_h6_50 = r_h6_50["ltf_trades"]
s_h6_50 = stats(tr_h6_50)
n_h6_50 = net_of(tr_h6_50)
print("B3-OPT halt6 cd10 lb50: %dt gross%+.1f NET%+.1f WR%.1f%% DD%.1f" % (
    s_h6_50["n"], s_h6_50["gross"], n_h6_50, s_h6_50["wr"], s_h6_50["dd"]))

# Trade-level comparison
ids14 = set((t["entry_ts"], round(float(t["r_multiple"]), 4)) for t in tr14)
ids50 = set((t["entry_ts"], round(float(t["r_multiple"]), 4)) for t in tr50)
print("\n=== HALT3 COMPARISON ===")
print("lb14: %d trades, lb50: %d trades" % (len(ids14), len(ids50)))
print("Common: %d, Unique to lb14: %d, Unique to lb50: %d" % (
    len(ids14 & ids50), len(ids14 - ids50), len(ids50 - ids14)))
print("Delta NET: %+.1fR" % (n50 - n14))

ids_h6 = set((t["entry_ts"], round(float(t["r_multiple"]), 4)) for t in tr_h6)
ids_h6_50 = set((t["entry_ts"], round(float(t["r_multiple"]), 4)) for t in tr_h6_50)
print("\n=== HALT6 COMPARISON ===")
print("lb14: %d trades, lb50: %d trades" % (len(ids_h6), len(ids_h6_50)))
print("Common: %d, Unique to lb14: %d, Unique to lb50: %d" % (
    len(ids_h6 & ids_h6_50), len(ids_h6 - ids_h6_50), len(ids_h6_50 - ids_h6)))
print("Delta NET: %+.1fR" % (n_h6_50 - n_h6))

print("\nDone (%0.0fs)" % (time.time() - t0))
