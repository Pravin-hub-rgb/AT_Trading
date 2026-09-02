"""Envelope Law validator — port of frontend/src/lib/envelope.ts.

For every day, walk the algo pivot chain and flag candles that breach the
marked extreme before the opposite kind prints:
  after an L marker until the next H, no candle low < L.px
  after an H marker until the next L, no candle high > H.px
Same-candle pairs are exempt. Atomic-candle: marker bar itself is one swing
unit, so checks start at a.idx + 1.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .walker import FlowCandle, walk_day

EPS = 1e-6


@dataclass
class EnvelopeViolation:
    idx: int  # global index of violating candle
    side: Literal["high", "low"]
    px: float
    markerIdx: int  # global index of violated marker's bar
    markerTime: str  # HH:MM of marker
    markerKind: Literal["H", "L"]
    markerPx: float
    day: str  # YYYY-MM-DD


def compute_envelope_violations(candles: list[FlowCandle]) -> list[EnvelopeViolation]:
    if not candles:
        return []

    # per-day grouping — identical to compute_algo_pivots
    by_day: dict[str, list[dict]] = {}
    for g_idx, c in enumerate(candles):
        d = c.date[:10]
        by_day.setdefault(d, []).append({"c": c, "g_idx": g_idx})

    out: list[EnvelopeViolation] = []
    for day_key, items in by_day.items():
        # walk_day returns pivots with idx as g_idx within items slice order
        # items is list of {"c": FlowCandle, "g_idx": global_idx}
        pivots = walk_day(items)
        # pivots idx are global g_idx already (since walk_day uses items[].g_idx)
        # But walk_day's internal walk uses items order, so pivots idx are global.
        # For envelope we need to scan candles between a and b.
        # Use global indices to find positions in items.
        # Build map global idx -> position in items
        pos_by_gidx = {it["g_idx"]: pos for pos, it in enumerate(items)}
        for i in range(len(pivots) - 1):
            a = pivots[i]
            b = pivots[i + 1]
            if a.idx == b.idx or a.kind == b.kind:
                continue
            # find positions of a and b in items
            a_pos = pos_by_gidx.get(a.idx)
            b_pos = pos_by_gidx.get(b.idx)
            if a_pos is None or b_pos is None:
                continue
            # scan from a.idx+1 to max(a.idx, b.idx) in terms of positions
            # a.idx+1 in the frontend means slice index +1, not global. Use positions.
            for pos in range(a_pos + 1, max(a_pos, b_pos) + 1):
                if pos >= len(items):
                    break
                cd = items[pos]["c"]
                g_idx = items[pos]["g_idx"]
                # marker's global idx is b.idx
                marker_gidx = b.idx
                if b.kind == "H" and cd.high > b.px + EPS:
                    out.append(EnvelopeViolation(
                        idx=g_idx, side="high", px=cd.high,
                        markerIdx=marker_gidx, markerTime=b.time,
                        markerKind="H", markerPx=b.px, day=day_key,
                    ))
                    break
                if b.kind == "L" and cd.low < b.px - EPS:
                    out.append(EnvelopeViolation(
                        idx=g_idx, side="low", px=cd.low,
                        markerIdx=marker_gidx, markerTime=b.time,
                        markerKind="L", markerPx=b.px, day=day_key,
                    ))
                    break
    return out
