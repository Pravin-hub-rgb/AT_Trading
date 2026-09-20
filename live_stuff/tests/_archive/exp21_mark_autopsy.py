"""Exp 21 Phase 1 — entry-time MARK-HISTORY autopsy (read-only study).

The swing chain's breaks lists give the B1/FLIP/B2 mark stream. Every v18
entry has a knowable mark history at the entry bar. Buckets (causal — marks
with idx <= entry bar):
- entry mark kind (B2 / FLIP)
- same-dir mark depth since last opposite mark (1/2/3/4+)
- failed-flip-reclaim in the last 4 marks (opp mark followed by same-dir)
- bars since last opposite mark (quartiles)
Outcome profile per bucket: n / losses / win R / loss R / WR / avg R.
Derived veto only if a clean bucket exists (half-split rule applies).
"""
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from replay_harness import load_candles, INSTRUMENT
from engine.v18_params import SWING, get_v18_params, V18_ENGINE
from src.btc.btc_routes import _compute_swings
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt

_p = dict(get_v18_params(INSTRUMENT)); _p.update(V18_ENGINE)
BASE = {k: _p[k] for k in ["sl_buf_atr", "ext_stop_r", "chop_thresh",
                           "atr_low_thresh", "atr_high_thresh", "mode",
                           "cooldown_bars", "max_consecutive_losses",
                           "htf_rr", "window_end"] if k in _p}
(c15, f15), (c1h, f1h) = load_candles()
sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
r = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=[], **BASE)
trades = r["ltf_trades"] if isinstance(r, dict) else r

marks = []
for s in sw15:
    for b in s.get("breaks", []):
        marks.append(dict(idx=int(b["idx"]), kind=b["kind"], dir=b["dir"],
                          px=float(b["px"]), swing=s["swing_index"]))
marks.sort(key=lambda m: (m["idx"], m["swing"]))

rows = []
for t in trades:
    i = int(t["entry_idx"])
    d = 1 if t["dir"] == "long" else -1
    same = "up" if d == 1 else "down"; opp = "down" if d == 1 else "up"
    prior = [m for m in marks if m["idx"] <= i]
    last_opp = None
    for m in reversed(prior):
        if m["dir"] == opp: last_opp = m; break
    depth = sum(1 for m in prior if m["dir"] == same and
                (last_opp is None or m["idx"] > last_opp["idx"]))
    last4 = prior[-4:]
    reclaim = False
    for k in range(len(last4) - 1):
        if last4[k]["dir"] == opp and any(
                mm["dir"] == same for mm in last4[k + 1:]):
            reclaim = True; break
    bsf = (i - last_opp["idx"]) if last_opp else 9999
    rows.append(dict(t=t, kind=t.get("break_kind", "?"), depth=depth,
                     reclaim=reclaim, bsf=bsf,
                     r=float(t["r_multiple"]),
                     yr=(t.get("entry_date") or "")[:4]))


def bucket(name, pred):
    sel = [x for x in rows if pred(x)]
    if not sel:
        print("  %-34s n=%4d" % (name, 0)); return
    losses = [x for x in sel if x["r"] < 0]
    wins = [x for x in sel if x["r"] > 0]
    lr = sum(x["r"] for x in losses); wr_ = sum(x["r"] for x in wins)
    wr = 100.0 * len(wins) / len(sel)
    print("  %-34s n=%4d  R=%+8.1f  WR=%4.1f%%  lossR=%+7.1f  winR=%+7.1f"
          % (name, len(sel), lr + wr_, wr, lr, wr_))


print("=== EXP 21 Phase 1: entry-time mark-history autopsy (coarse) ===")
print("total trades: %d" % len(rows))
print("\n-- entry mark kind --")
for k in sorted(set(x["kind"] for x in rows)):
    bucket("entry=%s" % k, lambda x, k=k: x["kind"] == k)
print("\n-- same-dir mark depth since last flip --")
for dpt in (1, 2, 3, 4):
    bucket("depth=%d" % dpt, lambda x, dpt=dpt: x["depth"] == dpt)
bucket("depth>=5", lambda x: x["depth"] >= 5)
print("\n-- failed-flip-reclaim in last 4 marks --")
bucket("reclaim=YES", lambda x: x["reclaim"])
bucket("reclaim=NO", lambda x: not x["reclaim"])
print("\n-- bars since last flip (quartiles) --")
vals = sorted(x["bsf"] for x in rows if x["bsf"] < 9999)
q1, q2, q3 = vals[len(vals) // 4], vals[len(vals) // 2], vals[3 * len(vals) // 4]
bucket("bsf<=%d (fresh flip)" % q1, lambda x: x["bsf"] <= q1)
bucket("bsf %d-%d" % (q1 + 1, q2), lambda x: q1 < x["bsf"] <= q2)
bucket("bsf %d-%d" % (q2 + 1, q3), lambda x: q2 < x["bsf"] <= q3)
bucket("bsf>%d (old flip)" % q3, lambda x: x["bsf"] > q3)

print("\n-- HALF-SPLIT check on candidate vetoes --")
for name, pred in [("veto depth>=4", lambda x: x["depth"] >= 4),
                   ("veto bsf 24-49", lambda x: q2 < x["bsf"] <= q3),
                   ("veto entry=B2", lambda x: x["kind"] == "B2")]:
    sel = [x for x in rows if pred(x)]
    if not sel: continue
    h1 = sum(x["r"] for x in sel if x["yr"] in ("2023", "2024"))
    h2 = sum(x["r"] for x in sel if x["yr"] in ("2025", "2026"))
    py = defaultdict(float)
    for x in sel: py[x["yr"]] += x["r"]
    print("  %-16s n=%3d  R=%+7.1f  H1=%+7.1f  H2=%+7.1f  %s"
          % (name, len(sel), h1 + h2, h1, h2,
             {k: round(v, 1) for k, v in sorted(py.items())}))
print("\n(exp21 done)")
