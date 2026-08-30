"""FirstSwingEngine — Python port of frontend/src/lib/firstswing.ts

Exact logic mirror for 1-min first & second swing detection.
- WalkerEngine is SINGLE SOURCE OF TRUTH for sealed pivots
- Break detection per BAR against PREVIOUS bar frozen extremes (eHiPrev/eLoPrev)
- Continuation takes precedence over reversal on same bar
- timeCap gates DECLARATION only, counting runs from bar one
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal, Optional

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


class FirstSwingEngine:
    def __init__(self, opts: Optional[dict] = None):
        opts = opts or {}
        self.time_cap: str = opts.get("timeCap", "09:29") if isinstance(opts, dict) else getattr(opts, "timeCap", "09:29")
        # sustainBars may be passed as sustainBars or sustain_bars
        if isinstance(opts, dict):
            self.sustain_bars: int = opts.get("sustainBars", opts.get("sustain_bars", 7))
        else:
            self.sustain_bars: int = 7

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
            self.seed_idx = g_idx

        # 1) Consume walker seals
        for p in self.walker.process_bar(c, g_idx):
            if not p.sealed:
                continue
            if self.bars_seen >= 2:
                self.armed = True
            if p.kind == "H":
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
            else:  # L
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

        # 3) Direction / break step — per BAR, against FROZEN extremes
        up_break = c.high > self.e_hi_prev.px
        down_break = c.low < self.e_lo_prev.px
        if self.armed:
            self._step(down_break, up_break)

        # 4) Keep candidate end glued to actual bar extreme
        if self.dir == "down" and c.low <= self.e_lo.px:
            self._set_cand(Lvl(px=c.low, idx=g_idx, time=self.t))
        if self.dir == "up" and c.high >= self.e_hi.px:
            self._set_cand(Lvl(px=c.high, idx=g_idx, time=self.t))

        # 5) Sustain check
        self._check_sustain(c)

        # 6) Advance frozen extremes
        if c.high > self.e_hi.px:
            self.e_hi = Lvl(px=c.high, idx=g_idx, time=self.t)
        if c.low < self.e_lo.px:
            self.e_lo = Lvl(px=c.low, idx=g_idx, time=self.t)
        self.e_hi_prev = Lvl(px=self.e_hi.px, idx=self.e_hi.idx, time=self.e_hi.time)
        self.e_lo_prev = Lvl(px=self.e_lo.px, idx=self.e_lo.idx, time=self.e_lo.time)
        # Walker extreme-pivot levels as of THIS bar become next bar's reference.
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
        # LOCKED, direction not yet confirmed
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
            tgt = self._latest_pivot(self.normal_highs)
            if tgt and self.hi > tgt.px:
                self.last_confirm_hit = {"pool": "normal", "px": tgt.px, "idx": tgt.idx, "time": tgt.time}
                self._confirm("chop")
        elif self.dir == "up":
            tgt = self._latest_pivot(self.normal_lows)
            if tgt and self.lo < tgt.px:
                self.last_confirm_hit = {"pool": "normal", "px": tgt.px, "idx": tgt.idx, "time": tgt.time}
                self._confirm("chop")

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

    def reset(self, seed_px: float, seed_idx: int, seed_time: str) -> None:
        """Re-initialize to detect a new swing starting from a pre-defined price level (e.g., first swing's extreme)."""
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
        self.break_marks.clear()

    def reset_with_candle(self, c: FlowCandle, g_idx: int) -> None:
        """True mirror of first-swing init: seed with actual OHLC of the cyan candle.

        This is what the user asked: “take ohlc value from 9:27 and run it though
        first swing engine”. After this, the next bar (09:28) is barsSeen=2 and must
        break the 09:27 low/high to lock — B1@09:28 breaking 24148.65.
        """
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
        self.break_marks.clear()


def compute_fs_v2_results(candles: list[FlowCandle], opts: Optional[dict] = None) -> list[FsV2Result]:
    by_day: dict[str, list[tuple[int, FlowCandle]]] = {}
    for g_idx, c in enumerate(candles):
        d = c.date[:10]
        by_day.setdefault(d, []).append((g_idx, c))
    out: list[FsV2Result] = []
    for day, items in by_day.items():
        eng = FirstSwingEngine(opts)
        for g_idx, c in items:
            eng.process_bar(c, g_idx)
        if not eng.declared or eng.start_idx < 0:
            continue
        out.append(
            FsV2Result(
                day=day,
                outcome="real",
                conf_idx=eng.confirmed_at_idx,
                seg=FlowSegment(
                    dir="B" if eng.dir == "up" else "S",
                    start_idx=eng.start_idx,
                    start_px=eng.start_px,
                    end_idx=eng.end_idx,
                    end_px=eng.end_px,
                ),
                source=eng.confirm_source,
                dir=eng.dir,
                breaks=eng.break_marks,
            )
        )
    return out


def compute_fs_v2_declared(candles: list[FlowCandle], opts: Optional[dict] = None) -> list[FlowSegment]:
    return [r.seg for r in compute_fs_v2_results(candles, opts)]


# Alias for backward compatibility — now points to the correct FirstSwingEngine
FsV2Engine = FirstSwingEngine
