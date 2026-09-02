"""WalkerEngine — Color-aware algo pivot walker.

Port of the WalkerEngine from frontend/src/lib/flowline.ts (lines 76-442).

Rules (course S6 + user spec):
    - GREEN candle path: LOW prints first -> HIGH   (bottom-to-top)
    - RED candle path:   HIGH prints first -> LOW   (top-to-bottom)
    - Each bar processed as TWO half-steps in that order.
    - Active leg tracks a running extreme ("stamp"). Same-direction breaks
      SHIFT the stamp (extended leg = no new pivot). An opposite-side break
      of the PREVIOUS bar's extreme SEALS the stamp as a pivot and flips.
    - INSIDE candle: range within prev bar -> its far-side extreme becomes a
      PENDING pivot. Next bar resolves:
        breaks near side  -> confirm (push pending), leg continues
        breaks far side   -> SKIP insider (discard), seal stamp, flip leg
    - Live-safe: only closed bars consumed; pending resolves on next close.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal, Optional


# ── data types ──────────────────────────────────────────────────────────────

Kind = Literal["H", "L"]
Dir = Literal["up", "down"]


@dataclass
class FlowCandle:
    """Input candle for the walker. `date` is ISO string like '2025-08-28T09:15:00'."""
    date: str
    open: float
    high: float
    low: float
    close: float


@dataclass
class AlgoPivot:
    """A sealed (or trailing) pivot emitted by the walker."""
    idx: int
    time: str  # HH:MM slice
    kind: Kind  # "H" or "L"
    px: float
    sealed: bool  # True = leg flipped after it; False = current forming swing


@dataclass
class WPending:
    """Pending insider stack — far-side extreme + near side, peel buffer."""
    k: int
    kind: Kind
    idx: int
    time: str
    px: float  # far-side extreme (current STACK's far edge)
    near: float  # near-side extreme (current STACK's near edge)
    inner: list[dict] = field(default_factory=list)


# ── helpers ──────────────────────────────────────────────────────────────────

def _bar_steps(c: FlowCandle) -> list[dict]:
    """Return the two half-steps for a bar in path order (low-first for green, high-first for red)."""
    green = c.close >= c.open
    return (
        [{"side": "low", "px": c.low}, {"side": "high", "px": c.high}]
        if green
        else [{"side": "high", "px": c.high}, {"side": "low", "px": c.low}]
    )


def _enforce_alternation(pivots: list[AlgoPivot]) -> list[AlgoPivot]:
    """Zigzag law: same-kind neighbours collapse into the more extreme mark."""
    out: list[AlgoPivot] = []
    for p in pivots:
        last = out[-1] if out else None
        if last and last.kind == p.kind:
            better = p.px > last.px if p.kind == "H" else p.px < last.px
            if better:
                out[-1] = p
            continue
        out.append(p)
    return out


def _dedupe(pivots: list[AlgoPivot]) -> list[AlgoPivot]:
    """Drop exact duplicates (same idx/kind/px)."""
    out: list[AlgoPivot] = []
    for p in pivots:
        last = out[-1] if out else None
        if last and last.idx == p.idx and last.kind == p.kind and last.px == p.px:
            continue
        out.append(p)
    return out


# ── engine ──────────────────────────────────────────────────────────────────

class WalkerEngine:
    """Color-aware candle path follower.

    Contract: feed CLOSED bars via process_bar(); each call returns the pivots
    SEALED during that bar. finalize() emits the trailing open swing.
    """

    def __init__(self) -> None:
        self.k: int = -1
        self.dir: Dir = "up"
        self.stamp_idx: int = -1
        self.stamp_k: int = -1
        self.stamp_t: str = ""
        self.stamp_px: float = math.nan
        self.prev_high: float = math.nan
        self.prev_low: float = math.nan
        # Marker band = px of the most recently PUSHED H pivot and L pivot.
        self.band_low: Optional[float] = None
        self.band_high: Optional[float] = None
        self.pending: Optional[WPending] = None
        # Running extremes since each side's last pushed pivot.
        self.hi_px: Optional[float] = None
        self.hi_idx: int = -1
        self.hi_k: int = -1
        self.hi_t: str = ""
        self.lo_px: Optional[float] = None
        self.lo_idx: int = -1
        self.lo_k: int = -1
        self.lo_t: str = ""
        # Confirm-override: original used items[hiK].close >= items[hiK].open
        # evaluated against the EXTREME BAR itself; we capture that bit when
        # the extreme updates.
        self.hi_close_green: bool = False
        self.lo_close_red: bool = False
        self.bar_out: list[AlgoPivot] = []

    # ── public API ──────────────────────────────────────────────────────────

    def process_bar(self, c: FlowCandle, g_idx: int) -> list[AlgoPivot]:
        """Process one closed bar. Returns the pivots SEALED during this bar."""
        self.bar_out = []
        self.k += 1
        k = self.k
        t = c.date[11:16] if len(c.date) >= 16 else ""

        if k == 0:
            # ---- seed from first bar's colour ----
            first_green = c.close >= c.open
            self._emit(AlgoPivot(idx=g_idx, time=t, kind="L" if first_green else "H",
                                 px=c.low if first_green else c.high, sealed=True))
            self.dir = "up" if first_green else "down"
            self.stamp_idx = g_idx
            self.stamp_k = 0
            self.stamp_t = t
            self.stamp_px = c.high if first_green else c.low
            self.prev_high = c.high
            self.prev_low = c.low
            if first_green:
                self.band_low = c.low
                self.lo_px = None
                self.hi_px = c.high
                self.hi_idx = g_idx
                self.hi_k = 0
                self.hi_t = t
                self.hi_close_green = True
            else:
                self.band_high = c.high
                self.hi_px = None
                self.lo_px = c.low
                self.lo_idx = g_idx
                self.lo_k = 0
                self.lo_t = t
                self.lo_close_red = True
            return self.bar_out

        flipped_this_bar = False
        skip_steps = False

        # ---- pending resolution BEFORE this bar's steps ----
        pend = self.pending
        if pend is not None:
            pk: Kind = pend.kind
            stack_hi = max(pend.px, pend.near)
            stack_lo = min(pend.px, pend.near)

            # ---- ONION RULE: nested insider absorbs into the stack ----
            if c.high < stack_hi and c.low > stack_lo:
                want_far = len(pend.inner) % 2 == 0
                pend.inner.append(
                    {"idx": pend.idx, "k": pend.k, "time": pend.time, "kind": pk, "px": pend.px}
                    if want_far
                    else {"idx": pend.idx, "k": pend.k, "time": pend.time,
                          "kind": "L" if pk == "H" else "H", "px": pend.near}
                )
                self.pending = WPending(
                    kind=pk, idx=g_idx, k=k, time=t,
                    px=c.high if pk == "H" else c.low,
                    near=c.low if pk == "H" else c.high,
                    inner=pend.inner,
                )
                flipped_this_bar = True
                skip_steps = True
            else:
                # STRICT breaks: an exact touch/equal-print does NOT count as a break.
                confirm_hit = c.low < pend.near if pk == "H" else c.high > pend.near
                skip_hit = c.high > pend.px if pk == "H" else c.low < pend.px
                if confirm_hit and not skip_hit:
                    # CONFIRM — seal pre-insider swing; peeled stack emits its
                    # remaining alternating layers (continuation keeps the leg);
                    # a plain single insider prints its far edge (+override).
                    self._push_stamp()
                    p = pend
                    had_peel = len(p.inner) > 0
                    last_rec = self._close_stack(p)
                    if had_peel and last_rec is not None:
                        self.stamp_idx = last_rec["idx"]
                        self.stamp_k = last_rec["k"]
                        self.stamp_t = last_rec["time"]
                        self.stamp_px = last_rec["px"]
                    else:
                        p_idx = p.idx
                        p_t = p.time
                        p_px = p.px
                        p_k = p.k
                        if pk == "H" and self.hi_px is not None and self.hi_px > p_px:
                            hi_after = self.hi_k > self.stamp_k or (self.hi_k == self.stamp_k and self.hi_close_green)
                            if hi_after:
                                p_idx = self.hi_idx
                                p_t = self.hi_t
                                p_px = self.hi_px
                                p_k = self.hi_k
                        if pk == "L" and self.lo_px is not None and self.lo_px < p_px:
                            lo_after = self.lo_k > self.stamp_k or (self.lo_k == self.stamp_k and self.lo_close_red)
                            if lo_after:
                                p_idx = self.lo_idx
                                p_t = self.lo_t
                                p_px = self.lo_px
                                p_k = self.lo_k
                        self._emit(AlgoPivot(idx=p_idx, time=p_t, kind=pk, px=p_px, sealed=True))
                        self._track_band(pk, p_px)
                        self.stamp_idx = p_idx
                        self.stamp_k = p_k
                        self.stamp_t = p_t
                        self.stamp_px = p_px
                    self.pending = None
                elif skip_hit and not confirm_hit:
                    # SINGLE-SIDE far break -> reversal flip
                    p0 = pend
                    self.pending = None
                    self._push_stamp()
                    self._close_stack(p0)
                    self.dir = "up" if pk == "H" else "down"
                    self.stamp_idx = g_idx
                    self.stamp_k = k
                    self.stamp_t = t
                    self.stamp_px = c.high if pk == "H" else c.low
                    flipped_this_bar = True
                    skip_steps = True
                elif skip_hit:
                    # DOUBLE-BREAK (volatile candle) — marker-band decides.
                    i_lo = min(pend.px, pend.near)
                    i_hi = max(pend.px, pend.near)
                    eff_lo = self.stamp_px if self.dir == "down" else (self.band_low if self.band_low is not None else float("-inf"))
                    eff_hi = self.stamp_px if self.dir == "up" else (self.band_high if self.band_high is not None else float("inf"))
                    inside_band = (
                        i_hi <= eff_hi and i_lo >= eff_lo
                        and c.high <= eff_hi and c.low >= eff_lo
                    )
                    if inside_band:
                        # Inside band -> SKIP insider (continuation)
                        self.pending = None
                        self._push_stamp()
                        self.dir = "up" if pk == "H" else "down"
                        self.stamp_idx = g_idx
                        self.stamp_k = k
                        self.stamp_t = t
                        self.stamp_px = c.high if pk == "H" else c.low
                        skip_steps = True
                    else:
                        # Band ESCAPE -> MARK the stack's far-side extreme (mirrored)
                        p = pend
                        self.pending = None
                        self._push_stamp()
                        last_rec = self._close_stack(p)
                        if last_rec is None:
                            self._emit(AlgoPivot(idx=p.idx, time=p.time, kind=pk, px=p.px, sealed=True))
                            self._track_band(pk, p.px)
                        self.dir = "down" if pk == "H" else "up"
                        self.stamp_idx = p.idx
                        self.stamp_k = p.k
                        self.stamp_t = p.time
                        self.stamp_px = p.near
                    flipped_this_bar = True

        for step in ([] if skip_steps else _bar_steps(c)):
            if step["side"] == "low":
                if self.dir == "down":
                    if step["px"] < self.stamp_px:
                        self.stamp_idx = g_idx
                        self.stamp_k = k
                        self.stamp_t = t
                        self.stamp_px = step["px"]
                elif step["px"] < self.prev_low:
                    # up-leg violated -> seal H stamp, flip down
                    self.pending = None
                    self._push_stamp()
                    self.dir = "down"
                    self.stamp_idx = g_idx
                    self.stamp_k = k
                    self.stamp_t = t
                    self.stamp_px = step["px"]
                    flipped_this_bar = True
            else:  # high
                if self.dir == "up":
                    if step["px"] > self.stamp_px:
                        self.stamp_idx = g_idx
                        self.stamp_k = k
                        self.stamp_t = t
                        self.stamp_px = step["px"]
                elif step["px"] > self.prev_high:
                    # down-leg violated -> seal L stamp, flip up
                    self.pending = None
                    self._push_stamp()
                    self.dir = "up"
                    self.stamp_idx = g_idx
                    self.stamp_k = k
                    self.stamp_t = t
                    self.stamp_px = step["px"]
                    flipped_this_bar = True

        # ---- inside-candle detection -> pending far-side extreme ----
        if (
            self.pending is None
            and not flipped_this_bar
            and c.open != c.close
            and c.high <= self.prev_high
            and c.low >= self.prev_low
        ):
            self.pending = WPending(
                kind="H" if self.dir == "down" else "L",
                idx=g_idx, k=k, time=t,
                px=c.high if self.dir == "down" else c.low,
                near=c.low if self.dir == "down" else c.high,
                inner=[],
            )

        _ = flipped_this_bar  # noqa: F841

        # running extremes since each side's last pushed pivot
        if self.hi_px is None or c.high > self.hi_px:
            self.hi_px = c.high
            self.hi_idx = g_idx
            self.hi_k = k
            self.hi_t = t
            self.hi_close_green = c.close >= c.open
        if self.lo_px is None or c.low < self.lo_px:
            self.lo_px = c.low
            self.lo_idx = g_idx
            self.lo_k = k
            self.lo_t = t
            self.lo_close_red = c.close < c.open

        self.prev_high = c.high
        self.prev_low = c.low
        return self.bar_out

    def finalize(self) -> Optional[AlgoPivot]:
        """Trailing open swing (unsealed) — call once after the day ends."""
        if self.k < 0:
            return None
        return AlgoPivot(
            idx=self.stamp_idx, time=self.stamp_t,
            kind="H" if self.dir == "up" else "L",
            px=self.stamp_px, sealed=False,
        )

    # ── private helpers ─────────────────────────────────────────────────────

    def _emit(self, p: AlgoPivot) -> None:
        self.bar_out.append(p)

    def _track_band(self, kind: Kind, px: float) -> None:
        if kind == "H":
            self.band_high = px
            self.hi_px = None
        else:
            self.band_low = px
            self.lo_px = None

    def _push_stamp(self) -> None:
        self._emit(AlgoPivot(
            idx=self.stamp_idx, time=self.stamp_t,
            kind="H" if self.dir == "up" else "L",
            px=self.stamp_px, sealed=True,
        ))
        self._track_band("H" if self.dir == "up" else "L", self.stamp_px)

    def _close_stack(self, p: WPending) -> Optional[dict]:
        """Close a resolved stack: append final alternating layer (only if peeled)
        and flush chronologically. Returns the last flushed record or None."""
        if len(p.inner) == 0:
            return None
        # ROLE-BASED edges: pendPx is ALWAYS far edge, pendNear the near edge.
        want_far = len(p.inner) % 2 == 0
        rec = (
            {"idx": p.idx, "k": p.k, "time": p.time, "kind": p.kind, "px": p.px}
            if want_far
            else {"idx": p.idx, "k": p.k, "time": p.time,
                  "kind": "L" if p.kind == "H" else "H", "px": p.near}
        )
        p.inner.append(rec)
        last: Optional[dict] = None
        while len(p.inner) > 0:
            ip = p.inner.pop(0)
            self._emit(AlgoPivot(idx=ip["idx"], time=ip["time"], kind=ip["kind"],
                                 px=ip["px"], sealed=True))
            self._track_band(ip["kind"], ip["px"])
            last = ip
        return last


# ── batch helpers ───────────────────────────────────────────────────────────

def walk_day(items: list[dict]) -> list[AlgoPivot]:
    """Walk all bars for one day, return all pivots (sealed + trailing)."""
    if not items:
        return []
    eng = WalkerEngine()
    all_pivots: list[AlgoPivot] = []
    for it in items:
        all_pivots.extend(eng.process_bar(it["c"], it["g_idx"]))
    tail = eng.finalize()
    if tail is not None:
        all_pivots.append(tail)
    return _enforce_alternation(_dedupe(all_pivots))


def compute_algo_pivots(candles: list[FlowCandle]) -> list[AlgoPivot]:
    """Compute all algo pivots across all days (one walker per day)."""
    by_day: dict[str, list[dict]] = {}
    for g_idx, c in enumerate(candles):
        d = c.date[:10]
        by_day.setdefault(d, []).append({"c": c, "g_idx": g_idx})
    out: list[AlgoPivot] = []
    for items in by_day.values():
        out.extend(walk_day(items))
    return out


@dataclass
class FlowSegment:
    """Flow-line segment between two pivots."""
    dir: Literal["B", "S"]
    start_idx: int
    start_px: float
    end_idx: int
    end_px: float


def compute_algo_flowline(candles: list[FlowCandle]) -> list[FlowSegment]:
    """Walker flow-line — per-day pivots chained into B/S segments."""
    by_day: dict[str, list[dict]] = {}
    for g_idx, c in enumerate(candles):
        d = c.date[:10]
        by_day.setdefault(d, []).append({"c": c, "g_idx": g_idx})
    segs: list[FlowSegment] = []
    for items in by_day.values():
        pivots = walk_day(items)
        for a, b in zip(pivots, pivots[1:]):
            segs.append(FlowSegment(
                dir="B" if b.px >= a.px else "S",
                start_idx=a.idx, start_px=a.px,
                end_idx=b.idx, end_px=b.px,
            ))
    return segs
