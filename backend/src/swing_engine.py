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


# ── whole-day swing loop ─────────────────────────────────────────────────────
# Uses FirstSwingEngine (correct port of frontend/src/lib/firstswing.ts) so
# swing 0/1 via whole-day exactly match the dedicated first/second-swing
# detection (intraday, StockChart overlays). 1min ONLY, minBars=14 for ALL swings.

def compute_whole_day_swings(candles: list[FlowCandle],
                               opts: Optional[dict] = None) -> list[dict]:
    """Run first-swing detection across ALL days, detecting MULTIPLE swings per day.

    Algorithm (per day) — mirrors frontend/src/lib/flowline.ts::computeSecondSwingResults
    and backend/src/intraday.py::detect_second_swing:
      1. First swing: fresh FirstSwingEngine, feed candles of the day naturally
         (bars_seen==1 init uses 09:15 OHLC, armed gate, etc.).
      2. On declaration: record swing, NEXT swing starts from NEXT candle after
         the declared extreme (prev_end_idx + 1) as new bar 1, fresh engine.
         This matches user's spec: "second swing used from start from the first
         swing end candle's next candle ... so for third swing it goes from
         second swing last candle +1".
      3. Repeat until no more swings or 50 per day cap.
    No forced stitching — each swing's start is the engine's natural start, which
    avoids artificial low->low / high->high forcing that produced "high to high"
    complaints. Frontend draws each swing as its own cyan/yellow segment.

    Only 1min is intended; caller (server / frontend) gates on interval == "1min".
    minBars=14 is enforced for every swing (user confirmed).

    Returns list of dicts with keys:
        day, swing_index, seg{start_idx/start_px/end_idx/end_px/dir},
        source, dir, kind, break_kind
    """
    from dataclasses import dataclass
    from typing import Literal as _Lit

    # Import here to avoid circular import at module load; FirstSwingEngine is
    # the SINGLE SOURCE OF TRUTH for swing detection (frontend + intraday).
    try:
        from .firstswing import FirstSwingEngine as _FSE  # type: ignore
    except Exception:
        # Fallback to legacy engine if firstswing unavailable (should not happen)
        _FSE = FsV2Engine  # type: ignore

    Dir = _Lit["up", "down"]

    @dataclass
    class WholeDaySwing:
        day: str
        swing_index: int
        seg: FlowSegment
        source: Optional[_Lit["chop", "sustain"]]
        dir: Dir
        kind: str   # "SUS" or "FS"
        break_kind: Optional[BreakKind]  # "B1"/"B2"/"FLIP" or None
        breaks: list = field(default_factory=list)  # full ordered FsBreakMark list
        confirmed_at_idx: int = -1
        confirmed_at_time: str = ""
        # The swing's true structural completion bar (the first bar where its
        # own high/low pivot was taken out). For chop swings this is where FS/SUS
        # should be marked — not the minBars-delayed declaration bar. e.g. a down
        # swing is complete the instant its high pivot breaks (31-Aug 11:11 high
        # 24001.7 broken at 11:14 -> FS@11:14, not 11:15).
        fs_at_idx: int = -1
        fs_at_time: str = ""

    # Normalise opts: ensure sustain_bars + min_bars + timeCap propagate correctly
    # FirstSwingEngine understands both sustainBars/sustain_bars and minBars/min_bars
    _opts: dict = {}
    if opts:
        _opts.update(opts)
    # Enforce 1min-only whole-day: minBars 14 for ALL swings (user confirmed)
    if "minBars" not in _opts and "min_bars" not in _opts:
        _opts["minBars"] = 14
    if "sustainBars" not in _opts and "sustain_bars" not in _opts:
        _opts["sustain_bars"] = 7
    # Keep timeCap 09:29 for first swing; later swings are naturally after cap anyway.
    # If caller wants to override, they can pass timeCap explicitly.
    if "timeCap" not in _opts and "time_cap" not in _opts:
        _opts["timeCap"] = "09:29"

    by_day: dict[str, list[tuple[int, FlowCandle]]] = {}
    for g_idx, c in enumerate(candles):
        d = c.date[:10]
        by_day.setdefault(d, []).append((g_idx, c))

    out: list[WholeDaySwing] = []
    for day, items in by_day.items():
        swing_index = 0
        # Position in items[] where the NEXT swing starts.
        # Mirrors frontend/src/lib/flowline.ts::computeSecondSwingResults and
        # backend/src/intraday.py::detect_second_swing:
        #   seedIdx = prev_end_idx + 1  (next candle after previous extreme)
        #   fresh FirstSwingEngine fed from seedIdx inclusive as bar 1 (no reset_with_candle).
        # This matches user's spec: "second swing used from start from the first swing
        # end candle's next candle not from the first swing end candle itself ... so for
        # third swing it goes from second swing last candle +1"
        next_start_pos = 0

        while True:
            if swing_index >= 50:  # safety cap per day
                break

            eng = _FSE(_opts)  # type: ignore

            swing_found_this_iter = False
            # Feed remaining bars of the day starting at next_start_pos
            for pos in range(next_start_pos, len(items)):
                g_idx, c = items[pos]
                eng.process_bar(c, g_idx)

                # Check declaration after each bar (both engines expose declared/start_idx)
                # For FirstSwingEngine: eng.declared + eng.start_idx >=0
                # For FsV2Engine: same via get_result, but we check directly for speed.
                is_declared = bool(getattr(eng, "declared", False))
                has_start = getattr(eng, "start_idx", -1) >= 0 or getattr(eng, "startIdx", -1) >= 0
                # Unified getter for end/start fields (handle both engines)
                # Try FirstSwingEngine shape first
                if is_declared and has_start:
                    # Pull fields in engine-agnostic way
                    if hasattr(eng, "end_idx"):
                        end_idx = eng.end_idx  # FsV2 / FirstSwing common? FirstSwing uses endIdx
                        # FirstSwingEngine uses endIdx, FsV2 uses end_idx
                        if end_idx == -1 and hasattr(eng, "endIdx"):
                            end_idx = eng.endIdx  # type: ignore
                    elif hasattr(eng, "endIdx"):
                        end_idx = eng.endIdx  # type: ignore
                    else:
                        end_idx = -1

                    # If not yet declared with end, try get_result helper (FsV2)
                    # For FirstSwing we already know declared; we can build result manually
                    # Use engine-specific extraction below instead of early break
                    pass

                # Prefer official get_result for FsV2Engine; for FirstSwingEngine we
                # check declared flag directly and synthesize result. Unified:
                result_seg = None
                result_dir = None
                result_source = None
                result_breaks = []
                result_conf_idx = -1

                if hasattr(eng, "get_result"):
                    # FsV2Engine path (legacy) — also works if _FSE == FirstSwing then no get_result
                    try:
                        r = eng.get_result(day)  # type: ignore
                        if r is not None:
                            result_seg = r.seg
                            result_dir = r.dir
                            result_source = r.source
                            result_breaks = r.breaks
                            result_conf_idx = r.conf_idx
                    except Exception:
                        pass
                else:
                    # FirstSwingEngine path
                    if getattr(eng, "declared", False) and getattr(eng, "start_idx", -1) >= 0:
                        # FirstSwing uses start_idx/start_px/end_idx/end_px etc.
                        # Also has dir, confirm_source, break_marks
                        try:
                            # Access FirstSwing fields (see firstswing.py)
                            s_idx = eng.start_idx  # type: ignore
                            s_px = eng.start_px  # type: ignore
                            e_idx = eng.end_idx  # type: ignore
                            e_px = eng.end_px  # type: ignore
                            # Fallback for camelCase (frontend port leftover)
                            if s_idx == -1 and hasattr(eng, "startIdx"):
                                s_idx = eng.startIdx  # type: ignore
                                s_px = eng.startPx  # type: ignore
                                e_idx = eng.endIdx  # type: ignore
                                e_px = eng.endPx  # type: ignore
                            if s_idx >= 0 and e_idx >= 0:
                                result_seg = FlowSegment(
                                    dir="B" if eng.dir == "up" else "S",  # type: ignore
                                    start_idx=s_idx,
                                    start_px=s_px,
                                    end_idx=e_idx,
                                    end_px=e_px,
                                )
                                result_dir = eng.dir  # type: ignore
                                result_source = eng.confirm_source  # type: ignore
                                result_breaks = getattr(eng, "break_marks", [])  # type: ignore
                                result_conf_idx = getattr(eng, "confirmed_at_idx", g_idx)  # type: ignore
                        except Exception:
                            pass

                if result_seg is not None:
                    # Derive label: sustain→"SUS", chop/null→"FS"
                    src_kind = "SUS" if result_source == "sustain" else "FS"
                    # Use the decisive break (last) — B2 for continuation, FLIP for reversal.
                    # First break is always B1; the last reveals whether it was B2 or FLIP.
                    decisive_break = result_breaks[-1] if result_breaks else None
                    bk: Optional[BreakKind] = None
                    if decisive_break is not None:
                        try:
                            bk = decisive_break.kind  # type: ignore
                        except Exception:
                            bk = None

                    # Derive confirmation time from the candle at confirmed_at_idx
                    _conf_time = ""
                    if result_conf_idx >= 0:
                        for _gi, _cc in items:
                            if _gi == result_conf_idx:
                                _conf_time = _cc.date[11:16] if len(_cc.date) >= 16 else ""
                                break

                    # FS/SUS marker position = the swing's OWN structural completion bar: the
                    # first bar >= the swing's end extreme where its opposing pivot
                    # was taken out (the chop cross). Declaration may be delayed by
                    # minBars, so this keeps the FS marker at the true completion bar
                    # (e.g. 31-Aug swing 2: the 11:11 high 24001.7 is broken at 11:14
                    # -> FS@11:14, NOT 11:15). A chop-cross that happens BEFORE the
                    # swing's extreme (mid-rally pullback break) is not a completion,
                    # so it is ignored — sustain swings keep the confirmed bar.
                    fs_at_idx = result_conf_idx
                    fs_at_time = _conf_time
                    if result_source == "chop" and getattr(eng, "first_chop_cross_idx", -1) >= 0:
                        _cx = int(getattr(eng, "first_chop_cross_idx", -1))
                        if _cx >= result_seg.end_idx:
                            fs_at_idx = _cx
                            fs_at_time = getattr(eng, "first_chop_cross_time", "") or _conf_time

                    out.append(WholeDaySwing(
                        day=day,
                        swing_index=swing_index,
                        seg=result_seg,
                        source=result_source,  # type: ignore
                        dir=result_dir,  # type: ignore
                        kind=src_kind,
                        break_kind=bk,
                        breaks=result_breaks,
                        confirmed_at_idx=result_conf_idx,
                        confirmed_at_time=_conf_time,
                        fs_at_idx=fs_at_idx,
                        fs_at_time=fs_at_time,
                    ))
                    swing_index += 1

                    # Seed NEXT swing at this swing's END extreme bar (not confirmation bar)
                    end_abs = result_seg.end_idx
                    # Find end candle object + its position in items[]
                    end_pos = -1
                    end_c: Optional[FlowCandle] = None
                    for p, (gi, cc) in enumerate(items):
                        if gi == end_abs:
                            end_pos = p
                            end_c = cc
                            break
                    if end_c is None:
                        # Fallback: synthesize candle at end_px if not found (should not happen)
                        # Use current c as fallback
                        end_c = c
                        end_pos = pos

                    # NEXT swing starts from the bar AFTER this swing's extreme
                    # (mirrors computeSecondSwingResults: seedIdx = endIdx+1, fresh engine)
                    next_start_pos = end_pos + 1 if end_pos >= 0 else pos + 1

                    swing_found_this_iter = True
                    break

            if not swing_found_this_iter:
                break

    # No forced stitching — each swing is independent, starting at next candle after
    # previous extreme (gap of 1 bar). This matches second-swing spec and avoids
    # artificial low->low / high->high forcing that produced "high to high" zigzag
    # complaints. The frontend draws each swing as its own segment (cyan/yellow).

    # Convert to dict for JSON serialization
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


# Alias for backward compatibility — now points to correct FirstSwingEngine (port of frontend/src/lib/firstswing.ts)
# The old FsV2Engine (flowline.ts port) is kept as LegacyFsV2Engine for any direct legacy usage.
try:
    from .firstswing import FirstSwingEngine as _CorrectFSE  # type: ignore
    FirstSwingEngine = _CorrectFSE  # type: ignore
    LegacyFsV2Engine = FsV2Engine
except Exception:
    FirstSwingEngine = FsV2Engine  # fallback if firstswing not available
    LegacyFsV2Engine = FsV2Engine
