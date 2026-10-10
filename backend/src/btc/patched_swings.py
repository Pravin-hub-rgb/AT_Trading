"""The B1 arming patch, as a second swing-chain builder that lives beside the shipped one.

WHY THIS EXISTS
---------------
The owner found, on the chart, a clean up-break of a local pivot at 2026-08-14
22:45 IST that produced no B1 mark. firstswing.py:297-307 defers arming by one bar
whenever a seal arrives, and while that deferral is pending it suppresses the break
outright - including breaks of pivots sealed several bars EARLIER, which is not the
phantom the rule was written to catch.

Measured on the real chain: 4,102 breaks dropped while not armed, of which 3,941
(96%) break a pivot sealed on an earlier bar and only 161 are the phantom case.

WHAT THE PATCH DOES
-------------------
Keeps the phantom suppression. Adds the missing case: a break running in the pending
leg's direction, against a level set on an earlier bar, arms on this bar and keeps
the break.

    old:  pending "up" + up_break   -> falls through, armed is False, dropped
    new:  pending "up" + up_break   -> arm, if e_hi_prev.idx < g_idx

Effect on fsent_champ_long: IS 528 -> 542 trades, +533.37R -> +649.41R; OOS 311
trades, +239.59R -> +266.70R. Chain 4,532 -> 4,597 legs.

WHY IT IS A SECOND MODULE AND NOT AN EDIT
-----------------------------------------
firstswing.py is never modified, so the shipped chain still exists and a side-by-side
comparison is possible at all.

The first two implementations swapped src.firstswing in sys.modules and reload()
ed src.btc.btc_swing around the call, then restored. Both leaked. Because
btc_routes does `from .btc_swing import compute_btc_swings` at import time, the
function object it holds shares __globals__ with the reloaded module, so a restore
that left the patched class in btc_swing.__dict__ silently made every SUBSEQUENT
shipped request use the patched chain - measured: the shipped path returned 2,296
swings after one patched call instead of 2,258. A comparison tool that quietly
changes the thing it is comparing against is worse than no tool.

This version builds both module pairs ONCE, under their own permanent names, and
never touches sys.modules afterwards:

    src.firstswing              shipped     (never rebound)
    src.btc.btc_swing           shipped     (never rebound)
    src.firstswing_b1patch      patched
    src.btc.btc_swing_b1patch   patched, bound to the patched firstswing at build time

No swap, no restore, no reload, nothing to leak, and no cross-contamination between
concurrent requests.

The owner asked for this on the /btc dropdown rather than as a separate chart so two
browser windows on two monitors show the same candles with one chain each.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Optional

_ANCHOR = '''            elif self._pending_leg_dir == "up" and down_break:
                self.armed = True
                self._pending_arm = False
                up_break = False
'''

_PATCH = _ANCHOR + '''            elif self._pending_leg_dir == "up" and up_break:
                if self.e_hi_prev.idx < g_idx:
                    self.armed = True
                    self._pending_arm = False
            elif self._pending_leg_dir == "down" and down_break:
                if self.e_lo_prev.idx < g_idx:
                    self.armed = True
                    self._pending_arm = False
'''

_SRC = Path(__file__).resolve().parents[1]
_FS_PATH = _SRC / "firstswing.py"
_SWING_PATH = _SRC / "btc" / "btc_swing.py"

PATCHED_FS = "src.firstswing_b1patch"
PATCHED_SWING = "src.btc.btc_swing_b1patch"

_patched_swing_fn = None


def _exec_module(name: str, path: Path, text: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__file__ = str(path)
    mod.__package__ = name.rsplit(".", 1)[0]
    mod.__dict__["__name__"] = name
    sys.modules[name] = mod           # before exec: @dataclass resolves via sys.modules
    exec(compile(text, str(path), "exec"), mod.__dict__)
    return mod


def _build_patched():
    """Build the patched firstswing + btc_swing pair, once, under their own names."""
    global _patched_swing_fn
    if _patched_swing_fn is not None:
        return _patched_swing_fn

    fs_src = _FS_PATH.read_text(encoding="utf-8")
    n = fs_src.count(_ANCHOR)
    if n != 1:
        raise RuntimeError(
            "B1 arming patch anchor matched %d times in %s - refusing to guess. "
            "The patch is inert until the anchor is unique again." % (n, _FS_PATH))

    # btc_swing imports SwingEngine by absolute name, so the patched firstswing has
    # to occupy `src.firstswing` WHILE btc_swing's body executes, and the binding
    # it takes is then permanent inside that module's own globals.
    saved = sys.modules.get("src.firstswing")
    sys.modules["src.firstswing"] = _exec_module(
        PATCHED_FS, _FS_PATH, fs_src.replace(_ANCHOR, _PATCH))
    try:
        swing_src = _SWING_PATH.read_text(encoding="utf-8")
        patched_swing = _exec_module(PATCHED_SWING, _SWING_PATH, swing_src)
    finally:
        if saved is not None:
            sys.modules["src.firstswing"] = saved     # shipped firstswing, unbound
        else:
            sys.modules.pop("src.firstswing", None)

    _patched_swing_fn = patched_swing.compute_btc_swings
    return _patched_swing_fn


def compute_swings_patched(flow, mode: str, min_bars: int = 14) -> list[dict]:
    """compute_btc_swings with the B1 arming patch. Same signature as the shipped one."""
    fn = _build_patched()
    opts = {"minBars": max(2, int(min_bars))}
    cap = max(1, len(flow) // 2)
    if mode == "continuous":
        return fn(flow, opts=opts, max_swings=cap)

    # daily mode needs the index-offset fix-up the route module does
    from .btc_routes import _IDX_FIELDS        # lazy: circular at module level
    swings: list[dict] = []
    slice_start = 0
    n = len(flow)
    for i in range(1, n + 1):
        if i == n or flow[i].date[:10] != flow[slice_start].date[:10]:
            chunk = flow[slice_start:i]
            day = fn(chunk, opts={"minBars": max(2, int(min_bars))},
                     max_swings=max(1, len(chunk) // 2))
            for s in day:
                for f in _IDX_FIELDS:
                    if s.get(f, -1) >= 0:
                        s[f] += slice_start
                seg = s.get("seg") or {}
                if seg.get("start_idx", -1) >= 0:
                    seg["start_idx"] += slice_start
                if seg.get("end_idx", -1) >= 0:
                    seg["end_idx"] += slice_start
                for b in s["breaks"]:
                    b["idx"] += slice_start
            swings.extend(day)
            slice_start = i
    return swings