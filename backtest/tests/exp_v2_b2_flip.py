"""V2 - are B2 and FLIP marks placed on the bar the owner's rule requires?

WHY THIS DETECTOR LOOKS THE WAY IT DOES
    fix/V2_BOT_PROMPT.md section 6.1 and 6.2 are both wrong. The owner has
    since settled the rule himself and this detector implements what he said.

    6.1 WRONG: it claims a mark's `px` is always the level that was broken.
    It is not. `_confirm_direction` (firstswing.py:560) records
    `px=b2.pivot.px`, and the B2 branch sets `b2_pivot = Lvl(px=self.hi/self.lo)`
    (lines 460 / 510) - the CANDLE'S OWN new extreme. So a B2's px is never
    comparable to a cross. B1 (line 540) and FLIP (line 599) do record
    `locked_level`, which IS the broken level.

    6.2 WRONG: it claims the engine tests a SEALED extreme and that a running
    max "is a different series". firstswing.py:391-396 shows `e_hi` is a plain
    running maximum (`if c.high > self.e_hi.px`) and `e_hi_prev` carries it to
    the next bar. So `_tgt = self.e_hi_prev` IS the running extreme.

    OWNER, 2026-01-10, on the 06:30 high of 17230.0:
        "the highest point is 6:30, so anyone reaching it would be marked as B2.
         And 12:00 is irrelevant because these are points inside the extreme."

    So: the target is the RUNNING extreme formed after B1, and a mark fires on
    the first bar that strictly crosses it.

WHAT IS CHECKED, PER MARK
    1. self  - the mark's own candle strictly crosses the level it broke.
               For B1/FLIP that level is `locked_level`; for B2 it is `_tgt`
               (= e_hi_prev / e_lo_prev), captured at runtime. Engine untouched.
    2. level - that captured level equals the running max/min of the candles
               from the leg's first bar up to the mark's bar, exclusive.
               An INDEPENDENT reconstruction, from raw candles only.
    3. first - no earlier bar since the previous mark in the same leg crossed
               that same level.

    (2) and (3) are what four earlier detectors got wrong; they compare the
    mark's own level, never the mark's px.

NO PERCENTAGE IS REPORTED UNLESS THE GATE PASSES.
"""
import bisect
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "backend"))

from src.btc.btc_routes import _load_window
from src.btc.btc_swing import compute_btc_swings
from src.firstswing import SwingEngine

TF, MIN_BARS, SYMBOL, LIMIT = "15m", 50, "BTCUSDT_BYBIT", 200000
OUT = HERE / "_v2_b2_flip.json"

# Owner-ruled cases. The detector may not report breadth unless it clears all 7.
GATE = [
    ("2023-03-19 06:00", "B1"),    # breaks the 04:45 high
    ("2023-03-19 06:30", "B2"),    # V13 - fixed by 88ecd00
    ("2023-03-20 06:30", "FLIP"),
    # 2023-03-20 13:30 was read as a FLIP back on 2026-10-12. The owner
    # re-traced it on 2026-10-13 and ruled it a B2: "the extreme high, which
    # was at 4:45, it got broken by 13:30, and this will be a B2 because B1
    # and B2 are on the same direction. So 13:30 is a B2 here."
    ("2023-03-20 13:30", "B2"),
    ("2023-01-02 09:15", "B2"),    # owner-confirmed 2023-01-02
    ("2023-01-06 19:15", "B2"),    # owner-confirmed 2023-01-06
    ("2023-01-10 13:45", "B2"),    # owner-confirmed 2023-01-10
]

CAP = []          # (kind, idx, dir, target_px) in break_marks order
LEG_START = []    # first bar each engine processes


