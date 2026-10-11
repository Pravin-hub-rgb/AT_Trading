"""SwingEngine � single source of truth for all swing detection.

Python port of frontend/src/lib/firstswing.ts.
Detects 1 or more swings per day.  Use compute_swing_results() for N swings,
compute_whole_day_swings() for all swings in a day.

- WalkerEngine is SINGLE SOURCE OF TRUTH for sealed pivots
- Break detection per BAR against PREVIOUS bar frozen extremes (eHiPrev/eLoPrev)
- Continuation takes precedence over reversal on same bar
- timeCap gates DECLARATION only, counting runs from bar one
- Chop target = LATEST sealed pivot only (latest_sealed_high/low), exact like the
  frontend FsV2Engine (backend/debug/firstswing_cf11277.ts chopTargetHigh/Low):
  "any new H kills old H / any new L kills old L" � killed pivots are dead, there
  is NO fallback scan to older pivots. Gap check at chop-target time (next candle
  must not breach pivot; requires pivot idx <= g_idx - 2) prevents micro-pivot noise.
  Backend-only additions kept deliberately (user-approved fixes beyond the TS):
  minBars=14 declaration guard, B2 1-candle pivot gap (b2_gap_bars=1),
  fresh-structure rule (chop may only target pivots formed after dir_established),
  flip-back-as-B2 (as_b2), first_chop_cross tracking for fs_at markers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal, Optional, Union

from .walker import WalkerEngine, FlowCandle


@dataclass
class FsBreakMark:
    idx: int
    time: str
    kind: Literal["B1", "B2", "FLIP"]
    dir: Literal["up", "down"]
    px: float


@dataclass
class Lvl:
    px: float
    idx: int
    time: str


State = Literal["watch", "locked", "confirmed"]


@dataclass
class FlowSegment:
    dir: Literal["B", "S"]
    start_idx: int
    start_px: float
    end_idx: int
    end_px: float


@dataclass
class FsV2Result:
    day: str
    outcome: Literal["real"]
    conf_idx: int
    seg: FlowSegment
    source: Optional[Literal["chop", "sustain"]]
    dir: Optional[Literal["up", "down"]]
    breaks: list[FsBreakMark]


class SwingEngine:
    def __init__(self, opts: Optional[dict] = None):
        opts = opts or {}
        self.time_cap: str = opts.get("timeCap", "09:29") if isinstance(opts, dict) else getattr(opts, "timeCap", "09:29")
        if isinstance(opts, dict):
            self.sustain_bars: int = opts.get("sustainBars", opts.get("sustain_bars", 7))
            self.min_bars: int = int(opts.get("minBars", opts.get("min_bars", 14)))
            raw_gap = opts.get("b2GapBars", opts.get("b2_gap_bars", opts.get("requirePivotGap", 1)))
            if isinstance(raw_gap, bool):
                self.b2_gap_bars: int = 1 if raw_gap else 0
            else:
                try:
                    self.b2_gap_bars: int = max(0, int(raw_gap))
                except Exception:
                    self.b2_gap_bars: int = 1
        else:
            self.sustain_bars: int = 7
            self.min_bars: int = 14
            self.b2_gap_bars: int = 1

        self.walker = WalkerEngine()
        self.bars_seen: int = 0
        self.t: str = "00:00"
        self.g_idx: int = -1
        self.hi: float = float("nan")
        self.lo: float = float("nan")
        self.ts_map: dict[int, str] = {}  # counter→datetime (for live counter-based g_idx)

        # Same-bar arm guard (swings after the first): a Walker seal emitted
        # during the CURRENT bar must not arm the engine for THAT bar � otherwise
        # a B1 can fire on the same bar the engine first got structure.
        # (30 Sep 2025: the 09:44 bar sealed H 24669.05 and the up-break fired in
        # that same bar -> phantom B1 up "breaking" the 09:43 high 24667.7, a
        # stamp shift inside the straight white 09:42->09:44 leg.) With the guard
        # the seal arms the engine from the NEXT bar: 09:44 no B1, 09:45 B1 down
        # breaking the 09:42 low 24647.15 � the structure-extreme break. B1 keeps
        # the approved extreme-break semantics ("09:30 B1 breaking 09:29 low",
        # old computeSecondSwingResults @ 7fe645d). Applied ONLY to swings after
        # the first (swing_index >= 1) � the first swing keeps the approved FsV2
        # session-extreme spec (firstswing_cf11277).
        if isinstance(opts, dict):
            self.defer_same_bar_arm: bool = bool(opts.get("defer_same_bar_arm", False))
        else:
            self.defer_same_bar_arm = bool(getattr(opts, "defer_same_bar_arm", False))
        self._pending_arm: bool = False
        self._pending_leg_dir = None  # walker leg dir at the bar a seal arrived (V-reversal check)

        self.e_hi: Lvl = Lvl(px=float("-inf"), idx=-1, time="")
        self.e_lo: Lvl = Lvl(px=float("inf"), idx=-1, time="")
        self.e_hi_prev: Lvl = Lvl(px=float("-inf"), idx=-1, time="")
        self.e_lo_prev: Lvl = Lvl(px=float("inf"), idx=-1, time="")
        self.e_hi_pivot_prev: Lvl = Lvl(px=float("-inf"), idx=-1, time="")
        self.e_lo_pivot_prev: Lvl = Lvl(px=float("inf"), idx=-1, time="")

        self.e_hi_pivot: Optional[Lvl] = None
        self.e_lo_pivot: Optional[Lvl] = None
        self.normal_highs: list[Lvl] = []
        self.normal_lows: list[Lvl] = []
        self.bar_highs: dict[int, float] = {}
        self.bar_lows: dict[int, float] = {}
        self.latest_sealed_high: Optional[Lvl] = None
        self.latest_sealed_low: Optional[Lvl] = None

        self.state: State = "watch"
        self.dir: Optional[Literal["up", "down"]] = None
        self.base_dir: Optional[Literal["up", "down"]] = None
        self.same_side_breaks: int = 0
        self.corner_pivot: Optional[Lvl] = None
        self.b2_pivot: Optional[Lvl] = None
        self.just_fired_b2: bool = False
        self.b1_bar_idx: int = -1
        self.allow_corner_record: bool = False
        self.dir_confirmed: bool = False
        self.locked_level: float = float("nan")
        self.flip_established: bool = False   # current dir was born from a FLIP, not a B1
        self.ever_b1_dir: Optional[Literal["up", "down"]] = None  # dir of last B1 that never got its B2
        self.dir_established_idx: int = -1    # bar where current leg became confirmed (B2 or flip)

        self.start_idx: int = -1
        self.start_time: str = ""
        self.start_px: float = float("nan")
        self.cand_idx: int = -1
        self.cand_time: str = ""
        self.cand_px: float = float("nan")

        self.declared: bool = False
        self.tier: Optional[Literal["real"]] = None
        self.end_time: str = ""
        self.end_idx: int = -1
        self.end_px: float = float("nan")
        self.confirmed_at_time: str = ""
        self.confirmed_at_idx: int = -1
        self.confirm_source: Optional[Literal["chop", "sustain"]] = None

        self.sustain_streak: int = 0
        self.armed: bool = False
        self.last_confirm_hit: Optional[dict] = None
        self.first_chop_cross_idx: int = -1
        self.first_chop_cross_px: float = float("nan")
        self.first_chop_cross_time: str = ""
        self.last_chop_cross_idx: int = -1
        self.last_chop_cross_px: float = float("nan")
        self.last_chop_cross_time: str = ""
        self._chop_cross_active: bool = False
        self.break_marks: list[FsBreakMark] = []
        self.seed_idx: int = -1

    @property
    def locked(self) -> bool:
        return self.state != "watch"

    def process_bar(self, c: FlowCandle, g_idx: int) -> None:
        if self.declared:
            return
        self.bars_seen += 1
        self.g_idx = g_idx
        self.t = c.date if len(c.date) >= 16 else ""
        self.hi = c.high
        self.lo = c.low
        self.ts_map[g_idx] = c.date

        self.just_fired_b2 = False

        # Deferred arming: a seal from the PREVIOUS bar arms the engine now
        # (see defer_same_bar_arm note in __init__).
        if self.defer_same_bar_arm and self._pending_arm:
            self.armed = True
            self._pending_arm = False

        if self.bars_seen == 1:
            self.e_hi = Lvl(px=c.high, idx=g_idx, time=self.t)
            self.e_lo = Lvl(px=c.low, idx=g_idx, time=self.t)
            self.e_hi_prev = Lvl(px=self.e_hi.px, idx=self.e_hi.idx, time=self.e_hi.time)
            self.e_lo_prev = Lvl(px=self.e_lo.px, idx=self.e_lo.idx, time=self.e_lo.time)
            self.e_hi_pivot = Lvl(px=self.e_hi.px, idx=self.e_hi.idx, time=self.e_hi.time)
            self.e_lo_pivot = Lvl(px=self.e_lo.px, idx=self.e_lo.idx, time=self.e_lo.time)
            self.e_hi_pivot_prev = Lvl(px=self.e_hi_pivot.px, idx=self.e_hi_pivot.idx, time=self.e_hi_pivot.time)
            self.e_lo_pivot_prev = Lvl(px=self.e_lo_pivot.px, idx=self.e_lo_pivot.idx, time=self.e_lo_pivot.time)
            self.latest_sealed_high = Lvl(px=self.e_hi.px, idx=self.e_hi.idx, time=self.e_hi.time)
            self.latest_sealed_low = Lvl(px=self.e_lo.px, idx=self.e_lo.idx, time=self.e_lo.time)
            self.bar_highs.clear()
            self.bar_lows.clear()
            self.seed_idx = g_idx

        self.bar_highs[g_idx] = c.high
        self.bar_lows[g_idx] = c.low

        # Snapshot latest sealed before walker kill (break-before-kill, live-smart)
        # Walker may seal a new H/L in this same bar that kills the victim (e.g. 09:44 H 24669.05 kills 09:38 H 24668.7)
        # Live ticks: 09:38 break (hi > tgt) happens before the new H is considered sealed.
        # So chop must be evaluated against prev_latest, then latest updated for next bar.
        _snap_high = self.latest_sealed_high
        _snap_low = self.latest_sealed_low
        # Keep deep copy for chop (Lvl is mutable dataclass)
        if _snap_high is not None:
            _snap_high = Lvl(px=_snap_high.px, idx=_snap_high.idx, time=_snap_high.time)
        if _snap_low is not None:
            _snap_low = Lvl(px=_snap_low.px, idx=_snap_low.idx, time=_snap_low.time)
        self._snap_high = _snap_high
        self._snap_low = _snap_low

        # Flow direction at bar start � the walker leg the bar's seals will
        # terminate. Used by the same-bar V-reversal arm exception (below).
        self._pending_leg_dir = self.walker.dir

        # The walker emits its seals as a batch on the bar they CONFIRM, but each
        # seal carries the idx of the candle the extreme actually belongs to. That
        # is the distinction the arming guard needs and e_hi_pivot cannot provide:
        # by the time the guard runs, e_hi_pivot has already been overwritten by
        # this bar's own batch, so on every seal bar it reads idx == g_idx and the
        # guard concludes nothing older was broken.
        #
        # Tracked per kind, because an up break is answered only by an H seal. The
        # owner's two candles on the same day are identical apart from this:
        #
        #   16:45  batch = H@16:30 (older) + L@16:45 (own low). No H seal of its
        #          own, so the high pivot standing is still the 16:30 one and the
        #          break of it arms. B1 lands there. Correct.
        #
        #   04:30  batch = H@04:00 (older) + L@04:15 (older) + H@04:30 (own high).
        #          It seals its OWN high as well as breaking the 04:00 high, so
        #          e_hi_pivot becomes 21822.4 @ g_idx and the guard refuses - while
        #          21822.4 did break 21814.1, the 04:00 candle's high, which the
        #          owner confirmed by eye: "4:30 clearly breaks this pivot high, and
        #          the B1 is not marked here."
        #
        #   07:00 (2023-02-05)  batch = H@07:00 only, its own high. No older H
        #          seal, so nothing was broken and no B1. "So what is wrong here?
        #          I cannot see the issue." Correct.
        self._seal_h_idx = -1
        self._seal_l_idx = -1

        for p in self.walker.process_bar(c, g_idx):
            if not p.sealed:
                continue
            tgt = self._seal_h_idx if p.kind == "H" else self._seal_l_idx
            if tgt < 0 or p.idx < tgt:
                if p.kind == "H":
                    self._seal_h_idx = p.idx
                else:
                    self._seal_l_idx = p.idx
            if self.bars_seen >= 2:
                if self.defer_same_bar_arm:
                    # Same-bar arm guard: defer to NEXT bar (the V-reversal
                    # exception is applied after the walker loop, below)
                    self._pending_arm = True
                else:
                    self.armed = True
            if p.kind == "H":
                # Any new H kills old H � gap validated at chop-target time, not here
                self.latest_sealed_high = Lvl(px=p.px, idx=p.idx, time=p.time)
                cur = self.e_hi_pivot  # type: ignore
                assert cur is not None
                if p.px > cur.px:
                    self.normal_highs.append(cur)
                    self.e_hi_pivot = Lvl(px=p.px, idx=p.idx, time=p.time)
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
                # Any new L kills old L � gap validated at chop-target time, not here
                self.latest_sealed_low = Lvl(px=p.px, idx=p.idx, time=p.time)
                cur = self.e_lo_pivot  # type: ignore
                assert cur is not None
                if p.px < cur.px:
                    self.normal_lows.append(cur)
                    self.e_lo_pivot = Lvl(px=p.px, idx=p.idx, time=p.time)
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
            # NOTE: no white-pivot rebuild and no latest_sealed overwrite here �
            # latest_sealed_* is updated ONLY at seal time above (lines with
            # "Any new H/L kills old H/L"), exactly like the frontend engine
            # (firstswing_cf11277.ts:198/224). Killed pivots stay dead.

        up_break = c.high > self.e_hi_prev.px
        down_break = c.low < self.e_lo_prev.px
        # Same-bar arm guard with V-reversal exception: a Walker seal arriving
        # THIS bar normally defers arming to the next bar � EXCEPT when the
        # break runs OPPOSITE to the leg the seal terminated (a V reversal off
        # the just-sealed pivot: 2026-09-03 09:27 breaking the sealed 09:26
        # high 23970.15). On the arming bar the SAME-direction break is
        # seed-colour flow extension (red seed: high->low; green seed: low->high)
        # and is suppressed, so B1 locks in the V direction.
        #
        # A same-direction break (2025-09-30 09:44 up-break past the sealed
        # up-leg top) used to stay deferred to the next bar unconditionally,
        # which cost a full candle on every one of them. The suppression was
        # only ever meant for the phantom - breaking a level sealed on THIS
        # bar, which is circular - but the implementation could not tell that
        # apart from breaking a level sealed EARLIER that merely happens to
        # land on a bar where a different seal is arriving. Measured on the
        # real chain, 4,102 breaks were dropped while not armed and 3,941 of
        # them (96%) broke a pivot sealed on an earlier bar.
        #
        # So the same-direction break is accepted whenever the walker sealed, on
        # this bar and of the matching kind, a pivot belonging to an EARLIER
        # candle - which is then a real break of that pivot. Owner-verified on the
        # chart: 2023-01-03 12:45 (seals the 12:30 pivot, crosses it, B1 there),
        # 2023-02-04 15:45, 2023-01-14 06:45, 2026-08-14 22:45, and the pair on
        # 2023-02-13 - 04:30 broken, 16:45 working - which differ only in whether
        # the bar sealed its own extreme as well.
        if self.defer_same_bar_arm and self._pending_arm and self.state == "watch":
            if self._pending_leg_dir == "down" and up_break:
                self.armed = True
                self._pending_arm = False
                down_break = False
            elif self._pending_leg_dir == "up" and down_break:
                self.armed = True
                self._pending_arm = False
                up_break = False
            elif self._pending_leg_dir == "up" and up_break:
                if self._seal_h_idx >= 0 and self._seal_h_idx < g_idx:
                    self.armed = True
                    self._pending_arm = False
            elif self._pending_leg_dir == "down" and down_break:
                if self._seal_l_idx >= 0 and self._seal_l_idx < g_idx:
                    self.armed = True
                    self._pending_arm = False
        if self.armed:
            self._step(down_break, up_break)

        if self.dir == "down" and c.low < self.e_lo.px:
            self._set_cand(Lvl(px=c.low, idx=g_idx, time=self.t))
        if self.dir == "up" and c.high > self.e_hi.px:
            self._set_cand(Lvl(px=c.high, idx=g_idx, time=self.t))

        self._check_sustain(c)

        if c.high > self.e_hi.px:
            self.e_hi = Lvl(px=c.high, idx=g_idx, time=self.t)
        if c.low < self.e_lo.px:
            self.e_lo = Lvl(px=c.low, idx=g_idx, time=self.t)
        self.e_hi_prev = Lvl(px=self.e_hi.px, idx=self.e_hi.idx, time=self.e_hi.time)
        self.e_lo_prev = Lvl(px=self.e_lo.px, idx=self.e_lo.idx, time=self.e_lo.time)
        assert self.e_hi_pivot is not None and self.e_lo_pivot is not None
        self.e_hi_pivot_prev = Lvl(px=self.e_hi_pivot.px, idx=self.e_hi_pivot.idx, time=self.e_hi_pivot.time)
        self.e_lo_pivot_prev = Lvl(px=self.e_lo_pivot.px, idx=self.e_lo_pivot.idx, time=self.e_lo_pivot.time)

        if self.state == "locked":
            self.allow_corner_record = True

    def _step(self, down_break: bool, up_break: bool) -> None:
        if self.state == "watch":
            if down_break:
                self._lock("down")
            elif up_break:
                self._lock("up")
            return
        if self.dir_confirmed:
            if self.dir == "down" and up_break and not down_break:
                # Flip back to a direction that still has a live B1 (never B2d)
                # from a flip-born direction: this break IS that legs B2, not a
                # new flip. (1 Sep 2026 swing 6: B1(up)@11:55 -> FLIP(down)@12:01
                # -> high-extreme break @12:05 was marked FLIP instead of B2.)
                if (
                    self.flip_established
                    and self.ever_b1_dir == "up"
                    and self.e_hi_pivot is not None
                    and self.hi > self.e_hi_pivot.px
                ):
                    self._flip("up", as_b2=True)
                else:
                    self._flip("up")
                self._check_chop()
                return
            if self.dir == "up" and down_break and not up_break:
                if (
                    self.flip_established
                    and self.ever_b1_dir == "down"
                    and self.e_lo_pivot is not None
                    and self.lo < self.e_lo_pivot.px
                ):
                    self._flip("down", as_b2=True)
                else:
                    self._flip("down")
                self._check_chop()
                return
            self._check_chop()
            return
        if self.dir == "down":
            b2_fired = False
            if down_break:
                if (
                    self.e_lo_pivot is not None
                    and self.e_lo_pivot.idx >= self.b1_bar_idx
                    and self.lo < self.e_lo_pivot.px
                ):
                    # B2 1-candle pivot gap (permanent default b2_gap_bars=1)
                    if getattr(self, "b2_gap_bars", 0) > 0:
                        p = self.e_lo_pivot  # type: ignore
                        if p.idx <= self.g_idx - 1 - self.b2_gap_bars:
                            gap_low = self.bar_lows.get(p.idx + 1)
                            if gap_low is not None and gap_low >= p.px:
                                self.b2_pivot = Lvl(px=self.lo, idx=self.g_idx, time=self.t)
                                self._confirm_direction()
                                self._check_chop()
                                b2_fired = True
                    else:
                        self.b2_pivot = Lvl(px=self.lo, idx=self.g_idx, time=self.t)
                        self._confirm_direction()
                        self._check_chop()
                        b2_fired = True
            if up_break and not b2_fired:
                self._flip("up")
                self._check_chop()
        elif self.dir == "up":
            b2_fired = False
            if up_break:
                if (
                    self.e_hi_pivot is not None
                    and self.e_hi_pivot.idx >= self.b1_bar_idx
                    and self.hi > self.e_hi_pivot.px
                ):
                    if getattr(self, "b2_gap_bars", 0) > 0:
                        p = self.e_hi_pivot  # type: ignore
                        if p.idx <= self.g_idx - 1 - self.b2_gap_bars:
                            gap_high = self.bar_highs.get(p.idx + 1)
                            if gap_high is not None and gap_high <= p.px:
                                self.b2_pivot = Lvl(px=self.hi, idx=self.g_idx, time=self.t)
                                self._confirm_direction()
                                self._check_chop()
                                b2_fired = True
                    else:
                        self.b2_pivot = Lvl(px=self.hi, idx=self.g_idx, time=self.t)
                        self._confirm_direction()
                        self._check_chop()
                        b2_fired = True
                    b2_fired = True
            if down_break and not b2_fired:
                self._flip("down")
                self._check_chop()

    def _lock(self, dir: Literal["up", "down"]) -> None:
        self.dir = dir
        self.base_dir = dir
        self.same_side_breaks = 1
        self.corner_pivot = None
        self.b2_pivot = None
        self.b1_bar_idx = self.g_idx
        self.state = "locked"
        self.allow_corner_record = False
        self.ever_b1_dir = dir
        self.flip_established = False
        s = self.e_lo if dir == "up" else self.e_hi
        self.start_idx = s.idx
        self.start_time = s.time
        self.start_px = s.px
        self.locked_level = self.e_hi_prev.px if dir == "up" else self.e_lo_prev.px
        self.break_marks.append(FsBreakMark(idx=self.g_idx, time=self.t, kind="B1", dir=dir, px=self.locked_level))

    def _confirm_direction(self) -> None:
        self.dir_confirmed = True
        self.ever_b1_dir = None  # B1+B2 complete - the leg is done, later flip-backs are genuine FLIPs
        # Chop may only target pivots formed AFTER this bar (fresh structure):
        # a break of a pre-B2 pivot is not the opposing break that completes
        # the leg. (1 Sep 2026 swing 8: B2@13:26, cross of the pre-B2 13:24 low
        # @13:27 marked fs_at mid-swing 8 bars before the 13:35 top.)
        self.dir_established_idx = self.g_idx
        b2 = self.b2_pivot
        self.locked_level = self.e_hi_prev.px if self.dir == "up" else self.e_lo_prev.px
        self.break_marks.append(
            FsBreakMark(
                idx=b2.idx if b2 else self.g_idx,
                time=b2.time if b2 else self.t,
                kind="B2",
                dir=self.dir,  # type: ignore
                px=b2.px if b2 else self.locked_level,
            )
        )
        self.b2_pivot = None
        self.just_fired_b2 = True

    def _flip(self, dir: Literal["up", "down"], as_b2: bool = False) -> None:
        self.dir = dir
        self.base_dir = None
        self.same_side_breaks = 0
        self.corner_pivot = None
        self.b2_pivot = None
        self.b1_bar_idx = -1
        self.allow_corner_record = False
        self.dir_confirmed = True
        self.flip_established = True
        self.dir_established_idx = self.g_idx  # chop may only target pivots formed after this bar
        # The pre-flip direction dies with its confirmation hunt: reset the
        # chop-cross tracking so the NEW direction records its OWN first chop
        # cross (fs_at), and reset the SUS streak so a stale count from the
        # dead leg can never confirm sustain against the new locked_level.
        # (1 Sep 2026: down-leg cross @11:27 survived the 11:28 flip, so the
        # declared up-swing 11:26-11:30 showed no FS mark at its own 11:34 chop.)
        self.first_chop_cross_idx = -1
        self.first_chop_cross_px = float("nan")
        self.first_chop_cross_time = ""
        self.last_chop_cross_idx = -1
        self.last_chop_cross_px = float("nan")
        self.last_chop_cross_time = ""
        self._chop_cross_active = False
        self.last_confirm_hit = None
        self.sustain_streak = 0
        s = self.e_lo if dir == "up" else self.e_hi
        self.start_idx = s.idx
        self.start_time = s.time
        self.start_px = s.px
        self.locked_level = self.e_hi_prev.px if dir == "up" else self.e_lo_prev.px
        # as_b2: same state transition as a flip, but the break is recorded as
        # the live B1 legs B2 (flip-back into a direction whose B1 never got B2).
        self.break_marks.append(FsBreakMark(idx=self.g_idx, time=self.t, kind="B2" if as_b2 else "FLIP", dir=dir, px=self.locked_level))

    def _check_chop(self) -> None:
        if self.just_fired_b2:
            return
        # A cross that opens before the leg has reached minBars is DISCARDED, not
        # parked. The owner, 2026-10-11: "if any FS comes before 50th bar, we look.
        # We neglect it. We just going to neglect it. We will wait 50th bar, and we
        # will be looking new FS after the 50th bar ... if we are just declaring,
        # like FS is there, but it hasn't given the signal of 50th bar, and the 50th
        # bar comes, then we are declaring that there is an FS. So this is wrong,
        # because we have to enter at FS."
        #
        # What the engine did instead: _chop_cross_active was set on any cross, and
        # _confirm() was re-entered on every following bar until bars_seen reached
        # minBars. So a cross that opened at bars_seen 46 or 47 survived untouched
        # and fired the moment bars_seen hit 50 - declaring the swing off an FS the
        # owner had already said to throw away. Measured on the live chain, that
        # happened on 481 of 2952 swings, gaps of 1 to 13 bars.
        #
        # Fix: the cross is only armed if the leg has already reached minBars when
        # it opens. An early cross leaves _chop_cross_active False, so the same
        # pivot is re-tested on every later bar and the cross is armed fresh on the
        # first bar at or after minBars - which is the "new FS after the 50th bar".
        if self.bars_seen < self.min_bars:
            self._chop_cross_active = False
            return
        # Use snapshot of latest sealed before this bar's walker kill (break-before-kill)
        # If a new H/L was sealed in this same bar that kills the victim, chop must still see victim.
        # Snapshot is stored as _snap_high/low in process_bar; if not set, fall back to latest.
        # We access via getattr to stay compatible with direct _check_chop calls (tests).
        if self.dir == "down":
            # Temporarily swap latest for snap for this check
            _orig = self.latest_sealed_high
            _snap = getattr(self, "_snap_high", None)
            if _snap is not None:
                self.latest_sealed_high = _snap
            tgt = self._chop_target_high()
            self.latest_sealed_high = _orig
            if tgt and self.hi > tgt.px:
                if not self._chop_cross_active:
                    # completing break = the TRANSITION into the cross
                    self.last_chop_cross_idx = self.g_idx
                    self.last_chop_cross_px = tgt.px
                    self.last_chop_cross_time = self.t
                self._chop_cross_active = True
                if self.first_chop_cross_idx < 0:
                    self.first_chop_cross_idx = self.g_idx
                    self.first_chop_cross_px = tgt.px
                    self.first_chop_cross_time = self.t
                self.last_confirm_hit = {"pool": "normal", "px": tgt.px, "idx": tgt.idx, "time": tgt.time}
                self._confirm("chop")
            else:
                self._chop_cross_active = False
        elif self.dir == "up":
            _orig_low = self.latest_sealed_low
            _snap_low = getattr(self, "_snap_low", None)
            if _snap_low is not None:
                self.latest_sealed_low = _snap_low
            tgt = self._chop_target_low()
            self.latest_sealed_low = _orig_low
            if tgt and self.lo < tgt.px:
                if not self._chop_cross_active:
                    # completing break = the TRANSITION into the cross
                    self.last_chop_cross_idx = self.g_idx
                    self.last_chop_cross_px = tgt.px
                    self.last_chop_cross_time = self.t
                self._chop_cross_active = True
                if self.first_chop_cross_idx < 0:
                    self.first_chop_cross_idx = self.g_idx
                    self.first_chop_cross_px = tgt.px
                    self.first_chop_cross_time = self.t
                self.last_confirm_hit = {"pool": "normal", "px": tgt.px, "idx": tgt.idx, "time": tgt.time}
                self._confirm("chop")
            else:
                self._chop_cross_active = False

    def _chop_target_high(self) -> Optional[Lvl]:
        # Exact like the frontend engine (firstswing_cf11277.ts chopTargetHigh):
        # the LATEST sealed high pivot ONLY � "any new H kills old H". If it
        # fails a gate there is NO fallback to older pivots; killed pivots are
        # dead and the market has moved on.
        p = self.latest_sealed_high
        if p is None or p.idx < 0 or p.idx > self.g_idx - 2:
            return None
        # Fresh-structure rule (backend addition, 1 Sep 2026 swing-8 fix): the
        # opposing pivot must have FORMED after the current leg was established
        # (B2 or flip) � breaking a pre-existing pivot does not complete the leg.
        if 0 <= self.dir_established_idx and p.idx <= self.dir_established_idx:
            return None
        # Gap rule: next candle after pivot must not breach pivot (1-candle gap)
        gap_high = self.bar_highs.get(p.idx + 1)
        if gap_high is None or gap_high > p.px:
            return None
        return p

    def _chop_target_low(self) -> Optional[Lvl]:
        # Exact like the frontend engine (firstswing_cf11277.ts chopTargetLow):
        # the LATEST sealed low pivot ONLY � "any new L kills old L". No fallback.
        p = self.latest_sealed_low
        if p is None or p.idx < 0 or p.idx > self.g_idx - 2:
            return None
        # Fresh-structure rule (backend addition, 1 Sep 2026 swing-8 fix): see above.
        if 0 <= self.dir_established_idx and p.idx <= self.dir_established_idx:
            return None
        # Gap rule: next candle after pivot must not breach pivot (1-candle gap)
        gap_low = self.bar_lows.get(p.idx + 1)
        if gap_low is None or gap_low < p.px:
            return None
        return p

    def _check_sustain(self, c: FlowCandle) -> None:
        # SUS removed � swing must need FS (chop). Sustain no longer declares FS.
        # Keeps Walker white vs yellow aligned: any tick crossing with gap is FS.
        # Sustained hold without opposite pivot break is no longer a swing.
        return

    def _confirm(self, src: Literal["chop", "sustain"], trig: Optional[dict] = None) -> None:
        if self.t[11:16] < self.time_cap:
            return
        if self.bars_seen < self.min_bars:
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

    def reset(self, seed_px: float, seed_idx: int, seed_time: str) -> None:
        self.walker = WalkerEngine()
        self.bars_seen = 1
        self.t = seed_time
        self.g_idx = seed_idx
        self.hi = float("nan")
        self.lo = float("nan")

        seed = Lvl(px=seed_px, idx=seed_idx, time=seed_time)
        self.e_hi = Lvl(px=seed.px, idx=seed.idx, time=seed.time)
        self.e_lo = Lvl(px=seed.px, idx=seed.idx, time=seed.time)
        self.e_hi_prev = Lvl(px=seed.px, idx=seed.idx, time=seed.time)
        self.e_lo_prev = Lvl(px=seed.px, idx=seed.idx, time=seed.time)
        self.e_hi_pivot = Lvl(px=seed.px, idx=seed.idx, time=seed.time)
        self.e_lo_pivot = Lvl(px=seed.px, idx=seed.idx, time=seed.time)
        self.e_hi_pivot_prev = Lvl(px=seed.px, idx=seed.idx, time=seed.time)
        self.e_lo_pivot_prev = Lvl(px=seed.px, idx=seed.idx, time=seed.time)
        self.latest_sealed_high = Lvl(px=seed.px, idx=seed.idx, time=seed.time)
        self.latest_sealed_low = Lvl(px=seed.px, idx=seed.idx, time=seed.time)
        self.bar_highs.clear()
        self.bar_lows.clear()

        self.normal_highs.clear()
        self.normal_lows.clear()

        self.state = "watch"
        self.dir = None
        self.base_dir = None
        self.same_side_breaks = 0
        self.corner_pivot = None
        self.b2_pivot = None
        self.just_fired_b2 = False
        self.b1_bar_idx = -1
        self.allow_corner_record = False
        self.dir_confirmed = False
        self.locked_level = float("nan")
        self.flip_established = False
        self.ever_b1_dir = None
        self.dir_established_idx = -1

        self.start_idx = -1
        self.start_time = ""
        self.start_px = float("nan")
        self.cand_idx = -1
        self.cand_time = ""
        self.cand_px = float("nan")

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
        self.armed = False
        self._pending_arm = False
        self.first_chop_cross_idx = -1
        self.first_chop_cross_px = float("nan")
        self.first_chop_cross_time = ""
        self.last_chop_cross_idx = -1
        self.last_chop_cross_px = float("nan")
        self.last_chop_cross_time = ""
        self._chop_cross_active = False
        self.break_marks.clear()
        self.ts_map.clear()

    def reset_with_candle(self, c: FlowCandle, g_idx: int) -> None:
        self.walker = WalkerEngine()
        self.bars_seen = 1
        self.t = c.date if len(c.date) >= 16 else ""
        self.g_idx = g_idx
        self.hi = float("nan")
        self.lo = float("nan")

        self.e_hi = Lvl(px=c.high, idx=g_idx, time=self.t)
        self.e_lo = Lvl(px=c.low, idx=g_idx, time=self.t)
        self.e_hi_prev = Lvl(px=self.e_hi.px, idx=self.e_hi.idx, time=self.e_hi.time)
        self.e_lo_prev = Lvl(px=self.e_lo.px, idx=self.e_lo.idx, time=self.e_lo.time)
        self.e_hi_pivot = Lvl(px=self.e_hi.px, idx=self.e_hi.idx, time=self.e_hi.time)
        self.e_lo_pivot = Lvl(px=self.e_lo.px, idx=self.e_lo.idx, time=self.e_lo.time)
        self.e_hi_pivot_prev = Lvl(px=self.e_hi_pivot.px, idx=self.e_hi_pivot.idx, time=self.e_hi_pivot.time)
        self.e_lo_pivot_prev = Lvl(px=self.e_lo_pivot.px, idx=self.e_lo_pivot.idx, time=self.e_lo_pivot.time)
        self.latest_sealed_high = Lvl(px=self.e_hi.px, idx=self.e_hi.idx, time=self.e_hi.time)
        self.latest_sealed_low = Lvl(px=self.e_lo.px, idx=self.e_lo.idx, time=self.e_lo.time)
        self.bar_highs.clear()
        self.bar_lows.clear()

        self.normal_highs.clear()
        self.normal_lows.clear()

        self.state = "watch"
        self.dir = None
        self.base_dir = None
        self.same_side_breaks = 0
        self.corner_pivot = None
        self.b2_pivot = None
        self.just_fired_b2 = False
        self.b1_bar_idx = -1
        self.allow_corner_record = False
        self.dir_confirmed = False
        self.locked_level = float("nan")
        self.flip_established = False
        self.ever_b1_dir = None
        self.dir_established_idx = -1

        self.start_idx = -1
        self.start_time = ""
        self.start_px = float("nan")
        self.cand_idx = -1
        self.cand_time = ""
        self.cand_px = float("nan")

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
        self.armed = False
        self._pending_arm = False
        self.first_chop_cross_idx = -1
        self.first_chop_cross_px = float("nan")
        self.first_chop_cross_time = ""
        self.last_chop_cross_idx = -1
        self.last_chop_cross_px = float("nan")
        self.last_chop_cross_time = ""
        self._chop_cross_active = False
        self.break_marks.clear()
        self.ts_map.clear()


# -- batch helpers ----------------------------------------------------------

def compute_swing_results(
    candles: list[FlowCandle],
    opts: Optional[dict] = None,
    swing_count: Union[int, Literal["whole"]] = 1,
) -> list[dict]:
    """Detect N swings per day across all days.

    Args:
        candles: All candles sorted globally by time.
        opts: Engine options (timeCap, sustainBars, minBars).
        swing_count: Number of swings per day. Use "whole" for all swings.

    Returns:
        List of swing dicts, one per swing, with keys:
            day, swing_index, seg{dir, start_idx, start_px, end_idx, end_px},
            source, dir, kind, break_kind, breaks, confirmed_at_idx, confirmed_at_time,
            fs_at_idx, fs_at_time
    """
    from dataclasses import dataclass as _dc, field as _f
    from typing import Literal as _Lit

    BreakKind = _Lit["B1", "B2", "FLIP"]

    @_dc
    class _Swing:
        day: str
        swing_index: int
        seg: FlowSegment
        source: Optional[_Lit["chop", "sustain"]]
        dir: _Lit["up", "down"]
        kind: str
        break_kind: Optional[BreakKind]
        breaks: list = _f(default_factory=list)
        confirmed_at_idx: int = -1
        confirmed_at_time: str = ""
        fs_at_idx: int = -1
        fs_at_time: str = ""

    _opts: dict = {}
    if opts:
        _opts.update(opts)
    if "minBars" not in _opts and "min_bars" not in _opts:
        _opts["minBars"] = 14
    if "sustainBars" not in _opts and "sustain_bars" not in _opts:
        _opts["sustain_bars"] = 7
    if "timeCap" not in _opts and "time_cap" not in _opts:
        _opts["timeCap"] = "09:29"
    if "b2GapBars" not in _opts and "b2_gap_bars" not in _opts and "requirePivotGap" not in _opts:
        _opts["b2GapBars"] = 1

    by_day: dict[str, list[tuple[int, FlowCandle]]] = {}
    for g_idx, c in enumerate(candles):
        d = c.date[:10]
        by_day.setdefault(d, []).append((g_idx, c))

    out: list[_Swing] = []
    for day, items in by_day.items():
        swing_index = 0
        next_start_pos = 0
        max_swings = 50 if swing_count == "whole" else swing_count

        while swing_index < max_swings:
            eng = SwingEngine(_opts)
            # Swings after the first: same-bar arm guard � a Walker seal arms the
            # engine from the NEXT bar, so a B1 can never fire on the bar the
            # engine first got structure. The first swing keeps the approved
            # FsV2 session-extreme semantics untouched.
            if swing_index > 0:
                eng.defer_same_bar_arm = True
            swing_found = False

            for pos in range(next_start_pos, len(items)):
                g_idx, c = items[pos]
                eng.process_bar(c, g_idx)

                if not eng.declared or eng.start_idx < 0:
                    continue

                src_kind = "SUS" if eng.confirm_source == "sustain" else "FS"
                decisive_break = eng.break_marks[-1] if eng.break_marks else None
                bk: Optional[BreakKind] = decisive_break.kind if decisive_break else None

                _conf_time = ""
                if eng.confirmed_at_idx >= 0:
                    for _gi, _cc in items:
                        if _gi == eng.confirmed_at_idx:
                            _conf_time = _cc.date if len(_cc.date) >= 16 else ""
                            break

                fs_at_idx = eng.confirmed_at_idx
                fs_at_time = _conf_time
                # FS marker = the opposing pivot-break that actually COMPLETED the
                # swing. If the first chop cross happened BEFORE the final extreme
                # (cross was gate-blocked by minBars, swing then extended), that
                # cross is stale - fall back to the bar that actually confirmed.
                if (
                    eng.confirm_source == "chop"
                    and eng.first_chop_cross_idx >= 0
                    and eng.first_chop_cross_idx >= eng.end_idx
                ):
                    fs_at_idx = eng.first_chop_cross_idx
                    fs_at_time = eng.first_chop_cross_time or _conf_time

                out.append(_Swing(
                    day=day,
                    swing_index=swing_index,
                    seg=FlowSegment(
                        dir="B" if eng.dir == "up" else "S",
                        start_idx=eng.start_idx,
                        start_px=eng.start_px,
                        end_idx=eng.end_idx,
                        end_px=eng.end_px,
                    ),
                    source=eng.confirm_source,
                    dir=eng.dir,  # type: ignore
                    kind=src_kind,
                    break_kind=bk,
                    breaks=list(eng.break_marks),
                    confirmed_at_idx=eng.confirmed_at_idx,
                    confirmed_at_time=_conf_time,
                    fs_at_idx=fs_at_idx,
                    fs_at_time=fs_at_time,
                ))
                swing_index += 1

                end_abs = eng.end_idx
                end_pos = -1
                for p, (gi, _cc) in enumerate(items):
                    if gi == end_abs:
                        end_pos = p
                        break
                next_start_pos = end_pos + 1 if end_pos >= 0 else pos + 1
                swing_found = True
                break

            if not swing_found:
                break

    return [
        {
            "day": s.day,
            "swing_index": s.swing_index,
            "seg": {
                "dir": s.seg.dir,
                "start_idx": s.seg.start_idx,
                "start_px": s.seg.start_px,
                "end_idx": s.seg.end_idx,
                "end_px": s.seg.end_px,
            },
            "source": s.source,
            "dir": s.dir,
            "kind": s.kind,
            "break_kind": s.break_kind,
            "breaks": [
                {"idx": b.idx, "time": b.time, "kind": b.kind, "dir": b.dir, "px": b.px}
                for b in s.breaks
            ],
            "confirmed_at_idx": s.confirmed_at_idx,
            "confirmed_at_time": s.confirmed_at_time,
            "fs_at_idx": s.fs_at_idx,
            "fs_at_time": s.fs_at_time,
        }
        for s in out
    ]


# Backward-compat aliases
FirstSwingEngine = SwingEngine
FsV2Engine = SwingEngine
compute_whole_day_swings = lambda candles, opts=None: compute_swing_results(candles, opts, swing_count="whole")
compute_fs_v2_results = lambda candles, opts=None: [
    FsV2Result(
        day=r["day"], outcome="real", conf_idx=r["confirmed_at_idx"],
        seg=FlowSegment(**r["seg"]), source=r["source"], dir=r["dir"],
        breaks=[FsBreakMark(**b) for b in r["breaks"]],
    )
    for r in compute_swing_results(candles, opts, swing_count=1)
]
compute_fs_v2_declared = lambda candles, opts=None: [r.seg for r in compute_fs_v2_results(candles, opts)]
