"""DISPLAY-ONLY white line: expand the candles the walker swallowed.

Nothing here reaches the engine. `compute_btc_swings` -> `SwingEngine` ->
`walker.WalkerEngine` is untouched, and this module runs `WalkerEngine`
completely unchanged as a read-only input. The only caller is the `flow` key of
the BTC chart route.

THE DEFECT IT FIXES
    `WalkerEngine` loses candles inside an insider stack. Two shapes, both of
    which cost the line a point:

      ONION  - a candle nested strictly inside the pending stack is absorbed;
               the stack records the PREVIOUS layer's `pend.px` / `pend.near`
               rather than this candle's own high/low.
      SWALLOW- a candle that matches neither `confirm_hit` nor `skip_hit` emits
               nothing at all. On 2023-01-08 that is the 07:45 candle: the ONION
               test fails because `c.high 16925.0 < stack_hi 16925.0` is false,
               `_bar_steps` runs, and no branch fires.

    2023-01-08 measured, stock walker:
        07:30 (07:30 in idx terms)  ONION   -> no pivot
        07:45                         SWALLOW -> no pivot
    so the line draws neither 07:30's high, nor 07:45 at all, nor 08:00's high.

THE OWNER'S RULE
    "for green, it is low to high. For red, it would be same candle, high to
     low. [...] So we are going zigzag, zigzag, zigzag."

    "for each insider bar green candle we have to go from low to high, low to
     high."

    A swallowed candle inside a stack DOES show its own two extremes, even when
    it is not strictly nested - 07:45 ties the stack boundary exactly
    (16925.0 against 16925.0) and still counts.

HOW IT IS APPLIED
    1. Run `WalkerEngine` unchanged over the window and keep its raw emissions.
    2. Mark a candle SWALLOWED when a pending insider stack was live at bar
       entry AND that bar emitted zero pivots.

       NOT `skip_steps`: at 07:45 the ONION test fails and `skip_steps` stays
       False, so `_bar_steps` actually runs and still emits nothing. A
       skip_steps rule finds the 1,772 ONION candles and misses all 161
       SWALLOWED ones - including the candle this whole case is about.
    3. Splice `_bar_steps(c)` for those candles only. Everything outside an
       insider stack is left exactly as the walker produced it, which is why the
       line grows by ~3% rather than by 150%.
    4. Sort by (candle index, position within that candle's colour-ordered
       pair) before the zigzag law.

       This is load-bearing. At stack resolution bar 682 emits L@678, H@679 and
       L@680 - indices EARLIER than splice points already emitted for the
       07:30 and 07:45 candles. Alternating in emission order would collapse
       the wrong neighbours.
    5. Apply stock `_dedupe` then stock `_enforce_alternation`, both unmodified.
       No tie-keeping: an equal same-kind neighbour is collapsed, because the
       owner ruled that a flat segment must never be drawn
       ("the lines are going horizontally [...] This cannot happen at all").

    Result on 2023-01-08, 07:00 -> 08:15, eight points ending at the 08:00 low:
       07:00 H 16929.5 | 07:00 L 16911.5 | 07:15 H 16928.0
       07:30 L 16924.0 | 07:30 H 16925.0 | 07:45 L 16924.5
       07:45 H 16925.0 | 08:00 L 16917.0
    against stock's four, which jump 07:15 straight to 08:00.
"""
from __future__ import annotations

from ..walker import AlgoPivot, FlowCandle, WalkerEngine, _bar_steps, _dedupe, _enforce_alternation


def _walk_window(items: list[tuple[int, FlowCandle]]) -> list[AlgoPivot]:
    """Stock walk over one window, with swallowed candles spliced back in.

    `items` is (chart index, candle) so pivot idx stays the CHART index and the
    daily/continuous split cannot shift anything.
    """
    eng = WalkerEngine()
    # (candle index, rank within that candle's colour-ordered pair, order hint,
    #  kind, px). `order hint` is 0 for a spliced point and 1 for a walker
    # emission, so at the same (candle, rank) the spliced point sorts FIRST -
    # see the note after the loop.
    rows: list[tuple[int, int, int, str, float]] = []

    for g_idx, c in items:
        pending_live = eng.pending is not None
        emitted = eng.process_bar(c, g_idx)
        pending_now = eng.pending is not None

        # A SWALLOWED candle had a stack live at entry and emitted nothing.
        # A ROOT is the candle that OPENS the stack (no stack at entry, one at
        # exit). Roots used to be skipped, which is the 2023-02-01 defect: the
        # root's own far side never entered the line, alternation collapsed it
        # against the previous swing high, and the next stack candle then drew
        # from a stale anchor. The owner: "we go from 10:00 low to 10:00 high,
        # then to 10:15 low directly [...] because we cannot go from low to
        # high on a red candle."
        splice = pending_live and not emitted
        opened = (not pending_live) and pending_now
        if splice or opened:
            already = {(int(p.idx), p.kind) for p in emitted}
            for rank, step in enumerate(_bar_steps(c)):
                kind = "H" if step["side"] == "high" else "L"
                if (g_idx, kind) in already:
                    continue      # walker already emits this side of this candle
                rows.append((g_idx, rank, 0, kind, float(step["px"])))

        for p in emitted:
            rows.append((int(p.idx), 0, 1, p.kind, float(p.px)))

    tail = eng.finalize()
    if tail is not None:
        rows.append((int(tail.idx), 0, 1, tail.kind, float(tail.px)))

    # Sorting note. `order hint` is what keeps 2023-01-08 correct once roots are
    # spliced. 07:15 is a root; its low 16911.5 TIES 07:00's low, and the owner
    # ruled that flat runs must never be drawn. With the spliced point ordered
    # ahead, 07:15's low lands beside 07:00's and the stock zigzag drops it as
    # a tie. Ordered behind, it would instead shadow 07:30's low 16924.0 and
    # the walk would lose the 07:30 point the owner confirmed.
    rows.sort(key=lambda r: (r[0], r[1], r[2]))
    pivots = [AlgoPivot(idx=i, time="", kind=k, px=px, sealed=True)
              for i, _rank, _order, k, px in rows]
    return _enforce_alternation(_dedupe(pivots))


def display_pivots(candles: list[FlowCandle], day_mode: str = "continuous") -> list[AlgoPivot]:
    if not candles:
        return []
    if day_mode == "daily":
        by_day: dict[str, list[tuple[int, FlowCandle]]] = {}
        for g_idx, c in enumerate(candles):
            by_day.setdefault(c.date[:10], []).append((g_idx, c))
        out: list[AlgoPivot] = []
        for items in by_day.values():
            out.extend(_walk_window(items))
        return out
    return _walk_window(list(enumerate(candles)))


def display_flow(candles: list[FlowCandle], day_mode: str = "continuous") -> list[dict]:
    """`compute_btc_flow`'s return shape, built from the expanded line."""
    pivots = display_pivots(candles, day_mode)
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