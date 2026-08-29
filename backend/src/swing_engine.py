"""FirstSwingEngine — Full first-swing detection with continuation/reversal/confirmation.

Port of FirstSwingEngine from frontend/src/lib/firstswing.ts (lines 59-527).

Rules (course S6 + user spec + docs/first swing detection theory.md):
    REAL — CONTINUATION: session extreme EXTENDS twice in a row (each break against
                          a FRESH extreme, never re-breaking one fixed level) -> dir confirmed.
    REAL — REVERSAL:     one extreme breaks, then price reverses and breaks the
                          OTHER original extreme — exactly ONE break needed -> dir confirmed (flip).
    REVERSAL CASE:       once locked (even dirConfirmed), an OPPOSITE extreme
                          break wipes the swing memory -> flip -> ONE chop/sustain confirms.
    once dir confirmed:   CHOP-BREAK (previous MARKED PIVOT taken out) or
                          N-BAR SUSTAIN -> declared. Sustain is FAILURE-TO-EXTEND:
                          selling swing = 7 closes back ABOVE the broken low;
                          buying swing = 7 closes back BELOW the broken high;
                          a fresh extreme print resets the streak.
    Levels: LIVING session extremes (A/B, zero-lag) drive lock/extend/flip/
            sustain-reference. Walker-sealed pivots are ONLY chop-back targets.
    timeCap gates DECLARATION only — counting runs from bar one; a pre-cap
    trigger is HELD (pending) and flushed on the first bar at/after the cap.
    Arming gate: no lock/flip fires before the first walker pivot exists.

Live-safe: closed bars only; declared end never repaints.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal, Optional

from .walker import WalkerEngine, FlowCandle, AlgoPivot


# ── data types ──────────────────────────────────────────────────────────────

Dir = Literal["up", "down"]
State = Literal["watch", "locked", "confirmed"]
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
class Lvl:
    """A price level with index and time."""
    px: float
    idx: int
    time: str


# ── engine ──────────────────────────────────────────────────────────────────

class FirstSwingEngine:
    """Full first-swing detection engine.

    Options:
        time_cap: nothing declares before this time (default "09:29")
        sustain_bars: N-bar sustain requirement (default 7)
    """

    # Tunables
    time_cap: str = "09:29"
    sustain_bars: int = 7

    def __init__(self, opts: Optional[dict] = None) -> None:
        if opts:
            self.time_cap = opts.get("time_cap", self.time_cap)
            self.sustain_bars = opts.get("sustain_bars", self.sustain_bars)

        self.walker = WalkerEngine()
        self.bars_seen: int = 0
        self.t: str = "00:00"
        self.g_idx: int = -1
        self.hi: float = math.nan
        self.lo: float = math.nan

        # Running session extremes (updated at end of each bar).
        self.e_hi = Lvl(px=float("-inf"), idx=-1, time="")
        self.e_lo = Lvl(px=float("inf"), idx=-1, time="")
        # Frozen extremes as of the PREVIOUS bar close.
        self.e_hi_prev = Lvl(px=float("-inf"), idx=-1, time="")
        self.e_lo_prev = Lvl(px=float("inf"), idx=-1, time="")
        # Frozen WALKER extreme-pivot levels as of the previous bar.
        self.e_hi_pivot: Optional[Lvl] = None
        self.e_lo_pivot: Optional[Lvl] = None
        self.e_hi_pivot_prev: Lvl = Lvl(px=float("-inf"), idx=-1, time="")
        self.e_lo_pivot_prev: Lvl = Lvl(px=float("inf"), idx=-1, time="")

        # Walker-sealed extreme pivots + demoted "normal" pivots.
        self.e_hi_pivot = None
        self.e_lo_pivot = None
        self.normal_highs: list[Lvl] = []
        self.normal_lows: list[Lvl] = []

        self.state: State = "watch"
        self.dir: Optional[Dir] = None
        self.base_dir: Optional[Dir] = None
        self.same_side_breaks: int = 0

        # CORNER pivot: the first walker-sealed pivot AFTER B1 in the locked
        # direction. This forms the V/^ corner shape. B2 requires a LATER pivot
        # to BREAK this corner (not the corner itself).
        self.corner_pivot: Optional[Lvl] = None
        # B2 trigger pivot: the pivot that BROKE the corner and triggered B2
        self.b2_pivot: Optional[Lvl] = None
        # Block chop/sustain on the same bar as B2
        self.just_fired_b2: bool = False
        # B1 bar index: only pivots from AFTER this bar can trigger B2
        self.b1_bar_idx: int = -1
        # Allow corner recording. Starts FALSE after lock, becomes TRUE on next bar.
        self.allow_corner_record: bool = False
        self.dir_confirmed: bool = False
        self.locked_level: float = math.nan

        self.start_idx: int = -1
        self.start_time: str = ""
        self.start_px: float = math.nan
        self.cand_idx: int = -1
        self.cand_time: str = ""
        self.cand_px: float = math.nan

        self.declared: bool = False
        self.tier: Optional[Literal["real"]] = None
        self.end_time: str = ""
        self.end_idx: int = -1
        self.end_px: float = math.nan
        self.confirmed_at_time: str = ""
        self.confirmed_at_idx: int = -1
        self.confirm_source: Optional[Literal["chop", "sustain"]] = None

        self.sustain_streak: int = 0
        # Arming gate: no lock/flip fires before walker emits its first pivot.
        self.armed: bool = False

        self.last_confirm_hit: Optional[dict] = None
        self.break_marks: list[FsBreakMark] = []

    @property
    def locked(self) -> bool:
        """True once a first break has locked a tentative direction."""
        return self.state != "watch"

    # ── public API ─────────────────────────────────────────────────────────

    def process_bar(self, c: FlowCandle, g_idx: int) -> None:
        """Feed one closed bar. State machine updates in-place."""
        if self.declared:
            return
        self.bars_seen += 1
        self.g_idx = g_idx
        self.t = c.date[11:16] if len(c.date) >= 16 else ""
        self.hi = c.high
        self.lo = c.low

        # Clear the B2-block flag at start of each bar.
        self.just_fired_b2 = False

        if self.bars_seen == 1:
            self.e_hi = Lvl(px=c.high, idx=g_idx, time=self.t)
            self.e_lo = Lvl(px=c.low, idx=g_idx, time=self.t)
            self.e_hi_prev = Lvl(px=c.high, idx=g_idx, time=self.t)
            self.e_lo_prev = Lvl(px=c.low, idx=g_idx, time=self.t)
            self.e_hi_pivot = Lvl(px=c.high, idx=g_idx, time=self.t)
            self.e_lo_pivot = Lvl(px=c.low, idx=g_idx, time=self.t)
            self.e_hi_pivot_prev = Lvl(px=c.high, idx=g_idx, time=self.t)
            self.e_lo_pivot_prev = Lvl(px=c.low, idx=g_idx, time=self.t)

        # 1) Consume walker seals — single source of truth for pivots.
        #    The FIRST flip-sealed pivot (bar-1 seed excluded) arms the engine.
        for p in self.walker.process_bar(c, g_idx):
            if not p.sealed:
                continue
            if self.bars_seen >= 2:
                self.armed = True
            if p.kind == "H":
                cur = self.e_hi_pivot
                if cur and p.px > cur.px:
                    self.normal_highs.append(cur)
                    self.e_hi_pivot = Lvl(px=p.px, idx=p.idx, time=p.time)
                    # CORNER: track first pivot after B1 as corner (V/^ shape).
                    if (
                        self.dir == "up"
                        and p.px > self.locked_level
                        and p.idx >= self.b1_bar_idx
                        and self.allow_corner_record
                    ):
                        if self.corner_pivot is None:
                            self.corner_pivot = Lvl(px=p.px, idx=p.idx, time=p.time)
                else:
                    self._push_unique(self.normal_highs, Lvl(px=p.px, idx=p.idx, time=p.time))
            else:
                cur = self.e_lo_pivot
                if cur and p.px < cur.px:
                    self.normal_lows.append(cur)
                    self.e_lo_pivot = Lvl(px=p.px, idx=p.idx, time=p.time)
                    # CORNER: track first pivot after B1 as corner (V/^ shape).
                    if (
                        self.dir == "down"
                        and p.px < self.locked_level
                        and p.idx >= self.b1_bar_idx
                        and self.allow_corner_record
                    ):
                        if self.corner_pivot is None:
                            self.corner_pivot = Lvl(px=p.px, idx=p.idx, time=p.time)
                else:
                    self._push_unique(self.normal_lows, Lvl(px=p.px, idx=p.idx, time=p.time))

        # 2) Direction/break step — per BAR, against FROZEN LIVING SESSION EXTREMES.
        #    Counting ALWAYS runs — timeCap gates DECLARATION only.
        up_break = c.high > self.e_hi_prev.px
        down_break = c.low < self.e_lo_prev.px
        if self.armed:
            self._step(down_break, up_break)

        # 3) Keep candidate end glued to actual bar extreme in swing dir.
        if self.dir == "down" and c.low <= self.e_lo.px:
            self._set_cand(Lvl(px=c.low, idx=g_idx, time=self.t))
        if self.dir == "up" and c.high >= self.e_hi.px:
            self._set_cand(Lvl(px=c.high, idx=g_idx, time=self.t))

        # 4) Sustain check (bar-level) once direction is confirmed.
        self._check_sustain(c)

        # 5) Advance frozen extremes to include THIS bar.
        if c.high > self.e_hi.px:
            self.e_hi = Lvl(px=c.high, idx=g_idx, time=self.t)
        if c.low < self.e_lo.px:
            self.e_lo = Lvl(px=c.low, idx=g_idx, time=self.t)
        self.e_hi_prev = Lvl(px=self.e_hi.px, idx=self.e_hi.idx, time=self.e_hi.time)
        self.e_lo_prev = Lvl(px=self.e_lo.px, idx=self.e_lo.idx, time=self.e_lo.time)
        # Walker extreme-pivot levels as of THIS bar become next bar's reference.
        if self.e_hi_pivot:
            self.e_hi_pivot_prev = Lvl(px=self.e_hi_pivot.px, idx=self.e_hi_pivot.idx,
                                       time=self.e_hi_pivot.time)
        if self.e_lo_pivot:
            self.e_lo_pivot_prev = Lvl(px=self.e_lo_pivot.px, idx=self.e_lo_pivot.idx,
                                       time=self.e_lo_pivot.time)
        # Enable corner recording for the NEXT bar onwards.
        if self.state == "locked":
            self.allow_corner_record = True

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

    # ── private helpers ────────────────────────────────────────────────────

    def _step(self, down_break: bool, up_break: bool) -> None:
        if self.state == "watch":
            if down_break:
                self._lock("down")
            elif up_break:
                self._lock("up")
            return

        if self.dir_confirmed:
            # REVERSAL CASE: opposite extreme break wipes thesis entirely.
            if self.dir == "down" and up_break and not down_break:
                self._flip("up")
                self._check_chop()
                return
            if self.dir == "up" and down_break and not up_break:
                self._flip("down")
                self._check_chop()
                return
            self._check_chop()
            return

        # LOCKED, direction not yet confirmed.
        # B2 confirmation:
        #   - If a corner pivot exists: B2 fires when PRICE breaks the corner.
        #   - If no corner yet: B2 fires on first break of B1 extreme.
        if self.dir == "down":
            if down_break:
                # Check against the latest walker-sealed eLoPivot.
                # Must be from a different bar than B1.
                if (
                    self.e_lo_pivot
                    and self.e_lo_pivot.idx >= self.b1_bar_idx
                    and self.lo < self.e_lo_pivot.px
                ):
                    self.b2_pivot = Lvl(px=self.lo, idx=self.g_idx, time=self.t)
                    self._confirm_direction()
                    self._check_chop()
            elif up_break:
                self._flip("up")
                self._check_chop()
        elif self.dir == "up":
            if up_break:
                if (
                    self.e_hi_pivot
                    and self.e_hi_pivot.idx >= self.b1_bar_idx
                    and self.hi > self.e_hi_pivot.px
                ):
                    self.b2_pivot = Lvl(px=self.hi, idx=self.g_idx, time=self.t)
                    self._confirm_direction()
                    self._check_chop()
            elif down_break:
                self._flip("down")
                self._check_chop()

    def _lock(self, dir: Dir) -> None:
        self.dir = dir
        self.base_dir = dir
        self.same_side_breaks = 1
        self.corner_pivot = None
        self.b2_pivot = None
        self.b1_bar_idx = self.g_idx
        self.state = "locked"
        self.allow_corner_record = False
        s = self.e_lo if dir == "up" else self.e_hi
        self.start_idx = s.idx
        self.start_time = s.time
        self.start_px = s.px
        self.locked_level = self.e_hi_prev.px if dir == "up" else self.e_lo_prev.px
        self.break_marks.append(FsBreakMark(
            idx=self.g_idx, time=self.t, kind="B1", dir=dir, px=self.locked_level,
        ))

    def _confirm_direction(self) -> None:
        self.dir_confirmed = True
        b2 = self.b2_pivot
        self.locked_level = self.e_hi_prev.px if self.dir == "up" else self.e_lo_prev.px
        self.break_marks.append(FsBreakMark(
            idx=b2.idx if b2 else self.g_idx,
            time=b2.time if b2 else self.t,
            kind="B2",
            dir=self.dir,
            px=b2.px if b2 else self.locked_level,
        ))
        self.b2_pivot = None
        self.just_fired_b2 = True

    def _flip(self, dir: Dir) -> None:
        self.dir = dir
        self.base_dir = None
        self.same_side_breaks = 0
        self.corner_pivot = None
        self.b2_pivot = None
        self.b1_bar_idx = -1
        self.allow_corner_record = False
        self.dir_confirmed = True
        s = self.e_lo if dir == "up" else self.e_hi
        self.start_idx = s.idx
        self.start_time = s.time
        self.start_px = s.px
        self.locked_level = self.e_hi_prev.px if dir == "up" else self.e_lo_prev.px
        self.break_marks.append(FsBreakMark(
            idx=self.g_idx, time=self.t, kind="FLIP", dir=dir, px=self.locked_level,
        ))

    def _check_chop(self) -> None:
        # Block chop on same bar as B2.
        if self.just_fired_b2:
            return
        if self.dir == "down":
            tgt = self._latest_pivot(self.normal_highs)
            if tgt and self.hi > tgt.px:
                self.last_confirm_hit = {"pool": "normal", "px": tgt.px,
                                        "idx": tgt.idx, "time": tgt.time}
                self._confirm("chop")
        elif self.dir == "up":
            tgt = self._latest_pivot(self.normal_lows)
            if tgt and self.lo < tgt.px:
                self.last_confirm_hit = {"pool": "normal", "px": tgt.px,
                                        "idx": tgt.idx, "time": tgt.time}
                self._confirm("chop")

    def _check_sustain(self, c: FlowCandle) -> None:
        # Block sustain on same bar as B2.
        if self.just_fired_b2:
            return
        if not self.dir_confirmed:
            self.sustain_streak = 0
            return
        # FRESH-EXTREME reset: a bar extending the swing belongs to the move.
        fresh = c.low < self.e_lo.px if self.dir == "down" else c.high > self.e_hi.px
        if fresh:
            self.sustain_streak = 0
            return
        # FAILURE-TO-EXTEND: selling swing sustains when price rests ABOVE broken low.
        ref = self.locked_level
        hold = c.close > ref if self.dir == "down" else c.close < ref
        self.sustain_streak = self.sustain_streak + 1 if hold else 0
        if self.sustain_streak >= self.sustain_bars:
            self._confirm("sustain")

    def _confirm(self, src: Literal["chop", "sustain"],
                 trig: Optional[dict] = None) -> None:
        # 9:29 rule: nothing DECLARES before the cap.
        if self.t < self.time_cap:
            return
        self.declared = True
        self.tier = "real"
        self.end_idx = self.cand_idx
        self.end_time = self.cand_time
        self.end_px = self.cand_px
        self.confirmed_at_time = trig["time"] if trig else self.t
        self.confirmed_at_idx = trig["idx"] if trig else self.g_idx
        self.confirm_source = src

    def _set_cand(self, l: Lvl) -> None:
        self.cand_idx = l.idx
        self.cand_time = l.time
        self.cand_px = l.px

    def _push_unique(self, pool: list[Lvl], l: Lvl) -> None:
        if not any(x.idx == l.idx and x.px == l.px for x in pool):
            pool.append(l)

    def _latest_pivot(self, pool: list[Lvl]) -> Optional[Lvl]:
        """Return the LATEST (most recent) marked pivot in the pool."""
        if not pool:
            return None
        return pool[-1]

    def debug_pools(self) -> dict:
        return {
            "armed": self.armed,
            "start_idx": self.start_idx,
            "start_px": self.start_px,
            "locked_level_px": self.locked_level,
            "last_confirm_hit": self.last_confirm_hit,
            "normal_highs": [f"{l.time}@{l.px:.2f}" for l in self.normal_highs],
            "normal_lows": [f"{l.time}@{l.px:.2f}" for l in self.normal_lows],
        }


# ── batch helpers ───────────────────────────────────────────────────────────

def compute_fs_v2_results(candles: list[FlowCandle],
                            opts: Optional[dict] = None) -> list[FsV2Result]:
    """Run first-swing detection on candles across all days.

    Args:
        candles: List of FlowCandle sorted by date globally.
        opts: Engine options (time_cap, sustain_bars).

    Returns:
        List of FsV2Result, one per day with a declared swing.
    """
    # Group candles by day.
    by_day: dict[str, list[tuple[int, FlowCandle]]] = {}
    for g_idx, c in enumerate(candles):
        d = c.date[:10]
        by_day.setdefault(d, []).append((g_idx, c))

    out: list[FsV2Result] = []
    for day, items in by_day.items():
        eng = FirstSwingEngine(opts)
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
