"""Standalone pass-2 FS reconciler - READ-ONLY. Reports; does not fix.

WHAT THIS IS
    A measurement harness. It reads the Bybit 15m window, takes the shipped
    pass-1 chain from `compute_btc_swings`, then independently re-derives every
    FS mark from the CHART's white line (`compute_btc_flow`'s pivot pipeline)
    and reports how many marks would move. It writes one JSON file and prints.

    It deliberately imports nothing from `firstswing.py` or `btc_swing.py` for
    its pass-2 work, and it never mutates them. The single monkeypatch is the
    `_confirm` hook used to capture pass 1's aim point, and it is restored
    before the script ends.

FROZEN RESOLVER (do not re-tune without the owner's chart)
    The 2025-07-20 case settles the gate. Owner-confirmed FS 15:15 breaks the
    14:45 pivot 118037.0 - a pivot that predates that leg's MB50 bar, broken ON
    the gate bar. So the gate is on the BREAK BAR, not the pivot index, which is
    what `firstswing.py` already ships (`bars_seen < min_bars`). An earlier
    revision of fix/FS_TWOPASS_BOT_PROMPT.md states the opposite; that
    statement is false and applying it reproduces the owner's own REJECTED
    alternative answer for 2025-07-20 (16:15 instead of 15:15).

    Three clauses, each mirrored from the engine:
      1 PROMOTE AT THE EMIT BAR. `firstswing.py` promotes a seal at line 328
        and runs `_check_chop` at line 431-432 on the SAME bar, so a pivot is
        aimed at from its own emit bar, not the bar after it. This is the
        insight the five failed attempts missed: the moment a pivot RETIRES is
        the bar the walker emitted it, not the candle the pivot belongs to.
      2 SPEND ON CONTAMINATION. `_check_chop` adds a level to `_spent` the
        moment it is first crossed, so a pivot is live only until its first
        strict cross and is dead after - it does not sit and wait for a later
        breach. Without this the scan slides backward by thousands of bars.
      3 THE OWNER'S GATES, verbatim: the target must be at least two bars old
        (`p.idx > g_idx - 2`), the candle right after the pivot must not breach
        it, and the break is a STRICT `>` / `<`.

    Every other gate `firstswing.py` applies to a real engine leg - fresh
    structure against `dir_established_idx`, and the chain-wide spent ledger -
    is NOT reproduced here. This resolver only substitutes the pivot SOURCE.
    It is therefore a lower bound on how much a pivot-source fix would move.

WHAT A MOVE MEANS HERE
    Not a proposal. A move is "the white line breaks this swing's other pivot
    first". A large negative move is the known per-leg-walker divergence
    showing through, not a candidate fix.
"""
import bisect
import collections
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "backend"))

from src.btc.btc_routes import _load_window
from src.btc.btc_swing import compute_btc_swings
from src.firstswing import SwingEngine
from src.walker import WalkerEngine, _dedupe, _enforce_alternation

TF, MIN_BARS, SYMBOL, LIMIT = "15m", 50, "BTCUSDT_BYBIT", 200000
OUT = HERE / "_fs_twopass.json"

# How far past the pass-1 FS bar a pass-2 resolution may reach. Generous; the
# report prints how many swings were still open at the cap.
SCAN_CAP_BARS = 4000

# A move larger than this many bars is not a timing shift, it is the engine and
# the chart walking different structures. Reported separately, never as a fix.
IMPOSSIBLE = 50

