"""Exp 19 Phase 1 — SL-swing attribution metrics (read-only study).

User question: of the direct -1R SL hits, how many were "the next swing"
(the opposite swing forming after entry)? Would the skip-first rule (enter on
the NEXT same-direction swing instead of the first) have avoided/moved them?

Read-only: runs the SHIPPED engine as-is, then studies trades + swing chain.
Stated approximations (conservative):
- "swing confirmed" = confirmed_at bar (cidx). Confirmations LAG breaks by up to
  mb bars, so M2/M4 (movable/counterfactual) undercount vs the real rule which
  acts on the swing's MARK (break) — earlier than confirmation.
- Counterfactual second-swing entry = candidate swing's confirmation-bar close,
  SL = that swing's origin pivot (start_px) -/+ buffer. Late-entry approximation.
- The rule also moves/skips WINNER entries — winners are analyzed too so the
  rough net effect is visible (full walk = Phase 2).
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
from src.btc.btc_engine import CandleStore
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt

_p = dict(get_v18_params(INSTRUMENT)); _p.update(V18_ENGINE)
BASE = {k: _p[k] for k in ["sl_buf_atr", "ext_stop_r", "chop_thresh",
                           "atr_low_thresh", "atr_high_thresh", "mode",
                           "cooldown_bars", "max_consecutive_losses",
                           "htf_rr", "window_end"] if k in _p}
MB15 = SWING["min_bars_15m"]; BUF = float(BASE.get("sl_buf_atr", 0.01))

(c15, f15), (c1h, f1h) = load_candles()
sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
r = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=[], **BASE)
trades = r["ltf_trades"] if isinstance(r, dict) else r
store = CandleStore(c15)
close = [float(c["close"]) for c in c15]
open_ = [float(c["open"]) for c in c15]
lo15 = [float(c["low"]) for c in c15]
hi15 = [float(c["high"]) for c in c15]
n = len(c15)

# ATR15 (14-bar SMA of TR), same construction as the engine
tr_l = [0.0] * n
for k in range(n):
    tr_l[k] = hi15[k] - lo15[k] if k == 0 else max(
        hi15[k] - lo15[k], abs(hi15[k] - close[k - 1]), abs(lo15[k] - close[k - 1]))
atr15 = [0.0] * n
for k in range(n):
    _lo = max(0, k - 13)
    atr15[k] = sum(tr_l[_lo:k + 1]) / (k - _lo + 1)


def cidx(s):
    ct = s.get("confirmed_at_time", "")
    return store.pos(ct) if ct else -1


# ---- swing structure dump (semantics check) ----
s0 = sw15[5]
print("SWING FIELDS:", sorted(s0.keys()))
print("SWING SAMPLE:", {k: (dict(v) if isinstance(v, dict) else v)
                        for k, v in s0.items()})

# ---- per-trade swing context ----
rows = []
match = 0
for t in trades:
    i = int(t["entry_idx"]); j = int(t["exit_idx"])
    d = 1 if t["dir"] == "long" else -1
    same = "up" if d == 1 else "down"; opp = "down" if d == 1 else "up"
    ie = int(t["swing_no"])
    ok = 0 <= ie < len(sw15) and sw15[ie].get("dir") == same
    match += 1 if ok else 0
    opp_i = same_i = None
    for k in range(ie + 1, len(sw15)):
        dk = sw15[k].get("dir")
        if dk == opp and opp_i is None: opp_i = k
        if dk == same and same_i is None: same_i = k
        if opp_i is not None and same_i is not None: break
    rows.append(dict(t=t, i=i, j=j, d=d, same=same, opp=opp, ie=ie, ok=ok,
                     opp_i=opp_i, same_i=same_i,
                     c_opp=cidx(sw15[opp_i]) if opp_i is not None else -1,
                     c_same=cidx(sw15[same_i]) if same_i is not None else -1,
                     sl=float(t["sl"]), r=float(t["r_multiple"]),
                     yr=(t.get("entry_date") or "")[:4]))
print("swing_no->same-dir match: %d/%d  (semantics check)"
      % (match, len(rows)))
print("trades: %d | swing count: %d" % (len(trades), len(sw15)))

sl_losses = [x for x in rows if x["t"]["outcome"] == "sl" and x["r"] <= -0.95]
wins = [x for x in rows if x["r"] > 0]
trail_neg = [x for x in rows if x["r"] < 0 and x["t"]["outcome"] != "sl"]
print("\nPOPULATION: %d trades | SL-direct: %d | trail-negative: %d | winners: %d"
      % (len(rows), len(sl_losses), len(trail_neg), len(wins)))


def cf(x):
    """Counterfactual second-swing entry (late approx): enter at candidate
    same-swing confirmation close; SL = that swing's origin pivot +/- buf.
    Walk to the original exit bar: dead -> -1R-ish fill; else R at orig exit."""
    if x["same_i"] is None or not (x["i"] < x["c_same"] < x["j"]):
        return None
    k = x["c_same"]; sw = sw15[x["same_i"]]
    seg = sw.get("seg", {}); spx = seg.get("start_px")
    if spx is None: return None
    e = close[k]
    if x["d"] == 1:
        sl_cf = float(spx) - BUF * atr15[k] if atr15[k] > 0 else float(spx)
        if sl_cf >= e: return None
        risk = e - sl_cf
        for b in range(k + 1, x["j"] + 1):
            if lo15[b] <= sl_cf:
                fill = min(sl_cf, open_[b])
                return (fill - e) / risk
        return (close[x["j"]] - e) / risk
    else:
        sl_cf = float(spx) + BUF * atr15[k] if atr15[k] > 0 else float(spx)
        if sl_cf <= e: return None
        risk = sl_cf - e
        for b in range(k + 1, x["j"] + 1):
            if hi15[b] >= sl_cf:
                fill = max(sl_cf, open_[b])
                return (e - fill) / risk
        return (e - close[x["j"]]) / risk


# ---- SL-loss metrics ----
print("\n=== SL-DIRECT LOSSES (the -1R book) ===")
agg = defaultdict(lambda: [0, 0.0, 0, 0])  # yr -> [n, sum_r, moved_n, avoided_n]
cnt = dict(close_death=0, opp_formed=0, movable=0, opp_first=0)
cf_out = dict(avoided=0, still_lost=0, skipped=0)
delta = 0.0
for x in sl_losses:
    i, j, d, sl = x["i"], x["j"], x["d"], x["sl"]
    dead_close = (d == 1 and close[j] < sl) or (d == -1 and close[j] > sl)
    cnt["close_death"] += 1 if dead_close else 0
    opp_formed = (x["c_opp"] >= i and x["c_opp"] <= j + MB15)
    cnt["opp_formed"] += 1 if opp_formed else 0
    movable = 0 <= x["c_same"] < j
    cnt["movable"] += 1 if movable else 0
    cnt["opp_first"] += 1 if (x["c_same"] < 0 or (x["c_opp"] >= 0 and x["c_same"] > x["c_opp"])) else 0
    a = agg[x["yr"]]
    a[0] += 1; a[1] += x["r"]
    r_cf = cf(x) if movable else None
    if not movable:
        cf_out["skipped"] += 1; delta += 1.0        # rule skips the trade: +1R vs -1R
        a[3] += 1
    elif r_cf is not None:
        a[2] += 1
        if r_cf > 0:
            cf_out["avoided"] += 1
        else:
            cf_out["still_lost"] += 1
        delta += r_cf - x["r"]
    else:
        pass  # cf not computable (pivot invalid); treat as unchanged
print("death quality: close-below-SL (structural) %d/%d, wick-only %d"
      % (cnt["close_death"], len(sl_losses), len(sl_losses) - cnt["close_death"]))
print("M3 opposite swing confirmed in [entry, death+mb]: %d/%d (%.0f%%)"
      % (cnt["opp_formed"], len(sl_losses), 100.0 * cnt["opp_formed"] / len(sl_losses)))
print("M2 movable (same-dir swing confirmed BEFORE death): %d/%d (%.0f%%)"
      % (cnt["movable"], len(sl_losses), 100.0 * cnt["movable"] / len(sl_losses)))
print("opposite-first ordering: %d/%d" % (cnt["opp_first"], len(sl_losses)))
print("counterfactual: avoided %d | still-lost %d | skipped-by-rule %d"
      % (cf_out["avoided"], cf_out["still_lost"], cf_out["skipped"]))
print("ROUGH net delta on the LOSS book: %+.1fR" % delta)
print("per-year (n / lossR / moved / skipped):")
for y in sorted(agg):
    a = agg[y]
    print("  %s: n=%d lossR=%+.1f moved=%d skipped=%d" % (y, a[0], a[1], a[2], a[3]))

# ---- winner-side cost of the rule ----
print("\n=== WINNERS (the rule moves/skips these too) ===")
wcnt = dict(movable=0, skipped=0, still_won=0, turned_loss=0, better=0)
wdelta = 0.0
wagg = defaultdict(lambda: [0, 0.0])
for x in wins:
    a = wagg[x["yr"]]; a[0] += 1; a[1] += x["r"]
    movable = 0 <= x["c_same"] < x["j"]
    if movable: wcnt["movable"] += 1
    else:
        wcnt["skipped"] += 1; wdelta -= x["r"]; continue
    r_cf = cf(x)
    if r_cf is None: continue
    wdelta += r_cf - x["r"]
    if r_cf > 0: wcnt["still_won"] += 1
    else: wcnt["turned_loss"] += 1
    if r_cf > x["r"]: wcnt["better"] += 1
print("winners movable: %d/%d | skipped-by-rule: %d (win R given up %.1f)"
      % (wcnt["movable"], len(wins), wcnt["skipped"],
         sum(x["r"] for x in wins if not (0 <= x["c_same"] < x["j"]))))
print("moved winners: still-won %d | turned-loss %d | better-than-original %d"
      % (wcnt["still_won"], wcnt["turned_loss"], wcnt["better"]))
print("ROUGH net delta on the WIN book: %+.1fR" % wdelta)
print("ROUGH NET (loss book + win book): %+.1fR" % (delta + wdelta))
print("\nNOTE: late-entry approximation (confirmation bar, not the mark); the")
print("real rule enters EARLIER at the swing's break. Phase-2 walk required")
print("for the true number. All figures coarse fills.")

print("\n(exp19 metrics done)")
