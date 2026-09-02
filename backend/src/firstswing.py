"""SwingEngine — single source of truth for all swing detection.

Python port of frontend/src/lib/firstswing.ts.
Detects 1 or more swings per day.  Use compute_swing_results() for N swings,
compute_whole_day_swings() for all swings in a day.

- WalkerEngine is SINGLE SOURCE OF TRUTH for sealed pivots
- Break detection per BAR against PREVIOUS bar frozen extremes (eHiPrev/eLoPrev)
- Continuation takes precedence over reversal on same bar
- timeCap gates DECLARATION only, counting runs from bar one
- Immediate 1-bar gap check at seal time prevents micro-pivot noise on chop targets
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
        else:
            self.sustain_bars: int = 7
            self.min_bars: int = 14

        self.walker = WalkerEngine()
        self.bars_seen: int = 0
        self.t: str = "00:00"
        self.g_idx: int = -1
        self.hi: float = float("nan")
        self.lo: float = float("nan")

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
        self.t = c.date[11:16] if len(c.date) >= 16 else ""
        self.hi = c.high
        self.lo = c.low

        self.just_fired_b2 = False

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

        for p in self.walker.process_bar(c, g_idx):
            if not p.sealed:
                continue
            if self.bars_seen >= 2:
                self.armed = True
            if p.kind == "H":
                gap_high = self.bar_highs.get(p.idx + 1)
                if gap_high is None or gap_high <= p.px:
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
                gap_low = self.bar_lows.get(p.idx + 1)
                if gap_low is None or gap_low >= p.px:
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

        up_break = c.high > self.e_hi_prev.px
        down_break = c.low < self.e_lo_prev.px
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
                self._flip("up")
                self._check_chop()
                return
            if self.dir == "up" and down_break and not up_break:
                self._flip("down")
                self._check_chop()
                return
            self._check_chop()
            return
        if self.dir == "down":
            if down_break:
                if (
                    self.e_lo_pivot is not None
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
                    self.e_hi_pivot is not None
                    and self.e_hi_pivot.idx >= self.b1_bar_idx
                    and self.hi > self.e_hi_pivot.px
                ):
                    self.b2_pivot = Lvl(px=self.hi, idx=self.g_idx, time=self.t)
                    self._confirm_direction()
                    self._check_chop()
            elif down_break:
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
        s = self.e_lo if dir == "up" else self.e_hi
        self.start_idx = s.idx
        self.start_time = s.time
        self.start_px = s.px
        self.locked_level = self.e_hi_prev.px if dir == "up" else self.e_lo_prev.px
        self.break_marks.append(FsBreakMark(idx=self.g_idx, time=self.t, kind="B1", dir=dir, px=self.locked_level))

    def _confirm_direction(self) -> None:
        self.dir_confirmed = True
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

    def _flip(self, dir: Literal["up", "down"]) -> None:
        self.dir = dir
        self.base_dir = None
        self.same_side_breaks = 0
        self.corner_pivot = None
        self.b2_pivot = None
        self.b1_bar_idx = -1
        self.allow_corner_record = False
        self.dir_confirmed = True
        # The pre-flip direction dies with its confirmation hunt: reset the
        # chop-cross tracking so the NEW direction records its OWN first chop
        # cross (fs_at), and reset the SUS streak so a stale count from the
        # dead leg can never confirm sustain against the new locked_level.
        # (1 Sep 2026: down-leg cross @11:27 survived the 11:28 flip, so the
        # declared up-swing 11:26-11:30 showed no FS mark at its own 11:34 chop.)
        self.first_chop_cross_idx = -1
        self.first_chop_cross_px = float("nan")
        self.first_chop_cross_time = ""
        self.last_confirm_hit = None
        self.sustain_streak = 0
        s = self.e_lo if dir == "up" else self.e_hi
        self.start_idx = s.idx
        self.start_time = s.time
        self.start_px = s.px
        self.locked_level = self.e_hi_prev.px if dir == "up" else self.e_lo_prev.px
        self.break_marks.append(FsBreakMark(idx=self.g_idx, time=self.t, kind="FLIP", dir=dir, px=self.locked_level))

    def _check_chop(self) -> None:
        if self.just_fired_b2:
            return
        if self.dir == "down":
            tgt = self._chop_target_high()
            if tgt and self.hi > tgt.px:
                if self.first_chop_cross_idx < 0:
                    self.first_chop_cross_idx = self.g_idx
                    self.first_chop_cross_px = tgt.px
                    self.first_chop_cross_time = self.t
                self.last_confirm_hit = {"pool": "normal", "px": tgt.px, "idx": tgt.idx, "time": tgt.time}
                self._confirm("chop")
        elif self.dir == "up":
            tgt = self._chop_target_low()
            if tgt and self.lo < tgt.px:
                if self.first_chop_cross_idx < 0:
                    self.first_chop_cross_idx = self.g_idx
                    self.first_chop_cross_px = tgt.px
                    self.first_chop_cross_time = self.t
                self.last_confirm_hit = {"pool": "normal", "px": tgt.px, "idx": tgt.idx, "time": tgt.time}
                self._confirm("chop")

    def _chop_target_high(self) -> Optional[Lvl]:
        p = self.latest_sealed_high
        if p is not None and p.idx >= 0 and p.idx <= self.g_idx - 2:
            return p
        return None

    def _chop_target_low(self) -> Optional[Lvl]:
        p = self.latest_sealed_low
        if p is not None and p.idx >= 0 and p.idx <= self.g_idx - 2:
            return p
        return None

    def _check_sustain(self, c: FlowCandle) -> None:
        if self.just_fired_b2:
            return
        if not self.dir_confirmed:
            self.sustain_streak = 0
            return
        fresh = (self.dir == "down" and c.low < self.e_lo.px) or (self.dir == "up" and c.high > self.e_hi.px)
        if fresh:
            self.sustain_streak = 0
            return
        ref = self.locked_level
        hold = (self.dir == "down" and c.close > ref) or (self.dir == "up" and c.close < ref)
        self.sustain_streak = self.sustain_streak + 1 if hold else 0
        if self.sustain_streak >= self.sustain_bars:
            self._confirm("sustain")

    def _confirm(self, src: Literal["chop", "sustain"], trig: Optional[dict] = None) -> None:
        if self.t < self.time_cap:
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
        self.first_chop_cross_idx = -1
        self.first_chop_cross_px = float("nan")
        self.first_chop_cross_time = ""
        self.break_marks.clear()

    def reset_with_candle(self, c: FlowCandle, g_idx: int) -> None:
        self.walker = WalkerEngine()
        self.bars_seen = 1
        self.t = c.date[11:16] if len(c.date) >= 16 else ""
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
        self.first_chop_cross_idx = -1
        self.first_chop_cross_px = float("nan")
        self.first_chop_cross_time = ""
        self.break_marks.clear()


# ── batch helpers ──────────────────────────────────────────────────────────

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
                            _conf_time = _cc.date[11:16] if len(_cc.date) >= 16 else ""
                            break

                fs_at_idx = eng.confirmed_at_idx
                fs_at_time = _conf_time
                if eng.confirm_source == "chop" and eng.first_chop_cross_idx >= 0:
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
