"""Exp 19 Phase 1 v2 — SL-swing attribution via the MARK (breaks) stream.

v1 lesson: confirmation-bar approximations lag by ~mb bars -> useless. v2 uses
the swing chain's own breaks lists (B1/FLIP/B2 marks with idx/dir/px) — the
real-time mark stream the walker already emits.

Metrics (per direct -1R SL loss, plus winners for the net view):
- M1: death quality — close beyond SL on the hit bar (structural) vs wick-only.
- M3': is there an OPPOSITE-direction mark at/near the death bar?
       (the SL hit IS the next opposite swing's mark?)
- M2': is there a same-direction B2 mark on a NEW swing between entry and
       death? (the skip-first rule would have moved the entry there)
- M4: counterfactual R for moved entries (entry = mark bar close, SL = that
       swing's origin pivot; causal check: pivot must be formed before mark).
Read-only; coarse fills; late-free (marks fire when they fire).
"""
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest"))
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
MB15 = SWING["min_bars_15m"]; BUF = float(BASE.get("sl_buf_atr", 0.01))

(c15, f15), (c1h, f1h) = load_candles()
sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
r = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=[], **BASE)
trades = r["ltf_trades"] if isinstance(r, dict) else r
close = [float(c["close"]) for c in c15]
open_ = [float(c["open"]) for c in c15]
lo15 = [float(c["low"]) for c in c15]
hi15 = [float(c["high"]) for c in c15]
n = len(c15)
tr_l = [0.0] * n
for k in range(n):
    tr_l[k] = hi15[k] - lo15[k] if k == 0 else max(
        hi15[k] - lo15[k], abs(hi15[k] - close[k - 1]), abs(lo15[k] - close[k - 1]))
atr15 = [0.0] * n
for k in range(n):
    _lo = max(0, k - 13)
    atr15[k] = sum(tr_l[_lo:k + 1]) / (k - _lo + 1)

# ---- global mark stream from the swing chain ----
sw_by_idx = {}
marks = []
for s in sw15:
    sw_by_idx[s["swing_index"]] = s
    for b in s.get("breaks", []):
        marks.append(dict(idx=int(b["idx"]), kind=b["kind"], dir=b["dir"],
                          px=float(b["px"]), swing=s["swing_index"]))
marks.sort(key=lambda m: (m["idx"], m["swing"]))
from collections import Counter
print("MARK STREAM: %d marks | kind/dir: %s"
      % (len(marks), dict(Counter((m["kind"], m["dir"]) for m in marks))))

import bisect as bs
midx = [m["idx"] for m in marks]


def swing_pivot_known(swing_index, at_bar):
    """Causal check: was the swing's origin pivot (start_px) already formed
    (seg.start_idx set) before bar `at_bar`? For up swings start=origin low;
    for down swings start=origin high."""
    s = sw_by_idx[swing_index]
    return int(s["seg"]["start_idx"]) <= at_bar


def cf(x):
    """Counterfactual second-swing entry via MARKS (causal):
    find first B2 mark, dir==same, idx in (i, j), on a NEW swing whose origin
    pivot was already formed at the mark bar. Entry = mark bar close,
    SL = that pivot -/+ buf. Walk to the original exit bar j."""
    i, j, d = x["i"], x["j"], x["d"]
    same = "up" if d == 1 else "down"
    lo_pos = bs.bisect_right(midx, i)
    for m in marks[lo_pos:]:
        if m["idx"] >= j: return None
        if m["dir"] != same or m["kind"] != "B2": continue
        if m["swing"] == x["ie"]: continue              # must be a NEW swing
        if not swing_pivot_known(m["swing"], m["idx"]): continue
        s2 = sw_by_idx[m["swing"]]
        spx = float(s2["seg"]["start_px"])
        k = m["idx"]; e = close[k]
        if d == 1:
            sl_cf = spx - BUF * atr15[k] if atr15[k] > 0 else spx
            if sl_cf >= e: return None
            risk = e - sl_cf
            for b in range(k + 1, j + 1):
                if lo15[b] <= sl_cf:
                    return (min(sl_cf, open_[b]) - e) / risk
            return (close[j] - e) / risk
        else:
            sl_cf = spx + BUF * atr15[k] if atr15[k] > 0 else spx
            if sl_cf <= e: return None
            risk = sl_cf - e
            for b in range(k + 1, j + 1):
                if hi15[b] >= sl_cf:
                    return (e - max(sl_cf, open_[b])) / risk
            return (e - close[j]) / risk
    return None


