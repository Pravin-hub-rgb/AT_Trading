"""FsV2Engine — Full first-swing detection (v2) with continuation/reversal/confirmation.

Port of FsV2Engine from frontend/src/lib/flowline.ts (lines 549-943).

Rules (course S6 + user spec + docs/first swing detection theory.md):
    REAL — CONTINUATION: session extreme EXTENDS twice in a row (each break against
                          a FRESH extreme, never re-breaking one fixed level) -> dir confirmed.
    REAL — REVERSAL:     one extreme breaks, then price reverses and breaks the
                          OTHER original extreme — exactly ONE break needed -> dir confirmed (flip).
    REAL — INVALIDATION: opposite extreme breaks the START before declaration -> reset.
    once dir confirmed:   CHOP-BREAK (previous MARKED PIVOT taken out, normal OR micro)
                          or N-BAR SUSTAIN -> declared. Sustain is FAILURE-TO-EXTEND:
                          selling swing = N closes back BELOW the broken low;
                          buying swing = N closes back ABOVE the broken high;
                          a fresh extreme print resets the streak.
    Levels: LIVING session extremes (A/B, zero-lag) drive lock/extend/flip/sustain-reference.
            Walker-sealed pivots are BOTH chop-break targets (normal) and E-level references.
            Micro pivots are additional chop-break targets.
    timeCap gates all actions — nothing before 9:29.
    v3 fast-path: single E-break lock + opposite-break invalidation.

Live-safe: closed bars only; declared end never repaints.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal, Optional

from .walker import WalkerEngine, FlowCandle, AlgoPivot


# ── data types ──────────────────────────────────────────────────────────────

Dir = Literal["up", "down"]
BreakKind = Literal["B1", "B2", "FLIP"]


@dataclass
class FsBreakMark:
    """Break marker: B1 (first A/B break), B2 (fresh-extreme extension), FLIP (reversal)."""
    idx: int
    time: str
    kind: BreakKind
    dir: Dir
    px: float


@dataclass
class FlowSegment:
    """First swing segment from start to end."""
    dir: Literal["B", "S"]  # "B" = buy (up), "S" = sell (down)
    start_idx: int
    start_px: float
    end_idx: int
    end_px: float


@dataclass
class FsV2Result:
    """Result of first-swing detection for one day."""
    day: str
    outcome: Literal["real"]
    conf_idx: int
    seg: FlowSegment
    source: Optional[Literal["chop", "sustain"]]
    dir: Dir
    breaks: list[FsBreakMark]


@dataclass
class FsLevel:
    """A price level with index and time."""
    px: float
    idx: int
    time: str


# ── engine ──────────────────────────────────────────────────────────────────

class FsV2Engine:
    """Full first-swing detection engine (v2).

    Options:
        sustainBars: N-bar sustain requirement (default 7)
    """

    # Tunables
    time_cap: str = "09:29"
    sustain_bars: int = 7

    def __init__(self, opts: Optional[dict] = None) -> None:
        if opts:
            self.sustain_bars = opts.get("sustain_bars", self.sustain_bars)

        self.walker = WalkerEngine()
        self.bars_seen: int = 0
        self.t: str = "00:00"
        self.g_idx: int = -1
        self.green: bool = False

        # Running session extremes (path-stamped — freshest candle wins).
        self.e_hi: FsLevel = FsLevel(px=float("-inf"), idx=-1, time="")
        self.e_lo: FsLevel = FsLevel(px=float("inf"), idx=-1, time="")
        # Walker extreme pivots (sealed pivots).
        self.e_hi_pivot: Optional[FsLevel] = None
        self.e_lo_pivot: Optional[FsLevel] = None

        # Normal (walker-sealed) and micro (local) pivot pools.
        self.normal_highs: list[FsLevel] = []
        self.normal_lows: list[FsLevel] = []
        self.micro_highs: list[FsLevel] = []
        self.micro_lows: list[FsLevel] = []

        # Direction state.
        self.dir: Optional[Dir] = None
        self.base_dir: Optional[Dir] = None
        self.same_side_breaks: int = 0
        self.opposite_side_breaks: int = 0
        self.dir_confirmed: bool = False
        self.dir_confirmed_idx: int = -1

        # Lock state.
        self.locked: bool = False
        self.locked_level_px: float = float("nan")

        # Swing start/candidate.
        self.start_idx: int = -1
        self.start_time: str = ""
        self.start_px: float = float("nan")
        self.cand_idx: int = -1
        self.cand_time: str = ""
        self.cand_px: float = float("nan")

        # Declaration.
        self.declared: bool = False
        self.tier: Optional[Literal["real"]] = None
        self.end_time: str = ""
        self.end_idx: int = -1
        self.end_px: float = float("nan")
        self.confirmed_at_time: str = ""
        self.confirmed_at_idx: int = -1
        self.confirm_source: Optional[Literal["chop", "sustain"]] = None
        self.last_confirm_hit: Optional[dict] = None

        # Sustain tracking.
        self.sustain_streak: int = 0

        # History for micro pivot detection.
        self.hist_h: list[float] = []
        self.hist_l: list[float] = []

        # Micro pivot state (previous bar extremes).
        self.p_high: float = float("nan")
        self.p_high_idx: int = -1
        self.p_high_t: str = ""
        self.pp_high: float = float("nan")
        self.pp_high_idx: int = -1
        self.pp_high_t: str = ""
        self.p_low: float = float("nan")
        self.p_low_idx: int = -1
        self.p_low_t: str = ""
        self.pp_low: float = float("nan")
        self.pp_low_idx: int = -1
        self.pp_low_t: str = ""

        # Break marks for chart.
        self.break_marks: list[FsBreakMark] = []

    # ── public API ─────────────────────────────────────────────────────────

    def process_bar(self, c: FlowCandle, g_idx: int) -> None:
        """Feed one closed bar. State machine updates in-place."""
        if self.declared:
            return
        self.bars_seen += 1
        self.t = c.date[11:16] if len(c.date) >= 16 else ""
        self.green = c.close >= c.open
        self.g_idx = g_idx

        if self.bars_seen == 1:
            self.e_hi = FsLevel(px=c.high, idx=g_idx, time=self.t)
            self.e_lo = FsLevel(px=c.low, idx=g_idx, time=self.t)
            self.e_hi_pivot = FsLevel(px=c.high, idx=g_idx, time=self.t)
            self.e_lo_pivot = FsLevel(px=c.low, idx=g_idx, time=self.t)

        # ---- A) Consume walker seals FIRST ----
        for p in self.walker.process_bar(c, g_idx):
            if not p.sealed:
                continue
            if p.kind == "H":
                cur = self.e_hi_pivot
                if cur and p.px > cur.px:
                    self.normal_highs.append(cur)
                    self.e_hi_pivot = FsLevel(px=p.px, idx=p.idx, time=p.time)
                else:
                    self._push_unique(self.normal_highs, FsLevel(px=p.px, idx=p.idx, time=p.time))
            else:
                cur = self.e_lo_pivot
                if cur and p.px < cur.px:
                    self.normal_lows.append(cur)
                    self.e_lo_pivot = FsLevel(px=p.px, idx=p.idx, time=p.time)
                else:
                    self._push_unique(self.normal_lows, FsLevel(px=p.px, idx=p.idx, time=p.time))

        # ---- B) Invalidation: opposite extreme breaks start before declaration ----
        if self.dir_confirmed and self.dir and not self.declared and self.start_idx >= 0:
            if self.dir == "up" and self.e_lo.px < self.start_px:
                self._invalidate()
            elif self.dir == "down" and self.e_hi.px > self.start_px:
                self._invalidate()

        # ---- C) Live path: capture extremes BEFORE halves loop ----
        e_lo_before = self.e_lo.px
        e_hi_before = self.e_hi.px

        # ---- D) Micro local-extremes (completed 2-side pivots) ----
        if self.dir_confirmed and self.dir and self.bars_seen >= 3 and math.isfinite(self.pp_high):
            top_formed = self.p_high > self.pp_high and (c.high < self.p_high or c.low < self.p_low)
            bot_formed = self.p_low < self.pp_low and (c.low > self.p_low or c.high > self.p_high)
            if top_formed and self.p_high_idx > self.start_idx:
                self._push_unique(self.micro_highs, FsLevel(px=self.p_high, idx=self.p_high_idx, time=self.p_high_t))
            if bot_formed and self.p_low_idx > self.start_idx:
                self._push_unique(self.micro_lows, FsLevel(px=self.p_low, idx=self.p_low_idx, time=self.p_low_t))

        self.hist_h.append(c.high)
        self.hist_l.append(c.low)

        # Process halves: green = [low, high], red = [high, low]
        halves: list[tuple[float, bool]] = (
            [(c.low, True), (c.high, False)] if self.green else [(c.high, True), (c.low, False)]
        )

        for px, is_low in halves:
            if self.declared:
                break

            # Live extreme stamps — always update
            if px > self.e_hi.px:
                self.e_hi = FsLevel(px=px, idx=g_idx, time=self.t)
                if self.dir == "up":
                    self._set_cand(self.e_hi)
            if px < self.e_lo.px:
                self.e_lo = FsLevel(px=px, idx=g_idx, time=self.t)
                if self.dir == "down":
                    self._set_cand(self.e_lo)

            # Nothing before timeCap
            if self.t < self.time_cap:
                continue

            # Get E-levels for break detection
            e_lo_lvl = self.e_lo_pivot.px if self.e_lo_pivot else self.e_lo.px
            e_hi_lvl = self.e_hi_pivot.px if self.e_hi_pivot else self.e_hi.px

            # ---- Direction detection ----
            if self.dir_confirmed:
                pass  # Only chop/sustain can fire after confirmation
            elif self.locked or self.dir:
                # Count same-side and opposite-side breaks
                if self.base_dir == "down" and px < e_lo_lvl and px < e_lo_before:
                    self.same_side_breaks += 1
                    if self.same_side_breaks >= 2:
                        self.dir_confirmed = True
                        self.dir_confirmed_idx = g_idx
                        self.locked_level_px = px
                elif self.base_dir == "up" and px > e_hi_lvl and px > e_hi_before:
                    self.same_side_breaks += 1
                    if self.same_side_breaks >= 2:
                        self.dir_confirmed = True
                        self.dir_confirmed_idx = g_idx
                        self.locked_level_px = px
                elif self.base_dir == "down" and px > e_hi_lvl and px > e_hi_before:
                    self.opposite_side_breaks = 1
                    self.dir = "up"
                    self.dir_confirmed = True
                    self.dir_confirmed_idx = g_idx
                    self.locked_level_px = e_hi_lvl
                elif self.base_dir == "up" and px < e_lo_lvl and px < e_lo_before:
                    self.opposite_side_breaks = 1
                    self.dir = "down"
                    self.dir_confirmed = True
                    self.dir_confirmed_idx = g_idx
                    self.locked_level_px = e_lo_lvl

            # ---- v3 fast-path: single E-break LOCK ----
            if not self.locked:
                down_break = self.dir == "down" and px < e_lo_lvl
                up_break = self.dir == "up" and px > e_hi_lvl
                first_break_down = self.dir is None and px < e_lo_lvl
                first_break_up = self.dir is None and px > e_hi_lvl

                if down_break or first_break_down:
                    self.locked = True
                    self.locked_level_px = e_lo_lvl
                    self._set_cand(self.e_lo)
                    if self.dir is None:
                        self.dir = "down"
                        self._initiate("down", self.t)
                        self.base_dir = "down"
                        self.same_side_breaks = 1
                    elif self.base_dir == "down":
                        self.same_side_breaks += 1
                        if self.same_side_breaks >= 2:
                            self.dir_confirmed = True
                            self.dir_confirmed_idx = g_idx
                            self.locked_level_px = px
                    else:
                        self.opposite_side_breaks = 1
                        self.dir = "up"
                        self.dir_confirmed = True
                        self.dir_confirmed_idx = g_idx

                elif up_break or first_break_up:
                    self.locked = True
                    self.locked_level_px = e_hi_lvl
                    self._set_cand(self.e_hi)
                    if self.dir is None:
                        self.dir = "up"
                        self._initiate("up", self.t)
                        self.base_dir = "up"
                        self.same_side_breaks = 1
                    elif self.base_dir == "up":
                        self.same_side_breaks += 1
                        if self.same_side_breaks >= 2:
                            self.dir_confirmed = True
                            self.dir_confirmed_idx = g_idx
                            self.locked_level_px = px
                    else:
                        self.opposite_side_breaks = 1
                        self.dir = "down"
                        self.dir_confirmed = True
                        self.dir_confirmed_idx = g_idx

            # ---- CHOP-BREAK ----
            if self.dir_confirmed and self.dir and self.start_idx >= 0:
                if self.dir == "down":
                    # For shorts: break of latest high pivot after start
                    normal_cands = [l for l in self.normal_highs if l.idx > self.start_idx and l.idx < g_idx]
                    if normal_cands:
                        target = max(normal_cands, key=lambda l: l.idx)
                        if px > target.px:
                            self.last_confirm_hit = {"pool": "normal", "px": target.px, "idx": target.idx, "time": target.time}
                            self.confirm_source = "chop"
                            self._confirm(g_idx, self.t)
                            return
                    micro_cands = [l for l in self.micro_highs if l.idx > self.start_idx and l.idx < g_idx]
                    if micro_cands:
                        target = max(micro_cands, key=lambda l: l.idx)
                        if px > target.px:
                            self.last_confirm_hit = {"pool": "micro", "px": target.px, "idx": target.idx, "time": target.time}
                            self.confirm_source = "chop"
                            self._confirm(g_idx, self.t)
                            return
                else:
                    # For longs: break of latest low pivot after start (with 1-bar gap for lows)
                    normal_cands = [l for l in self.normal_lows if l.idx > self.start_idx and l.idx + 1 < g_idx]
                    if normal_cands:
                        target = max(normal_cands, key=lambda l: l.idx)
                        if px < target.px:
                            self.last_confirm_hit = {"pool": "normal", "px": target.px, "idx": target.idx, "time": target.time}
                            self.confirm_source = "chop"
                            self._confirm(g_idx, self.t)
                            return
                    micro_cands = [l for l in self.micro_lows if l.idx > self.start_idx and l.idx + 1 < g_idx]
                    if micro_cands:
                        target = max(micro_cands, key=lambda l: l.idx)
                        if px < target.px:
                            self.last_confirm_hit = {"pool": "micro", "px": target.px, "idx": target.idx, "time": target.time}
                            self.confirm_source = "chop"
                            self._confirm(g_idx, self.t)
                            return

        # ---- E) N-candle sustain (bar-level) ----
        if self.t < self.time_cap:
            self.sustain_streak = 0
        elif self.dir_confirmed and self.dir and not self.declared:
            made_new_extreme = (self.dir == "down" and self.e_lo.px < e_lo_before) or \
                             (self.dir == "up" and self.e_hi.px > e_hi_before)
            if made_new_extreme:
                self.sustain_streak = 0
            else:
                if self.dir == "down":
                    self.sustain_streak = self.sustain_streak + 1 if c.close < self.locked_level_px else 0
                else:
                    self.sustain_streak = self.sustain_streak + 1 if c.close > self.locked_level_px else 0
            if self.sustain_streak >= self.sustain_bars:
                self.confirm_source = "sustain"
                self._confirm(g_idx, self.t)
                return
        else:
            self.sustain_streak = 0

        # ---- Shift micro history ----
        self.pp_high, self.pp_high_idx, self.pp_high_t = self.p_high, self.p_high_idx, self.p_high_t
        self.p_high, self.p_high_idx, self.p_high_t = c.high, g_idx, self.t
        self.pp_low, self.pp_low_idx, self.pp_low_t = self.p_low, self.p_low_idx, self.p_low_t
        self.p_low, self.p_low_idx, self.p_low_t = c.low, g_idx, self.t

    def get_result(self, day: str) -> Optional[FsV2Result]:
        """Return structured result if declared, else None."""
        if not self.declared or self.start_idx < 0:
            return None
        return FsV2Result(
            day=day,
            outcome="real",
            conf_idx=self.confirmed_at_idx,
            seg=FlowSegment(
                dir="B" if self.dir == "up" else "S",
                start_idx=self.start_idx,
                start_px=self.start_px,
                end_idx=self.end_idx,
                end_px=self.end_px,
            ),
            source=self.confirm_source,
            dir=self.dir,
            breaks=self.break_marks,
        )

    # ── private helpers ───────────────────────────────────────────────────

    def _invalidate(self) -> None:
        """Reset all state after opposite extreme breaks start."""
        self.dir = None
        self.locked = False
        self.dir_confirmed = False
        self.dir_confirmed_idx = -1
        self.base_dir = None
        self.same_side_breaks = 0
        self.opposite_side_breaks = 0
        self.sustain_streak = 0
        self.locked_level_px = float("nan")
        self.micro_highs.clear()
        self.micro_lows.clear()
        self.start_idx = -1
        self.start_time = ""
        self.start_px = float("nan")
        self.cand_idx = -1
        self.cand_time = ""
        self.cand_px = float("nan")

    def _initiate(self, dir: Dir, t: str) -> None:
        """Initialize swing on first break."""
        self.dir = dir
        self.micro_highs.clear()
        self.micro_lows.clear()
        self.sustain_streak = 0
        self.base_dir = None
        self.same_side_breaks = 0
        self.opposite_side_breaks = 0
        self.dir_confirmed = False
        self.dir_confirmed_idx = -1
        # Swing start = counter-extreme at initiation moment
        s = self.e_lo if dir == "up" else self.e_hi
        self.start_idx = s.idx
        self.start_time = s.time
        self.start_px = s.px
        self._set_cand(self.e_hi if dir == "up" else self.e_lo)

    def _set_cand(self, l: FsLevel) -> None:
        self.cand_idx = l.idx
        self.cand_time = l.time
        self.cand_px = l.px

    def _push_unique(self, pool: list[FsLevel], l: FsLevel) -> None:
        if not any(x.idx == l.idx and x.px == l.px for x in pool):
            pool.append(l)

    def _confirm(self, g_idx: int, t: str) -> None:
        """Confirm the swing (hard timeCap gate)."""
        if t < self.time_cap:
            return
        self.declared = True
        self.tier = "real"
        self.end_idx = self.cand_idx
        self.end_time = self.cand_time
        self.end_px = self.cand_px
        self.confirmed_at_time = t
        self.confirmed_at_idx = g_idx

    def debug_pools(self) -> dict:
        return {
            "start_idx": self.start_idx,
            "start_px": self.start_px,
            "locked_level_px": self.locked_level_px,
            "last_confirm_hit": self.last_confirm_hit,
            "normal_highs": [f"{l.time}@{l.px:.2f}" for l in self.normal_highs],
            "micro_highs": [f"{l.time}@{l.px:.2f}" for l in self.micro_highs],
        }

    def reset(self, seed_px: float, seed_idx: int, seed_time: str) -> None:
        """Re-initialize the engine to detect a new swing starting from a
        pre-defined price level (e.g., the first swing's extreme).

        After reset, the next process_bar call increments bars_seen to 2,
        skipping the bars_seen==1 initialization — the seed bar is already set.
        This allows us to re-run swing detection from an arbitrary point."""
        # Fresh walker (pivot history not shared with first swing)
        self.walker = WalkerEngine()

        # Fake bars_seen=1 state so next process_bar goes to bars_seen=2
        self.bars_seen = 1
        self.t = seed_time
        self.g_idx = seed_idx
        self.green = False

        # Seed extremes — these are the "session start" for second-swing detection
        self.e_hi = FsLevel(px=seed_px, idx=seed_idx, time=seed_time)
        self.e_lo = FsLevel(px=seed_px, idx=seed_idx, time=seed_time)
        self.e_hi_pivot = FsLevel(px=seed_px, idx=seed_idx, time=seed_time)
        self.e_lo_pivot = FsLevel(px=seed_px, idx=seed_idx, time=seed_time)

        # Zero all direction/state
        self.dir: Optional[Dir] = None
        self.base_dir: Optional[Dir] = None
        self.same_side_breaks = 0
        self.opposite_side_breaks = 0
        self.dir_confirmed = False
        self.dir_confirmed_idx = -1
        self.locked = False
        self.locked_level_px = float("nan")

        # Zero swing start/candidate
        self.start_idx = -1
        self.start_time = ""
        self.start_px = float("nan")
        self.cand_idx = -1
        self.cand_time = ""
        self.cand_px = float("nan")

        # Zero declaration
        self.declared = False
        self.tier = None
        self.end_time = ""
        self.end_idx = -1
        self.end_px = float("nan")
        self.confirmed_at_time = ""
        self.confirmed_at_idx = -1
        self.confirm_source = None
        self.last_confirm_hit = None
        self.sustain_streak = 0

        # Clear pools
        self.normal_highs.clear()
        self.normal_lows.clear()
        self.micro_highs.clear()
        self.micro_lows.clear()
        self.hist_h.clear()
        self.hist_l.clear()
        self.break_marks.clear()

        # Reset micro pivot state
        self.p_high = float("nan")
        self.pp_high = float("nan")
        self.p_high_idx = -1
        self.pp_high_idx = -1
        self.p_high_t = ""
        self.pp_high_t = ""
        self.p_low = float("nan")
        self.pp_low = float("nan")
        self.p_low_idx = -1
        self.pp_low_idx = -1
        self.p_low_t = ""
        self.pp_low_t = ""


# ── batch helpers ───────────────────────────────────────────────────────────

def compute_fs_v2_results(candles: list[FlowCandle],
                            opts: Optional[dict] = None) -> list[FsV2Result]:
    """Run first-swing detection on candles across all days.

    Args:
        candles: List of FlowCandle sorted by date globally.
        opts: Engine options (sustain_bars).

    Returns:
        List of FsV2Result, one per day with a declared swing.
    """
    by_day: dict[str, list[tuple[int, FlowCandle]]] = {}
    for g_idx, c in enumerate(candles):
        d = c.date[:10]
        by_day.setdefault(d, []).append((g_idx, c))

    out: list[FsV2Result] = []
    for day, items in by_day.items():
        eng = FsV2Engine(opts)
        for g_idx, c in items:
            eng.process_bar(c, g_idx)

        result = eng.get_result(day)
        if result is not None:
            out.append(result)
    return out


def compute_fs_v2_declared(candles: list[FlowCandle],
                            opts: Optional[dict] = None) -> list[FlowSegment]:
    """Return declared segments only (real swing days)."""
    return [r.seg for r in compute_fs_v2_results(candles, opts)]


# Alias for backward compatibility — now points to correct FirstSwingEngine (port of frontend/src/lib/firstswing.ts)
# The old FsV2Engine (flowline.ts port) is kept as LegacyFsV2Engine for any direct legacy usage.
try:
    from .firstswing import FirstSwingEngine as _CorrectFSE  # type: ignore
    FirstSwingEngine = _CorrectFSE  # type: ignore
    LegacyFsV2Engine = FsV2Engine
except Exception:
    FirstSwingEngine = FsV2Engine  # fallback if firstswing not available
    LegacyFsV2Engine = FsV2Engine