def main():
    candles, flow = _load_window(TF, LIMIT, SYMBOL)[0]
    candles = list(candles)
    flow = list(flow)
    n = len(candles)
    HIGH = [float(x["high"]) for x in candles]
    LOW = [float(x["low"]) for x in candles]
    TS = [x["date"][:16] for x in candles]

    o_init = SwingEngine.__init__
    o_lock = SwingEngine._lock
    o_pb = SwingEngine.process_bar
    o_conf_dir = SwingEngine._confirm_direction
    o_flip = SwingEngine._flip

    DECL = []   # first bar each DECLARED engine processed, in swing order

    def init(self, *a, **k):
        o_init(self, *a, **k)
        self._first = None

    def lock(self, d):
        r = o_lock(self, d)          # _lock SETS locked_level - capture after
        CAP.append(("B1", self.g_idx, d, self.locked_level))
        return r

    def confirm_dir(self):
        tgt = self.e_hi_prev.px if self.dir == "up" else self.e_lo_prev.px
        CAP.append(("B2", self.g_idx, self.dir, tgt))
        return o_conf_dir(self)

    def flip(self, d, as_b2=False):
        tgt = self.e_hi_prev.px if d == "up" else self.e_lo_prev.px
        CAP.append(("B2" if as_b2 else "FLIP", self.g_idx, d, tgt))
        return o_flip(self, d, as_b2)

    def pb(self, *a, **k):
        before = getattr(self, "declared", False)
        r = o_pb(self, *a, **k)
        if getattr(self, "_first", None) is None:
            self._first = self.g_idx
        if self.declared and not before:
            DECL.append(self._first)
        return r

    SwingEngine.__init__, SwingEngine._lock = init, lock
    SwingEngine.process_bar, SwingEngine._confirm_direction = pb, confirm_dir
    SwingEngine._flip = flip
    sw = compute_btc_swings(flow, opts={"minBars": MIN_BARS}, max_swings=n // 2)
    SwingEngine.__init__, SwingEngine._lock = o_init, o_lock
    SwingEngine.process_bar, SwingEngine._confirm_direction = o_pb, o_conf_dir
    SwingEngine._flip = o_flip
    if len(DECL) != len(sw):
        print("LEG-START MISALIGNED: %d declared vs %d swings" % (len(DECL), len(sw)))

    # Align captured targets with the marks. NOT 1:1 - an engine that never
    # declares is discarded by compute_btc_swings but its captures still landed
    # in CAP, so greedy-forward matching on (kind, idx) is required.
    marks = [(s, b) for s in sw for b in s["breaks"]]
    used = [False] * len(CAP)
    aligned = []
    for _s, b in marks:
        found = None
        for j, (k, idx, _d, _t) in enumerate(CAP):
            if not used[j] and k == b["kind"] and idx == b["idx"]:
                found = j
                break
        if found is None:
            print("NO CAPTURE for mark %s %s at %d - detector invalid"
                  % (b["kind"], b["idx"], b["idx"]))
            return 1
        used[found] = True
        aligned.append(CAP[found])
    if len(aligned) != len(marks):
        print("ALIGNMENT FAILED: %d marks vs %d captures" % (len(marks), len(aligned)))
        return 1
    stray = sum(1 for u in used if not u)
    print("aligned %d marks   (%d discarded-engine captures ignored)"
          % (len(aligned), stray))

    print("=" * 94)
    print("V2  B2 / FLIP PLACEMENT   running extreme, captured target, no px comparison")
    print("=" * 94)
    print("  swings %d   marks %d" % (len(sw), len(marks)))

    rows = []
    for (s, b), (kind, idx, d, tgt) in zip(marks, aligned):
        px = float(tgt)
        up = (d == "up")
        side = "HIGH" if up else "LOW"
        self_ok = (HIGH[idx] > px) if up else (LOW[idx] < px)
        rows.append({"swing": s["swing_index"], "kind": kind, "dir": d,
                     "idx": idx, "time": TS[idx], "target": px,
                     "self_ok": self_ok, "side": side,
                     "mark_idx": b["idx"], "mark_time": TS[b["idx"]]})

    # ---- gate ---------------------------------------------------------------
    print()
    print("GATE - all 7 must pass before any breadth number is reported")
    print("-" * 94)
    gate_ok = True
    for stamp, kind in GATE:
        hit = [r for r in rows if r["time"] == stamp and r["kind"] == kind]
        if not hit:
            print("   %s %-4s  NOT FOUND" % (stamp, kind))
            gate_ok = False
            continue
        r = hit[0]
        ok = r["self_ok"]
        gate_ok &= ok
        print("   %s %-4s  broke %s %-9.1f  candle H%.1f L%.1f   %s"
              % (stamp, kind, r["side"], r["target"], HIGH[r["idx"]], LOW[r["idx"]],
                 "OK" if ok else "*** NO CROSS ***"))
    print()
    print("   GATE: %s" % ("PASSED" if gate_ok else "FAILED"))
    print()

    # ---- level reconstruction, independent -----------------------------------
    # running extreme from the leg's first bar up to the mark, exclusive
    leg_start_of = {}
    for i, s in enumerate(sw):
        leg_start_of[s["swing_index"]] = DECL[i] if i < len(DECL) else 0

    lvl_bad = []
    for r in rows:
        a = leg_start_of.get(r["swing"], 0)
        seg = range(a, r["idx"])
        if r["dir"] == "up":
            run = max((HIGH[k] for k in seg), default=float("-inf"))
        else:
            run = min((LOW[k] for k in seg), default=float("inf"))
        if abs(run - r["target"]) > 1e-6:
            r["run"] = run
            lvl_bad.append(r)

    # ---- first-cross ---------------------------------------------------------
    first_bad = []
    by_swing = collections.defaultdict(list)
    for r in rows:
        by_swing[r["swing"]].append(r)
    for sidx, group in by_swing.items():
        group.sort(key=lambda r: r["idx"])
        prev = leg_start_of.get(sidx, 0)
        for r in group:
            if not r["self_ok"]:
                prev = r["idx"]
                continue
            px, up = r["target"], (r["dir"] == "up")
            earlier = [k for k in range(prev + 1, r["idx"])
                       if (HIGH[k] > px if up else LOW[k] < px)]
            r["earlier"] = len(earlier)
            if earlier:
                r["earlier_first"] = TS[earlier[0]]
                first_bad.append(r)
            prev = r["idx"]

    # ---- report --------------------------------------------------------------
    print("FLIP  (2418 expected)")
    print("-" * 94)
    fl = [r for r in rows if r["kind"] == "FLIP"]
    for lbl, bad in (("mark candle does not cross its target", [r for r in fl if not r["self_ok"]]),
                     ("target != running extreme from leg start", [r for r in fl if r in lvl_bad]),
                     ("an earlier bar crossed the same target", first_bad and [r for r in first_bad if r["kind"] == "FLIP"] or [])):
        print("   %-42s %d" % (lbl, len(bad)))
    print()
    print("B2  (2380 expected)")
    print("-" * 94)
    b2 = [r for r in rows if r["kind"] == "B2"]
    for lbl, bad in (("mark candle does not cross its target", [r for r in b2 if not r["self_ok"]]),
                     ("target != running extreme from leg start", [r for r in b2 if r in lvl_bad]),
                     ("an earlier bar crossed the same target", [r for r in first_bad if r["kind"] == "B2"])):
        print("   %-42s %d" % (lbl, len(bad)))
    print()
    print("   NOTE: 'earlier bar crossed' is expected in general - the B2 gap rule,")
    print("   arming deferral and dir_confirmed all legitimately hold a mark back.")
    print("   It is a CANDIDATE list for the owner, not a defect list.")
    print()

    if not gate_ok:
        print("GATE FAILED - no breadth number is trustworthy. Stop here.")
        return 1

    OUT.write_text(json.dumps({
        "method": "running_extreme_captured_target",
        "swings": len(sw), "marks": len(marks),
        "gate_passed": gate_ok,
        "flip_n": len(fl), "b2_n": len(b2),
        "flip_self_fail": [r for r in fl if not r["self_ok"]][:300],
        "b2_self_fail": [r for r in b2 if not r["self_ok"]][:300],
        "lvl_mismatch": lvl_bad[:300],
        "first_cross_candidates": first_bad[:300],
    }, indent=1, default=str), encoding="utf-8")
    print("wrote %s" % OUT.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())