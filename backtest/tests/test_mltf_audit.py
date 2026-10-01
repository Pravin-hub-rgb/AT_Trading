"""Audit multi-LTF: does exp_mltf inflate R independently of cd=0?"""
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
sw1h20 = _compute_swings(f1h, "continuous", min_bars=20)
sw1h10 = _compute_swings(f1h, "continuous", min_bars=10)
fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                     max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)
sim = build_module()
print("Loaded (%0.0fs)" % (time.time() - t0))

B3 = dict(b3_k=8, b3_mode="close")

# 1. Single-position (no mltf) with cd=10 — baseline
kw_single = {**BP, "chop_thresh": 55.0, **B3, "exp_persist": 2,
             "max_consecutive_losses": 6, "cooldown_bars": 10, "exp31_lb": 50}
r = sim(c1h, sw1h10, c15, sw15, fine_ltf=fine, **kw_single)
tr = r["ltf_trades"]
s = stats(tr)
print("\n=== SINGLE-POSITION (no mltf) ===")
print("  %dt gross%+.1f NET%+.1f WR%.1f%% DD%.1f" % (s["n"], s["gross"], net_of(tr), s["wr"], s["dd"]))

# 2. Multi-LTF with cd=10 — same params, just mltf on
kw_mltf_cd10 = {**kw_single, "exp_mltf": True}
r = sim(c1h, sw1h10, c15, sw15, fine_ltf=fine, **kw_mltf_cd10)
tr = r["ltf_trades"]
s = stats(tr)
print("\n=== MULTI-LTF cd=10 ===")
print("  %dt gross%+.1f NET%+.1f WR%.1f%% DD%.1f" % (s["n"], s["gross"], net_of(tr), s["wr"], s["dd"]))
# Show per-year breakdown
py = {}
for t in tr:
    y = t.get("exit_date", "")[:4]
    if y: py[y] = py.get(y, 0.0) + float(t["r_multiple"])
print("  Per-year: %s" % {k: round(v, 1) for k, v in sorted(py.items())})

# 3. Multi-LTF with cd=0 — the "OPTIMAL" config
kw_mltf_cd0 = {**kw_single, "exp_mltf": True, "cooldown_bars": 0}
r = sim(c1h, sw1h10, c15, sw15, fine_ltf=fine, **kw_mltf_cd0)
tr = r["ltf_trades"]
s = stats(tr)
print("\n=== MULTI-LTF cd=0 (OPTIMAL-like) ===")
print("  %dt gross%+.1f NET%+.1f WR%.1f%% DD%.1f" % (s["n"], s["gross"], net_of(tr), s["wr"], s["dd"]))
py = {}
for t in tr:
    y = t.get("exit_date", "")[:4]
    if y: py[y] = py.get(y, 0.0) + float(t["r_multiple"])
print("  Per-year: %s" % {k: round(v, 1) for k, v in sorted(py.items())})

# 4. Check: how many trades overlap in mltf cd=10?
r2 = sim(c1h, sw1h10, c15, sw15, fine_ltf=fine, **kw_mltf_cd10)
tr2 = r2["ltf_trades"]
overlaps = 0
for i, t1 in enumerate(tr2):
    e1 = int(t1["entry_ts"])
    x1 = int(t1["exit_ts"])
    for t2 in tr2[i+1:]:
        e2 = int(t2["entry_ts"])
        if e2 < x1:  # t2 enters before t1 exits
            overlaps += 1
            break
print("\n=== OVERLAP ANALYSIS (mltf cd=10) ===")
print("  Total trades: %d" % len(tr2))
print("  Trades that overlap with at least one other: %d" % overlaps)
print("  Max concurrent potential: %d" % max(
    sum(1 for t2 in tr2 if int(t2["entry_ts"]) <= int(t1["exit_ts"]) and int(t2["exit_ts"]) >= int(t1["entry_ts"]))
    for t1 in tr2) if tr2 else 0)

# 5. Check: how many EXTRA trades does mltf add vs single?
r_single = sim(c1h, sw1h10, c15, sw15, fine_ltf=fine, **kw_single)
tr_single = set(t["entry_ts"] for t in r_single["ltf_trades"])
tr_mltf = set(t["entry_ts"] for t in tr2)
extra = tr_mltf - tr_single
print("  Trades in mltf but NOT in single: %d" % len(extra))
print("  Trades in single but NOT in mltf: %d" % len(tr_single - tr_mltf))

print("\nDone (%0.0fs)" % (time.time() - t0))
