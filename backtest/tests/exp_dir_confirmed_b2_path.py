"""
Decisive test for the biggest assumption in the invariant harness.

`exp_swing_invariants.py` puts 17950 of 20460 suppressed breaks into one bucket:

    confirmed/with the leg - no B2 by design (chop/FS only)

88% of everything it classifies rests on a single structural claim about
`firstswing._step`:

    once `dir_confirmed` is set, there is NO plain-B2 path at all. The two
    one-sided branches inside `if self.dir_confirmed:` emit only `_flip`, and a
    with-the-leg break matches neither, so it falls through to `_check_chop()`
    and produces no mark.

That claim is read off the source. Nobody has ever tested it. If it is wrong,
the harness has been reporting "by design" for 88% of its suppressions and
would happily pass while the engine is wrong.

THE TEST

Pick every bar the harness buckets as "confirmed/with the leg". For each one,
run the engine normally EXCEPT that `dir_confirmed` is forced False for exactly
that one `_step` call and then restored. That is the B2 path, so if the claim is
right a B2 must now appear at that bar.

  B2 appears  -> dir_confirmed was the blocker -> bucket attribution CORRECT
  no B2       -> something else blocks it     -> the claim is WRONG

Restoring immediately after the single step keeps every other decision the
engine makes identical to baseline, so any new B2 is attributable to that one
bit and nothing else. Both runs use the same engine and the same seed data, so
the chains are directly comparable bar-for-bar.

Usage:
    python -u exp_dir_confirmed_b2_path.py

Exit 0 if the claim survives, 1 if it does not.
"""

from __future__ import annotations

import collections
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT / "backtest/tests", ROOT / "backend"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from src.firstswing import SwingEngine  # noqa: E402

MIN_BARS = 50
SYMBOL = "BTCUSDT_BYBIT"
INTERVAL = "15m"
LIMIT = 200_000


def build():
    from src.btc.btc_routes import _load_window
    from src.btc.btc_swing import compute_btc_swings

    candles, flow = _load_window(INTERVAL, LIMIT, SYMBOL)[0]
    candles = list(candles)
    return candles, list(flow)


def marks_of(candles, flow):
    from src.btc.btc_swing import compute_btc_swings

    swings = compute_btc_swings(
        flow, opts={"minBars": MIN_BARS}, max_swings=max(1, len(candles) // 2)
    )
    out: set[tuple[int, str]] = set()
    for s in swings:
        for b in s["breaks"]:
            out.add((int(b["idx"]), b["kind"]))
    return swings, out


def main() -> int:
    candles, flow = build()
    ts = [c["date"][:16] for c in candles]

    # ── baseline ─────────────────────────────────────────────────────────────
    base_swings, base_marks = marks_of(candles, flow)
    print("=" * 78)
    print("DIR_CONFIRMED -> B2 PATH")
    print("=" * 78)
    print("  baseline: %d swings, %d marks" % (len(base_swings), len(base_marks)))
    print()

    # ── find the bars the harness buckets as "confirmed/with the leg" ─────────
    target: list[int] = []
    _orig_step = SwingEngine._step

    def find(self, down_break: bool, up_break: bool):  # type: ignore[no-untyped-def]
        if (
            getattr(self, "dir_confirmed", False)
            and getattr(self, "state", None) == "locked"
            and not (up_break and down_break)
        ):
            d = "up" if up_break else "down"
            if getattr(self, "dir", None) is not None and d == self.dir:
                target.append(int(self.g_idx))
        return _orig_step(self, down_break, up_break)

    SwingEngine._step = find  # type: ignore[method-assign]
    marks_of(candles, flow)
    SwingEngine._step = _orig_step  # type: ignore[method-assign]

    # a bar already carrying a mark cannot demonstrate anything
    target = [g for g in sorted(set(target)) if (g, "B2") not in base_marks]
    print("  bars matching 'confirmed + with-the-leg + one-sided': %d" % len(target))
    print()

    # ── forced run: dir_confirmed False for exactly one step ─────────────────
    forced: list[int] = []

    def force(self, down_break: bool, up_break: bool):  # type: ignore[no-untyped-def]
        flip_back = False
        if int(self.g_idx) in target_set:
            self.dir_confirmed = False
            forced.append(int(self.g_idx))
            flip_back = True
        try:
            return _orig_step(self, down_break, up_break)
        finally:
            if flip_back:
                # restore immediately so every LATER decision is identical to
                # baseline; only this one step saw the flag down
                self.dir_confirmed = True

    target_set = set(target)
    SwingEngine._step = force  # type: ignore[method-assign]
    new_swings, new_marks = marks_of(candles, flow)
    SwingEngine._step = _orig_step  # type: ignore[method-assign]

    b2_now = {g for g, k in new_marks if k == "B2"}
    b2_before = {g for g, k in base_marks if k == "B2"}
    produced = sorted(b2_now - b2_before & set(target))

    print("  forced dir_confirmed=False on %d bars" % len(forced))
    print("  baseline marks: %d    forced-run marks: %d" % (len(base_marks), len(new_marks)))
    print()

    print("-" * 78)
    print("VERDICT")
    print("-" * 78)
    if produced:
        print("  A B2 appeared on %d of the forced bars." % len(produced))
        print("  dir_confirmed WAS the blocker -> the harness bucket is CORRECT.")
        print("  sample:")
        for g in produced[:10]:
            print("    %s" % ts[g])
        print()
        print("  RESULT: claim HOLDS")
        return 0
    print("  No B2 appeared on any forced bar.")
    print("  So dir_confirmed is NOT what suppresses them, and the harness")
    print("  bucket 'confirmed/with the leg - no B2 by design' is WRONG -")
    print("  something else is doing the blocking and is still unidentified.")
    print()
    print("  RESULT: claim FAILS")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