# The owner's confirmed outcomes, verbatim from exp_fs_breaks_pivot.py plus the
# 2023-01-08 case this harness exists for.
OWNER_MUST_HAVE = {
    "2023-03-19 18:30": "owner: first strict cross of the 18:00 low 27131.0",
    "2023-07-02 07:00": "owner: newest pivot 30545.6 crossed cleanly",
    "2023-10-15 15:15": "owner chart walkthrough",
    "2024-07-16 19:00": "owner: 17:45 high 64127.0 contaminated the pivot",
    "2025-07-20 15:15": "owner: 15:15 is the 50th bar AND the first cross of 14:45 118037.0",
    "2025-08-22 21:45": "owner chart walkthrough",
}
OWNER_MUST_NOT_HAVE = {
    "2023-03-19 19:00": "already contaminated at 18:30",
    "2023-07-02 06:30": "breaks no pivot",
    "2024-07-16 18:00": "already contaminated at 17:45",
    "2025-07-20 15:30": "pivot already taken at 15:15",
}
OWNER_BUG_CASE = "2023-01-08 11:45"

# ── pass 1: the shipped chain, plus the pivot each FS aimed at ──────────────
TARGET = {}
_real_confirm = SwingEngine._confirm


def _capture(self, src, trig=None):
    if (self.t[11:16] >= self.time_cap and self.bars_seen >= self.min_bars
            and self._chop_cross_active):
        h = self.last_confirm_hit or {}
        TARGET[self.last_chop_cross_idx] = (h.get("idx"), h.get("px"))
    return _real_confirm(self, src, trig)


# ── the white line: one continuous walker, deduped, alternation-enforced ───
def build_white_line(flow):
    """Return {kind: (emit_bars, rows)} with rows = (emit_bar, idx, px, first_break).

    `first_break` is the first bar in the pivot's LIFETIME that strictly crosses
    it, i.e. [emit_bar, next same-kind emit bar]. -1 when nothing crosses it.

    Lifetime, not unbounded: a same-kind pivot retires the standing one when the
    walker emits it, so a pivot cannot be broken after its successor appeared.
    """
    n = len(flow)
    emit = {}
    raw = []
    eng = WalkerEngine()
    for i, c in enumerate(flow):
        for p in eng.process_bar(c, i):
            raw.append(p)
            emit[(int(p.idx), p.kind, float(p.px))] = i
    pivots = _enforce_alternation(_dedupe(raw))
    out = {}
    for kind in ("L", "H"):
        rows = sorted(
            ((emit.get((int(p.idx), kind, float(p.px)), n - 1), int(p.idx), float(p.px))
             for p in pivots if p.kind == kind),
            key=lambda r: r[0],
        )
        out[kind] = [r[0] for r in rows], rows
    return out, pivots


def resolve(seg, kind, lower, low, high):
    """Faithful per-bar mirror of `_check_chop` over the white line.

    seg = (emit_bars, rows); kind 'L' -> break DOWN through a low, 'H' -> up.
    lower = the leg's MB50 bar index (the gate is on the BREAK BAR).
    Returns (fs_idx, reason).
    """
    emit_bars, rows = seg
    px_of = low if kind == "L" else high
    # Start at the pivot standing immediately before the gate bar: that is the
    # one `_check_chop` is aiming at when the window opens.
    m = max(bisect.bisect_right(emit_bars, lower - 1) - 1, 0)
    for k in range(m, len(rows)):
        eb, idx, px = rows[k]
        if eb > lower + SCAN_CAP_BARS:
            return None, "open-at-cap"
        hi = rows[k + 1][0] if k + 1 < len(rows) else len(low)
        window = px_of[eb:hi + 1]
        hit = np.flatnonzero(window < px) if kind == "L" else np.flatnonzero(window > px)
        if not len(hit):
            continue                       # nothing crosses it in its lifetime
        j = eb + int(hit[0])
        if j < lower:
            continue                       # SPENT inside the 50-bar window
        if idx > j - 2:
            continue                       # must be at least two bars old
        if j > idx + 1:
            seg_ = px_of[idx + 1:j]
            early = np.flatnonzero(seg_ < px) if kind == "L" else np.flatnonzero(seg_ > px)
            if len(early):
                continue                   # already contaminated - SPENT
        return j, "ok"
    return None, "exhausted"


