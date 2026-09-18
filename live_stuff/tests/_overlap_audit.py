"""AUDIT: concurrent-position overlap for multi-LTF configs (coarse trades)."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import build_module, BASE, load_candles, _compute_swings, SWING, MB15

(c15, f15), (c1h, f1h) = load_candles()
sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
sw1h10 = _compute_swings(f1h, "continuous", min_bars=10)
sim = build_module()

for tag, over, s_htf in [("multi-LTF alone (cd10)", dict(exp_mltf=True), sw1h),
                         ("OPTIMAL (cd0+mltf+mb1h10+chop55+persist2)",
                          dict(exp_mltf=True, exp_persist=2, cooldown_bars=0,
                               chop_thresh=55.0), sw1h10)]:
    r = sim(c1h, s_htf, c15, sw15, fine_ltf=[], **{**BASE, **over})
    tr = r["ltf_trades"] if isinstance(r, dict) else r
    evs = []
    for x in tr:
        evs.append((int(x["entry_ts"]), 1))
        evs.append((int(x["exit_ts"]) + 900, -1))
    evs.sort()
    cur = 0; mx = 0; hist = {}
    for _, delta in evs:
        cur += delta; mx = max(mx, cur)
        hist[cur] = hist.get(cur, 0) + 1
    tot = sum(hist.values())
    print("%s: n=%d | max concurrent=%d | bars-at-concurrency: %s"
          % (tag, len(tr), mx, {k: round(100.0 * v / tot, 1) for k, v in sorted(hist.items())}))
print("(overlap audit done)")
