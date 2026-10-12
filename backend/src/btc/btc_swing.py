"""BTC swing chain — real swings with B1/B2/FLIP breaks + FS/SUS labels.

Adaptation of src/firstswing.py::compute_swing_results for 24/7 BTC data:

    - ONE group for the whole window (no per-calendar-day reseed) so the
      swing chain is continuous and swing_index never resets
    - timeCap disabled ("00:00") — BTC has no session open to gate against
    - swing cap scales with the window instead of Nifty's 50/day

SwingEngine + WalkerEngine are imported UNCHANGED — same parity-tested
engines as Nifty. Swings are computed on exactly the candles the caller
passes: the chart's OWN timeframe (15m chart -> 15m swings, 5m -> 5m).
Never a lower timeframe projection.
"""
from __future__ import annotations

from typing import Optional, Union

from src.firstswing import FlowSegment, SwingEngine
from src.walker import AlgoPivot, FlowCandle, WalkerEngine, _dedupe, _enforce_alternation


def compute_btc_swings(
    candles: list[FlowCandle],
    opts: Optional[dict] = None,
    swing_count: Union[int, str] = "whole",
    max_swings: Optional[int] = None,
) -> list[dict]:
    """Continuous swing chain over the given candles (any timeframe).

    Args:
        candles: window candles sorted by time. idx values passed to the
            engine are positions in THIS list (chart logical indices).
        opts: engine opts (minBars, sustainBars/sustain_bars, b2GapBars).
            timeCap is forced to "00:00" (24/7).
        swing_count: "whole" or an int cap per window.
        max_swings: hard safety cap for "whole" mode (default scales with
            the window size).

    Returns:
        Same dict shape as Nifty's compute_swing_results:
            day, swing_index, seg{dir,start_idx,start_px,end_idx,end_px},
            source, dir, kind ("FS"/"SUS"), break_kind ("B1"/"B2"/"FLIP"),
            breaks[{idx,time,kind,dir,px}], confirmed_at_idx/time,
            fs_at_idx, fs_at_time
    """
    if not candles:
        return []

    _opts: dict = dict(opts or {})
    _opts.setdefault("minBars", 14)
    _opts.setdefault("sustainBars", 7)
    _opts.setdefault("b2GapBars", 1)
    _opts["timeCap"] = "00:00"  # 24/7: never gate declarations on session time

    if swing_count == "whole":
        cap = max_swings if max_swings is not None else min(
            1000, max(1, len(candles) // 2)
        )
    else:
        cap = max(1, int(swing_count))

    out: list[dict] = []
    swing_index = 0
    next_start_pos = 0

    # One set for the whole chain: a pivot broken by any mark on any leg is
    # spent for every later leg too. See firstswing._spent_pivots.
    spent_pivots: set = set()

    while swing_index < cap:
        eng = SwingEngine(_opts)
        eng.spent_pivots = spent_pivots
        # Swings after the first: same-bar arm guard (a Walker seal arms the
        # engine from the NEXT bar) — identical to the Nifty batch helper.
        if swing_index > 0:
            eng.defer_same_bar_arm = True
        swing_found = False
        # The bar this leg's warmup counts from. NOT seg.start_idx: that is where
        # the DIRECTION was established, which can be many bars after the engine
        # was constructed, so it is not what minBars counts against. bars_seen
        # starts at 0 on this bar, so the 50th bar is leg_start_idx + min_bars - 1.
        leg_start_pos = None

        for pos in range(next_start_pos, len(candles)):
            c = candles[pos]
            if leg_start_pos is None:
                leg_start_pos = pos
            eng.process_bar(c, pos)  # g_idx == window position (chart logical idx)

            if not eng.declared or eng.start_idx < 0:
                continue

            src_kind = "SUS" if eng.confirm_source == "sustain" else "FS"
            decisive = eng.break_marks[-1] if eng.break_marks else None
            bk = decisive.kind if decisive else None

            conf_time = ""
            if 0 <= eng.confirmed_at_idx < len(candles):
                conf_time = candles[eng.confirmed_at_idx].date

            # FS marker = the opposing pivot-break that COMPLETED the swing.
            # A pre-final-extreme chop cross is stale (gate-blocked by minBars,
            # swing then extended) — fall back to the confirmation bar.
            fs_at_idx = eng.confirmed_at_idx
            fs_at_time = conf_time
            # The completing break = the LATEST chop cross before declaration.
            # The FIRST cross can be stale: gate-blocked before the final
            # extreme, swing then extended (e.g. swing 18-19 Jan 2025: first
            # cross 18:45 at bar 21, leg extended to the 21:15 top, completing
            # cross 01:45 = first ungated bar). confirmed_at_idx stays the
            # legal declaration time (trail arming) - only the marker moves.
            if (
                eng.confirm_source == "chop"
                and eng.last_chop_cross_idx >= 0
                and eng.last_chop_cross_idx >= eng.end_idx
            ):
                fs_at_idx = eng.last_chop_cross_idx
                fs_at_time = (
                    candles[fs_at_idx].date
                    if 0 <= fs_at_idx < len(candles)
                    else conf_time
                )

            out.append(
                {
                    "day": candles[eng.start_idx].date[:10]
                    if 0 <= eng.start_idx < len(candles)
                    else "",
                    "swing_index": swing_index,
                    "seg": {
                        "dir": "B" if eng.dir == "up" else "S",
                        "start_idx": eng.start_idx,
                        "start_px": eng.start_px,
                        "end_idx": eng.end_idx,
                        "end_px": eng.end_px,
                    },
                    "source": eng.confirm_source,
                    "dir": eng.dir,
                    "kind": src_kind,
                    "break_kind": bk,
                    "breaks": [
                        {
                            "idx": b.idx,
                            "time": b.time,
                            "kind": b.kind,
                            "dir": b.dir,
                            "px": b.px,
                        }
                        for b in eng.break_marks
                    ],
                    "confirmed_at_idx": eng.confirmed_at_idx,
                    "confirmed_at_time": conf_time,
                    "fs_at_idx": fs_at_idx,
                    "fs_at_time": fs_at_time,
                    # Owner, 2026-10-12: "I think we should be also marking the
                    # 50th bar so that I can clearly rule it out ... according to
                    # the study that I have chosen on the dropdown, the MB should
                    # be shown." leg_start_idx is the bar minBars counts from,
                    # so min_bars_idx is the first bar on which this leg is
                    # allowed to declare.
                    "leg_start_idx": (leg_start_pos if leg_start_pos is not None
                                      else eng.start_idx),
                    "min_bars": int(_opts.get("minBars", 14)),
                    "min_bars_idx": ((leg_start_pos if leg_start_pos is not None
                                      else eng.start_idx)
                                     + int(_opts.get("minBars", 14)) - 1),
                }
            )
            swing_index += 1

            # Stitch: the next engine starts on the bar AFTER this swing's
            # end extreme (same rule as Nifty's whole-day chain).
            end_abs = eng.end_idx
            end_pos = end_abs if 0 <= end_abs < len(candles) else pos
            next_start_pos = end_pos + 1
            swing_found = True
            break

        if not swing_found:
            break

    return out


def compute_btc_flow(
    candles: list[FlowCandle],
    day_mode: str = "continuous",
) -> list[dict]:
    """Walker flow-line segments (the white path) for the window.

    continuous: ONE walker across the whole window — the path chains across
        midnight (24/7 BTC).
    daily:      walkers re-seed per calendar day (Nifty convention — no line
        ever connects one day's last pivot to the next day's first pivot).

    Returns dicts shaped like the frontend FlowSegment:
        {dir: "B"|"S", startIdx, startPx, endIdx, endPx}
    (idx values are window positions == chart logical indices).
    """

    def _chain(pivots: list[AlgoPivot]) -> list[dict]:
        return [
            {
                "dir": "B" if b.px >= a.px else "S",
                "startIdx": a.idx,
                "startPx": a.px,
                "endIdx": b.idx,
                "endPx": b.px,
            }
            for a, b in zip(pivots, pivots[1:])
        ]

    if day_mode == "daily":
        by_day: dict[str, list[dict]] = {}
        for g_idx, c in enumerate(candles):
            by_day.setdefault(c.date[:10], []).append({"c": c, "g_idx": g_idx})
        segs: list[dict] = []
        for items in by_day.values():
            eng = WalkerEngine()
            pivots: list[AlgoPivot] = []
            for it in items:
                pivots.extend(eng.process_bar(it["c"], it["g_idx"]))
            tail = eng.finalize()
            if tail is not None:
                pivots.append(tail)
            segs.extend(_chain(_enforce_alternation(_dedupe(pivots))))
        return segs

    eng = WalkerEngine()
    pivots_c: list[AlgoPivot] = []
    for g_idx, c in enumerate(candles):
        pivots_c.extend(eng.process_bar(c, g_idx))
    tail = eng.finalize()
    if tail is not None:
        pivots_c.append(tail)
    return _chain(_enforce_alternation(_dedupe(pivots_c)))