def main():
    candles, flow = _load_window(TF, LIMIT, SYMBOL)[0]
    candles = list(candles)
    flow = list(flow)
    TS = [c["date"][:16] for c in candles]
    LOW = np.array([float(c["low"]) for c in candles])
    HIGH = np.array([float(c["high"]) for c in candles])

    SwingEngine._confirm = _capture
    try:
        swings = compute_btc_swings(flow, opts={"minBars": MIN_BARS},
                                    max_swings=max(1, len(flow) // 2))
    finally:
        SwingEngine._confirm = _real_confirm

    white, pivots = build_white_line(flow)

    print("=" * 88)
    print("FS PASS-2 RECONCILER  (standalone, read-only)")
    print("=" * 88)
    print("  candles %d   pass-1 swings %d   white-line pivots %d"
          % (len(candles), len(swings), len(pivots)))
    print("  resolver: gate on BREAK BAR, promote at emit+0, spend-on-contamination")
    print()

    counts = collections.Counter()
    moves = []
    reasons = collections.Counter()
    for s in swings:
        f1 = s["fs_at_idx"]
        kind = "L" if s["dir"] == "up" else "H"
        f2, why = resolve(white[kind], kind, s["min_bars_idx"], LOW, HIGH)
        reasons[why] += 1
        if f2 is None:
            counts["unresolved"] += 1
            continue
        if f2 == f1:
            counts["unchanged"] += 1
            continue
        counts["moved"] += 1
        delta = f2 - f1
        counts["later" if delta > 0 else "earlier"] += 1
        if abs(delta) > IMPOSSIBLE:
            counts["impossible"] += 1
        ti, tp = TARGET.get(f1, (None, None))
        moves.append({
            "swing": s["swing_index"], "dir": s["dir"],
            "backend_idx": f1, "backend_time": TS[f1],
            "backend_target": None if ti is None else {"idx": ti, "time": TS[ti], "px": tp},
            "white_idx": f2, "white_time": TS[f2], "delta_bars": delta,
        })

    total = len(swings)
    print("RESULT")
    print("-" * 88)
    print("  unchanged  %5d" % counts["unchanged"])
    print("  moved      %5d   (later %d / earlier %d)"
          % (counts["moved"], counts["later"], counts["earlier"]))
    print("  unresolved %5d   %s" % (counts["unresolved"], dict(reasons)))
    print("  of the moved, |delta| > %d bars (impossible as a timing shift): %d"
          % (IMPOSSIBLE, counts["impossible"]))
    print()

    # ---- anchors -----------------------------------------------------------
    by_fs = {}
    for s in swings:
        by_fs.setdefault((s.get("fs_at_time") or "")[:16], []).append(s)

    def pass2_for(stamp):
        s = by_fs[stamp][0]
        kind = "L" if s["dir"] == "up" else "H"
        f2, _ = resolve(white[kind], kind, s["min_bars_idx"], LOW, HIGH)
        return s, (TS[f2] if f2 else None)

    print("OWNER ANCHORS")
    print("-" * 88)
    # every pass-2 FS stamp, computed once - the "must stay clear" anchors are
    # about the whole chain, not one swing
    pass2_stamps = set()
    for s in swings:
        kind = "L" if s["dir"] == "up" else "H"
        f2, _ = resolve(white[kind], kind, s["min_bars_idx"], LOW, HIGH)
        if f2 is not None:
            pass2_stamps.add(TS[f2])

    anchor_rows = []
    verdict_ok = 0
    for stamp in sorted(OWNER_MUST_HAVE):
        s, got = pass2_for(stamp)
        held = got == stamp
        verdict_ok += held
        anchor_rows.append({"stamp": stamp, "rule": "must hold",
                            "pass1": stamp, "pass2": got, "ok": held})
        print("  %-18s pass1 %-18s pass2 %-18s %s"
              % (stamp, stamp, got or "NONE", "OK" if held else "*** MOVED ***"))
    for stamp in sorted(OWNER_MUST_NOT_HAVE):
        clear = stamp not in pass2_stamps
        verdict_ok += clear
        anchor_rows.append({"stamp": stamp, "rule": "must stay clear",
                            "pass2": stamp if not clear else None, "ok": clear})
        print("  %-18s must stay clear                       %s"
              % (stamp, "OK" if clear else "*** APPEARS ***"))

    bug = None
    if OWNER_BUG_CASE in by_fs:
        s, got = pass2_for(OWNER_BUG_CASE)
    else:
        # the backend currently marks this one at 08:00; find the swing by its
        # pass-1 stamp instead
        cand = [s for s in swings if (s.get("fs_at_time") or "")[:16] == "2023-01-08 08:00"]
        s = cand[0] if cand else None
        got = None
        if s:
            kind = "L" if s["dir"] == "up" else "H"
            f2, _ = resolve(white[kind], kind, s["min_bars_idx"], LOW, HIGH)
            got = TS[f2] if f2 else None
    landed = got == OWNER_BUG_CASE
    anchor_rows.append({"stamp": OWNER_BUG_CASE, "rule": "expected to move here",
                        "pass1": (s.get("fs_at_time") or "")[:16] if s else None,
                        "pass2": got, "ok": landed})
    print("  %-18s pass1 %-18s pass2 %-18s %s"
          % (OWNER_BUG_CASE, (s.get("fs_at_time") or "")[:16] if s else "-",
             got or "NONE", "OK" if landed else "*** NOT REPRODUCED ***"))
    print()
    print("  anchors correct: %d / %d" % (verdict_ok, len(anchor_rows)))
    print()

    # ---- 20 dated examples -------------------------------------------------
    moves.sort(key=lambda m: abs(m["delta_bars"]))
    if len(moves) >= 20:
        # 10 tightest, 10 widest - the two ends are the informative ones
        pick = moves[:10] + moves[-10:]
    else:
        pick = moves
    print("20 DATED EXAMPLES  (10 tightest, 10 widest)")
    print("-" * 88)
    for m in pick:
        t = m["backend_target"]
        print("  backend %s  white line %s  (%+d bars)   %s  %s"
              % (m["backend_time"], m["white_time"], m["delta_bars"], m["dir"],
                 "broke %s @%s" % (t["time"], t["px"]) if t else "target unknown"))
    print()

    imp = sorted((m for m in moves if abs(m["delta_bars"]) > IMPOSSIBLE),
                 key=lambda m: -abs(m["delta_bars"]))
    print("IMPOSSIBLE MOVES (|delta| > %d bars) - first 12" % IMPOSSIBLE)
    print("-" * 88)
    for m in imp[:12]:
        t = m["backend_target"]
        print("  backend %s  white line %s  (%+d bars)   swing %d"
              % (m["backend_time"], m["white_time"], m["delta_bars"], m["swing"]))
    print("  %d of %d moved swings are in this class." % (len(imp), counts["moved"]))
    print()

    OUT.write_text(json.dumps({
        "resolver": {"gate": "break_bar", "promote": "emit+0",
                     "spend": "on_contamination", "min_bars": MIN_BARS,
                     "scan_cap_bars": SCAN_CAP_BARS},
        "candles": len(candles), "pass1_swings": len(swings),
        "white_line_pivots": len(pivots),
        "unchanged": counts["unchanged"], "moved": counts["moved"],
        "later": counts["later"], "earlier": counts["earlier"],
        "unresolved": counts["unresolved"],
        "impossible": counts["impossible"],
        "reasons": dict(reasons),
        "anchors_correct": verdict_ok, "anchors_total": len(anchor_rows),
        "anchors": anchor_rows,
        "examples": pick,
        "impossible_examples": imp[:60],
        "all_moves": moves,
    }, indent=1, default=str), encoding="utf-8")
    print("wrote %s" % OUT.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())