def analyze(tr_set, label):
    agg = defaultdict(lambda: [0, 0.0, 0, 0])
    m = dict(n=0, close_death=0, opp_mark_at_death=0, movable=0)
    out = dict(skipped=0, avoided=0, still_lost=0, still_won=0, turned=0)
    delta = 0.0
    for t in tr_set:
        i = int(t["entry_idx"]); j = int(t["exit_idx"])
        d = 1 if t["dir"] == "long" else -1
        same = "up" if d == 1 else "down"; opp = "down" if d == 1 else "up"
        ie = int(t["swing_no"]); sl = float(t["sl"]); rv = float(t["r_multiple"])
        # trigger swing: last same-dir mark at/before entry bar
        trig = None
        for mk in reversed(marks[:bs.bisect_right(midx, i)]):
            if mk["dir"] == same: trig = mk; break
        ie_eff = trig["swing"] if trig else ie
        x = dict(i=i, j=j, d=d, ie=ie_eff)
        m["n"] += 1
        a = agg[(t.get("entry_date") or "")[:4]]
        a[0] += 1; a[1] += rv
        if label.startswith("SL"):
            dead_close = (d == 1 and close[j] < sl) or (d == -1 and close[j] > sl)
            m["close_death"] += 1 if dead_close else 0
            opp_near = any(mm["dir"] == opp and abs(mm["idx"] - j) <= 2
                           for mm in marks[bs.bisect_left(midx, max(0, j - 2)):
                                            bs.bisect_right(midx, j + 2)])
            m["opp_mark_at_death"] += 1 if opp_near else 0
        mv = cf(x) is not None
        m["movable"] += 1 if mv else 0
        a[2] += 1 if mv else 0
        r_cf = cf(x) if mv else None
        if not mv:
            if label.startswith("SL"):
                out["skipped"] += 1; delta += 1.0          # rule skips: +1R vs -1R
                a[3] += 1
            else:
                out["skipped"] += 1; delta -= rv           # rule skips a winner
        elif r_cf is not None:
            if label.startswith("SL"):
                (out.__setitem__("avoided", out["avoided"] + 1) if r_cf > 0
                 else out.__setitem__("still_lost", out["still_lost"] + 1))
            else:
                (out.__setitem__("still_won", out["still_won"] + 1) if r_cf > 0
                 else out.__setitem__("turned", out["turned"] + 1))
            delta += r_cf - rv
    print("\n=== %s === n=%d" % (label, m["n"]))
    if label.startswith("SL"):
        print("M1 death quality: close-beyond-SL %d/%d (%.0f%%), wick-only %d"
              % (m["close_death"], m["n"], 100.0 * m["close_death"] / m["n"],
                 m["n"] - m["close_death"]))
        print("M3' opposite mark within +-2 bars of death: %d/%d (%.0f%%)"
              % (m["opp_mark_at_death"], m["n"],
                 100.0 * m["opp_mark_at_death"] / m["n"]))
    print("M2' movable by marks (same-dir NEW-swing B2 before exit): %d/%d (%.0f%%)"
          % (m["movable"], m["n"], 100.0 * m["movable"] / m["n"]))
    print("outcomes: %s" % out)
    print("ROUGH net delta: %+.1fR" % delta)
    for y in sorted(agg):
        a = agg[y]
        print("  %s: n=%d sumR=%+.1f movable=%d skipped=%d"
              % (y, a[0], a[1], a[2], a[3]))
    return delta


sl_losses = [t for t in trades if t["outcome"] == "sl" and float(t["r_multiple"]) <= -0.95]
wins = [t for t in trades if float(t["r_multiple"]) > 0]
print("POPULATION: %d trades | SL-direct %d | winners %d"
      % (len(trades), len(sl_losses), len(wins)))
d1 = analyze(sl_losses, "SL-DIRECT LOSSES (-1R book)")
d2 = analyze(wins, "WINNERS")
print("\nROUGH NET (loss + win): %+.1fR" % (d1 + d2))
print("NOTE: mark-based (breaks stream), causal pivot check applied; entry at")
print("mark-bar close is the study approx (engine convention: next open).")
print("(exp19 metrics v2 done)")
